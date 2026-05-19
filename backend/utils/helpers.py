import os
import jwt
import asyncio
import logging
import resend
from html import escape
from urllib.parse import quote
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


def get_frontend_url() -> str:
    return (
        os.environ.get("FRONTEND_URL")
        or os.environ.get("APP_URL")
        or os.environ.get("CLIENT_URL")
        or "http://localhost:3000"
    ).rstrip("/")


def build_request_url(request_id: str) -> str:
    return f"{get_frontend_url()}/?request={quote(str(request_id), safe='')}"


def render_request_email(
    *,
    heading: str,
    request_id: str,
    request_number: str,
    request_title: str,
    intro: str,
    requester_name: str = "",
    actor_name: str = "",
    status_label: str = "",
    comments: str = "",
    action_label: str = "Review request",
) -> str:
    request_url = build_request_url(request_id)
    detail_rows = [
        ("Request no.", request_number),
        ("Form", request_title),
        ("Requester", requester_name),
        ("Updated by", actor_name),
        ("Status", status_label),
        ("Comments", comments),
    ]
    rows_html = "".join(
        f"""
        <tr>
          <td style="padding:10px 12px;color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid #e2e8f0;">{escape(label)}</td>
          <td style="padding:10px 12px;color:#0f172a;font-size:14px;font-weight:600;border-bottom:1px solid #e2e8f0;">{escape(str(value))}</td>
        </tr>
        """
        for label, value in detail_rows
        if value
    )

    return f"""
    <div style="margin:0;padding:24px;background:#f8fafc;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
      <div style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
        <div style="background:#0f172a;padding:18px 22px;">
          <div style="color:#93c5fd;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;">Justino Online Forms</div>
          <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;line-height:1.25;">{escape(heading)}</h1>
        </div>
        <div style="padding:22px;">
          <p style="margin:0 0 18px;color:#334155;font-size:15px;line-height:1.55;">{escape(intro)}</p>
          <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;margin-bottom:22px;">
            <tbody>{rows_html}</tbody>
          </table>
          <a href="{escape(request_url, quote=True)}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;padding:11px 16px;border-radius:6px;">{escape(action_label)}</a>
          <p style="margin:18px 0 0;color:#64748b;font-size:12px;line-height:1.45;">
            If the button does not open, copy this link into your browser:<br />
            <a href="{escape(request_url, quote=True)}" style="color:#2563eb;">{escape(request_url)}</a>
          </p>
        </div>
      </div>
    </div>
    """


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


async def require_form_manager(user=Depends(get_current_user)):
    if user["role"] not in ("super_admin", "manager"):
        raise HTTPException(status_code=403, detail="Admin or manager access required")
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
