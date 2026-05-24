from datetime import datetime, timedelta, timezone
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import jwt

from app.core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


password_hasher=PasswordHasher()

def hash_password(plain_pass:str)->str:
    return password_hasher.hash(plain_pass)

def verify_password(plain_pass:str,hashed_pass:str)->bool:
    try:
        return password_hasher.verify(hashed_pass,plain_pass)
    except(ValueError,VerificationError,VerifyMismatchError):
        return False

def create_access_token(
    user_id:str,
    username:str,
    email:str,
    role:str
)->str:
    expire=datetime.now(timezone.utc)+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload={
        "sub":user_id,
        "username":username,
        "email":email,
        "role":role,
        "exp":expire,
    }
    
    return jwt.encode(payload,SECRET_KEY,ALGORITHM)


