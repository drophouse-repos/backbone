import logging
from database.BASE import BaseDatabaseOperation
from models import OrganizationModel
from aws_utils import generate_presigned_url
import requests
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_presigned_url_to_base64(presigned_url: str):
	response = requests.get(presigned_url)
	if response.status_code == 200:
		content_type = response.headers.get('Content-Type')
		
		if not content_type or not content_type.startswith("image/"):
			print(f"Invalid content type: {content_type}")
			return presigned_url
		
		image_base64 = base64.b64encode(response.content).decode('utf-8')
		data_url = f"data:{content_type};base64,{image_base64}"
		
		return data_url
	else:
		print(f"Error downloading image. Status code: {response.status_code}")
		return presigned_url

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
	async def get_org_by_id(self, org_id: str) -> dict:
		try:
			org_data = await self.db.organizations.find_one({"org_id": org_id}, {'_id': 0})
			if org_data:
				bucket_name = 'drophouse-skeleton'

				if 'mask' in org_data and org_data['mask'] != None and org_data['mask'] != '' and 'data:image' not in org_data['mask']:
					org_data['mask'] = generate_presigned_url(org_data['mask'], bucket_name)
				if 'logo' in org_data and org_data['logo'] != None and org_data['logo'] != '' and 'data:image' not in org_data['logo']:
					org_data['logo'] = generate_presigned_url(org_data['logo'], bucket_name)
				if 'greenmask' in org_data and org_data['greenmask'] != None and org_data['greenmask'] != '' and 'data:image' not in org_data['greenmask']:
					org_data['greenmask'] = generate_presigned_url(org_data['greenmask'], bucket_name)
				if 'favicon' in org_data and org_data['favicon'] != None and org_data['favicon'] != '' and 'data:image' not in org_data['favicon']:
					org_data['favicon'] = generate_presigned_url(org_data['favicon'], bucket_name)

				for designs in org_data['landingpage']:
					if 'asset' in designs and designs['asset'] != None and designs['asset'] != '' and 'data:image' not in designs['asset']:
						designs['asset'] = generate_presigned_url(designs['asset'], bucket_name)
					if 'asset_back' in designs and designs['asset_back'] != None and designs['asset_back'] != '' and 'data:image' not in designs['asset_back']:
						designs['asset_back'] = generate_presigned_url(designs['asset_back'], bucket_name)

				for product in org_data['products']:
					if 'mask' in product and product['mask'] != None and product['mask'] != '' and 'data:image' not in product['mask']:
						product['mask'] = convert_presigned_url_to_base64(generate_presigned_url(product['mask'], bucket_name))
					if 'defaultProduct' in product and product['defaultProduct'] != None and product['defaultProduct'] != '' and 'data:image' not in product['defaultProduct']:
						product['defaultProduct'] = convert_presigned_url_to_base64(generate_presigned_url(product['defaultProduct'], bucket_name))

					for index in product['colors']:
						if 'front' in product['colors'][index]['asset'] and product['colors'][index]['asset'] != None and product['colors'][index]['asset']['front'] != '' and 'data:image' not in product['colors'][index]['asset']:
							product['colors'][index]['asset']['front'] = convert_presigned_url_to_base64(generate_presigned_url(product['colors'][index]['asset']['front'], bucket_name))
						if 'back' in product['colors'][index]['asset'] and product['colors'][index]['asset'] != None and product['colors'][index]['asset']['back'] != '' and 'data:image' not in product['colors'][index]['asset']:
							product['colors'][index]['asset']['back'] = convert_presigned_url_to_base64(generate_presigned_url(product['colors'][index]['asset']['back'], bucket_name))
				
				return org_data
			else:
				logger.warning(f"No organization found with org_id: {org_id}")
				return {}
		except Exception as e:
			logger.error(f"Error retrieving organization by ID: {e}")
			return {}