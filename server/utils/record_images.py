import traceback
from inspect import currentframe, getframeinfo
from models.BrowsedImageDataModel import BrowsedImageDataModel
from database.BASE import BaseDatabaseOperation
from fastapi import HTTPException  # , Request
import logging
import base64
import io
from PIL import Image
import boto3
from botocore.client import Config
from botocore.exceptions import NoCredentialsError
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def record_prompt_and_image(
    image: str,
    browsed_data: BrowsedImageDataModel,
    db_ops: BaseDatabaseOperation,
    user_id: str,
):
    try:
        if processAndSaveImage(image, browsed_data.img_id):
            result = await db_ops.create(user_id, browsed_data)
            logger.info(f"Image recorded: {result}")
            return True
    except Exception as error:
        logger.error(f"Error in record_prompt_and_image: {error}")
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
    

def processAndSaveImage(image_data: str, img_id: str):
    try:
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        compressed_image_bytes = buffered.getvalue()
        s3_client = boto3.client('s3', region_name='us-east-2',
                  config=Config(signature_version='s3v4'))

        image_key = f"{img_id}.jpg"
        s3_bucket_name = "browse-image-v2"  # Replace with your bucket name

        s3_client.upload_fileobj(
            io.BytesIO(compressed_image_bytes),
            s3_bucket_name,
            image_key,
            ExtraArgs={"ACL": "public-read", "ContentType": "image/jpeg", "ContentDisposition": "inline"},
        )
        return True
    except NoCredentialsError:
        logger.error("No AWS credentials found")
        raise HTTPException(status_code=500, detail={'message':"Missing Credentials",'currentFrame': getframeinfo(currentframe())})
    except Exception as error:
        logger.error(f"Error in processAndSaveImage: {error}")
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
