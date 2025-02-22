from datetime import datetime, timedelta
import logging
from database.BASE import BaseDatabaseOperation
from database.SaltOperations import SaltOperations
from fastapi import Depends
from db import get_db_ops
from models.OrderItemModel import OrderItem
from aws_utils import generate_presigned_url
from models.UserInitModel import UserInitModel
from models.EncryptModel import EncryptModel
import uuid
from typing import Optional
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserOperations(BaseDatabaseOperation):
    async def get_or_set(self, encrypt_model: EncryptModel, salt_db_ops: SaltOperations) -> dict:
        try:
            if encrypt_model and encrypt_model.salt_id and encrypt_model.encrypted_data:
                user_id = await salt_db_ops.decrypt_and_remove(encrypt_model, remove_key=False)
                user_data = await self.db.users.find_one({"user_id": user_id}, {'_id': 0})
                if user_data:
                    user_data['user_id'] = encrypt_model.encrypted_data
                    user_data['key_id'] = encrypt_model.salt_id
                    return user_data
            else:
                epoch = datetime.now().strftime('%m%d%Y%H%M%S%f')[:-3]
                new_guest_id = str(uuid.uuid4())
                user_doc = UserInitModel(
                    user_id=new_guest_id, # store unencrypted guest id in db
                    email=f"Guest_{epoch}@drophouse.ai",
                    first_name="Guest",
                    last_name=epoch,
                    account_type='guest'
                )
                result = await self.db.users.insert_one(user_doc.dict())
                if result.inserted_id:
                    encrypt_model = await salt_db_ops.create_and_encrypt(new_guest_id)
                    user_dict = user_doc.dict()
                    user_dict['user_id'] = encrypt_model.encrypted_data
                    user_dict['key_id'] = encrypt_model.salt_id
                    return user_dict
                else:
                    raise Exception("Failed to insert new guest user")
        except Exception as e:
            logger.error(f"Error retrieving or setting user data: {e}")
            return {}

    async def get(self, user_id=None) -> list:
        try:
            # Fetch orders, either for a specific user or all orders if user_id is None
            query = {} if user_id is None else {"user_id": user_id}
            orders = await self.db.orders.find(query).to_list(length=None)

            if not orders:
                return []  

            # Prepare a list of user_ids from the orders to fetch user data in one go
            user_ids = {order['user_id'] for order in orders}
            users = await self.db.users.find({"user_id": {"$in": list(user_ids)}}).to_list(length=None)
            user_dict = {user['user_id']: user for user in users}  # Create a dictionary of users by user_id

            # Enrich each order with user data and signed URLs for images
            for order in orders:
                user_data = user_dict.get(order['user_id'], {})
                order['user_info'] = user_data  # Add user info to each order
                if "item" in order:  # Assuming each order has an 'items' key
                    for item in order["item"]:
                        img_id = item["img_id"]
                        thumbnail_img_id = "t_" + img_id
                        item["thumbnail"] = generate_presigned_url(thumbnail_img_id, "thumbnails-cart")
                        item["img_url"] = generate_presigned_url(img_id, "browse-image-v2")
            
            return orders
        except Exception as e:
            logger.error(f"Error retrieving orders with user data: {e}")
            return []

    async def get_userByEmail(self, user_email) -> list:
        try:
            user_data = await self.db.users.find_one({'email':user_email}, {'_id':0})
            if user_data:
                return user_data
            else:
                return []
        except Exception as e:
            logger.error(f"Error retrieving orders with user data: {e}")
            return []

    async def create(self, user_id: str, order_info: OrderItem) -> bool:
        pass

    async def remove(self, user_id: str, order_info: OrderItem) -> bool:
        pass
    
    async def update(self, user_id: str, order_id: str, new_status: str):
        try:
            orders_update_result = await self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": new_status}}
            )

            if orders_update_result.modified_count > 0:
                logger.info(f"Order status updated successfully for order ID {order_id}")
                return True
            else:
                logger.warning(f"No changes made to the order status for order ID {order_id}")
                return False

        except Exception as e:
            logger.critical(f"Error in updating order status for user {user_id} with order ID {order_id}: {e}")
            return False
    
    async def check_student_order(self, user_id:str):
        try:
            result = await self.db.users.find_one({
                "user_id": user_id,
                "orders": {
                    "$elemMatch": {
                        "status": {"$in": ["pending", "verified", "shipped", "delivering", "delivered"]}
                    }
                }
            })
            if result:
                return True
            else:
                return False 
        except Exception as e:
            logger.critical(f"Error checking student order status: {e}")
            return False

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