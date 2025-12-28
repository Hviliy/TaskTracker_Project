from fastapi import FastAPI
from app.api.routes.tasks import router as tasks_router

app = FastAPI(title="Task Tracker")

app.include_router(tasks_router)

@app.get("/health")
def health():
    return {"status": "ok"}