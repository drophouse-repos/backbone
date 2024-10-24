from pydantic import ConfigDict, BaseModel, Field, EmailStr
from typing import Optional

class UserInitModel(BaseModel):
    user_id: Optional[str] = Field(..., description="User's ID")
    email: EmailStr = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    account_type: Optional[str] = Field(None, description="User's account type")

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)