import json
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import stripe
import logging
import traceback
from inspect import currentframe, getframeinfo
import os
from database.SaltOperations import SaltOperations
from database.BASE import BaseDatabaseOperation
from db import get_db_ops
from models.CheckoutModel import CheckoutModel
from models.EncryptModel import EncryptModel
from aws_utils import generate_presigned_url, processAndSaveImage
from database.OrderOperations import OrderOperations
from database.UserOperations import UserOperations
from database.CartOperations import CartOperations
from database.LikedImageOperations import LikedImageOperations
from database.PricesOperations import PricesOperations
from routers.cart import remove_from_cart
from email_service.EmailService import EmailService
from utils.stripe_utils import capitalize_first_letter
from utils.update_like import unlike_image
from verification import verify_id_token
from routers.order_info import PlaceOrderDataRequest, place_order
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
email_service = EmailService()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
stripe_webhook_key = os.environ.get("STRIPE_WEBHOOK_SECRET")
stripe_tax_id = os.environ.get("STRIPE_TAX_ID")

stripe_router = APIRouter()
freeShipping = int(os.environ.get("FREE_SHIPPING_THRESHOLD")) if os.environ.get("FREE_SHIPPING_THRESHOLD") else 100

@stripe_router.post("/create-student-checkout")
async def create_student_checkout(
    CheckoutModel: CheckoutModel,
    order_db_ops: BaseDatabaseOperation = Depends(get_db_ops(OrderOperations)),
    price_db_ops: BaseDatabaseOperation = Depends(get_db_ops(PricesOperations)),
    salt_db_ops: BaseDatabaseOperation = Depends(get_db_ops(SaltOperations)),
    cart_db_ops: BaseDatabaseOperation = Depends(get_db_ops(CartOperations)),
    user_db_ops: BaseDatabaseOperation = Depends(get_db_ops(UserOperations)),
    user_id: str = Depends(verify_id_token),
):
    try:
        isOrdered = await user_db_ops.check_student_order(user_id)
        if(isOrdered):
            raise HTTPException(status_code=422, detail={'message':"You have already placed an order. Contact us if you want to change it", 'currentFrame': getframeinfo(currentframe())})

        shipping_info_meta = CheckoutModel.shipping_info
        org_id = CheckoutModel.org_id
        org_name = CheckoutModel.org_name
        print(org_name)
        for item in CheckoutModel.products:
            img_id = item.img_id
            thumbnail = item.thumbnail
            thumbnail_img_id = "t_" + img_id
            if thumbnail and thumbnail.startswith("data:image"):
                processAndSaveImage(thumbnail, thumbnail_img_id, "thumbnails-cart")

        items = CheckoutModel.products
        print(items)
        await order_db_ops.remove_unpaid_order(user_id)
        order_data_request = PlaceOrderDataRequest(shipping_info=shipping_info_meta, item=items)
        order_id = await place_order(order_data_request, user_id, org_id, org_name, order_db_ops)
        
        order_model = await order_db_ops.getByOrderID(order_id)
        priceMap = await price_db_ops.get()
        
        message_body = f'<div>\
            <span><strong>User Name:</strong> {order_model.shipping_info.firstName} {order_model.shipping_info.lastName}</span><br>\
            <span><strong>User Id:</strong> {order_model.user_id}</span><br><br>\
            <span><strong>Order Id:</strong> {order_model.order_id}</span><br>\
            <span><strong>Date & Time:</strong> {order_model.timestamp.strftime("%d/%m/%Y, %H:%M:%S")}</span<br><br>\
            <span><strong>Address:</strong> {order_model.shipping_info.streetAddress} {order_model.shipping_info.streetAddress2}, {order_model.shipping_info.city}, \
            {order_model.shipping_info.stateProvince} - {order_model.shipping_info.postalZipcode}</span><br>\
            <span><strong>Email:</strong> {order_model.shipping_info.email}</span><br>\
            <span><strong>Phone Number:</strong> {order_model.shipping_info.phone}</span><br>\
            <br><hr><br>'

        amount_total = 0
        items = order_model.item
        for item in items:
            thumbnail_img_id = "t_" + item.img_id
            thumbnail = generate_presigned_url(thumbnail_img_id, "thumbnails-cart")

            message_body += f'<div style="display:flex">\
                <div style="order:1"><img src="{thumbnail}" style="width:150px; height:150px;"></div>\
                <div style="order:2; margin-left:15px;">\
                    <span><strong>Item Type:</strong> {item.apparel}</span><br>'
            if(item.apparel != "Mug" or item.apparel != "cap"):
                message_body += f'<span><strong>Item Size:</strong> {item.size}</span><br>'

            message_body += f'<span><strong>Item Color:</strong> {item.color}</span><br><br>\
                <span><strong>Item img_id:</strong> {item.img_id}</span><br>\
                <span><strong>Item Prompt:</strong> {item.prompt}</span><br><br>\
                <span><strong>Item Price:</strong>$ {priceMap[item.apparel.lower()]}</span><br>\
            </div></div><br><br>';
            amount_total = int(amount_total) + int(priceMap[item.apparel.lower()])

        message_body += f'\
            <span><strong>Amount Total:</strong>$ {float(amount_total):.2f}</span><br>\
        </div>'
        
        to_mail = os.environ.get("TO_EMAIL") if os.environ.get("TO_EMAIL") else "support@drophouse.art"
        email_service.send_email(
            from_email='bucket@drophouse.art',
            to_email=to_mail,
            subject='Drophouse Order',
            name=f"{order_model.shipping_info.firstName} {order_model.shipping_info.lastName}",
            email="",
            message_body=message_body
        )

        uid = order_model.user_id
        items = order_model.item
        img_ids = [item.img_id for item in items]
        for img_id in img_ids:
            result = await remove_from_cart(img_id, uid, cart_db_ops)
            if result:
                logger.info(f"Successfully removed item {img_id} from cart for user {uid}.")
            else:
                logger.info(f"Item {img_id} not found in cart for user {uid}.")
        await order_db_ops.update_order_status(uid, order_id, 'pending')
        return True
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in  checkout session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

