from pydantic import StringConstraints, BaseModel, Field  # , EmailStr, validator

# from typing import Optional
from typing_extensions import Annotated


class RetrieveModel(BaseModel):
    userId: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="userId", description="User ID is required."
    )
