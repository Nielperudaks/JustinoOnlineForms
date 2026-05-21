from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
import os
import logging
from pathlib import Path
from fastapi import WebSocket
from pymongo.errors import OperationFailure
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


def is_railway_environment() -> bool:
    return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))


def should_run_startup_task(name: str, local_default: bool = True) -> bool:
    # Railway production databases can be small; avoid startup writes unless explicitly enabled.
    default = False if is_railway_environment() else local_default
    return get_bool_env(name, default)


def is_low_disk_operation_failure(exc: OperationFailure) -> bool:
    return exc.details.get("code") == 14031 or exc.details.get("codeName") == "OutOfDiskSpace"


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
    if should_run_startup_task("ENSURE_INDEXES_ON_STARTUP"):
        try:
            await ensure_indexes()
        except OperationFailure as exc:
            if is_low_disk_operation_failure(exc):
                logger.error("Startup index creation skipped because MongoDB is low on disk: %s", exc)
            else:
                raise
    else:
        logger.info("Startup index creation skipped")

    if should_run_startup_task("SEED_ON_STARTUP"):
        try:
            from seed import seed_data
            await seed_data(db)
        except OperationFailure as exc:
            if is_low_disk_operation_failure(exc):
                logger.error("Startup seed skipped because MongoDB is low on disk: %s", exc)
            else:
                raise
    else:
        logger.info("Startup seed skipped")
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

