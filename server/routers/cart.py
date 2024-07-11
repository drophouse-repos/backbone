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
from models.ItemModel import ItemModel
from database.CartOperations import CartOperations
from utils.update_cart import add_to_cart, remove_from_cart
from verification import verify_id_token

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cart_router = APIRouter()

class RemoveFromCartRequest(BaseModel):
    img_id: str


@cart_router.post("/add_to_cart")
async def update_cart(
    request: ItemModel,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(CartOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message':"User ID is required.", 'currentFrame': getframeinfo(currentframe())})
        img_id = request.img_id
        exists = await db_ops.duplicate_images(user_id, img_id)
        if exists:
            raise HTTPException(status_code=400, detail={'message':"Item already exists in cart", 'currentFrame': getframeinfo(currentframe())})

        background_tasks.add_task(
            add_to_cart,
            user_id=user_id,
            product_info=request,
            db_ops=db_ops,
        )
        logger.info(f"Item added: {request.img_id}")
        return True
    except HTTPException as http_exc:
        if http_exc.status_code == 422:
            details = http_exc.detail
            logger.error(f"HTTPException 422 occurred: {details}")
            raise HTTPException(status_code=422, detail={'message':"Unprocessable Entity", 'currentFrame': getframeinfo(currentframe())})
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in update_cart: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"An unexpected error occurred", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})


@cart_router.post("/remove_from_cart")
async def remove_from_cart_endpoint(
    request: RemoveFromCartRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(CartOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message':"User ID is required.", 'currentFrame': getframeinfo(currentframe())})
        img_id = request.img_id
        background_tasks.add_task(
            remove_from_cart,
            user_id=user_id,
            img_id=img_id,
            db_ops=db_ops,
        )
        logger.info(f"Item removed: {img_id}")
        return True
    except HTTPException as http_exc:
        if http_exc.status_code == 422:
            details = http_exc.detail
            logger.error(f"HTTPException 422 occurred: {details}")
            raise HTTPException(status_code=422, detail={'message':"Unprocessable Entity", 'currentFrame': getframeinfo(currentframe())})
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in remove {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"An unexpected error occurred", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@cart_router.get("/get_cart_number")
async def get_cart_number(
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(CartOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message':"User ID is required.", 'currentFrame': getframeinfo(currentframe())})
        result = await db_ops.get_cart_number(user_id)
        return {"cart_number": result}
    except Exception as e:
        logger.error(f"Error in get cart number: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@cart_router.get("/view_cart")
async def view_cart(
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(CartOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message':"User ID is required.",'currentFrame': getframeinfo(currentframe())})
        result = await db_ops.get(user_id)
        for cart_item in result:
            cart_item["thumbnail"] = generate_presigned_url(
                cart_item["thumbnail"], "thumbnails-cart"
            )
            cart_item["image"] = generate_presigned_url(
                cart_item["img_id"], "browse-image-v2"
            )
        return {"cart": result}
    except HTTPException as http_exc:
        if http_exc.status_code == 422:
            details = http_exc.detail
            logger.error(f"HTTPException 422 occurred: {details}")
            raise HTTPException(status_code=422, detail={'message':"Unprocessable Entity", 'currentFrame': getframeinfo(currentframe())})
        raise http_exc
    except Exception as e:
        logger.error(f"Error in view cart: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})


@cart_router.post("/move_to_another_cart")
async def move_to_another_cart(
    request_data: ItemModel,
    user_id: str = Depends(verify_id_token),
    db_ops: CartOperations = Depends(get_db_ops(CartOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message':"User ID is required.", 'currentFrame': getframeinfo(currentframe())})
        userExist = await db_ops.checkUserExist(user_id)
        if not userExist:
            raise HTTPException(status_code=401, detail={'message':"User is not exist.", 'currentFrame': getframeinfo(currentframe())})
        result = await db_ops.toggle_save_for_later(user_id, request_data)
        return {"result": result}
    except Exception as e:
        logger.error(f"Error in move_to_another_cart: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@cart_router.post("/save_img")
async def move_to_another_cart(
    request_data: ItemModel,
):
    try:
        toggled = request_data.toggled
        if toggled:
            processAndSaveImage(toggled, request_data.img_id, "browse-image-v2")
        thumbnail = request_data.thumbnail
        thumbnail_id = f"t_{request_data.img_id}"
        processAndSaveImage(thumbnail, thumbnail_id, "thumbnails-cart")
        request_data.thumbnail = thumbnail_id
        request_data.toggled = None
        return True
    except Exception as error:
        logger.error(f"Error in add_to_cart: {error}")
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

