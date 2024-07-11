import uuid
import traceback
from inspect import currentframe, getframeinfo
from fastapi import APIRouter, HTTPException, BackgroundTasks  # , Request
from pydantic import BaseModel
from dotenv import load_dotenv
from aws_utils import generate_presigned_url, processAndSaveImage
from fastapi import Depends
import logging
from db import get_db_ops
from database.BASE import BaseDatabaseOperation
from database.LikedImageOperations import LikedImageOperations

from utils.update_like import like_image, unlike_image
from verification import verify_id_token
from utils.error_check import checkUnprocessibleEntity
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

favorite_router = APIRouter()


class LikeHandlerRequest(BaseModel):
    img_id: str
    prompt: str
    like: bool



@favorite_router.post("/like_image")
async def like_image_route(
    request: LikeHandlerRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(LikedImageOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message': "User ID is required.", 'currentFrame': getframeinfo(currentframe())})
        userExist = await db_ops.checkUserExist(user_id)
        if not userExist:
            raise HTTPException(status_code=401, detail={'message': "User is not exist.", 'currentFrame': getframeinfo(currentframe())})
        like = request.like
        if like:
            exists = await db_ops.duplicate_images(user_id, request.img_id)
            if exists:
                raise HTTPException(status_code=400, detail={'message': "Item already exists in liked images", 'currentFrame': getframeinfo(currentframe())})
            background_tasks.add_task(
                like_image,
                user_id=user_id,
                img_id=request.img_id,
                prompt=request.prompt,
                db_ops=db_ops,
            )
        else:
            background_tasks.add_task(
                unlike_image,
                user_id=user_id,
                img_id=request.img_id,
                prompt=request.prompt,
                db_ops=db_ops,
            )
    except HTTPException as http_exc:
        checkUnprocessibleEntity(http_exc)
        raise http_exc
    except Exception as e:
        logger.error(f"Error in generate_image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message': "Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})



@favorite_router.get("/get_liked_images")
async def get_liked_images(
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(LikedImageOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message': "User ID is required.", 'currentFrame': getframeinfo(currentframe())})
        liked_images = await db_ops.get(user_id)
        for image in liked_images:
            img_id = image["img_id"]
            image["signed_url"] = generate_presigned_url(img_id, "browse-image-v2")
        return {"liked_images": liked_images}
    except HTTPException as http_exc:
        checkUnprocessibleEntity(http_exc)
        raise http_exc
    except Exception as e:
        logger.error(f"Error in get_liked_images: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message': "Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@favorite_router.get("/get_image_url")
async def get_liked_images(
    img_id: str,
):
    try:
        url = generate_presigned_url(img_id, "browse-image-v2")
        return {"url": url}
    except HTTPException as http_exc:
        checkUnprocessibleEntity(http_exc)
        raise http_exc
    except Exception as e:
        logger.error(f"Error in get_image_url: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message': "Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
    
class LikeExistRequest(BaseModel):
    img_id: str

@favorite_router.post("/get_is_liked")
async def get_is_liked(
    request: LikeExistRequest,
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(LikedImageOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message': "User ID is required.", 'currentFrame': getframeinfo(currentframe())})
        is_liked = await db_ops.duplicate_images(user_id, request.img_id)
        return is_liked
    except HTTPException as http_exc:
        checkUnprocessibleEntity(http_exc)
        raise http_exc
    except Exception as e:
        logger.error(f"Error in get_liked_images: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message': "Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})