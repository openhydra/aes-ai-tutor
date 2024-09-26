from typing import List

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

import aitutor.server.db.repository.conversation_repository as conversation_repository
import aitutor.server.db.repository.message_repository as message_repository
from aitutor.server.api_server.api_schemas import (
    ConversationInput,
    HttpCustomeResponseMessage,
    MessageOutput,
)
from aitutor.utils import build_logger

logger = build_logger()
conversation_router = APIRouter(prefix="/conversations", tags=["aitutor 对话记录"])


@conversation_router.post(
    "",
    summary="新增会话",
    response_model=ConversationInput,
    responses={500: {"model": HttpCustomeResponseMessage}},
)
def add_conversation(
    request: Request, body: ConversationInput, response: Response
) -> JSONResponse:
    try:
        id = conversation_repository.add_conversation_to_db(
            conversation_id="",
            chat_type=body.chat_type,
            user_id=body.user_id,
            name=body.name,
            temp_kb_id=body.temp_kb_id,
        )
    except Exception as e:
        logger.error(f"新增会话失败：{e}")
        response.status_code = 500
        return HttpCustomeResponseMessage(message="新增会话失败")
    body.id = id
    return JSONResponse(status_code=201, content=body.model_dump())


# update conversation
@conversation_router.patch(
    "/{conversation_id}",
    summary="更新会话",
    response_model=ConversationInput,
    responses={
        500: {"model": HttpCustomeResponseMessage},
        404: {"model": HttpCustomeResponseMessage},
    },
)
def update_conversation(
    request: Request, conversation_id: str, body: ConversationInput, response: Response
) -> JSONResponse:
    try:
        conversation_repository.update_conversation(
            conversation_id=conversation_id,
            name=body.name,
        )
    except Exception as e:
        # check exception type
        if isinstance(e, conversation_repository.NotFoundException):
            response.status_code = 404
            response = HttpCustomeResponseMessage(message="Conversation not found")
            return JSONResponse(status_code=404, content=response.model_dump())

        else:
            logger.error(f"更新会话失败：{e}")
            response.status_code = 500
            return JSONResponse(
                status_code=500,
                content=HttpCustomeResponseMessage(
                    custome_error_code=500, message="Update conversation failed"
                ).model_dump(),
            )
    body.id = conversation_id
    return JSONResponse(status_code=200, content=body.model_dump())


@conversation_router.get(
    "/{conversation_id}",
    summary="查询会话",
    response_model=ConversationInput,
    responses={
        500: {"model": HttpCustomeResponseMessage},
        404: {"model": HttpCustomeResponseMessage},
    },
)
def get_conversation_by_id(
    request: Request, conversation_id: str, response: Response
) -> JSONResponse:
    try:
        conversation = conversation_repository.get_conversation_by_id(conversation_id)
    except Exception as e:
        logger.error(f"获取会话失败：{e}")
        # check exception type
        if isinstance(e, conversation_repository.NotFoundException):
            response.status_code = 404
            response = HttpCustomeResponseMessage(message="Conversation not found")
            return JSONResponse(status_code=404, content=response.model_dump())

        else:
            logger.error(f"获取会话失败：{e}")
            response.status_code = 500
            return JSONResponse(
                status_code=500,
                content=HttpCustomeResponseMessage(
                    custome_error_code=500, message="Get conversation failed"
                ).model_dump(),
            )
    return JSONResponse(status_code=200, content=conversation.model_dump())


# get conversation list by user id
@conversation_router.get(
    "/users/{user_id}",
    summary="获取会话列表",
    response_model=List[ConversationInput],
    responses={500: {"model": HttpCustomeResponseMessage}},
)
def get_conversation_list(
    request: Request, user_id: str, response: Response
) -> JSONResponse:
    try:
        conversation_list = conversation_repository.list_conversations_with_user_id(
            user_id
        )
    except Exception as e:
        logger.error(f"获取会话列表失败：{e}")
        response.status_code = 500
        return JSONResponse(
            status_code=500,
            content=HttpCustomeResponseMessage(
                custome_error_code=500, message="Get conversation list failed"
            ).model_dump(),
        )

    return JSONResponse(
        status_code=200, content=[c.model_dump() for c in conversation_list]
    )


