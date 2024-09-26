import uuid
from typing import Dict, List

from aitutor.server.api_server.api_schemas import MessageOutput
from aitutor.server.db.models.message_model import MessageModel
from aitutor.server.db.session import with_session


@with_session
def add_message_to_db(
    session,
    conversation_id: str,
    chat_type,
    query,
    response="",
    message_id=None,
    metadata: Dict = {},
):
    """
    新增聊天记录
    """
    if not message_id:
        message_id = uuid.uuid4().hex
    m = MessageModel(
        id=message_id,
        chat_type=chat_type,
        query=query,
        response=response,
        conversation_id=conversation_id,
        meta_data=metadata,
    )
    session.add(m)
    session.commit()
    return m.id


@with_session
def update_message(session, message_id, response: str = None, metadata: Dict = None):
    """
    更新已有的聊天记录
    """
    m = session.query(MessageModel).filter_by(id=message_id).first()
    if m is not None:
        if response is not None:
            m.response = response
        if isinstance(metadata, dict):
            m.meta_data = metadata
        session.add(m)
        session.commit()
        return m.id


@with_session
def get_message_by_id(session, message_id) -> MessageOutput:
    """
    查询聊天记录
    """
    m = session.query(MessageModel).filter_by(id=message_id).first()
    return MessageOutput(
        id=m.id,
        chat_type=m.chat_type,
        query=m.query,
        response=m.response,
        conversation_id=m.conversation_id,
        messages=[
            {"content": f"response: {m.response}", "role": "assistant"},
            {"content": f"query: {m.query}", "role": "user"},
        ],
    )


@with_session
def list_messages_by_conversation_id(session, conversation_id) -> List[MessageOutput]:
    """
    根据会话id查询聊天记录
    """
    messages = (
        session.query(MessageModel)
        .filter_by(conversation_id=conversation_id)
        .order_by(MessageModel.create_time)
        .all()
    )
    messages = [
        MessageOutput(
            id=m.id,
            chat_type=m.chat_type,
            query=m.query,
            response=m.response,
            conversation_id=m.conversation_id,
            messages=[
                {"content": f"{m.query}", "role": "user"},
                {"content": f"{m.response}", "role": "assistant"},
            ],
        )
        for m in messages
    ]
    return messages


@with_session
def feedback_message_to_db(session, message_id, feedback_score, feedback_reason):
    """
    反馈聊天记录
    """
    m = session.query(MessageModel).filter_by(id=message_id).first()
    if m:
        m.feedback_score = feedback_score
        m.feedback_reason = feedback_reason
    session.commit()
    return m.id


@with_session
def filter_message(session, conversation_id: str, limit: int = 10):
    messages = (
        session.query(MessageModel)
        .filter_by(conversation_id=conversation_id)
        .
        # 用户最新的query 也会插入到db，忽略这个message record
        filter(MessageModel.response != "")
        .
        # 返回最近的limit 条记录
        order_by(MessageModel.create_time.desc())
        .limit(limit)
        .all()
    )
    # 直接返回 List[MessageModel] 报错
    data = []
    for m in messages:
        data.append({"query": m.query, "response": m.response})
    return data
