import logging
from database.BASE import BaseDatabaseOperation
from models import AnalysisModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisOperations(BaseDatabaseOperation):
    async def create(self, analysis_data: AnalysisModel) -> bool:
        try:
            analysis_data = analysis_data.model_dump()
            result = await self.db.analysis.insert_one(analysis_data)
            return result.inserted_id is not None
        except Exception as e:
            logger.critical(f"Error adding to analysis: {e}")
            return False

    async def update(self, task_id, data):
        # Implementation for updating analysis if needed
        pass

    async def remove(self, task_id: str) -> bool:
        # Implementation for removing analysis if needed
        pass

    async def get(self, task_id):
        pass