import traceback
from inspect import currentframe, getframeinfo
import base64
from datetime import datetime
import difflib
import io
import json
from typing import Callable, Optional
import uuid
import openai
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from openai import AsyncOpenAI, OpenAI
from dotenv import load_dotenv
import os
from fastapi import Depends
import logging
from models.EncryptModel import EncryptModel
from db import get_db_ops
from models.BrowsedImageDataModel import BrowsedImageDataModel
from models.AnalysisModel import AnalysisModel
from database.BrowsedImageOperations import BrowsedImageOperations
from database.BASE import BaseDatabaseOperation
from database.SaltOperations import SaltOperations
from database.PromptOperations import PromptOperations
from database.AnalysisOperations import AnalysisOperations
from ai_models.ImageGenerator import ImageGenerator
from ai_models.OpenAIImageGenerator import OpenAIImageGenerator
from ai_models.TitanImageGenerator import TitanImageGenerator
from ai_models.StableDiffusionGenerator import StableDiffusionGenerator
from utils.error_check import handle_openai_error
from utils.record_images import record_prompt_and_image
from utils.save_analysis import save_analysis
from verification import verify_id_token
from botocore.client import Config
import asyncio
from email_service.EmailService import EmailService
from profanity_check import predict, predict_prob
from redis import get_redis_database

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
email_service = EmailService()
imagen_router = APIRouter()

class BrowseImageDataRequest(BaseModel):
    prompt: str

class StorePromptRequest(BaseModel):
    prompt1: str
    prompt2: str
    prompt3: str
    chosenNum: int

class AskGPTRequest(BaseModel):
    prompt: str
    user_key: Optional[str] = None
    
class ImageRequest(BaseModel):
    idx: int
    prompt: str
    task_id: str
    user_key: Optional[str] = None

key = os.environ.get("OPENAI_KEY")
client = AsyncOpenAI(api_key=key)
def get_ai_model(class_type: type[ImageGenerator]) -> Callable:
    def dependency():
        return class_type()
    return dependency

async def set_redis_task(user_id, task_id, task_info):
    redis = get_redis_database()
    await redis.hset(f"user:{user_id}:tasks", task_id, json.dumps(task_info))

async def set_redis_images(user_id, task_id, index, task_info):
    redis = get_redis_database()
    await redis.hset(f"user:{user_id}:tasks:{task_id}:images", index, json.dumps(task_info))

async def get_redis_task(user_id, task_id):
    redis = get_redis_database()   
    task_info = await redis.hget(f"user:{user_id}:tasks", task_id)
    return json.loads(task_info) if task_info else None

async def get_redis_images(user_id, task_id, index):
    redis = get_redis_database()   
    task_info = await redis.hget(f"user:{user_id}:tasks:{task_id}:images", index)
    return json.loads(task_info) if task_info else None

async def delete_redis_task(user_id, task_id):
    redis = get_redis_database()   
    await redis.hdel(f"user:{user_id}:tasks", task_id)
    for i in range(6):
        await redis.hdel(f"user:{user_id}:tasks:{task_id}:images", str(i))

async def clear_taskstorage(user_id, task_id):
    redis = get_redis_database()   
    await delete_redis_task(user_id, task_id)

task_timeout = 600 
async def schedule_task_deletion(user_id, task_id, task_timeout):
    await asyncio.sleep(task_timeout)
    await clear_taskstorage(user_id, task_id)

async def record_analysis(background_tasks, analysis_db_ops, user_id, task_id, idx):
    task_info = await get_redis_task(user_id, task_id)
    if task_info:
        analysis_data = AnalysisModel(
                task_id= task_id,
                index= idx,
                time_taken= json.dumps(task_info['time_taken'] if 'time_taken' in task_info else {}),
                prompts= task_info['prompts'],
                status= json.dumps(task_info['image_status'])
            )
        background_tasks.add_task(
            save_analysis,
            analysis= analysis_data,
            db_ops=analysis_db_ops
        )     
        await clear_taskstorage(user_id, task_id)


