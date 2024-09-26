import asyncio
import json
import uuid
import os
from typing import AsyncIterable, List, Optional

from aitutor.server.api_server.api_schemas import OpenAIChatOutput
from fastapi import Body, File, Form, UploadFile
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chains import LLMChain
from langchain.prompts.chat import ChatPromptTemplate
from sse_starlette.sse import EventSourceResponse

from aitutor.server.callback_handler.conversation_callback_handler import (
    ConversationCallbackHandler,
)
from aitutor.server.chat.utils import History
from aitutor.server.knowledge_base.kb_cache.faiss_cache import memo_faiss_pool
from aitutor.server.knowledge_base.utils import KnowledgeFile
from aitutor.server.utils import (
    BaseResponse,
    get_ChatOpenAI,
    get_default_llm,
    get_Embeddings,
    get_prompt_template,
    get_temp_dir,
    run_in_thread_pool,
    wrap_done,
)
from aitutor.settings import Settings
from aitutor.utils import build_logger

logger = build_logger()


def _parse_files_in_thread(
    user_id: str,
    files: List[UploadFile],
    dir: str,
    zh_title_enhance: bool,
    chunk_size: int,
    chunk_overlap: int,
):
    """
    通过多线程将上传的文件保存到对应目录内。
    生成器返回保存结果：[success or error, filename, msg, docs]
    """

    def parse_file(file: UploadFile) -> dict:
        """
        保存单个文件。
        """
        try:
            # 获取文件大小
            file_byte = file.size

            # 检查文件大小是否超过 10MB
            if file_byte > 10 * 1024 * 1024:
                msg = f"文件大小为 {file_byte} 超出限制 10MB"
                return False, file.filename, msg, []
            filename = file.filename
            file_path = os.path.join(dir, filename)
            file_content = file.file.read()  # 读取上传文件的内容

            if not os.path.isdir(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))
            with open(file_path, "wb") as f:
                f.write(file_content)
            kb_file = KnowledgeFile(user_id=user_id, filename=filename, knowledge_base_name="temp")
            kb_file.filepath = file_path
            docs = kb_file.file2text(
                zh_title_enhance=zh_title_enhance,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            return True, filename, f"成功上传文件 {filename}", docs
        except Exception as e:
            msg = f"{filename} 文件上传失败，报错信息为: {e}"
            return False, filename, msg, []

    params = [{"file": file} for file in files]
    for result in run_in_thread_pool(parse_file, params=params):
        yield result


def upload_temp_docs(
    user_id: str = Form(..., description="用户ID"),
    files: List[UploadFile] = File(..., description="上传文件，支持多文件"),
    prev_id: str = Form(None, description="前知识库ID"),
    chunk_size: int = Form(
        Settings.kb_settings.CHUNK_SIZE, description="知识库中单段文本最大长度"
    ),
    chunk_overlap: int = Form(
        Settings.kb_settings.OVERLAP_SIZE, description="知识库中相邻文本重合长度"
    ),
    zh_title_enhance: bool = Form(
        Settings.kb_settings.ZH_TITLE_ENHANCE, description="是否开启中文标题加强"
    ),
) -> BaseResponse:
    """
    将文件保存到临时目录，并进行向量化。
    返回临时目录名称作为ID，同时也是临时向量库的ID。
    """
    if prev_id is not None:
        memo_faiss_pool.pop(prev_id)

    failed_files = []
    documents = []
    succeeded_files = []
    path, id = get_temp_dir(prev_id)
    for success, file, msg, docs in _parse_files_in_thread(
        user_id=user_id,
        files=files,
        dir=path,
        zh_title_enhance=zh_title_enhance,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    ):
        if success:
            documents += docs
            succeeded_files.append({"filename": file})
        else:
            failed_files.append({
                "filename": file,
                "msg": msg
            })
    try:
        with memo_faiss_pool.load_vector_store(kb_name=id).acquire() as vs:
            vs.add_documents(documents)
    except Exception as e:
        logger.error(f"Failed to add documents to faiss: {e}")

    return BaseResponse(data={"id": id, "succeeded_files": succeeded_files,"failed_files": failed_files})

async def chat_with_file(
    query: str = Body(..., description="用户输入", examples=["你好"]),
    knowledge_id: str = Body(..., description="临时知识库ID"),
    conversation_id: str = Body("", description="对话框ID"),
    message_id: str = Body(None, description="数据库消息ID"),
    top_k: int = Body(
        Settings.kb_settings.VECTOR_SEARCH_TOP_K, description="匹配向量数"
    ),
    score_threshold: float = Body(
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
    stream: bool = Body(False, description="流式输出"),
    max_tokens: Optional[int] = Body(
        None, description="限制LLM生成Token数量，默认None代表模型最大值"
    ),
):
    if knowledge_id not in memo_faiss_pool.keys():
        return BaseResponse(
            code=404, data={f"未找到临时知识库 {knowledge_id}，请先上传文件"}
        )

    history = [History.from_data(h) for h in history]

    async def knowledge_base_chat_iterator() -> AsyncIterable[str]:
        try:
            nonlocal max_tokens
            callback = AsyncIteratorCallbackHandler()
            if isinstance(max_tokens, int) and max_tokens <= 0:
                max_tokens = None

            callbacks = [callback]
            conversation_callback = ConversationCallbackHandler(
                conversation_id=conversation_id,
                message_id=message_id,
                chat_type="file_chat",
                query=query,
            )
            callbacks.append(conversation_callback)

            model = get_ChatOpenAI(
                model_name=get_default_llm(),
                temperature=0.5,
                max_tokens=max_tokens,
                callbacks=callbacks,
            )

            embed_func = get_Embeddings()
            embeddings = await embed_func.aembed_query(query)
            with memo_faiss_pool.acquire(knowledge_id) as vs:
                docs = vs.similarity_search_with_score_by_vector(
                    embeddings, k=top_k, score_threshold=score_threshold
                )
                docs = [x[0] for x in docs]

            context = "\n".join([doc.page_content for doc in docs])
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

            chain = LLMChain(prompt=chat_prompt, llm=model)

            # Begin a task that runs in the background.
            task = asyncio.create_task(
                wrap_done(
                    chain.ainvoke({"context": context, "question": query}), callback.done
                ),
            )

            source_documents = []
            for inum, doc in enumerate(docs):
                filename = doc.metadata.get("source")
                text = f"""出处 [{inum + 1}] [{filename}] \n\n{doc.page_content}\n\n"""
                source_documents.append(text)

            if len(source_documents) == 0:  # 没有找到相关文档
                source_documents.append(
                    f"""<span style='color:red'>未找到相关文档,该回答为大模型自身能力解答！</span>"""
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