import traceback
from inspect import currentframe, getframeinfo
from database.BASE import BaseDatabaseOperation
from fastapi import HTTPException
import logging
from pydantic import BaseModel
from utils.error_check import checkUnprocessibleEntity
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LikeHandlerRequestDB(BaseModel):
    img_id: str
    prompt: str

async def like_image(
    img_id: str, prompt: str, user_id: str, db_ops: BaseDatabaseOperation
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message':"User ID is required.",'currentFrame': getframeinfo(currentframe())})
        model = LikeHandlerRequestDB(img_id=img_id, prompt=prompt)
        result = await db_ops.create(user_id, model)
        logger.info(f"Image liked: {result}")
        return True
    except HTTPException as http_exc:
        checkUnprocessibleEntity(http_exc)
        raise http_exc
    except Exception as error:
        logger.error(f"Error in add liked image: {error}")
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})


async def unlike_image(
    img_id: str, prompt: str, user_id: str, db_ops: BaseDatabaseOperation
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message':"User ID is required.",'currentFrame': getframeinfo(currentframe())})
        model = LikeHandlerRequestDB(img_id=img_id, prompt=prompt)
        result = await db_ops.remove(user_id, model)
        logger.info(f"Image removed: {result}")
        return True
    except HTTPException as http_exc:
        checkUnprocessibleEntity(http_exc)
        raise http_exc
    except Exception as error:
        logger.error(f"Error in remove liked image: {error}")
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})