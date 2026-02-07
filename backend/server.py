from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
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
    return {"message": "Workflow Bridge API"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    from seed import seed_data
    await seed_data(db)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
