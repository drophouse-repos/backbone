import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks #, Request
import traceback
from inspect import currentframe, getframeinfo

# from fastapi.exceptions import RequestValidationError
# from fastapi.responses import JSONResponse
from pydantic import BaseModel
# from openai import OpenAI
# import asyncio
from dotenv import load_dotenv

# import os
# from PIL import Image
# from botocore.exceptions import NoCredentialsError
from db import get_db_ops
from database.BASE import BaseDatabaseOperation
from database.ShippingOperations import ShippingOperations
from fastapi import Depends

# from models.RetrieveModel import RetrieveModel
from models.ShippingModel import ShippingModel
from verification import verify_id_token

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

shipping_info_router = APIRouter()

@shipping_info_router.post("/update_shipping_information")
async def update_shipping_info(
    request_data: ShippingModel,
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(ShippingOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message': "User ID is required.", 'currentFrame': getframeinfo(currentframe())})
        userExist = await db_ops.checkUserExist(user_id)
        if not userExist:
            raise HTTPException(status_code=401, detail={'message': "User is not exist.", 'currentFrame': getframeinfo(currentframe())})

        result = await db_ops.update(user_id, request_data)
        return result
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in update shipping info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message': "Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})


@shipping_info_router.get("/get_shipping_information")
async def get_shipping_info(
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(ShippingOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message': "User ID is required.", 'currentFrame': getframeinfo(currentframe())})

        shipping_info = await db_ops.get(user_id)
        return {"shipping_info": shipping_info}
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in get shipping info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message': "Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})


@shipping_info_router.get("/get_basic_info")
async def get_basic_info(
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(ShippingOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message': "User ID is required.", 'currentFrame': getframeinfo(currentframe())})

        result = await db_ops.getBasicInfo(user_id)
        return result
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in get basic user info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message': "Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
    
class BasicInfoUpdateRequest(BaseModel):
    firstName: str
    lastName: str
    email: str
    phone: str

    
@shipping_info_router.post("/update_basic_info")
async def update_basic_info(
    request: BasicInfoUpdateRequest,
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(ShippingOperations)),
):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail={'message': "User ID is required.", 'currentFrame': getframeinfo(currentframe())})

        result = await db_ops.updateBasicInfo(user_id, request.firstName, request.lastName, request.email, request.phone)
        return result
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in get basic user info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message': "Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
