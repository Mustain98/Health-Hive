# app/core/auth.py
from argon2 import PasswordHasher
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.user import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

password_hasher = PasswordHasher()

SECRET_KEY = "MusTaj2611998"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 10          # short-lived access token
REFRESH_TOKEN_EXPIRE_DAYS = 7           # longer-lived refresh token

security = HTTPBearer()


def hash_password(password: str):
    print("in hash password", password)
    return password_hasher.hash(password)


def verify_password(plain_password: str, hash_password: str):
    try:
        # argon2 expects (hash, plain)
        password_hasher.verify(hash_password, plain_password)
        return True
    except Exception as e:
        print("Password verification Falied: ", e)
        return False


def _encode_token(to_encode: dict, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = to_encode.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict) -> str:
    """
    data typically contains: {"sub": <user_id>, "email": <email>}
    We enforce token type "access" here.
    """
    payload = data.copy()
    if "type" not in payload:
        payload["type"] = "access"

    return _encode_token(
        payload,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    """
    Create a long-lived refresh token bound only to the user id.
    """
    payload = {
        "sub": str(user_id),
        "type": "refresh",
    }
    return _encode_token(
        payload,
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = auth.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        token_type = payload.get("type", "access")
        if token_type != "access":
            # Don't allow refresh tokens to be used for normal auth
            raise credentials_exception

        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception

        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception

    return user
