import logging
import traceback
from inspect import currentframe, getframeinfo
from pydantic import BaseModel
from db import get_db_ops
from database.BASE import BaseDatabaseOperation
from models.OrganizationModel import OrganizationModel
from database.OrganizationOperation import OrganizationOperation
from fastapi import APIRouter, HTTPException, Depends
from aws_utils import generate_presigned_url
import requests
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

org_router = APIRouter()

@org_router.post("/organisation_list")
async def organisation_list(
	db_ops: BaseDatabaseOperation = Depends(get_db_ops(OrganizationOperation)),
):
	try:
		result = await db_ops.get()
		return result;
	except Exception as e:
		logger.error(f"Error in getting Organization: {str(e)}", exc_info=True)
		raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@org_router.post("/create_organisation")
async def create_organisation(
	request : OrganizationModel,
	db_ops: BaseDatabaseOperation = Depends(get_db_ops(OrganizationOperation)),
):
	try:
		result = await db_ops.create(request)
		return result;
	except Exception as e:
		logger.error(f"Error in creating Organization: {str(e)}", exc_info=True)
		raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

class org_id(BaseModel):
    org_id: str

class BucketRequest(BaseModel):
    img_id: str

@org_router.post("/get_organisation_by_id")
async def get_organisation_by_id(
    request : org_id,
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(OrganizationOperation)),
):
    try:
        result = await db_ops.get_org_by_id(request.org_id)
        return result;
    except Exception as e:
        logger.error(f"Error in creating Organization: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@org_router.post("/convert_bucketurl_to_base64")
async def convert_bucketurl_to_base64(
    request: BucketRequest,
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(OrganizationOperation)),
):
    try:
        img_id = request.img_id
        presigned_url = generate_presigned_url(img_id, "drophouse-skeleton")
        response = requests.get(presigned_url)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type')
            
            if not content_type or not content_type.startswith("image/"):
                raise ValueError(f"Invalid content type: {content_type}")
            
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            data_url = f"data:{content_type};base64,{image_base64}"
            
            return {"data_url": data_url}
        else:
            raise ValueError(f"Error downloading image. Status code: {response.status_code}")
    
    except Exception as e:
        print(f"Error processing bucket URL: {e}")
        return {"error": str(e)}