async def task_callback(user_id, task_id, index, isFailed, duration, image=None, model=None):
    logger.info(f"Image Generation index: [{index}], took -> {duration.total_seconds():.2f} seconds")
    redis = get_redis_database()
    lock_key = f"lock:{user_id}:{task_id}"
    
    try:
        lock = await redis.setnx(lock_key, "locked")
        if lock:
            try:
                await redis.expire(lock_key, 10)  # Set an expiration to avoid deadlock

                task_info = await get_redis_task(user_id, task_id)
                if task_info:
                    if 'image_status' not in task_info:
                        task_info['image_status'] = {}
                    if 'time_taken' not in task_info:
                        task_info['time_taken'] = {}
                    # if 'image' not in task_info:
                        # task_info['image'] = {}

                    if image is not None and model is not None:
                        # task_info['image'][index] = (index, image, model)
                        await set_redis_images(user_id, task_id, index, (index, image, model))

                    task_info['time_taken'][index] = f"{duration.total_seconds():.2f} seconds"
                    task_info['image_status'][index] = 'completed' if not isFailed else 'failed'
                    
                    await set_redis_task(user_id, task_id, task_info)
            except Exception as e:
                logger.info('Redis - setting data error (1)', str(e))
            finally:
                await redis.delete(lock_key)
        else:
            logger.warning("Failed to acquire lock, retrying...")
            await asyncio.sleep(1)
            await task_callback(user_id, task_id, index, isFailed, duration, image, model)
    except Exception as e:
        logger.info('Redis - setting data error (2)', str(e))
    finally:
        pass

async def generate_prompts(prompt: str):
    
    messages = [
        {"role": "system", "content": """You are a prompt engineering assistant with a focus on optimizing prompts for generating 
         high-quality images. You will be given a user prompt, and you must return JSON with three prompts: the original user prompt, an 
         enhanced prompt, and a super-enhanced prompt. The enhanced prompt should include every word of the original prompt and 
         not exceed 15-17 words. The super-enhanced prompt should also include every word of the original prompt and have 25-30 words. 
         Remember to only return valid JSON, no more or less than three prompts. 
         Your suggestions should increase the original prompt's specificity and detail to generate vivid and engaging images. The structure should be
         as follows:
         {
            "Prompts": [
                {
                    "Prompt1": ""
                },
                {
                    "Prompt2": ""
                },
                {
                    "Prompt3": ""
                }
            ]
        }"""},  
        {
        "role": "user",
        "content": """A majestic waterfall in the forest."""
        },
        {
        "role": "assistant",
        "content": """{
            "Prompts": [
                {
                    "Prompt1": "A majestic waterfall in the forest."
                },
                {
                    "Prompt2": "A majestic waterfall cascading down rocks, surrounded by lush forest."
                },
                {
                    "Prompt3": "A majestic waterfall in the forest, cascading down rocks into a clear pool, surrounded by thick, lush trees under a bright sky."
                }
            ]
        }"""
        },
        {
        "role": "user",
        "content": prompt
        }
    ]
    try:
        completion = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        response_format= { "type": "json_object" }
        )
    except openai.OpenAIError as e:
        handle_openai_error(e)      
    return completion.choices[0].message.content
    
