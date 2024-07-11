import logging
from database.BASE import BaseDatabaseOperation
from models import ItemModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LikedImageOperations(BaseDatabaseOperation):
    async def create(self, user_id: str, product_info) -> bool:
        try:
            product_data = product_info.model_dump()
            result = await self.db.users.update_one(
                {"user_id": user_id}, {"$push": {"liked_images": product_data}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.critical(f"Error saving image: {e}")
            return False

    async def remove(self, user_id: str, product_info: ItemModel) -> bool:
        try:
            img_id = product_info.img_id
            result = await self.db.users.update_one(
                {"user_id": user_id}, {"$pull": {"liked_images": {"img_id": img_id}}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.critical(f"Error removing image: {e}")
            return False

    async def update(self, uid, data):
        pass

    async def get(self, user_id: str) -> list:
        try:
            user = await self.db.users.find_one(
                {"user_id": user_id}, {"liked_images": 1}
            )
            if user and "liked_images" in user:
                return user["liked_images"]
            else:
                return []
        except Exception as e:
            logger.error(f"Error retrieving liked images: {e}")
            return []
        
    async def duplicate_images(self, user_id: str, img_id: str) -> bool:
        try:
            img_id_prefix = img_id.split("_")[0]
            exists = await self.db.users.find_one(
                {
                    "user_id": user_id,
                    "liked_images": {
                        "$elemMatch": {"img_id": {"$regex": f"^{img_id_prefix}(_|$)"}}
                    },
                }
            )
            return bool(exists)
        except Exception as e:
            logger.critical(f"Error checking for duplicate images in liked images: {e}")
            return False
    
    async def checkUserExist(self, user_id):
        try:
            user = await self.db.users.find_one(
                {"user_id": user_id},
            )
            if user:
                return True
            else: return False
        except Exception as e:
            logger.error(f"Error retrieving user info: {e}")
            return False
