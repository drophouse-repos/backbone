import os
from datetime import datetime
from ai_models.ImageGenerator import ImageGenerator
from openai import AsyncOpenAI
import openai
key = os.environ.get("OPENAI_KEY")
client = AsyncOpenAI(api_key=key)

class OpenAIImageGenerator(ImageGenerator):
	async def generate_single_image(self, idx, prompt, callback, user_id, task_id):
		start = datetime.now()
		try:
			response = await client.images.generate(
				model="dall-e-2",
				prompt= prompt,
				n=1,
				size="512x512",
				response_format="b64_json"
			)

			duration = datetime.now() - start
			callback(user_id, task_id, idx, False, duration, response.data[0].b64_json, 'openai')
			return idx, response.data[0].b64_json, 'openai'
		except openai.OpenAIError as e:
			duration = datetime.now() - start
			callback(user_id, task_id, idx, True, duration)
			raise HTTPException(status_code=500, detail={'message':f"OpenAI Error: {str(e)}",'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})