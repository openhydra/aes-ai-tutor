import uuid

from fastapi import Body, Path
from sqlalchemy.exc import IntegrityError

from aitutor.server.db.repository.knowledge_base_repository import (
    get_kb_detail,
    kb_name_exists_for_user,
    list_kbs_from_db,
    list_kbs_from_db_by_user_id,
    list_public_kbs_from_db
)
from aitutor.server.knowledge_base.kb_service.base import KBServiceFactory
from aitutor.server.knowledge_base.utils import validate_kb_name
from aitutor.server.utils import BaseResponse, ListResponse, get_default_embedding
from aitutor.settings import Settings
from aitutor.utils import build_logger

logger = build_logger()


def list_all_kbs():
    # Get List of Knowledge Base
    kbs = list_kbs_from_db()
    
    # 替换 id 字段为 kb_id
    modified_kbs = []
    for kb in kbs:
        kb_dict = kb.dict()
        kb_dict['kb_id'] = kb_dict.pop('id')
        modified_kbs.append(kb_dict)
    
    return ListResponse(data=modified_kbs)

def list_kbs(user_id: str):
    # Get List of Knowledge Base
    kbs = list_kbs_from_db_by_user_id(user_id)
    
    # 替换 id 字段为 kb_id
    modified_kbs = []
    for kb in kbs:
        kb_dict = kb.dict()
        kb_dict['kb_id'] = kb_dict.pop('id')
        modified_kbs.append(kb_dict)
    
    return ListResponse(data=modified_kbs)

def list_public_kbs():
    # Get List of Public Knowledge Base
    kbs = list_public_kbs_from_db()
    
    # 替换 id 字段为 kb_id
    modified_kbs = []
    for kb in kbs:
        kb_dict = kb.dict()
        kb_dict['kb_id'] = kb_dict.pop('id')
        modified_kbs.append(kb_dict)
    
    return ListResponse(data=modified_kbs)


def create_kb(
    user_id: str = Body(..., examples=["fdd34328-48b4-4682-b69c-52bdf8950697"]),
    kb_name: str = Body(..., examples=["samples"]),
    vector_store_type: str = Body("faiss"),
    kb_info: str = Body("", description="知识库内容简介，用于Agent选择知识库。"),
    embed_model: str = Body(get_default_embedding()),
    is_private: bool = Body(True),
) -> BaseResponse:
    # Create selected knowledge base
    kb_id = uuid.uuid4().hex
    if not validate_kb_name(kb_name):
        return BaseResponse(code=403, msg="Don't attack me")
    if kb_name is None or kb_name.strip() == "":
        return BaseResponse(code=404, msg="知识库名称不能为空，请重新填写知识库名称")
    # 检查是否存在同名知识库
    if kb_name_exists_for_user(user_id, kb_name):
        return BaseResponse(code=409, msg=f"用户 {user_id} 已存在同名知识库 '{kb_name}'，请选择其他名称")

    kb = KBServiceFactory.get_service(
        user_id, kb_id, kb_name, vector_store_type, embed_model, kb_info=kb_info
    )
    try:
        kb.is_private = is_private
        kb.create_kb()
    except Exception as e:
        msg = f"创建知识库出错： {e}"
        logger.error(f"{e.__class__.__name__}: {msg}")
        return BaseResponse(code=500, msg=msg)

    return BaseResponse(code=200, msg=f"已新增知识库 {kb_name}", data=kb_id)


def delete_kb(
    kb_id: str = Path(..., examples=["fdd34328-48b4-4682-b69c-52bdf8950697"]),
) -> BaseResponse:

    kb = KBServiceFactory.get_service_by_id(kb_id)

    if kb is None:
        return BaseResponse(code=404, msg=f"未找到知识库 id:{kb_id}")

    try:
        status = kb.clear_vs()
        status = kb.drop_kb()
        if status:
            return BaseResponse(code=200, msg=f"成功删除知识库 id:{kb_id}")
    except Exception as e:
        msg = f"删除知识库时出现意外： {e}"
        logger.error(f"{e.__class__.__name__}: {msg}")
        return BaseResponse(code=500, msg=msg)

    return BaseResponse(code=500, msg=f"删除知识库失败 id:{kb_id}")


def get_kb_info(
    kb_id: str = Path(..., examples=["fdd34328-48b4-4682-b69c-52bdf8950697"]),
):
    kb_detail = get_kb_detail(kb_id)
    if not kb_detail:
        return  BaseResponse(code=404, msg=f"未找到知识库 id:{kb_id}")
    return BaseResponse(code=200, msg=f"知识库信息", data=kb_detail)
