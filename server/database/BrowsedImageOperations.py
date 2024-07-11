from database.BASE import BaseDatabaseOperation
from models import BrowsedImageDataModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrowsedImageOperations(BaseDatabaseOperation):
    async def create(self, user_id: str, image_data: BrowsedImageDataModel) -> bool:
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {"$push": {"browsed_images": image_data.model_dump()}},
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding browsed image: {e}")
            return False

    async def update(self, data):
        pass

    async def remove(self, user_id):
        pass

    async def get(self, user_id):
        pass


