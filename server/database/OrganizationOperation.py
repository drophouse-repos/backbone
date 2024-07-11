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