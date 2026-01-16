from fastapi import FastAPI
import logfire

from contextlib import asynccontextmanager
import uvicorn
from src.handlers import(
    handle_create_attempt,
    handle_get_attempt,
    handle_get_user_attempts,
    handle_get_exercise_attempts,
    handle_get_best_attempt,
    handle_get_all_best_attempts,
    handle_grade_ephemeral,
    handle_attempt_graded,
    set_nats_client,
)

from src.config import settings
from src.database import init_db
from src.nats_client import NATSClient


from prometheus_fastapi_instrumentator import Instrumentator

nats_client = NATSClient()
logfire.configure()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Attempt Service...")
    
    init_db()
    
    await nats_client.connect()
    set_nats_client(nats_client) 

    await nats_client.subscribe("attempts.create", handle_create_attempt)
    await nats_client.subscribe("attempts.get", handle_get_attempt)
    await nats_client.subscribe("attempts.user", handle_get_user_attempts)
    await nats_client.subscribe("attempts.exercise", handle_get_exercise_attempts)
    await nats_client.subscribe("attempts.best", handle_get_best_attempt)
    await nats_client.subscribe("attempts.best.all", handle_get_all_best_attempts)
    await nats_client.subscribe("attempts.grade_ephemeral", handle_grade_ephemeral)
    
    await nats_client.subscribe("attempt.graded", handle_attempt_graded)

    print("Attempt Service ready!")

    yield
    
    print("Shutting down Attempt Service...")
    await nats_client.close()

app = FastAPI(title="Attempt Service", lifespan=lifespan)
logfire.instrument_fastapi(app)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "attempt-service"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)