@imagen_router.post("/ask_gpt")
async def generate_text(request: AskGPTRequest, 
                        retry: int = 0,
                        ai_model_primary = Depends(get_ai_model(TitanImageGenerator)),
                        ai_model_secondary = Depends(get_ai_model(OpenAIImageGenerator)),
                        salt_db_ops: SaltOperations = Depends(get_db_ops(SaltOperations)),
                        user_id: str = Depends(verify_id_token),                       
                        ):
    try:
        if request.user_key: # user_key only exists for guest users
            user_id = await salt_db_ops.decrypt_and_remove(EncryptModel(salt_id=request.user_key, encrypted_data=user_id), remove_key=False)
        if len(request.prompt) > 600:   
            raise HTTPException(status_code=400, detail={'message':"Prompt is too long",'currentFrame': getframeinfo(currentframe())})
        profane = predict([request.prompt])   
        if (profane[0] == 1):
            raise HTTPException(status_code=400, detail={'message':"Profanity detected in prompt",'currentFrame': getframeinfo(currentframe())})                
        response_text = await generate_prompts(request.prompt)    
        response_json, message = validate_structure(response_text)
        if not response_json:
            if retry < 3:
                return await generate_text(request, retry=retry+1, ai_model_primary=ai_model_primary, ai_model_secondary=ai_model_secondary, salt_db_ops=salt_db_ops, user_id=user_id)
            else:
                raise HTTPException(status_code=409, detail={'message':"The chance of this not working is 1 in a million, but it just happened. Please try again.",'currentFrame': getframeinfo(currentframe())}) 
        
        task_id = str(uuid.uuid4())
        enhanced_prompts = [response_json['Prompts'][i][f'Prompt{i+1}'] for i in range(3)]      
        image_tasks = (
            [ai_model_primary.generate_single_image(idx, prompt, task_callback, user_id, task_id) for idx, prompt in enumerate(enhanced_prompts)] +
            [ai_model_secondary.generate_single_image(idx+3, prompt, task_callback, user_id, task_id) for idx, prompt in enumerate(enhanced_prompts)]
        )
        task = asyncio.create_task(
        handle_image_generation(task_id, image_tasks, user_id),
            name=f"image-gen-{task_id}" 
        )

        task_info = {
            "status": "processing",
            "prompts": enhanced_prompts
        }
        task_info["image_status"] = {}
        for i in range(len(enhanced_prompts)):
            task_info["image_status"][i] = 'processing'
            task_info["image_status"][i+3] = 'processing'

        await set_redis_task(user_id, task_id, task_info)

        asyncio.create_task(schedule_task_deletion(user_id, task_id, task_timeout))
        response_json['task_id'] = task_id
        return {"response": response_json}
    except openai.OpenAIError as e:
        handle_openai_error(e)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in assigning image task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':f"Error in assigning image task: {str(e)}", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

