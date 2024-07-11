import datetime
from typing import Annotated, Optional
from pydantic import BaseModel, StringConstraints, Field

class EncryptModel(BaseModel):
    salt_id:  Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="salt_id", description="saltId is required."
    )
    # salt:  Optional[str] = Field(
    #     ..., alias="salt", description="salt is required."
    # )
    encrypted_data: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., alias="encrypted_data", description="Encrypted Data is required."
    )