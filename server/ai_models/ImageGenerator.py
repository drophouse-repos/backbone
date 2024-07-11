import traceback
from inspect import currentframe, getframeinfo
import asyncio
from abc import ABC, abstractmethod
from fastapi import HTTPException


class ImageGenerator(ABC):
    # async def generate_images(self, prompts, dictionary_id, task_results):
    #     task = asyncio.gather(*[
    #         self.generate_single_image(prompt) for prompt in prompts
    #     ], return_exceptions=True)
    #     try:
    #         image_responses = await task
    #         task_results[dictionary_id] = image_responses
    #         return image_responses
    #     except Exception as e:
    #         raise HTTPException(status_code=500, detail={'message':str(e),'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

    @abstractmethod
    async def generate_single_image(self, idx, prompt):
        pass