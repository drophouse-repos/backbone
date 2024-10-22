import json
import logging
import os
import traceback
from inspect import currentframe, getframeinfo
from fastapi import APIRouter, HTTPException, Request, Response
from dotenv import load_dotenv
from fastapi.responses import JSONResponse, RedirectResponse
from database.AuthOperations import AuthOperations
from database.UserOperations import UserOperations
from database.SaltOperations import SaltOperations
from fastapi import Depends
from database.BASE import BaseDatabaseOperation
from db import get_db_ops
from models.EncryptModel import EncryptModel
from models.UserInitModel import UserInitModel
from verification import verify_id_token
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from cryptography.fernet import Fernet
from pydantic import BaseModel

import jwt
from datetime import datetime, timedelta

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
auth_router = APIRouter()

settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saml', 'saml_settings.json')

with open(settings_path) as f:
	saml_settings = json.load(f)
	
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
def create_jwt_token(user_id: str):
	payload = {
		"user_id": user_id,
		"exp": datetime.utcnow() + timedelta(hours=24)
	}
	token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
	return token

class JwtRequest(BaseModel):
	eid: str
	email: str

class DemoRequest(BaseModel):
	origin: str

@auth_router.post("/auth")
async def basic_auth(
	request_data: UserInitModel,
	user_id: str = Depends(verify_id_token),
	db_ops: BaseDatabaseOperation = Depends(get_db_ops(AuthOperations)),
):
	try:
		auth_result = await db_ops.update(user_id, request_data)
		if auth_result == 1:
			return {"message": "user located"}
		elif auth_result == 2:
			return {"message": "user created"}
		else:
			raise HTTPException(status_code=401, detail={'message':"Authentication failed.", 'currentFrame': getframeinfo(currentframe())})
	except HTTPException as http_exc:
		raise http_exc
	except Exception as e:
		logger.error(f"Authentication error: {str(e)}", exc_info=True)
		raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})
   
@auth_router.post("/demo/auth")
async def demo_login(
	request : DemoRequest,
	db_ops: BaseDatabaseOperation = Depends(get_db_ops(AuthOperations)),
	salt_db_ops: BaseDatabaseOperation = Depends(get_db_ops(SaltOperations)),
):
	try:
		DEMO_FRONTEND_DOMAIN = os.environ.get("DEMO_FRONTEND_DOMAIN")
		auth_result = await db_ops.update('afea8IldvKNlGDawLWvO1W9XFv93', UserInitModel(
			email= "batman@drophouse.ai",
			first_name= "Bruce",
			last_name= "Wayne",
			phone_number=None
		))

		data = "batman@drophouse.ai"
		encrypt_model = await salt_db_ops.create_and_encrypt(data)

		if auth_result == 1:
			return JSONResponse({
				"url": f'{DEMO_FRONTEND_DOMAIN}/?eid={encrypt_model.salt_id}&email={encrypt_model.encrypted_data}'
			})
		elif auth_result == 2:
			return JSONResponse({
					"url" :f'{DEMO_FRONTEND_DOMAIN}/?eid={encrypt_model.salt_id}&email={encrypt_model.encrypted_data}'
				}
			)
		else:
			raise HTTPException(status_code=401, detail={'message':"Authentication failed.", 'currentFrame': getframeinfo(currentframe())})
	except HTTPException as http_exc:
		raise http_exc
	except Exception as e:
		logger.error(f"Authentication error: {str(e)}", exc_info=True)
		raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@auth_router.get("/saml/metadata")
async def saml_metadata():
	auth = OneLogin_Saml2_Auth({}, saml_settings)
	saml_metadata = auth.get_settings().get_sp_metadata()
	errors = auth.get_settings().validate_metadata(saml_metadata)
	if len(errors) > 0:
		return JSONResponse({"errors": errors}, status_code=500)
	return Response(content=saml_metadata, media_type="application/xml")

@auth_router.get("/saml/login")
async def saml_login(request: Request):
	auth = await init_saml_auth(request)
	return RedirectResponse(auth.login())

