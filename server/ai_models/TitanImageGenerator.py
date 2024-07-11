import traceback
from inspect import currentframe, getframeinfo
import base64
import os
import json
from random import random
from ai_models.ImageGenerator import ImageGenerator
import boto3
import asyncio
from botocore.exceptions import ClientError, BotoCoreError 
import botocore
from fastapi import HTTPException
from utils.error_check import handle_boto3_error
from datetime import datetime

class TitanImageGenerator(ImageGenerator):
    async def generate_single_image(self, idx, prompt, callback, user_id, task_id):
        start = datetime.now()
        try:
            bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1', aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"))
            accept = "application/json"
            content_type = "application/json"
            num = int(random() * 10000)
            body = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {
                    "text": prompt
                },
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "height": 512,
                    "width": 512,
                    "cfgScale": 8.0,
                    "seed": num
                }
            }
            json_body = json.dumps(body)
            byte_body = json_body.encode('utf-8')
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.invoke_model_with_args,bedrock, byte_body, accept, content_type)
            response_body = json.loads(response.get("body").read())
            base64_image = response_body.get("images")[0]            
            base64_bytes = base64_image.encode('ascii')
            image_bytes = base64.b64decode(base64_bytes)
            duration = datetime.now() - start
            callback(user_id, task_id, idx, False, duration, base64.b64encode(image_bytes).decode('utf-8'), 'titan')
            return idx, base64.b64encode(image_bytes).decode('utf-8'), 'titan'
        except ClientError as e:
            duration = datetime.now() - start
            callback(user_id, task_id, idx, True, duration)
            return handle_boto3_error(e)
        except BotoCoreError as e:
            duration = datetime.now() - start
            callback(user_id, task_id, idx, True, duration)
            raise HTTPException(status_code=500, detail={'message':f"AWS Botocore Error: {str(e)}",'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
        except Exception as e:
            duration = datetime.now() - start
            callback(user_id, task_id, idx, True, duration)
            raise HTTPException(status_code=500, detail={'message':f"generate with bedrock error{str(e)}",'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
        
    def invoke_model_with_args(self, bedrock, byte_body, accept, content_type):
        return bedrock.invoke_model(
            body=byte_body,
            modelId="amazon.titan-image-generator-v1",
            accept=accept,
            contentType=content_type
        )