import datetime
from typing import List
from pydantic import StringConstraints, BaseModel, Field, constr
from typing_extensions import Annotated
from enum import Enum
from models.ItemModel import ItemModel
from models.ShippingModel import ShippingModel


class OrderStatus(str, Enum):
    UNPAID = "unpaid"
    PENDING = "pending"
    VERIFIED = "verified"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    SHIPPED = "shipped"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"

class UserTypes(str, Enum):
    ALUMNI = 'alumni'
    STUDENT = 'student'

class OrderItem(BaseModel):
    user_id: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="user_id", description="User ID is required."
    )
    user_type: UserTypes = Field(..., description="Usertype is required.")

    org_id: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="org_id", description="Organisation Id is required."
    )

    org_name: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="org_name", description="Organisation Name is required."
    )

    order_id: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="order_id", description="Unique order ID is required."
    )
    item: List[ItemModel] = Field(..., description="Item details are required.")
    shipping_info: ShippingModel = Field(
        ..., description="Shipping details are required."
    )
    status: OrderStatus = Field(..., description="Order status is required.")
    timestamp: datetime.datetime = Field(
        None, alias="timestamp", description="Timestamp is required."
    )
