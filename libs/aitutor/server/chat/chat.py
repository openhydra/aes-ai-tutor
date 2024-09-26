import asyncio
import json
import uuid
from typing import AsyncIterable, List

from fastapi import Body
from langchain.chains import ConversationChain
from langchain.prompts.chat import ChatPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain_core.messages import convert_to_messages
from sse_starlette.sse import EventSourceResponse

from aitutor.server.api_server.api_schemas import OpenAIChatOutput
from aitutor.server.callback_handler.agent_callback_handler import (
    AgentExecutorAsyncIteratorCallbackHandler,
    AgentStatus,
)
from aitutor.server.callback_handler.conversation_callback_handler import (
    ConversationCallbackHandler,
)
from aitutor.server.chat.utils import History
from aitutor.server.memory.conversation_db_buffer_memory import (
    ConversationBufferDBMemory,
)
from aitutor.server.utils import (
    MsgType,
    build_logger,
    get_ChatOpenAI,
    get_default_llm,
    get_prompt_template,
    get_tool,
    wrap_done,
)
from aitutor.settings import Settings

logger = build_logger()


def create_models_from_config(configs, callbacks, stream, max_tokens):
    configs = configs or Settings.model_settings.LLM_MODEL_CONFIG
    models = {}
    prompts = {}
    for model_type, params in configs.items():
        model_name = params.get("model", "").strip() or get_default_llm()
        callbacks = callbacks if params.get("callbacks", False) else None
        # 判断是否传入 max_tokens 的值, 如果传入就按传入的赋值(api 调用且赋值), 如果没有传入则按照初始化配置赋值(ui 调用或 api 调用未赋值)
        max_tokens_value = (
            max_tokens if max_tokens is not None else params.get("max_tokens", 1000)
        )
        model_instance = get_ChatOpenAI(
            model_name=model_name,
            temperature=params.get("temperature", 0.5),
            max_tokens=max_tokens_value,
            callbacks=callbacks,
            streaming=stream,
            local_wrap=False,
        )
        models[model_type] = model_instance
        prompt_name = params.get("prompt_name", "default")
        prompt_template = get_prompt_template(type=model_type, name=prompt_name)
        prompts[model_type] = prompt_template
    return models, prompts


def create_models_chains(
    history, history_len, prompts, models, tools, callbacks, conversation_id, metadata
):
    memory = None
    chat_prompt = None

    if history and conversation_id:
        chat_prompt = PromptTemplate.from_template(
                Settings.prompt_settings.llm_model["with_history"], template_format="jinja2"
            )
        memory = ConversationBufferDBMemory(
            conversation_id=conversation_id,
            llm=models["llm_model"],
            message_limit=history_len,
        )
    else:
        input_msg = History(role="user", content=prompts["llm_model"]).to_msg_template(
            False
        )
        chat_prompt = ChatPromptTemplate.from_messages([input_msg])

    if "action_model" in models and tools:
        llm = models["action_model"]
    else:
        llm = models["llm_model"]
        llm.callbacks = callbacks
        chain = ConversationChain(prompt=chat_prompt, llm=llm, memory=memory)
        full_chain = {"input": lambda x: x["input"]} | chain
    return full_chain


