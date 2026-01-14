from src.database import get_session_local
from src.schemas import (
    AttemptResponse, 
    BestAttemptRequest
)
from src import grading
from src.nats_client import NATSClient
from src import crud
import json

_nats_client: NATSClient = None

def set_nats_client(client: NATSClient):
    global _nats_client
    _nats_client = client

async def handle_create_attempt(data: dict):
    print(f"Received attempt submission: {list(data.keys())}")
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        required = ["user_id", "exercise_id", "code", "language", "function_name", "test_cases"]
        if not all(k in data for k in required):
            print(f"Missing fields. Received: {data.keys()}")
            return {"error": "Missing fields"}

        # 1. Save Initial "PENDING" Attempt
        attempt = crud.create_attempt(
            db=db,
            user_id=data["user_id"],
            exercise_id=data["exercise_id"],
            code=data["code"],
            stars=0,
            score=0
        )
        attempt.status = "pending"
        db.commit()
        db.refresh(attempt)
        
        # 2. Prepare the Job
        try:
            harness_code = grading.prepare_grading_job(
                code=data["code"],
                language=data["language"],
                function_name=data["function_name"],
                test_cases=data["test_cases"]
            )
            
            print(f"DEBUG: generated harness code length: {len(harness_code)}")
            print(f"DEBUG: test_cases count: {len(data['test_cases'])}")
            if len(data['test_cases']) > 0:
                 print(f"DEBUG: first test case: {data['test_cases'][0]}")
            
            # 3. Publish "execution.job" (Fire and Forget)
            job_payload = {
                "attempt_id": attempt.id,
                "language": data["language"],
                "code": harness_code,            # The code to RUN (with tests)
                "original_code": data["code"],   # The code to LINT
                "type": "grading_job"
            }
            
            if _nats_client:
                await _nats_client.publish("execution.job", job_payload)
                print(f"Published grading job for attempt {attempt.id}")
            else:
                print("CRITICAL: NATS client missing, job not published")
                
        except Exception as e:
            print(f"Error preparing job: {e}")
            attempt.status = "error"
            attempt.feedback = f"Internal Error: {str(e)}"
            db.commit()
            return {"error": str(e)}

        # 4. Return Pending Status immediately
        response = AttemptResponse.model_validate(attempt).model_dump(mode='json')
        return response
        
    except Exception as e:
        print(f"Error creating attempt: {e}")
        return {"error": str(e)}
    finally:
        db.close()

async def handle_attempt_graded(data: dict):
    """
    Subscribes to 'attempt.graded'
    Payload: { "attempt_id": 123, "execution_output": "...", "lint_output": "...", "error": "..." }
    """
    print(f"Received graded result for attempt {data.get('attempt_id')}")
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        attempt_id = data.get("attempt_id")
        if not attempt_id: return
        
        attempt = crud.get_attempt_by_id(db, attempt_id)
        if not attempt:
            print("Attempt not found for grading result")
            return
            
        print(f"DEBUG: Graded payload received. Execution Output:\n{data.get('execution_output', 'NONE')}")
        print(f"DEBUG: Lint Output:\n{data.get('lint_output', 'NONE')}")
            
        results = grading.compute_grade_from_results(
            execution_output=data.get("execution_output", ""),
            lint_output=data.get("lint_output", "")
        )
        
        attempt.score = results["score"]
        attempt.stars = results["stars"]
        attempt.status = "completed"
        
        db.commit()
        print(f"Attempt {attempt_id} updated with score {attempt.score}")
        
    except Exception as e:
        print(f"Error processing grading result: {e}")
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
        
        result = {}
        for exercise_id, attempt_data in best_attempts.items():
            result[str(exercise_id)] = attempt_data
        
        return result
        
    except Exception as e:
        print(f"Error getting all best attempts: {e}")
        return {"error": str(e)}
    finally:
        db.close()

async def handle_grade_ephemeral(data: dict):
    if not _nats_client:
        return {"error": "NATS client not initialized"}

    try:
        required = ["code", "language", "function_name", "test_cases"]
        if not all(k in data for k in required):
            return {"error": "Missing required fields"}

        harness_code = grading.prepare_grading_job(
            code=data["code"],
            language=data["language"],
            function_name=data["function_name"],
            test_cases=data["test_cases"]
        )

        exec_payload = {
            "language": data["language"],
            "code": harness_code,
            "mode": "run"
        }
        exec_resp = await _nats_client.request("execution.run", exec_payload, timeout=10.0)
        
        lint_payload = {
            "language": data["language"],
            "code": data["code"],
            "mode": "lint"
        }
        try:
            lint_resp = await _nats_client.request("execution.run", lint_payload, timeout=10.0)
        except Exception as e:
            print(f"Linting failed: {e}")
            lint_resp = {}

        results = grading.compute_grade_from_results(
            execution_output=exec_resp.get("output", "") + "\n" + str(exec_resp.get("error") or ""),
            lint_output=lint_resp.get("output", "")
        )
        
        print(f"DEBUG: Ephemeral Grading Results: {results}")
        return results
        
    except Exception as e:
        print(f"Error grading ephemeral attempt: {e}")
        return {"error": str(e)}