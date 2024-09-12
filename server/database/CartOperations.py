import logging
from database.BASE import BaseDatabaseOperation
from models import ItemModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CartOperations(BaseDatabaseOperation):
    async def create(self, user_id: str, product_info: ItemModel) -> bool:
        try:
            product_data = product_info.model_dump()
            result = await self.db.users.update_one(
                {"user_id": user_id}, {"$push": {"cart": product_data}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.critical(f"Error adding to cart: {e}")
            return False

    async def remove(self, user_id: str, img_id: str) -> bool:
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id}, {"$pull": {"cart": {"img_id": img_id}}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.critical(f"Error removing image: {e}")
            return False

    async def update(self, uid, data):
        # Implementation for updating cart items if needed
        pass

    async def get(self, user_id: str) -> list:
        try:
            user = await self.db.users.find_one({"user_id": user_id}, {"cart": 1})
            if user and "cart" in user:
                return user["cart"]
            else:
                return []
        except Exception as e:
            logger.error(f"Error retrieving cart: {e}")
            return []


    async def get_cart_and_fav_number(self, user_id: str) -> dict:
        try:
            user = await self.db.users.find_one({"user_id": user_id}, {"cart": 1, "liked_images": 1})
            count = {}
            if user and "cart" in user:
                cart = user["cart"]
                count['cart_number'] = len(cart)
            else:
                count['cart_number'] = 0

            if user and "liked_images" in user:
                liked = user["liked_images"]
                count['liked_number'] = len(liked)
            else:
                count['liked_number'] = 0

            return count
        except Exception as e:
            logger.error(f"Error retrieving cart count: {e}")
            return 0

    async def get_cart_number(self, user_id: str) -> int:
        try:
            user = await self.db.users.find_one({"user_id": user_id}, {"cart": 1})
            if user and "cart" in user:
                cart = user["cart"]
                count = sum(1 for item in cart)
                return count
            else:
                return 0
        except Exception as e:
            logger.error(f"Error retrieving cart count: {e}")
            return 0


    async def duplicate_images(self, user_id: str, img_id: str) -> bool:
        try:
            exists = await self.db.users.find_one(
                {
                    "user_id": user_id,
                    "cart.img_id": img_id
                },
                {"_id": 1}
            )
            return bool(exists)
        except Exception as e:
            logger.critical(f"Error checking for duplicate images in cart: {e}")
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