async def handle_image_generation(task_id, image_tasks, user_id):
    start = datetime.now()
    await asyncio.gather(*image_tasks, return_exceptions=True)
    duration = datetime.now() - start
    logger.info(f"Success - Total image Generation took -> {duration.total_seconds():.2f} seconds")
    
    redis = get_redis_database()
    lock_key = f"lock:{user_id}:{task_id}"
    try:
        lock = await redis.setnx(lock_key, "locked")
        if lock:
            try:
                await redis.expire(lock_key, 10)  # Set an expiration to avoid deadlock
                
                task_info = await get_redis_task(user_id, task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["total_time_taken"] = f"{duration.total_seconds():.2f} seconds"
                    await set_redis_task(user_id, task_id, task_info)

            except Exception as e:
                logger.info('Redis - setting data error (3)', str(e))
            finally:
                await redis.delete(lock_key)
        else:
            logger.warning("Failed to acquire lock, retrying...")
            await asyncio.sleep(1)
            await task_callback(user_id, task_id, index, isFailed, duration, image, model)
    except Exception as e:
        logger.info('Redis - setting data error (4)', str(e))
    finally:
        pass
        
@imagen_router.post("/get_image")
async def get_generated_image(
    request: ImageRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(BrowsedImageOperations)),
    salt_db_ops: SaltOperations = Depends(get_db_ops(SaltOperations)),
    analysis_db_ops: BaseDatabaseOperation = Depends(get_db_ops(AnalysisOperations)),
):
    try:
        if request.user_key: # user_key only exists for guest users
            user_id = await salt_db_ops.decrypt_and_remove(EncryptModel(salt_id=request.user_key, encrypted_data=user_id), remove_key=False)
        photo = None
        task_id = request.task_id
        task_info = await get_redis_task(user_id, task_id)
        if not task_info:
            raise HTTPException(status_code=400, detail={'message':"Please try again",'currentFrame': getframeinfo(currentframe())})

        image_status = task_info['image_status']
        if task_info['status'] == 'processing':
            if image_status != None and (image_status[str(request.idx)] == 'completed' and image_status[str(request.idx + 3)] == 'completed'):
                pass
            else:
                counter = 0
                max_wait = 60 # worst case wait for 60 seconds
                while (
                    task_info != None and
                    task_info['status'] == 'processing' and
                    (
                        image_status[str(request.idx)] == "processing" or
                        image_status[str(request.idx + 3)] == 'processing'
                    ) and
                    counter < max_wait
                ):
                    counter = counter + 1
                    await asyncio.sleep(1)
                    task_info = await get_redis_task(user_id, task_id)
                    if task_info:
                        image_status = task_info['image_status']

                task_info = await get_redis_task(user_id, task_id)
                if not task_info:
                    raise HTTPException(status_code=400, detail={'message':"Please try again",'currentFrame': getframeinfo(currentframe())})
                image_status = task_info['image_status']

        if task_info['status'] == 'processing' and (image_status != None and (image_status[str(request.idx)] == 'failed' and image_status[str(request.idx + 3)] == 'failed')):
            logger.error(f"Both primary and secondary images failed to generate: Prompt Violates Our Content Policy (1)", exc_info=True)
            await record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
            raise HTTPException(status_code=400, detail={'message':"Prompt Violates Our Content Policy",'currentFrame': getframeinfo(currentframe())})

        if task_info['status'] == 'completed' or (image_status != None and (image_status[str(request.idx)] == 'completed' or image_status[str(request.idx + 3)] == 'completed')):
            images = {
                str(request.idx): await get_redis_images(user_id, task_id, str(request.idx)),
                str(request.idx+3): await get_redis_images(user_id, task_id, str(request.idx+3))
            }
            # images = task_info['image']
            if images and images != None:
                primary_image = images[str(request.idx)] if str(request.idx) in images else None
                if isinstance(primary_image, Exception) or primary_image == None:
                    secondary_image = images[str(request.idx+3)] if str(request.idx+3) in images else None
                    if isinstance(secondary_image, Exception) or secondary_image == None:
                        logger.error(f"Both primary and secondary images failed to generate: Prompt Violates Our Content Policy (2)", exc_info=True)
                        await record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
                        raise HTTPException(status_code=400, detail={'message':"Prompt Violates Our Content Policy",'currentFrame': getframeinfo(currentframe())})
                    else:
                        photo = {"idx": request.idx + 3, "photo": secondary_image[1], "name": secondary_image[2]}
                else:
                    photo = {"idx": request.idx, "photo": primary_image[1], "name": primary_image[2]}
                img_id = str(uuid.uuid4())       
                timestamp = datetime.utcnow()

                browsed_data = BrowsedImageDataModel(
                    img_id=img_id, prompt=request.prompt, timestamp=timestamp
                )
                background_tasks.add_task(
                    record_prompt_and_image,
                    image=photo['photo'],
                    browsed_data=browsed_data,
                    db_ops=db_ops,
                    user_id=user_id,
                )
                await record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
                return {"photo": photo['photo'], "img_id": img_id}
            else:
                await record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
                raise HTTPException(status_code=400, detail={'message':"Images not found",'currentFrame': getframeinfo(currentframe())})
        elif task_info['status'] == 'failed':
            await record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
            raise HTTPException(status_code=500, detail={'message':"Image generation failed",'currentFrame': getframeinfo(currentframe())})
        else:
            await record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
            raise HTTPException(status_code=500, detail={'message':"Unexpected task status",'currentFrame': getframeinfo(currentframe())})
    except openai.OpenAIError as e:
        handle_openai_error(e)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in get_image: {str(e)}", exc_info=True)
        await record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
        raise HTTPException(status_code=500, detail={'message':f"Internal Server Error: {str(e)}", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@imagen_router.post("/store_prompt")
async def store_prompt(
    request: StorePromptRequest,
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(PromptOperations)),
):
    result = await db_ops.create(request)
    return result

def validate_structure(response_str):
    try:
        data = json.loads(response_str)
        if "Prompts" not in data:
            return False, "Missing 'Prompts' key."
        if not isinstance(data["Prompts"], list):
            return False, "'Prompts' must be a list."
        expected_keys = ["Prompt1", "Prompt2", "Prompt3"]
        actual_keys = [key for item in data["Prompts"] for key in item]
        if sorted(actual_keys) != sorted(expected_keys):
            return False, "Each dictionary combined in 'Prompts' must contain 'Prompt1', 'Prompt2', and 'Prompt3'."
        return data, "Valid JSON and structure."
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, f"An error occurred: {str(e)}"
