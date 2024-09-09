import traceback
from inspect import currentframe, getframeinfo
from aws_utils import processAndSaveImage
from fastapi import HTTPException
from database.BASE import BaseDatabaseOperation
from models.ItemModel import ItemModel
from database.CartOperations import CartOperations
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_to_cart(product_info: ItemModel, user_id: str, db_ops: CartOperations):
    try:
        thumbnail = product_info.thumbnail
        thumbnail_id = f"t_{product_info.img_id}"
        processAndSaveImage(thumbnail, thumbnail_id, "thumbnails-cart")
        if product_info.toggled and product_info.toggled.startswith("data:image"):
            processAndSaveImage(product_info.toggled, f"e_{product_info.img_id}", "browse-image-v2")
            product_info.toggled = True
            
        product_info.thumbnail = thumbnail_id
        result = await db_ops.create(user_id, product_info)
        logger.info(f"Added to cart: {result}")
        return True
    except Exception as error:
        logger.error(f"Error in add_to_cart: {error}")
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})


async def remove_from_cart(img_id: str, user_id: str, db_ops: CartOperations):
    try:
        result = await db_ops.remove(user_id, img_id)
        logger.info(f"Removed from cart: {result}")
        return True
    except Exception as error:
        logger.error(f"Error in remove_from_cart: {error}")
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})