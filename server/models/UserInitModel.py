from pydantic import ConfigDict, BaseModel, Field, EmailStr  # , field_validator
from typing import Optional  # , List


class UserInitModel(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    model_config = ConfigDict(use_enum_values=True, from_attributes=True)
