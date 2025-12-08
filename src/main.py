from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

from src.config import settings
from src.database import init_db
from src.nats_client import NATSClient
from src.handlers import (
    handle_create_attempt,
    handle_get_attempt,
    handle_get_user_attempts,
    handle_get_exercise_attempts,
    handle_get_best_attempt,
    handle_get_all_best_attempts,
    handle_grade_ephemeral,
    set_nats_client 
)
from prometheus_client import make_asgi_app

nats_client = NATSClient()

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

    
    print("Attempt Service ready!")
    

    yield
    
    print("Shutting down Attempt Service...")
    await nats_client.close()

app = FastAPI(title="Attempt Service", lifespan=lifespan)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "attempt-service"
    }

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)