@stripe_router.post("/create-checkout-session")
async def create_checkout_session(
    request : Request,
    CheckoutModel: CheckoutModel,
    order_db_ops: BaseDatabaseOperation = Depends(get_db_ops(OrderOperations)),
    price_db_ops: BaseDatabaseOperation = Depends(get_db_ops(PricesOperations)),
    salt_db_ops: BaseDatabaseOperation = Depends(get_db_ops(SaltOperations)),
    user_id: str = Depends(verify_id_token),
): 
    line_items = []  
    total_purchase_price = 0
    priceMap = await price_db_ops.get()
    org_id = CheckoutModel.org_id
    org_name = CheckoutModel.org_name
    print(org_name)
    for item in CheckoutModel.products:
        img_id = item.img_id
        thumbnail = item.thumbnail
        thumbnail_img_id = "t_" + img_id
        if thumbnail and thumbnail.startswith("data:image"):
            processAndSaveImage(thumbnail, thumbnail_img_id, "thumbnails-cart")
            thumbnail = generate_presigned_url(thumbnail_img_id, "thumbnails-cart")
        color = await capitalize_first_letter(item.color)
        apparel = await capitalize_first_letter(item.apparel)
        if item.apparel.lower() not in priceMap: # Apparel Price not found
            raise HTTPException(status_code=404, detail={'message':"Can't able to checkout, please try again", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})

        item_price = int(priceMap[item.apparel.lower()]) * 100
        line_item = {
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"Rose Hulman {color} {apparel}",
                    "description": f"{item.prompt}\nSize: {item.size}",
                    "images": [thumbnail],
                    # "metadata": {
                    #     "prompt": item.prompt,
                    #     "img_id": img_id,  
                    #     "color": item.color,
                    #     "size": item.size,
                    #     "apparel": item.apparel,
                    # },
                },
                "unit_amount": item_price,
            },
            "quantity": 1,
            "tax_rates": ['txr_1P0nomGZeOMzbUq89P21Cq98'],
        }
        total_purchase_price = int(total_purchase_price) + int(item_price)
        line_items.append(line_item)
    try:
        shipping_info_meta = CheckoutModel.shipping_info
        user_email = shipping_info_meta.email
        shipping_info = f"{shipping_info_meta.streetAddress} {shipping_info_meta.city} {shipping_info_meta.postalZipcode}"
        items = CheckoutModel.products
        org_id = CheckoutModel.org_id
        org_name = str(CheckoutModel.org_name)
        await order_db_ops.remove_unpaid_order(user_id)
        order_data_request = PlaceOrderDataRequest(shipping_info=shipping_info_meta, item=items)
        order_id = await place_order(order_data_request, user_id, org_id, org_name, order_db_ops)
        encrypt_model = await salt_db_ops.create_and_encrypt(order_id)
        encrypt_id = encrypt_model.salt_id
        encrypted_oid = encrypt_model.encrypted_data
        
        shipping_option = {
                    'shipping_rate_data': {
                        'type': 'fixed_amount',
                        'fixed_amount': {
                            'amount': 600 if total_purchase_price < (freeShipping * 100) else 0,  # 600 -> $6.00
                            'currency': 'usd',
                        },
                        'display_name': 'Free shipping after $100' if total_purchase_price < (freeShipping * 100) else 'Free shipping',
                        # 'display_name': '',
                        # Delivers in time estimation
                        # 'delivery_estimate': {
                        #     'minimum': {
                        #         'unit': 'business_day',
                        #         'value': 1,
                        #     },
                        #     'maximum': {
                        #         'unit': 'business_day',
                        #         'value': 1,
                        #     },
                        # }
                    }
                }

        frontend_url = request.headers.get('origin')
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            customer_email=user_email,
            line_items=line_items,
            mode="payment",
            success_url=f"{frontend_url}/success",
            cancel_url=f"{frontend_url}/product",
            #automatic_tax={'enabled': True},
            expires_at=int(time.time()) + 3600,
            allow_promotion_codes=True,
            invoice_creation= {
                "enabled": "true"
            },
            custom_fields=[
                {
                "key": "shiping_address",
                "label": {"type": "custom", "custom": "Shipping Address"},
                "optional": False,
                "type": "dropdown",
                "dropdown": 
                    {
                    "options": 
                        [
                            {"label": shipping_info, "value": "default"},
                        ],
                    },
                },
            ],
            shipping_options=[shipping_option],
            metadata={
                "encrypt_id": encrypt_id,
                "encrypted_oid": encrypted_oid,
            },
        )
        return JSONResponse({"url": checkout_session.url})
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error in  checkout session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={'message':"Internal Server Error", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())})


