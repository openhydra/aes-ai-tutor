import uuid
from typing import List

from aitutor.server.api_server.api_schemas import ConversationInput
from aitutor.server.db.models.conversation_model import ConversationModel
from aitutor.server.db.session import with_session


class NotFoundException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


@with_session
def add_conversation_to_db(
    session,
    chat_type: str,
    name: str = None,
    user_id: str = None,
    conversation_id: str = None,
    temp_kb_id: str = None,
) -> str:
    """
    新增会话
    """
    if not conversation_id:
        conversation_id = uuid.uuid4().hex
    c = ConversationModel(
        id=conversation_id, chat_type=chat_type, user_id=user_id, name=name, temp_kb_id=temp_kb_id
    )
    session.add(c)
    session.commit()
    return c.id


@with_session
def get_conversation_by_id(
    session,
    conversation_id: str,
) -> ConversationInput:
    """
    查询会话
    """
    conversation = (
        session.query(ConversationModel)
        .filter(ConversationModel.id == conversation_id)
        .first()
    )
    if not conversation:
        raise NotFoundException(f"Conversation {conversation_id} not found")
    return ConversationInput(
        id=conversation.id,
        chat_type=conversation.chat_type,
        user_id=conversation.user_id,
        name=conversation.name,
        temp_kb_id=conversation.temp_kb_id,
        create_time=conversation.create_time.isoformat(),
    )


@with_session
def update_conversation(session, conversation_id: str, name: str = None) -> str:
    """
    更新已有的会话
    """
    conversation = (
        session.query(ConversationModel)
        .filter(ConversationModel.id == conversation_id)
        .first()
    )
    if conversation:
        conversation.name = name
        session.commit()
    else:
        raise NotFoundException(f"Conversation {conversation_id} not found")
    return conversation_id


@with_session
def delete_conversation(session, conversation_id: str) -> str:
    """
    删除会话及其所有消息记录
    """
    # 删除会话
    conversation = (
        session.query(ConversationModel)
        .filter(ConversationModel.id == conversation_id)
        .first()
    )
    if conversation:
        session.delete(conversation)
        session.commit()
        return True
    else:
        raise NotFoundException(f"Conversation {conversation_id} not found")


@with_session
def list_conversations_with_user_id(session, user_id: str) -> List[ConversationInput]:
    """
    列出用户的所有会话
    """
    conversations = (
        session.query(ConversationModel)
        .filter(ConversationModel.user_id == user_id)
        .order_by(ConversationModel.create_time.desc())
        .all()
    )
    return [
        ConversationInput(
            id=conversation.id,
            chat_type=conversation.chat_type,
            user_id=conversation.user_id,
            name=conversation.name,
            temp_kb_id=conversation.temp_kb_id,
            create_time=conversation.create_time.isoformat(),
        )
        for conversation in conversations
    ]


@with_session
def list_all_conversations(session) -> List[ConversationInput]:
    """
    列出所有会话
    """
    conversations = (
        session.query(ConversationModel)
        .order_by(ConversationModel.create_time.desc())
        .all()
    )
    return [
        ConversationInput(
            id=conversation.id,
            chat_type=conversation.chat_type,
            user_id=conversation.user_id,
            name=conversation.name,
            temp_kb_id=conversation.temp_kb_id,
            create_time=conversation.create_time.isoformat(),
        )
        for conversation in conversations
    ]


@with_session
def delete_conversations_by_user_id(session, user_id: str) -> List[ConversationInput]:
    """
    删除用户的所有会话
    """
    conversations = (
        session.query(ConversationModel)
        .filter(ConversationModel.user_id == user_id)
        .all()
    )
    for conversation in conversations:
        session.delete(conversation)
    session.commit()
    return [
        ConversationInput(
            id=conversation.id,
            chat_type=conversation.chat_type,
            user_id=conversation.user_id,
            name=conversation.name,
            temp_kb_id=conversation.temp_kb_id,
            create_time=conversation.create_time.isoformat(),
        )
        for conversation in conversations
    ]
