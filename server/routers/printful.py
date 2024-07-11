import logging
import requests
import traceback
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from inspect import currentframe, getframeinfo

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
printful_router = APIRouter()

# Ensure your .env file has a line like this: PRINTFUL_PRIVATE_TOKEN=your_private_token
PRIVATE_TOKEN = os.environ.get('PRINTFUL_PRIVATE_TOKEN');
BASE_URL = 'https://api.printful.com'

order_data = {
    "recipient": {
        "name": "bala pradeep",
        "address1": "2046, villapuram housing board",
        "city": "Madurai",
        "state_code": "CA",
        "country_code": "US",
        "zip": "90001"
    },
    "items": [
        {
            "variant_id": "#65c042bfbe5f93",	
            "quantity": 1
        }
    ]
}

@printful_router.get("/create_order")
async def create_order():
    try:
        endpoint = '/orders'
        response = printful_request(endpoint, method='POST', data=order_data)
        return JSONResponse(content=response)
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in creating printful order: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            'message': "Internal Server Error",
            'currentFrame': getframeinfo(currentframe()),
            'detail': str(traceback.format_exc())
        })

def printful_request(endpoint, method='GET', data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {
        'Authorization': f"Bearer {PRIVATE_TOKEN}",
        'Content-Type': 'application/json'
    }

    if method == 'GET':
        response = requests.get(url, headers=headers)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    elif method == 'PUT':
        response = requests.put(url, headers=headers, json=data)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers)
    else:
        raise ValueError("Unsupported HTTP method")

    if response.status_code not in range(200, 299):
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

    return response.json()