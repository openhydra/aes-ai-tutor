from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from aitutor.server.db.base import Base


class ConversationModel(Base):
    """
    会话模型，表示用户的一个聊天会话
    """

    __tablename__ = "conversation"
    id = Column(String(32), primary_key=True, comment="对话框ID")
    user_id = Column(String(64), comment="用户ID")
    name = Column(String(100), comment="对话框名称")
    chat_type = Column(String(50), comment="聊天类型")
    temp_kb_id = Column(String(32), comment="临时知识库ID")
    create_time = Column(DateTime, default=func.now(), comment="创建时间")

    # 会话与消息的一对多关系
    messages = relationship(
        "MessageModel", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Conversation(id='{self.id}', user_id='{self.user_id}', name='{self.name}', chat_type='{self.chat_type}', temp_kb_id='{self.temp_kb_id}',create_time='{self.create_time}')'>"
