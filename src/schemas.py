from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AttemptCreate(BaseModel):
    user_id: int
    exercise_id: int
    code: str

class AttemptResponse(BaseModel):
    id: int
    user_id: int
    exercise_id: int
    code_submitted: str
    score: int
    stars: int
    attempted_at: datetime
    status: str
    feedback: Optional[str] = None
    test_pass_rate: Optional[float] = None
    execution_output: Optional[str] = None
    
    class Config:
        from_attributes = True

class BestAttemptRequest(BaseModel):
    user_id: int
    exercise_id: int