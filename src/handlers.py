from src.models import Attempt
from src.database import get_session_local
from src.schemas import AttemptResponse, AttemptCreate, GradeRequest, BestAttemptRequest
from src.grading import grade_python_attempt
from datetime import datetime, timezone

async def handle_create_attempt(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        msg = AttemptCreate(**data)
        
        attempt = Attempt(
            user_id=msg.user_id,
            exercise_id=msg.exercise_id,
            code_submitted=msg.code,
            attempted_at=datetime.now(timezone.utc)
        )
        
        if "language" in data and "function_name" in data and "test_cases" in data:
            grade_result = grade_python_attempt(
                msg.code,
                data["function_name"],
                data["test_cases"]
            )
            attempt.score = grade_result["score"]
            attempt.stars = grade_result["stars"]
        
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        
        return AttemptResponse.model_validate(attempt).model_dump(mode='json')
    except Exception as e:
        print(f"Error creating attempt: {e}")
        return {"error": str(e)}
    finally:
        db.close()

async def handle_get_user_attempts(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        user_id = data.get("user_id")
        attempts = db.query(Attempt).filter(Attempt.user_id == user_id).all()
        
        return {
            "attempts": [AttemptResponse.model_validate(a).model_dump(mode='json') for a in attempts]
        }
    finally:
        db.close()

async def handle_get_best_attempt(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        msg = BestAttemptRequest(**data)
        
        attempt = db.query(Attempt).filter(
            Attempt.user_id == msg.user_id,
            Attempt.exercise_id == msg.exercise_id
        ).order_by(
            Attempt.stars.desc(),
            Attempt.score.desc(),
            Attempt.attempted_at.desc()
        ).first()
        
        if attempt:
            return AttemptResponse.model_validate(attempt).model_dump(mode='json')
        return {"error": "No attempts found"}
    finally:
        db.close()

async def handle_get_all_best_attempts(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        user_id = data.get("user_id")
        
        attempts = db.query(Attempt).filter(Attempt.user_id == user_id).all()
        
        best_attempts = {}
        for attempt in attempts:
            ex_id = attempt.exercise_id
            if ex_id not in best_attempts or (
                attempt.stars > best_attempts[ex_id].stars or
                (attempt.stars == best_attempts[ex_id].stars and attempt.score > best_attempts[ex_id].score)
            ):
                best_attempts[ex_id] = attempt
        
        return {
            "attempts": [AttemptResponse.model_validate(a).model_dump(mode='json') for a in best_attempts.values()]
        }
    finally:
        db.close()