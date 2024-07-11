import hashlib
import logging
from cryptography.fernet import Fernet
import uuid
from database.BASE import BaseDatabaseOperation
from models.EncryptModel import EncryptModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SaltOperations(BaseDatabaseOperation):
    async def create(self, data):
        pass

    async def remove(self, salt_id):
        pass

    async def update(self, salt_id, data):
        pass

    async def get(self, salt_id):
        pass
    
    async def create_and_encrypt(self, data: str) -> EncryptModel:
        key = Fernet.generate_key()
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data.encode())
        encrypted_data = encrypted_data.decode()
        key_id = str(uuid.uuid4())
        salt_document = {
            "_id": key_id,
            "salt": key,
        }
        await self.db.salts.insert_one(salt_document)
        return EncryptModel(salt_id=key_id, encrypted_data=encrypted_data)

    async def decrypt_and_remove(self, salt_info: EncryptModel) -> str:
        key_id = salt_info.salt_id
        key_document = await self.db.salts.find_one({"_id": key_id})
    
        if not key_document:
            raise ValueError("Key not found")
        
        key_document = key_document['salt']
        fernet = Fernet(key_document)
        decrypted_data = fernet.decrypt(salt_info.encrypted_data.encode())
        decrypted_data = decrypted_data.decode()

        await self.db.salts.delete_one({"_id": key_id})
        return decrypted_data