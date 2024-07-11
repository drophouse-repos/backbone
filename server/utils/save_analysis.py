import traceback
from fastapi import HTTPException
from inspect import currentframe, getframeinfo
from models.AnalysisModel import AnalysisModel
from database.BASE import BaseDatabaseOperation
from database.AnalysisOperations import AnalysisOperations
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def save_analysis(
	analysis : AnalysisModel,
	db_ops: AnalysisOperations,
):
	try:
		record_analysis = os.environ.get("RECORD_ANALYSIS")
		if(record_analysis):
			result = await db_ops.create(analysis)
			logger.info(f"Analysis Saved : {result}")

		return True
	except Exception as error:
		logger.error(f"Error in record_prompt_and_image: {error}")
		raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
