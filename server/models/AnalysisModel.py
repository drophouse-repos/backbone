from typing import List
from pydantic import BaseModel

class AnalysisModel(BaseModel):
	task_id : str
	index : int
	time_taken : str
	prompts : List[str]
	status :  str