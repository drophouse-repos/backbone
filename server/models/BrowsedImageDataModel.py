import datetime
from pydantic import BaseModel  # , Field, EmailStr, validator, constr

# from typing import Optional


class BrowsedImageDataModel(BaseModel):
    img_id: str
    prompt: str
    timestamp: datetime.datetime