async def chat(
    query: str = Body(..., description="用户输入", examples=["恼羞成怒"]),
    metadata: dict = Body({}, description="附件，可能是图像或者其他功能", examples=[]),
    conversation_id: str = Body("", description="对话框ID"),
    message_id: str = Body(None, description="数据库消息ID"),
    history_len: int = Body(-1, description="从数据库中取历史消息的数量"),
    history: List[History] = Body(
        [],
        description="历史对话，设为一个整数可以从数据库中读取历史消息",
        examples=[
            [
                {"role": "user", "content": "我们来玩成语接龙，我先来，生龙活虎"},
                {"role": "assistant", "content": "虎头虎脑"},
            ]
        ],
    ),
    stream: bool = Body(True, description="流式输出"),
    chat_model_config: dict = Body({}, description="LLM 模型配置", examples=[]),
    tool_config: dict = Body({}, description="工具配置", examples=[]),
    max_tokens: int = Body(None, description="LLM最大token数配置", example=4096),
):
    """Agent 对话"""

    async def chat_iterator() -> AsyncIterable[OpenAIChatOutput]:
        try:
            callback = AgentExecutorAsyncIteratorCallbackHandler()
            callbacks = [callback]
            conversation_callback = ConversationCallbackHandler(
                conversation_id=conversation_id,
                message_id=message_id,
                chat_type="llm_chat",
                query=query,
            )
            callbacks.append(conversation_callback)

            models, prompts = create_models_from_config(
                callbacks=callbacks,
                configs=chat_model_config,
                stream=stream,
                max_tokens=max_tokens,
            )
            all_tools = get_tool().values()
            tools = [tool for tool in all_tools if tool.name in tool_config]
            tools = [t.copy(update={"callbacks": callbacks}) for t in tools]
            full_chain = create_models_chains(
                prompts=prompts,
                models=models,
                conversation_id=conversation_id,
                tools=tools,
                callbacks=callbacks,
                history=history,
                history_len=history_len,
                metadata=metadata,
            )


            task = asyncio.create_task(
                wrap_done(
                    full_chain.ainvoke(
                        {
                            "input": query,
                        }
                    ),
                    callback.done,
                )
            )

            last_tool = {}
            async for chunk in callback.aiter():
                data = json.loads(chunk)
                data["tool_calls"] = []
                data["message_type"] = MsgType.TEXT

                if data["status"] == AgentStatus.tool_start:
                    last_tool = {
                        "index": 0,
                        "id": data["run_id"],
                        "type": "function",
                        "function": {
                            "name": data["tool"],
                            "arguments": data["tool_input"],
                        },
                        "tool_output": None,
                        "is_error": False,
                    }
                    data["tool_calls"].append(last_tool)
                if data["status"] in [AgentStatus.tool_end]:
                    last_tool.update(
                        tool_output=data["tool_output"],
                        is_error=data.get("is_error", False),
                    )
                    data["tool_calls"] = [last_tool]
                    last_tool = {}
                    try:
                        tool_output = json.loads(data["tool_output"])
                        if message_type := tool_output.get("message_type"):
                            data["message_type"] = message_type
                    except:
                        ...
                elif data["status"] == AgentStatus.agent_finish:
                    try:
                        tool_output = json.loads(data["text"])
                        if message_type := tool_output.get("message_type"):
                            data["message_type"] = message_type
                    except:
                        ...

                if data["status"] == AgentStatus.llm_end:
                    break

                ret = OpenAIChatOutput(
                    id=f"chat{uuid.uuid4()}",
                    object="chat.completion.chunk",
                    content=data.get("text", ""),
                    role="assistant",
                    tool_calls=data["tool_calls"],
                    model=models["llm_model"].model_name,
                    status=data["status"],
                    message_type=data["message_type"],
                    message_id=message_id,
                )
                yield ret.model_dump_json()
            await task
        except asyncio.exceptions.CancelledError:
            logger.warning("streaming progress has been interrupted by user.")
            return
        except Exception as e:
            logger.error(f"error in chat: {e}")
            yield {"data": json.dumps({"error": str(e)})}
            return

    if stream:
        return EventSourceResponse(chat_iterator())
    else:
        ret = OpenAIChatOutput(
            id=f"chat{uuid.uuid4()}",
            object="chat.completion",
            content="",
            role="assistant",
            finish_reason="stop",
            tool_calls=[],
            status=AgentStatus.agent_finish,
            message_type=MsgType.TEXT,
            message_id=message_id,
        )

        async for chunk in chat_iterator():
            data = json.loads(chunk)
            if text := data["choices"][0]["delta"]["content"]:
                ret.content += text
            if data["status"] == AgentStatus.tool_end:
                ret.tool_calls += data["choices"][0]["delta"]["tool_calls"]
            ret.model = data["model"]
            ret.created = data["created"]

        return ret.model_dump()
