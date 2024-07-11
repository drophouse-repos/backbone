import traceback
from inspect import currentframe, getframeinfo
import base64
from datetime import datetime
import difflib
import io
import json
from typing import Callable
import uuid
import openai
from fastapi import APIRouter, HTTPException, BackgroundTasks  # , Request
from pydantic import BaseModel
from openai import AsyncOpenAI, OpenAI
from dotenv import load_dotenv
import os
from fastapi import Depends
import logging
from db import get_db_ops
from models.BrowsedImageDataModel import BrowsedImageDataModel
from models.AnalysisModel import AnalysisModel
from database.BrowsedImageOperations import BrowsedImageOperations
from database.BASE import BaseDatabaseOperation
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
import json
from botocore.client import Config
import asyncio
import threading
from email_service.EmailService import EmailService
from profanity_check import predict, predict_prob

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
    
class ImageRequest(BaseModel):
    idx: int
    prompt: str
    task_id: str

key = os.environ.get("OPENAI_KEY")
client = AsyncOpenAI(api_key=key)
task_storage = {}

## TODO: add a timeout for each task. 
def get_ai_model(class_type: type[ImageGenerator]) -> Callable:
    def dependency():
        return class_type()
    return dependency

@imagen_router.post("/task_storage_analytics")
def get_task_num():
    activeTasks = 0
    for user_id in task_storage:
        if user_id in task_storage:
            activeTasks = activeTasks + len(task_storage[user_id])
    return f"Active Users Count: {len(task_storage)}, Active Tasks Count: {activeTasks}" 

task_timeout = 600 
def clear_taskstorage(user_id, task_id):
    if user_id and task_id:
        if user_id in task_storage and task_id in task_storage[user_id]:
            del task_storage[user_id][task_id]

        if user_id in task_storage and len(task_storage[user_id]) == 0:
            del task_storage[user_id]

def record_analysis(background_tasks, analysis_db_ops, user_id, task_id, idx):
    if user_id in task_storage and task_id in task_storage[user_id]:
        analysis_data = AnalysisModel(
                task_id= task_id,
                index= idx,
                time_taken= json.dumps(task_storage[user_id][task_id]['time_taken']),
                prompts= task_storage[user_id][task_id]['prompts'],
                status= json.dumps(task_storage[user_id][task_id]['image_status'])
            )
        background_tasks.add_task(
            save_analysis,
            analysis= analysis_data,
            db_ops=analysis_db_ops
        )     
        del task_storage[user_id][task_id]

