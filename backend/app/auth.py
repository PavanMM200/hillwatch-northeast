import hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, Request
from sqlalchemy import select
from .database import Session, User, LoginSession
from .errors import ServiceError

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    result = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return salt + ':' + result.hex()
def check_password(password, stored):
    return hmac.compare_digest(hash_password(password, stored.split(':')[0]), stored)
def current_user(request: Request):
    token = request.cookies.get('hill_session', '')
    with Session() as db:
        s = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
        if not s or datetime.fromisoformat(s.expires) <= datetime.now(timezone.utc):
            raise ServiceError('AUTH_REQUIRED', 'Sign in with an authorized account.', 401)
        return db.get(User, s.user_id)
def roles(*allowed):
    def require(user=Depends(current_user)):
        if user.role not in allowed: raise ServiceError('FORBIDDEN', 'Your role cannot perform this operation.', 403)
        return user
    return require
def new_session(db, user):
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                        expires=(datetime.now(timezone.utc)+timedelta(hours=8)).isoformat()))
    return token
