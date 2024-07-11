from pydantic import (
    field_validator,
    StringConstraints,
    ConfigDict,
    BaseModel,
    Field,
    EmailStr,
)
from typing import Optional
from typing_extensions import Annotated


class EmailModel(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    name: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="name", description="User name is required."
    )
    message: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="message", description="Message is required."
    )