def task_callback(user_id, task_id, index, isFailed, duration, image=None, model=None):
    logger.info(f"Image Generation index: [{index}], took -> {duration.total_seconds():.2f} seconds")
    if user_id in task_storage and task_id in task_storage[user_id]:
        if 'image_status' not in task_storage[user_id][task_id]:
            task_storage[user_id][task_id]['image_status'] = {}
        if 'time_taken' not in task_storage[user_id][task_id]:
            task_storage[user_id][task_id]['time_taken'] = {}
        if 'image' not in task_storage[user_id][task_id]:
            task_storage[user_id][task_id]['image'] = {}

        task_storage[user_id][task_id]['time_taken'][index] = f"{duration.total_seconds():.2f} seconds"
        task_storage[user_id][task_id]['image_status'][index] = 'completed' if not isFailed else 'failed'
        if image != None and model != None:
            task_storage[user_id][task_id]['image'][index] = (index, image, model)
        if not task_storage[user_id][task_id]["events"][index].is_set():
            task_storage[user_id][task_id]["events"][index].set()

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
                        user_id: str = Depends(verify_id_token),                       
                        ):
    try:
        if len(request.prompt) > 600:   
            raise HTTPException(status_code=400, detail={'message':"Prompt is too long",'currentFrame': getframeinfo(currentframe())})
        profane = predict([request.prompt])   
        if (profane[0] == 1):
            raise HTTPException(status_code=400, detail={'message':"Profanity detected in prompt",'currentFrame': getframeinfo(currentframe())})                
        response_text = await generate_prompts(request.prompt)    
        response_json, message = validate_structure(response_text)
        if not response_json:
            if retry < 3:
                return await generate_text(request, retry=retry+1, ai_model_primary=ai_model_primary, ai_model_secondary=ai_model_secondary) 
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
        if user_id not in task_storage :
            task_storage[user_id] = {}

        task_storage[user_id][task_id] = {
            "task": task,
            "prompts": enhanced_prompts,
            "status": "processing",
            "images": None
        }
        task_storage[user_id][task_id]["events"] = {}
        for i in range(len(enhanced_prompts)):
            task_storage[user_id][task_id]["events"][i] = asyncio.Event()
            task_storage[user_id][task_id]["events"][i+3] = asyncio.Event()

        timer = threading.Timer(task_timeout, clear_taskstorage, args=(user_id, task_id))
        timer.start()
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
    try:
        await asyncio.gather(*image_tasks, return_exceptions=True)
        duration = datetime.now() - start
        logger.info(f"Success - Total image Generation took -> {duration.total_seconds():.2f} seconds")
        if user_id in task_storage and task_id in task_storage[user_id]:
            task_storage[user_id][task_id]["status"] = "completed"
            task_storage[user_id][task_id]["total_time_taken"] = f"{duration.total_seconds():.2f} seconds"
    except asyncio.CancelledError:
        duration = datetime.now() - start
        logger.info(f"Cancelled - Total image Generation took -> {duration.total_seconds():.2f} seconds")
    except Exception as e:
        logger.error(f"Error during image generation: {str(e)}", exc_info=True)
        duration = datetime.now() - start
        logger.info(f"Failed - Total Image Generation took -> {duration.total_seconds():.2f} seconds")
        if user_id in task_storage and task_id in task_storage[user_id]:
            task_storage[user_id][task_id]["status"] = "failed"
            task_storage[user_id][task_id]["total_time_taken"] = f"{duration.total_seconds():.2f} seconds"
        raise HTTPException(status_code=500, detail={'message':f"Error during image generation: {str(e)}", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
        
@imagen_router.post("/get_image")
async def get_generated_image(
    request: ImageRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_id_token),
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(BrowsedImageOperations)),
    analysis_db_ops: BaseDatabaseOperation = Depends(get_db_ops(AnalysisOperations)),
):
    try:
        photo = None
        if user_id not in task_storage or request.task_id not in task_storage[user_id]:
            raise HTTPException(status_code=404, detail={'message':"Task not found",'currentFrame': getframeinfo(currentframe())})

        user_tasks = task_storage.get(user_id)
        task_info = user_tasks.get(request.task_id)
        image_status = task_info.get('image_status')

        if not task_info:
            raise HTTPException(status_code=404, detail={'message':"Task not found",'currentFrame': getframeinfo(currentframe())})
        if task_info['status'] == 'processing':
            if image_status != None and (image_status.get(request.idx) == 'completed' and image_status.get(request.idx + 3) == 'completed'):
                task_info['task'].cancel()
            else:
                event_task1 = asyncio.create_task(
                    task_storage[user_id][request.task_id]["events"].get(request.idx).wait()
                )
                event_task2 = asyncio.create_task(
                    task_storage[user_id][request.task_id]["events"].get(request.idx+3).wait()
                )
                
                try:
                    await asyncio.wait([event_task1, task_info['task']], return_when=asyncio.FIRST_COMPLETED)
                    image_status = task_info.get('image_status')
                    if user_id not in task_storage or request.task_id not in task_storage[user_id]:
                        raise HTTPException(status_code=404, detail={'message':"Task not found",'currentFrame': getframeinfo(currentframe())})
                    if task_storage[user_id][request.task_id]["events"][request.idx].is_set() and image_status != None and image_status.get(request.idx) == 'completed':
                        task_info['task'].cancel()
                        if not task_storage[user_id][request.task_id]["events"][request.idx+3].is_set():
                            event_task2.cancel()
                    if (image_status == None or image_status.get(request.idx) == None or image_status.get(request.idx) == 'failed'):
                        await asyncio.wait([event_task2, task_info['task']], return_when=asyncio.FIRST_COMPLETED)
                        image_status = task_info.get('image_status')
                        if task_storage[user_id][request.task_id]["events"][request.idx+3].is_set():
                            task_info['task'].cancel()
                        if (image_status == None or image_status.get(request.idx + 3) == None or image_status.get(request.idx + 3) == 'failed'):
                            record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
                            raise HTTPException(status_code=400, detail={'message':"Prompt Violates Our Content Policy",'currentFrame': getframeinfo(currentframe())})
                except asyncio.CancelledError:
                    pass 
                except HTTPException as http_exc:
                    raise http_exc
                except Exception as e:
                    record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
                    raise HTTPException(status_code=500, detail={'message':f"Error during image generation: {str(e)}", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
                
                user_tasks = task_storage.get(user_id)
                task_info = user_tasks.get(request.task_id)
                image_status = task_info.get('image_status')
        
        if task_info['status'] == 'completed' or (image_status != None and (image_status.get(request.idx) == 'completed' or image_status.get(request.idx + 3) == 'completed')):
            images = task_info.get('image')
            if images and images != None:
                primary_image = images.get(request.idx)
                if isinstance(primary_image, Exception) or primary_image == None:
                    secondary_image = images.get(request.idx+3)
                    if isinstance(secondary_image, Exception) or secondary_image == None:
                        logger.error(f"Both primary and fallackb images failed to generate: {secondary_image}", exc_info=True)
                        record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
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
                record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
                return {"photo": photo['photo'], "img_id": img_id}
            else:
                record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
                raise HTTPException(status_code=400, detail={'message':"Images not found",'currentFrame': getframeinfo(currentframe())})
        elif task_info['status'] == 'failed':
            record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
            raise HTTPException(status_code=500, detail={'message':"Image generation failed",'currentFrame': getframeinfo(currentframe())})
        else:
            record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
            raise HTTPException(status_code=500, detail={'message':"Unexpected task status",'currentFrame': getframeinfo(currentframe())})
    except openai.OpenAIError as e:
        handle_openai_error(e)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in get_image: {str(e)}", exc_info=True)
        record_analysis(background_tasks, analysis_db_ops, user_id, request.task_id, request.idx)
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



