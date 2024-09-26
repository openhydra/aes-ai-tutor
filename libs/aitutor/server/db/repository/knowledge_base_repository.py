from sqlalchemy.exc import IntegrityError
from aitutor.server.db.models.knowledge_base_model import (
    KnowledgeBaseModel,
    KnowledgeBaseSchema,
)
from aitutor.server.db.session import with_session


@with_session
def add_kb_to_db(session, user_id, kb_id, kb_name, kb_info, vs_type, embed_model, is_private):
    # 创建知识库实例
    kb = KnowledgeBaseModel(
        id=kb_id,
        user_id=user_id,
        kb_name=kb_name,
        kb_info=kb_info,
        vs_type=vs_type,
        embed_model=embed_model,
        is_private=is_private,
    )
    session.add(kb)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        print(f"Error: {e}")
    return kb.id

@with_session
def update_kb_info(session, kb_id, kb_info, is_private):
    kb = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.id == kb_id)
        .first()
    )
    if kb:
        kb.kb_info = kb_info
        kb.is_private = is_private
        session.commit()
        return True
    return False


@with_session
def list_kbs_from_db(session, min_file_count: int = -1):
    kbs = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.file_count > min_file_count)
        .all()
    )
    kbs = [KnowledgeBaseSchema.model_validate(kb) for kb in kbs]
    return kbs

@with_session
def list_public_kbs_from_db(session, min_file_count: int = -1):
    kbs = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.file_count > min_file_count)
        .filter(KnowledgeBaseModel.is_private == False)
        .all()
    )
    kbs = [KnowledgeBaseSchema.model_validate(kb) for kb in kbs]
    return kbs


@with_session
def list_kbs_from_db_by_user_id(session, user_id, min_file_count: int = -1):
    kbs = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.user_id == user_id)
        .filter(KnowledgeBaseModel.file_count > min_file_count)
        .all()
    )
    kbs = [KnowledgeBaseSchema.model_validate(kb) for kb in kbs]
    return kbs


@with_session
def kb_exists(session, kb_id):
    kb = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.id == kb_id)
        .first()
    )
    status = True if kb else False
    return status

@with_session
def kb_name_exists_for_user(session, user_id, kb_name):
    kb = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.user_id == user_id)
        .filter(KnowledgeBaseModel.kb_name == kb_name)
        .first()
    )
    return kb is not None


@with_session
def load_kb_from_db(session, kb_id):
    kb = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.id == kb_id)
        .first()
    )
    if kb:
        user_id, kb_name, vs_type, embed_model = kb.user_id, kb.kb_name, kb.vs_type, kb.embed_model
    else:
        user_id, kb_name, vs_type, embed_model = None, None, None, None
    return user_id, kb_name, vs_type, embed_model


@with_session
def delete_kb_from_db(session, kb_id):
    kb = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.id == kb_id)
        .first()
    )
    if kb:
        session.delete(kb)
    return True


@with_session
def get_kb_detail(session, kb_id) -> dict:
    kb: KnowledgeBaseModel = (
        session.query(KnowledgeBaseModel)
        .filter(KnowledgeBaseModel.id == kb_id)
        .first()
    )
    if kb:
        return {
            "kb_id": kb.id,
            "user_id": kb.user_id,
            "kb_name": kb.kb_name,
            "kb_info": kb.kb_info,
            "vs_type": kb.vs_type,
            "embed_model": kb.embed_model,
            "file_count": kb.file_count,
            "create_time": kb.create_time.isoformat(),
            "is_private": kb.is_private,
        }
    else:
        return {}
