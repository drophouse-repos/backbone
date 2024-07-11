from database.BASE import BaseDatabaseOperation
from models import PromptModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptOperations(BaseDatabaseOperation):
    async def create(self, prompt_data: PromptModel) -> bool:
        try:
            prompt_data = prompt_data.model_dump()
            result = await self.db.prompts.insert_one(prompt_data)
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Error adding browsed image: {e}")
            return False

    async def update(self, data):
        pass

    async def remove(self, user_id):
        pass

    async def get(self, user_id):
        pass


