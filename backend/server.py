from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
import os
import logging
from pathlib import Path
from fastapi import WebSocket
from realtime import manager
from utils.helpers import db, _client as client, get_int_env

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(redirect_slashes=False)
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import routes
from routes.auth import auth_router
from routes.users import users_router
from routes.departments import departments_router
from routes.form_templates import templates_router
from routes.requests import requests_router
from routes.notifications import notifications_router
from routes.dashboard import dashboard_router

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(departments_router)
api_router.include_router(templates_router)
api_router.include_router(requests_router)
api_router.include_router(notifications_router)
api_router.include_router(dashboard_router)

@api_router.get("/")
async def root():
    return {"message": "Justino Online Forms API"}


@api_router.get("/realtime/status")
async def realtime_status():
    return await manager.get_status()

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    GZipMiddleware,
    minimum_size=get_int_env("GZIP_MINIMUM_SIZE", 1000),
)


def get_bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


async def ensure_indexes():
    await db.users.create_index("id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.users.create_index("department_id")
    await db.departments.create_index("id", unique=True)
    await db.departments.create_index("code", unique=True)
    await db.form_templates.create_index("id", unique=True)
    await db.form_templates.create_index([("department_id", 1), ("is_active", 1)])
    await db.requests.create_index("id", unique=True)
    await db.requests.create_index([("created_at", -1)])
    await db.requests.create_index([("department_id", 1), ("status", 1), ("created_at", -1)])
    await db.requests.create_index([("requester_id", 1), ("created_at", -1)])
    await db.requests.create_index([("approvals.approver_id", 1), ("status", 1), ("created_at", -1)])
    await db.requests.create_index([("custodian.user_id", 1), ("status", 1), ("created_at", -1)])
    await db.notifications.create_index("id", unique=True)
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("is_read", 1)])

@app.on_event("startup")
async def startup_event():
    if get_bool_env("ENSURE_INDEXES_ON_STARTUP", True):
        await ensure_indexes()
    if get_bool_env("SEED_ON_STARTUP", True):
        from seed import seed_data
        await seed_data(db)
    else:
        logger.info("Startup seed skipped: SEED_ON_STARTUP is false")
    await manager.startup()

@app.on_event("shutdown")
async def shutdown_db_client():
    await manager.shutdown()
    client.close()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            message = await ws.receive_text()
            if message == "ping":
                await ws.send_text("pong")
    except:
        manager.disconnect(ws)

