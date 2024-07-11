from fastapi import APIRouter, HTTPException, BackgroundTasks  # , Request
from pydantic import BaseModel
import os
import traceback
from inspect import currentframe, getframeinfo
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import subprocess
from dotenv import load_dotenv
from aws_utils import generate_presigned_url, processAndSaveImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import Depends
import logging
from db import get_db_ops
from models.EmailModel import EmailModel
from email_service.EmailService import EmailService
from utils.error_check import checkUnprocessibleEntity
from verification import verify_id_token

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
key = os.environ.get("SENDGRID_API_KEY")

email_router = APIRouter()
email_service = EmailService(sendgrid_key=key)

@email_router.post("/send_email")
async def send_email(
    request_data: EmailModel,
    user_id: str = Depends(verify_id_token),
    ):
    if not user_id:
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
    try:
        to_mail = os.environ.get("TO_EMAIL") if os.environ.get("TO_EMAIL") else "support@drophouse.art"
        email_service.send_email(
            from_email='bucket@drophouse.art',
            to_email=to_mail,
            subject='Drophouse User Feedback / Inquiry',
            name=request_data.name,
            email=request_data.email,
            message_body=request_data.message
        )
    except HTTPException as http_exc:
        checkUnprocessibleEntity(http_exc)
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
