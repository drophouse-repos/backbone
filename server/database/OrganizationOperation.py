import logging
from database.BASE import BaseDatabaseOperation
from models import OrganizationModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrganizationOperation(BaseDatabaseOperation):
	async def create(self, org_info: OrganizationModel) -> bool:
		try:
			org_data = org_info.model_dump()
			# org_data.org_id = str(uuid.uuid4())
			result = await self.db.organizations.insert_one(org_data)
			return result.modified_count > 0
		except Exception as e:
			logger.critical(f"Error adding organizations data to db : {e}")
			return False

	async def remove(self) -> bool:
		pass

	async def update(self, org_info:OrganizationModel):
		try:
			org_data = org_info.model_dump()
			org_id = org_info.org_id

			result = await self.db.organizations.update_one(
				{"org_id": org_id},
				{"$set": org_data}
			)
			return result.modified_count > 0
		except Exception as e:
			logger.critical(f"Error in updating organization: {e}")
			return False

	async def get_live_count(self) -> dict:
	    try:
	        result = {
	            'user_count': 0,
	            'org_count': 0,
	            'design_count': 0
	        }

	        users = await self.db.users.find({}, {"_id": 1, "browsed_images": 1}).to_list(length=None)
	        if users:
	            result['user_count'] = len(users)
	            result['design_count'] = sum(len(user.get('browsed_images', [])) for user in users)

	        result['org_count'] = await self.db.organizations.count_documents({})
	        return result

	    except Exception as e:
	        logger.error(f"Error retrieving live counts: {e}")
	        return {
	            'user_count': 0,
	            'org_count': 0,
	            'design_count': 0
	        }

	async def get(self):
		try:
			org_data = await self.db.organizations.find({}, {'_id':0}).to_list(length=None)
			if org_data:
				org_dict = {org['org_id']: org for org in org_data}
				return org_dict
			else:
				return {}
		except Exception as e:
			logger.error(f"Error retrieving prices: {e}")
			return []
	async def get_org_by_id(self, org_id: str) -> dict:
		try:
			org_data = await self.db.organizations.find_one({"org_id": org_id}, {'_id': 0})
			if org_data:
				return org_data
			else:
				logger.warning(f"No organization found with org_id: {org_id}")
				return {}
		except Exception as e:
			logger.error(f"Error retrieving organization by ID: {e}")
			return {}