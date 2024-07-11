import logging
import pgeocode
from database.BASE import BaseDatabaseOperation
from fastapi.responses import JSONResponse
from models import ShippingModel

# Set up the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShippingOperations(BaseDatabaseOperation):
    async def create(self, user_id: str, shipping_info: ShippingModel) -> bool:
        try:
            shipping_data = shipping_info.model_dump()
            result = await self.db.users.update_one(
                {"user_id": user_id}, {"$push": {"shipping_info": shipping_data}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.critical(f"Error saving shipping info: {e}")
            return False

    async def validate_zipcode_with_api(self, state_code: str, zipcode: str):
        nomi = pgeocode.Nominatim('us')
        location = nomi.query_postal_code(zipcode)
        
        if location.empty:
            return False
        
        return location.state_code == state_code

    async def update(self, user_id: str, shipping_info: ShippingModel):
        try:
            isMatched = await self.validate_zipcode_with_api(shipping_info.stateProvince, shipping_info.postalZipcode)
            if not isMatched:
                raise ValueError("State - zipcode doesn't match")

            shipping_data = shipping_info.model_dump()
            
            if shipping_info.addressType not in ["primary", "secondary"]:
                raise ValueError("Invalid address type")
            
            result = await self.db.users.update_one(
                {
                    "user_id": user_id,
                    "shipping_info.addressType": shipping_info.addressType,
                },
                {"$set": {"shipping_info.$": shipping_data}},
            )

            if result.modified_count == 0:
                existing_count = await self.db.users.count_documents({
                    "user_id": user_id,
                    "shipping_info.addressType": shipping_info.addressType
                })
                if existing_count >= 2:
                    raise ValueError(f"Cannot add more than one {shipping_info.addressType} address")
                
                result = await self.db.users.update_one(
                    {"user_id": user_id},
                    {"$push": {"shipping_info": shipping_data}}
                )

            return JSONResponse(
                status_code=200,
                content= {"detail": result.modified_count > 0}
            )
        except Exception as e:
            logger.critical(f"Error saving shipping info: {e}")
            return JSONResponse(
                status_code=422,
                content={"detail": str(e)},
            )

    async def remove(self, user_id: str, shipping_info: ShippingModel) -> bool:
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$pull": {
                        "shipping_info": {"addressType": shipping_info.AddressType}
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing shipping info: {e}")
        return False

    async def get(self, user_id):
        try:
            user = await self.db.users.find_one(
                {"user_id": user_id}, {"shipping_info": 1}
            )
            if user and "shipping_info" in user:
                return user["shipping_info"]
            else:
                return []
        except Exception as e:
            logger.error(f"Error retrieving shipping info: {e}")
            return []

    async def updateBasicInfo(self, user_id, firstName, lastName, email, phone):
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "first_name": firstName,
                        "last_name": lastName,
                        "email": email,
                        "phone_number": phone,
                    }
                }
            )
            if result.matched_count > 0:
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error retrieving basic user info: {e}")
            return []
        
    async def getBasicInfo(self, user_id):
        try:
            result = await self.db.users.find_one(
                {"user_id": user_id},
                {"first_name": 1, "last_name": 1, "email": 1, "phone_number": 1},
            )
            if result:
                basic_info = {
                    "firstName": result.get("first_name", ""),
                    "lastName": result.get("last_name", ""),
                    "email": result.get("email", ""),
                    "phone": result.get("phone_number", ""),
                }
                return basic_info
            else:
                return []
        except Exception as e:
            logger.error(f"Error retrieving basic user info: {e}")
            return []
        
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