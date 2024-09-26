from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, func, BOOLEAN, UniqueConstraint
from sqlalchemy.orm import relationship

from aitutor.server.db.base import Base


class KnowledgeBaseModel(Base):
    """
    知识库模型
    """

    __tablename__ = "knowledge_base"
    id = Column(String(64), primary_key=True, comment="知识库ID")
    user_id = Column(String(64), comment="用户ID")
    kb_name = Column(String(50), comment="知识库名称")
    kb_info = Column(String(200), comment="知识库简介(用于Agent)")
    vs_type = Column(String(50), comment="向量库类型")
    embed_model = Column(String(50), comment="嵌入模型名称")
    file_count = Column(Integer, default=0, comment="文件数量")
    is_private = Column(BOOLEAN, default=True, comment="是否私有")
    create_time = Column(DateTime, default=func.now(), comment="创建时间")

    __table_args__ = (
        UniqueConstraint('user_id', 'kb_name', name='uix_user_id_kb_name'), # 唯一复合约束
    )

    knowledge_files = relationship(
        "KnowledgeFileModel", back_populates="knowledge_base"
    )
    file_docs = relationship("FileDocModel", back_populates="knowledge_base")
    # summary_chunk = relationship('SummaryChunkModel', back_populates='knowledge_base')

    def __repr__(self):
        return f"<KnowledgeBase(id='{self.id}', kb_name='{self.kb_name}',kb_intro='{self.kb_info} vs_type='{self.vs_type}', embed_model='{self.embed_model}', file_count='{self.file_count}', create_time='{self.create_time}')>"


# 创建一个对应的 Pydantic 模型
class KnowledgeBaseSchema(BaseModel):
    id: str
    user_id: str
    kb_name: str
    kb_info: Optional[str]
    vs_type: Optional[str]
    embed_model: Optional[str]
    file_count: Optional[int]
    is_private: Optional[bool]
    create_time: Optional[datetime]

    class Config:
        from_attributes = True  # 确保可以从 ORM 实例进行验证
