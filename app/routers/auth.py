from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import re

from app.core.database import get_session
from app.core.auth import verify_password, create_access_token, hash_password
from app.models.user import User
from app.schemas.user import (
    UserLogin,
    UserRegister,
    UserRead,
)
from app.schemas.token import Token

auth_router = APIRouter()


# ---------- helpers (router-only) ----------

def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "user"


def _get_user_by_email(session: Session, email: str):
    return session.exec(select(User).where(User.email == email)).first()


def _get_user_by_username(session: Session, username: str):
    return session.exec(select(User).where(User.username == username)).first()


def _generate_username(session: Session, email: str) -> str:
    base = _slugify(email.split("@")[0])
    candidate = base
    i = 1

    while _get_user_by_username(session, candidate):
        i += 1
        candidate = f"{base}{i}"

    return candidate


def _ensure_unique_email(session: Session, email: str):
    if _get_user_by_email(session, email):
        raise HTTPException(status_code=400, detail="Email already registered")


def _ensure_unique_username(session: Session, username: str):
    if _get_user_by_username(session, username):
        raise HTTPException(status_code=400, detail="Username already taken")


# ---------- register common user ----------

@auth_router.post("/auth/users/register", response_model=UserRead)
def register_user(
    new_user: UserRegister,
    session: Session = Depends(get_session),
):
    email = new_user.email.lower().strip()
    _ensure_unique_email(session, email)

    if new_user.username:
        username = _slugify(new_user.username)
        _ensure_unique_username(session, username)
    else:
        username = _generate_username(session, email)

    hashed = hash_password(new_user.password)

    user = User(
        email=email,
        username=username,
        full_name=new_user.full_name,
        hashed_password=hashed,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ---------- login (username OR email) ----------

@auth_router.post("/auth/login", response_model=Token)
def login_user(
    user_data: UserLogin,
    session: Session = Depends(get_session),
):
    identifier = user_data.identifier.strip()

    if "@" in identifier:
        user = _get_user_by_email(session, identifier.lower())
    else:
        user = _get_user_by_username(session, identifier)

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username/email or password")

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return Token(access_token=access_token, token_type="bearer")