@stripe_router.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    order_db_ops: BaseDatabaseOperation = Depends(get_db_ops(OrderOperations)),
    cart_db_ops: BaseDatabaseOperation = Depends(get_db_ops(CartOperations)),
    price_db_ops: BaseDatabaseOperation = Depends(get_db_ops(PricesOperations)),
    like_db_ops: BaseDatabaseOperation = Depends(get_db_ops(LikedImageOperations)),
    salt_db_ops: BaseDatabaseOperation = Depends(get_db_ops(SaltOperations))):
    webhook_secret = stripe_webhook_key
    request_data = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload=request_data,
            sig_header=sig_header,
            secret=webhook_secret,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={'message':"Invalid payload", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())}
        ) from e
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={'message':"Invalid signature", 'currentFrame': getframeinfo(currentframe()), 'detail': str(traceback.format_exc())}
        ) from e

    if event["type"] in [
        "checkout.session.async_payment_succeeded",
        "checkout.session.completed",
        "payment_intent.succeeded",
    ]:
        
        metadata = event["data"]["object"]["metadata"]
        name = event["data"]["object"]["customer_details"]["name"]
        encrypt_id = metadata.get("encrypt_id")
        encrypted_oid = metadata.get("encrypted_oid")
        encrypt_model = EncryptModel(salt_id=encrypt_id, encrypted_data=encrypted_oid)
        order_id = await salt_db_ops.decrypt_and_remove(encrypt_model)
        order_model = await order_db_ops.getByOrderID(order_id)
        priceMap = await price_db_ops.get()
        # metadata_body = str(event)+"<br><br> order info => <br><br>"+str(order_model)
        
        message_body = f'<div>\
            <span><strong>User Name:</strong> {order_model.shipping_info.firstName} {order_model.shipping_info.lastName}</span><br>\
            <span><strong>User Id:</strong> {order_model.user_id}</span><br><br>\
            <span><strong>Order Id:</strong> {order_model.order_id}</span><br>\
            <span><strong>Date & Time:</strong> {order_model.timestamp.strftime("%d/%m/%Y, %H:%M:%S")}</span<br><br>\
            <span><strong>Address:</strong> {order_model.shipping_info.streetAddress} {order_model.shipping_info.streetAddress2}, {order_model.shipping_info.city}, \
            {order_model.shipping_info.stateProvince} - {order_model.shipping_info.postalZipcode}</span><br>\
            <span><strong>Email:</strong> {order_model.shipping_info.email}</span><br>\
            <span><strong>Phone Number:</strong> {order_model.shipping_info.phone}</span><br>\
            <br><hr><br>'

        items = order_model.item
        for item in items:
            thumbnail_img_id = "t_" + item.img_id
            thumbnail = generate_presigned_url(thumbnail_img_id, "thumbnails-cart")

            message_body += f'<div style="display:flex">\
                <div style="order:1"><img src="{thumbnail}" style="width:150px; height:150px;"></div>\
                <div style="order:2; margin-left:15px;">\
                    <span><strong>Item Type:</strong> {item.apparel}</span><br>'
            if(item.apparel != "Mug" or item.apparel != "cap"):
                message_body += f'<span><strong>Item Size:</strong> {item.size}</span><br>'

            message_body += f'<span><strong>Item Color:</strong> {item.color}</span><br><br>\
                <span><strong>Item img_id:</strong> {item.img_id}</span><br>\
                <span><strong>Item Prompt:</strong> {item.prompt}</span><br><br>\
                <span><strong>Item Price:</strong>$ {priceMap[item.apparel.lower()]}</span><br>\
            </div></div><br><br>';


        message_body += f'\
            <span><strong>Amount Subtotal:</strong>$ {(float(event["data"]["object"]["amount_subtotal"])/100):.2f}</span><br>\
            <span><strong>Shipping Amount:</strong>$ {(float(event["data"]["object"]["shipping_cost"]["amount_total"])/100):.2f}</span><br>\
            <span><strong>Amount Total:</strong>$ {(float(event["data"]["object"]["amount_total"])/100):.2f}</span><br>\
        </div>'
        
        to_mail = os.environ.get("TO_EMAIL") if os.environ.get("TO_EMAIL") else "support@drophouse.art"
        email_service.send_email(
            from_email='bucket@drophouse.art',
            to_email=to_mail,
            subject='Drophouse Order',
            name=name,
            email="",
            message_body=message_body
        )

        uid = order_model.user_id
        items = order_model.item
        img_ids = [item.img_id for item in items]
        for img_id in img_ids:
            result = await remove_from_cart(img_id, uid, cart_db_ops)
            if result:
                logger.info(f"Successfully removed item {img_id} from cart for user {uid}.")
            else:
                logger.info(f"Item {img_id} not found in cart for user {uid}.")

            like_result = await unlike_image(uid, img_id, 'remove', like_db_ops)
            if like_result:
                logger.info(f"Successfully removed item {img_id} from favorites/liked for user {uid}.")
            else:
                logger.info(f"Item {img_id} not found in favorites/liked for user {uid}.")

        await order_db_ops.update_order_status(uid, order_id, 'pending')
        logger.info(f"Handled event type: {event['type']}")
    else:
        logger.info(f"Unhandled event type {event['type']}")
    return JSONResponse({"status": "success"})