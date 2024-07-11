import logging
import traceback
from inspect import currentframe, getframeinfo

from db import get_db_ops
from database.BASE import BaseDatabaseOperation
from models.OrganizationModel import OrganizationModel
from database.OrganizationOperation import OrganizationOperation
from fastapi import APIRouter, HTTPException, Depends

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