# get all conversation list
@conversation_router.get(
    "",
    summary="获取所有会话列表",
    response_model=List[ConversationInput],
    responses={500: {"model": HttpCustomeResponseMessage}},
)
def get_all_conversation_list(request: Request, response: Response) -> JSONResponse:
    try:
        conversation_list = conversation_repository.list_all_conversations()
    except Exception as e:
        logger.error(f"获取所有会话列表失败：{e}")
        response.status_code = 500
        return JSONResponse(
            status_code=500,
            content=HttpCustomeResponseMessage(
                custome_error_code=500, message="Get all conversation list failed"
            ).model_dump(),
        )

    return JSONResponse(
        status_code=200, content=[c.model_dump() for c in conversation_list]
    )


# delete conversation by id
@conversation_router.delete(
    "/{conversation_id}",
    summary="删除会话",
    responses={
        500: {"model": HttpCustomeResponseMessage},
        404: {"model": HttpCustomeResponseMessage},
    },
)
def delete_conversation_by_id(
    request: Request, conversation_id: str, response: Response
) -> JSONResponse:
    try:
        conversation_repository.delete_conversation(conversation_id)
    except Exception as e:
        # check exception type
        if isinstance(e, conversation_repository.NotFoundException):
            response.status_code = 404
            response = HttpCustomeResponseMessage(message="Conversation not found")
            return JSONResponse(status_code=404, content=response.model_dump())

        else:
            logger.error(f"删除会话失败：{e}")
            response.status_code = 500
            return JSONResponse(
                status_code=500,
                content=HttpCustomeResponseMessage(
                    custome_error_code=500, message="Delete conversation failed"
                ).model_dump(),
            )
    return JSONResponse(
        status_code=200, content=ConversationInput(id=conversation_id).model_dump()
    )


# delete conversation by user id
@conversation_router.delete(
    "/users/{user_id}",
    summary="删除用户所有会话",
    response_model=List[ConversationInput],
    responses={
        500: {"model": HttpCustomeResponseMessage},
        404: {"model": HttpCustomeResponseMessage},
    },
)
def delete_conversation_by_user_id(
    request: Request, user_id: str, response: Response
) -> JSONResponse:
    try:
        conversation_list = conversation_repository.delete_conversations_by_user_id(
            user_id
        )
    except Exception as e:
        # check exception type
        if isinstance(e, conversation_repository.NotFoundException):
            response.status_code = 404
            response = HttpCustomeResponseMessage(message="Conversation not found")
            return JSONResponse(status_code=404, content=response.model_dump())

        else:
            logger.error(f"删除会话失败：{e}")
            response.status_code = 500
            return JSONResponse(
                status_code=500,
                content=HttpCustomeResponseMessage(
                    custome_error_code=500, message="Delete conversation failed"
                ).model_dump(),
            )
    return JSONResponse(
        status_code=200, content=[c.model_dump() for c in conversation_list]
    )


# get messages list by conversation id
@conversation_router.get(
    "/messages/{conversation_id}",
    summary="获取消息列表",
    response_model=List[MessageOutput],
    responses={500: {"model": HttpCustomeResponseMessage}},
)
def get_messages_list(
    request: Request, conversation_id: str, response: Response
) -> JSONResponse:
    try:
        messages = message_repository.list_messages_by_conversation_id(conversation_id)
    except Exception as e:
        logger.error(f"获取消息列表失败：{e}")
        response.status_code = 500
        return JSONResponse(
            status_code=500,
            content=HttpCustomeResponseMessage(
                custome_error_code=500, message="Get messages list failed"
            ).model_dump(),
        )

    return JSONResponse(status_code=200, content=[m.model_dump() for m in messages])


# get message by message id
@conversation_router.get(
    "/message/{message_id}",
    summary="获取消息记录",
    response_model=MessageOutput,
    responses={500: {"model": HttpCustomeResponseMessage}},
)
def get_message(request: Request, message_id: str, response: Response) -> JSONResponse:
    try:
        message = message_repository.get_message_by_id(message_id)
    except Exception as e:
        logger.error(f"获取消息记录：{e}")
        response.status_code = 500
        return JSONResponse(
            status_code=500,
            content=HttpCustomeResponseMessage(
                custome_error_code=500, message="Get message failed"
            ).model_dump(),
        )

    return JSONResponse(status_code=200, content=message.model_dump())
