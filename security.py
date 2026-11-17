import os, hashlib, hmac, secrets
import datetime as dt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from . import models

SECRET = os.getenv("SECRET_KEY", "dev-only-secret-change-me-in-production-0000")
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(p: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${h}"

def verify_password(p: str, stored: str) -> bool:
    salt, h = stored.split("$")
    cand = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(cand, h)

def create_token(username: str, role: str) -> str:
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=8)
    return jwt.encode({"sub": username, "role": role, "exp": exp}, SECRET, algorithm="HS256")

def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> models.User:
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.query(models.User).filter_by(username=data["sub"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user

def require_roles(*roles: str):
    def dep(user: models.User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return dep
