from fastapi import FastAPI
from app.api.routes.tasks import router as tasks_router
from app.api.routes.auth import router as auth_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.users import router as users_router
from app.api.routes.topics import router as topics_router
from app.ui.router import router as ui_router

app = FastAPI(title="Task Tracker")

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(topics_router)
app.include_router(analytics_router)
app.include_router(users_router)
app.include_router(ui_router)

@app.get("/start")
def start():
    return {"status": "ok"}