@auth_router.post("/saml/acs")
async def saml_acs(
	request: Request,
	db_ops: BaseDatabaseOperation = Depends(get_db_ops(AuthOperations)),
	salt_db_ops: BaseDatabaseOperation = Depends(get_db_ops(SaltOperations)),
):
	auth = await init_saml_auth(request)
	auth.process_response()
	errors = auth.get_errors()
	attributes = auth.get_attributes()   
	STUDENT_FRONTEND_DOMAIN = os.environ.get("STUDENT_FRONTEND_DOMAIN")
	if len(errors) == 0:
		extracted_attributes = {
				"tenant_id": attributes.get("http://schemas.microsoft.com/identity/claims/tenantid", [None])[0],
				"given_name": attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname", [None])[0],
				"surname": attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname", [None])[0],
				"email": attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", [None])[0],
				"org": attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name", [None])[0],
			}
		request.session['samlUserdata'] = attributes
		request.session['samlNameId'] = auth.get_nameid()
		request.session['samlSessionIndex'] = auth.get_session_index()
		auth_result = await db_ops.update(extracted_attributes["email"], UserInitModel(
			email=extracted_attributes["email"],
			first_name=extracted_attributes["surname"],
			last_name=extracted_attributes["given_name"],
			phone_number=None
		))
		
		data = extracted_attributes['email']
		logger.info(f"Email: {extracted_attributes}")
		logger.info(f"auth result: {auth_result}")
		encrypt_model = await salt_db_ops.create_and_encrypt(data)
		
		if auth_result == 1:
			return RedirectResponse(url=f'{STUDENT_FRONTEND_DOMAIN}/product?eid={encrypt_model.salt_id}&email={encrypt_model.encrypted_data}', status_code=303)
		elif auth_result == 2:
			return RedirectResponse(url=f'{STUDENT_FRONTEND_DOMAIN}/product?eid={encrypt_model.salt_id}&email={encrypt_model.encrypted_data}', status_code=303)
		else:
			raise HTTPException(status_code=401, detail={'message':"Authentication failed.", 'currentFrame': getframeinfo(currentframe())})
	else:
		logger.error(f"SAML ACS error: {errors}")
		return JSONResponse({"errors": errors}, status_code=400)

@auth_router.post("/saml/jwt")
async def saml_jwt(
	request:JwtRequest,
	db_ops: BaseDatabaseOperation = Depends(get_db_ops(UserOperations)),
	salt_db_ops: BaseDatabaseOperation = Depends(get_db_ops(SaltOperations)),
):
	try:
		logger.info(f"Session contents: {request.email}")
		if request.email:
			en_user_email = request.email
			if en_user_email:
				encrypt_model = EncryptModel(salt_id=request.eid, encrypted_data=request.email)
				user_email = await salt_db_ops.decrypt_and_remove(encrypt_model)

				user_data = await db_ops.get_userByEmail(user_email)
				if 'user_id' in user_data:
					token = create_jwt_token(user_data['user_id'])
					return {
						'user_data' : user_data,
						'token' : token
					}
				else:
					return False
			else:
				return False
		else:
			return False
	except Exception as e:
		logger.error(f"Error creating jwt token : {e}")
		return False

class fingerprint(BaseModel):
    fingerprint: str

@auth_router.post("/set-or-get-guest")
async def setorget_guest(
	request : fingerprint,
    db_ops: BaseDatabaseOperation = Depends(get_db_ops(UserOperations))
):
    try:
        result = await db_ops.get_or_set(request.fingerprint)
        token = create_jwt_token(result['user_id'])
        return {
        	'user_data': result,
        	'token': token
        };
    except Exception as e:
        logger.error(f"Error in set-or-get-guest Organization: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})


async def init_saml_auth(req: Request):
	request_data = {
		'https': 'on',
		'http_host': req.headers.get('host'),
		'script_name': req.url.path,
		'server_port': req.url.port,
		'get_data': req.query_params,
		'post_data': await req.form() if req.method == "POST" else {}
	}
	auth = OneLogin_Saml2_Auth(request_data, saml_settings)
	return auth