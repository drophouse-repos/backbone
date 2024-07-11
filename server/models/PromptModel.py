from pydantic import BaseModel

class StorePromptModel(BaseModel):
    prompt1: str
    prompt2: str
    prompt3: str
    chosenNum: int