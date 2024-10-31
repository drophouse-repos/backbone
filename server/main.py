import os
import json

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from utils.format_error import format_error

from routers import (
    auth_router,
    imagen_router,
    favorite_router,
    shipping_info_router,
    cart_router,
    order_info_router,
    stripe_router,
    email_router,
    static_router,
    prices_router,
    org_router
)
import asyncio
import uvicorn
import logging
import signal
import sys
from db import connect_to_mongo, close_mongo_connection
from redis import connect_to_redis, close_redis_connection
import firebase_admin
from firebase_admin import credentials
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

if sys.platform == "win32":
    import win32api
    import win32con

load_dotenv()
cred = credentials.Certificate("service_firebase.json")
firebase_admin.initialize_app(cred)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from email_service.EmailService import EmailService
app = FastAPI()
email_service = EmailService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://drophouse.rose-hulman.edu",
    ],
    allow_origin_regex=r".*\.drophouse\.ai$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    response = await call_next(request)
    session = request.cookies.get('session')
    if session:
        response.set_cookie(
            key='session',
            value=session,
            httponly=True,
            secure=True  # Ensures the cookie is only sent over HTTPS
        )
    return response


SEND_EMAIL_FOR_STATUS_CODES = {429, 500}
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    route_info = request.scope.get('route')
    path = route_info.path if route_info else "unknown"
    name = route_info.name if route_info else "unknown"
    response = await format_error(
        path=path, name=name, 
        code=exc.status_code, exception=exc.detail
    )
    if exc.status_code in SEND_EMAIL_FOR_STATUS_CODES:
        email_service.notify_error(response)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.get("/")
def root():
    return {"message": "Welcome to the New Order!!!"}

app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("startup", connect_to_redis)
app.add_event_handler("shutdown", close_mongo_connection)
app.add_event_handler("shutdown", close_redis_connection)
app.include_router(auth_router)
app.include_router(imagen_router)
app.include_router(favorite_router)
app.include_router(shipping_info_router)
app.include_router(cart_router)
app.include_router(prices_router)
app.include_router(order_info_router)
app.include_router(stripe_router)
app.include_router(email_router)
app.include_router(static_router)
app.include_router(org_router)

# Graceful shutdown handler
async def grace_shutdown(signal, loop):
    logger.info(f"Received signal {signal.name}, shutting down gracefully...")
    await close_mongo_connection()  # Close MongoDB connection here
    await close_redis_connection()  # Close Redis connection here
    # Add any other shutdown cleanup logic (e.g., closing Redis if you're using it)
    loop.stop()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = json.dumps(exc.errors(), indent=2)
    print(error_details)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    
    if not sys.platform == "win32":
        # Register signal handlers for graceful shutdown
        signals = (signal.SIGINT, signal.SIGTERM)
        for s in signals:
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(grace_shutdown(s, loop)))

    try:
        port = int(os.environ.get("SERVER_PORT", 8080))
        uvicorn.run(app, host="0.0.0.0", port=port)
    except KeyboardInterrupt:
        logger.info("Shutting down due to KeyboardInterrupt...")
        loop.run_until_complete(close_mongo_connection())  # Ensure MongoDB closes
    finally:
        loop.close()