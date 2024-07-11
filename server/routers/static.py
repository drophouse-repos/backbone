from fastapi import APIRouter, Path
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import asyncio
from dotenv import load_dotenv
import os
from PIL import Image
from botocore.exceptions import NoCredentialsError
import stripe


load_dotenv()
IMAGES_DIRECTORY = "images"
static_router = APIRouter()

@static_router.get("/image/{image_name}")
async def get_image(image_name: str = Path(..., title="The name of the image file")):
    image_path = os.path.join(IMAGES_DIRECTORY, image_name)    
    try:
        return FileResponse(image_path)
    except FileNotFoundError:
        return JSONResponse(content={"error": "Image not found"}, status_code=404)

