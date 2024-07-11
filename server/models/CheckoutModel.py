from pydantic import (
    StringConstraints,
    BaseModel,
    conint,
    Field,
    constr
)  # , EmailStr, validator
from typing import List, Optional, Union
from typing_extensions import Annotated
from models.ShippingModel import ShippingModel
from models.ItemModel import ItemModel

class CheckoutModel(BaseModel):
    products: List[ItemModel]
    shipping_info: Optional[ShippingModel] = Field(
        ..., description="Shipping details are optional."
    )
    org_id: str
    org_name: str
