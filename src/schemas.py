from pydantic import BaseModel
from datetime import datetime

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
    
    class Config:
        from_attributes = True

class GradeRequest(BaseModel):
    code: str
    language: str
    function_name: str
    test_cases: list

class BestAttemptRequest(BaseModel):
    user_id: int
    exercise_id: int