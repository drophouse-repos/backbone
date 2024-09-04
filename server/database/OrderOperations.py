from datetime import datetime, timedelta
import logging
from database.BASE import BaseDatabaseOperation
from models.OrderItemModel import OrderItem
from aws_utils import generate_presigned_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderOperations(BaseDatabaseOperation):
    async def create(self, user_id: str, order_info: OrderItem) -> bool:
        try:
            order_data = order_info.model_dump()
            orders_insert_result = await self.db.orders.insert_one(order_data)
            return (
                orders_insert_result.inserted_id is not None
            )
        except Exception as e:
            logger.critical(f"Error adding to order: {e}")
            return False

    async def remove(self, user_id: str, order_info: OrderItem) -> bool:
        try:
            order_id = order_info.order_id
            orders_delete_result = await self.db.orders.delete_one(
                {"order_id": order_id}
            )
            return (
                orders_delete_result.deleted_count > 0
            )
        except Exception as e:
            logger.critical(f"Error in removing order: {e}")
            return False

    async def update(self, user_id: str, updated_order_info: OrderItem):
        try:
            updated_order_data = updated_order_info.model_dump()
            order_id = updated_order_info.order_id

            orders_update_result = await self.db.orders.update_one(
                {"order_id": order_id}, {"$set": updated_order_data}
            )
            return (
                orders_update_result.modified_count > 0
            )
        except Exception as e:
            logger.critical(f"Error in updating order: {e}")
            return False

    async def get(self, user_id: str) -> list:
        try:
            orders = await self.db.orders.find({"user_id": user_id}, {'_id':0}).to_list(length=None)
            for idx in range(len(orders)):
                order = orders[idx]
                for item in order["item"]:
                    img_id = item["img_id"]
                    thumbnail_img_id = "t_" + img_id
                    item["thumbnail"] = generate_presigned_url(thumbnail_img_id, "thumbnails-cart")
            return orders
        except Exception as e:
            logger.error(f"Error retrieving orders: {e}")
            return []
        
    async def getByOrderID(self, order_id: str):
        try:
            raw_order = await self.db.orders.find_one({"order_id": order_id})
            order = OrderItem(**raw_order)
            return order
        except Exception as e:
            logger.error(f"Error retrieving orders: {e}")
            print("order not found")
            return
        
    async def update_order_status(self, user_id: str, order_id: str, new_status: str):
        try:
            orders_update_result = await self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": new_status}},
            )

            return (
                orders_update_result.modified_count > 0
            )
        except Exception as e:
            logger.critical(f"Error updating order status: {e}")
            return False
        
    async def remove_unpaid_order(self, user_id: str):
        try:
            one_hour_ago = datetime.now() - timedelta(hours=1)
            result = await self.db.orders.delete_many({
                "timestamp": {"$lt": one_hour_ago},
                "status": "unpaid"
            })
            return result
        except Exception as e:
            logger.critical(f"Error updating order status: {e}")
            return False

