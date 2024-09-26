from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncIterable, List, Literal, Optional

from fastapi import Body, Request
from fastapi.concurrency import run_in_threadpool
from langchain.chains import LLMChain
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.prompts.chat import ChatPromptTemplate
from sse_starlette.sse import EventSourceResponse

from aitutor.server.agent.tools_factory.search_internet import search_engine
from aitutor.server.api_server.api_schemas import OpenAIChatOutput
from aitutor.server.callback_handler.conversation_callback_handler import (
    ConversationCallbackHandler,
)
from aitutor.server.chat.utils import History
from aitutor.server.knowledge_base.kb_doc_api import search_docs, search_temp_docs
from aitutor.server.knowledge_base.kb_service.base import KBServiceFactory
from aitutor.server.knowledge_base.utils import format_reference
from aitutor.server.utils import (
    BaseResponse,
    api_address,
    build_logger,
    check_embed_model,
    get_ChatOpenAI,
    get_default_llm,
    get_prompt_template,
    wrap_done,
)
from aitutor.settings import Settings

logger = build_logger()


async def chat_with_kb(
    kb_id: str = Body(..., examples=["fdd34328-48b4-4682-b69c-52bdf8950697"]),
    query: str = Body(..., description="用户输入", examples=["你好"]),
    mode: Literal["local_kb", "temp_kb", "search_engine"] = Body(
        "local_kb", description="知识来源"
    ),
    kb_name: str = Body(
        "",
        description="mode=local_kb时为知识库名称；temp_kb时为临时知识库ID，search_engine时为搜索引擎名称",
        examples=["samples"],
    ),
    conversation_id: str = Body("", description="对话框ID"),
    message_id: str = Body(None, description="数据库消息ID"),
    top_k: int = Body(
        Settings.kb_settings.VECTOR_SEARCH_TOP_K, description="匹配向量数"
    ),
    score_threshold: int | float = Body(
        Settings.kb_settings.SCORE_THRESHOLD,
        description="知识库匹配相关度阈值，取值范围在0-1之间，SCORE越小，相关度越高，取到1相当于不筛选，建议设置在0.5左右",
        ge=0,
        le=2,
    ),
    history: List[History] = Body(
        [],
        description="历史对话",
        examples=[
            [
                {"role": "user", "content": "我们来玩成语接龙，我先来，生龙活虎"},
                {"role": "assistant", "content": "虎头虎脑"},
            ]
        ],
    ),
    stream: bool = Body(True, description="流式输出"),
    model: str = Body(None, description="LLM 模型名称。"),
    temperature: float = Body(None, description="LLM 采样温度", ge=0.0, le=2.0
    ),
    max_tokens: Optional[int] = Body(None,
        description="限制LLM生成Token数量，默认None代表模型最大值",
    ),
):
    if mode == "local_kb":
        kb = KBServiceFactory.get_service_by_id(kb_id)
        if kb is None:
            return BaseResponse(code=404, msg=f"未找到知识库 {kb_name}")

    async def knowledge_base_chat_iterator() -> AsyncIterable[str]:
        try:
            nonlocal history, max_tokens

            history = [History.from_data(h) for h in history]

            if mode == "local_kb":
                kb = KBServiceFactory.get_service_by_id(kb_id)
                ok, msg = kb.check_embed_model()
                if not ok:
                    raise ValueError(msg)
                docs = await run_in_threadpool(
                    search_docs,
                    kb_id=kb_id,
                    query=query,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    file_name="",
                    metadata={},
                )
                source_documents = format_reference(
                    kb_name, docs, api_address(is_public=True)
                )
            elif mode == "temp_kb":
                ok, msg = check_embed_model()
                if not ok:
                    raise ValueError(msg)
                docs = await run_in_threadpool(
                    search_temp_docs,
                    kb_name,
                    query=query,
                    top_k=top_k,
                    score_threshold=score_threshold,
                )
                source_documents = format_reference(
                    kb_name, docs, api_address(is_public=True)
                )
            elif mode == "search_engine":
                result = await run_in_threadpool(search_engine, query, top_k, kb_name)
                docs = [x.dict() for x in result.get("docs", [])]
                source_documents = [
                    f"""出处 [{i + 1}] [{d['metadata']['filename']}]({d['metadata']['source']}) \n\n{d['page_content']}\n\n"""
                    for i, d in enumerate(docs)
                ]
            else:
                docs = []
                source_documents = []

            callback = AsyncIteratorCallbackHandler()
            callbacks = [callback]
            conversation_callback = ConversationCallbackHandler(
                conversation_id=conversation_id,
                message_id=message_id,
                chat_type="kb_chat",
                query=query,
            )
            callbacks.append(conversation_callback)

            llm = get_ChatOpenAI(
                model_name=model,
                temperature=temperature,
                max_tokens=max_tokens,
                callbacks=callbacks,
            )

            context = "\n\n".join([doc["page_content"] for doc in docs])

            if len(docs) == 0:  # 如果没有找到相关文档，使用Empty模板
                prompt_template = get_prompt_template("rag", "empty")
            else:
                prompt_template = get_prompt_template("rag", "default")
            input_msg = History(role="user", content=prompt_template).to_msg_template(
                False
            )
            chat_prompt = ChatPromptTemplate.from_messages(
                [i.to_msg_template() for i in history] + [input_msg]
            )

            chain = LLMChain(prompt=chat_prompt, llm=llm)

            # Begin a task that runs in the background.
            task = asyncio.create_task(
                wrap_done(
                    chain.ainvoke({"context": context, "question": query}),
                    callback.done,
                ),
            )

            if len(source_documents) == 0:  # 没有找到相关文档
                source_documents.append(
                    f"<span style='color:red'>未找到相关文档,该回答为大模型自身能力解答！</span>"
                )

            if stream:
                async for token in callback.aiter():
                    # Use server-sent-events to stream the response
                    yield json.dumps({"answer": token}, ensure_ascii=False)
                yield json.dumps({"docs": source_documents}, ensure_ascii=False)
            else:
                answer = ""
                async for token in callback.aiter():
                    answer += token
                yield json.dumps(
                    {"answer": answer, "docs": source_documents}, ensure_ascii=False
                )
            await task
        except asyncio.exceptions.CancelledError:
            logger.warning("streaming progress has been interrupted by user.")
            return

    return EventSourceResponse(knowledge_base_chat_iterator())
