import os
import jwt
import asyncio
import logging
import resend
from email_validator import EmailNotValidError, validate_email
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import hashlib

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get('JWT_SECRET', 'fallback_secret')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

security = HTTPBearer()

mongo_url = os.environ['MONGO_URL']
_client = AsyncIOMotorClient(mongo_url)
db = _client[os.environ['DB_NAME']]

RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
EMAIL_FROM_NAME = os.environ.get('EMAIL_FROM_NAME', 'Justino Online Forms')
REPLY_TO_EMAIL = os.environ.get('REPLY_TO_EMAIL', '')
RESEND_ALLOW_TEST_MODE = os.environ.get('RESEND_ALLOW_TEST_MODE', 'false').lower() == 'true'
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def hash_password(password: str) -> str:
    # Pre-hash to fixed length (bcrypt-safe)
    sha = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(sha)



def verify_password(plain: str, hashed: str) -> bool:
    sha = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return pwd_context.verify(sha, hashed)


def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    logger.info(f"Login attempt for: {user.get('email', 'Unknown')}")
    logger.info(f"User found: {bool(user)}")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    if "has_viewed_tutorial" not in user:
        user["has_viewed_tutorial"] = False
    return user


async def require_admin(user=Depends(get_current_user)):
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def normalize_email_address(email_value: str) -> str:
    normalized = validate_email(email_value, check_deliverability=False)
    return normalized.normalized


def build_sender_address() -> str:
    if not SENDER_EMAIL:
        raise ValueError("SENDER_EMAIL is not configured")

    sender_email = normalize_email_address(SENDER_EMAIL)
    if sender_email.lower().endswith("@resend.dev") and not RESEND_ALLOW_TEST_MODE:
        raise ValueError(
            "SENDER_EMAIL is using Resend's test sender. Set SENDER_EMAIL to an address on your verified domain "
            "to deliver email to arbitrary recipients."
        )

    if EMAIL_FROM_NAME:
        return f"{EMAIL_FROM_NAME} <{sender_email}>"

    return sender_email


async def send_email_notification(to_email: str, subject: str, html: str):
    if not RESEND_API_KEY:
        logger.info(f"Email skipped (no API key): {subject} -> {to_email}")
        return

    if not to_email:
        logger.info(f"Email skipped (no recipient): {subject}")
        return

    try:
        recipient_email = normalize_email_address(to_email)
        sender_address = build_sender_address()
        params = {
            "from": sender_address,
            "to": [recipient_email],
            "subject": subject,
            "html": html
        }
        if REPLY_TO_EMAIL:
            params["reply_to"] = normalize_email_address(REPLY_TO_EMAIL)

        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent: {subject} -> {recipient_email} ({response.get('id', 'no-id')})")
    except EmailNotValidError as exc:
        logger.error(f"Email validation failed for '{to_email}': {exc}")
    except ValueError as exc:
        logger.error(f"Email configuration error: {exc}")
    except Exception as e:
        logger.error(f"Email failed: {e}")
