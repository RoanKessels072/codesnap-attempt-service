from src.database import get_session_local
from src.schemas import (
    AttemptResponse, 
    AttemptCreate, 
    BestAttemptRequest
)
from src.grading import grade_submission_raw
from src.nats_client import NATSClient
from src import crud


_nats_client: NATSClient = None

def set_nats_client(client: NATSClient):
    global _nats_client
    _nats_client = client

async def handle_create_attempt(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        if not all(k in data for k in ["user_id", "exercise_id", "code"]):
            return {"error": "Missing required fields: user_id, exercise_id, or code"}
        
        if not all(k in data for k in ["language", "function_name", "test_cases"]):
            return {"error": "Missing grading information: language, function_name, or test_cases"}
        
        attempt = crud.create_attempt(
            db=db,
            user_id=data["user_id"],
            exercise_id=data["exercise_id"],
            code=data["code"],
            language=data["language"],
            function_name=data["function_name"],
            test_cases=data["test_cases"]
        )
        
        return AttemptResponse.model_validate(attempt).model_dump(mode='json')
        
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        print(f"Error creating attempt: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Internal error: {str(e)}"}
    finally:
        db.close()


async def handle_get_attempt(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        attempt_id = data.get("id")
        if not attempt_id:
            return {"error": "Missing attempt id"}
        
        attempt = crud.get_attempt_by_id(db, attempt_id)
        
        if not attempt:
            return {"error": "Attempt not found"}
        
        return AttemptResponse.model_validate(attempt).model_dump(mode='json')
        
    except Exception as e:
        print(f"Error getting attempt: {e}")
        return {"error": str(e)}
    finally:
        db.close()


async def handle_get_user_attempts(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        user_id = data.get("user_id")
        if not user_id:
            return {"error": "Missing user_id"}
        
        attempts = crud.get_user_attempts(db, user_id)
        return {"attempts": attempts}
        
    except Exception as e:
        print(f"Error getting user attempts: {e}")
        return {"error": str(e)}
    finally:
        db.close()


async def handle_get_exercise_attempts(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        exercise_id = data.get("exercise_id")
        if not exercise_id:
            return {"error": "Missing exercise_id"}
        
        limit = data.get("limit")
        attempts = crud.get_exercise_attempts(db, exercise_id, limit)
        
        return {
            "attempts": [
                AttemptResponse.model_validate(a).model_dump(mode='json') 
                for a in attempts
            ]
        }
        
    except Exception as e:
        print(f"Error getting exercise attempts: {e}")
        return {"error": str(e)}
    finally:
        db.close()


async def handle_get_best_attempt(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        msg = BestAttemptRequest(**data)
        
        best_attempt = crud.get_best_attempt_for_exercise(db, msg.user_id, msg.exercise_id)
        
        if best_attempt:
            return best_attempt
        return None
        
    except Exception as e:
        print(f"Error getting best attempt: {e}")
        return {"error": str(e)}
    finally:
        db.close()


async def handle_get_all_best_attempts(data: dict):
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        user_id = data.get("user_id")
        if not user_id:
            return {"error": "Missing user_id"}
        
        best_attempts = crud.get_user_best_attempts(db, user_id)
        return best_attempts
        
    except Exception as e:
        print(f"Error getting all best attempts: {e}")
        return {"error": str(e)}
    finally:
        db.close()

async def handle_grade_ephemeral(data: dict):
    if not _nats_client:
        return {"error": "NATS client not initialized in handler"}

    try:
        required = ["code", "language", "function_name", "test_cases"]
        if not all(k in data for k in required):
            return {"error": "Missing required fields: code, language, function_name, test_cases"}

        result = await grade_submission_raw(
            nats=_nats_client,
            code=data["code"],
            language=data["language"],
            function_name=data["function_name"],
            test_cases=data["test_cases"]
        )
        
        return result
        
    except Exception as e:
        print(f"Error grading ephemeral attempt: {e}")
        return {"error": str(e)}