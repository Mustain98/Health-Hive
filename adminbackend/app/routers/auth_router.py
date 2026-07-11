from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import jwt
from datetime import datetime, timedelta, timezone
from core.supabase_client import supabase
from core.auth import get_current_user, SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/api/auth", tags=["Auth"])

ph = PasswordHasher()
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def _create_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username  # OAuth2 spec uses 'username' field
    password = form_data.password

    # Fetch user from Supabase by email
    result = supabase.table("users").select("id, email, user_type, hashed_password").eq("email", email).single().execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = result.data

    # Verify password using Argon2
    try:
        ph.verify(user["hashed_password"], password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check admin role
    if user.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access only. Your account does not have admin privileges.",
        )

    token = _create_token(user["id"], "admin")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": "admin",
        }
    }


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id")
    
    # Fetch full user details from Supabase
    result = supabase.table("users").select("id, email, full_name, user_type, username").eq("id", user_id).single().execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
        
    user = result.data
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name", ""),
        "role": user.get("user_type", "admin"),
        "username": user.get("username", "")
    }
