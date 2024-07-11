from fastapi import HTTPException
import logging
from database.BASE import BaseDatabaseOperation
from models import UserInitModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthOperations(BaseDatabaseOperation):
    async def update(self, user_id: str, user_data: UserInitModel) -> dict:
        # Check if the user exists
        user_exists = await self.db.users.find_one({"user_id": user_id})
        if user_exists:
            return 1
        else:
            try:
                user_document = user_data.model_dump()
                user_document["user_id"] = user_id  # Ensure user_id is in the document
                result = await self.db.users.insert_one(user_document)
                if result.inserted_id:
                    return 2
                else:
                    return -1
            except Exception as e:
                logger.error(f"Error creating new user: {e}")
                # Using HTTPException to signal an internal error
                raise HTTPException(status_code=500, detail="Database error")

    async def create(self, data):
        pass

    async def remove(self, user_id):
        pass

    async def get(self, user_id):
        pass
