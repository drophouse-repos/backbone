# from pydantic import field_validator, ConfigDict, BaseModel, Field, EmailStr
# from typing import List, Optional
# from enum import Enum

# from models.CartItemModel import CartItem
# from models.BrowsedImageDataModel import BrowsedImageDataModel
# from server.models.UserInitModel import UserInitModel


# class UserModel(UserInitModel):
#     browsed_images: List[BrowsedImageDataModel] = Field(default_factory=list, description="List of browsed images IDs")
#     liked_images: List[CartItemModel] = Field(default_factory=list, description="List of saved images IDs")
#     cart: List[CartItem] = Field(default_factory=list, description="List of items in the user's cart")
#     model_config = ConfigDict(use_enum_values=True, from_attributes=True)

#     @field_validator('user_id')
#     @classmethod
#     def user_id_must_be_valid(cls, v):
#         if not v or len(v) < 5:
#             raise ValueError('User ID must be at least 5 characters long')
#         return v
