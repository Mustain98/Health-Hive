# app/routers/auth.py
from datetime import datetime, timezone
import re

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Cookie,
)
from fastapi.security import OAuth2PasswordRequestForm

from jose import jwt, JWTError
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_password,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
)
from app.models.user import User
from app.schemas.user import (
    UserLogin,
    UserRegister,
    UserRead,
    UserUpdate,
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

@auth_router.post("/auth/register", response_model=UserRead)
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
    response: Response,
    session: Session = Depends(get_session),
):
    identifier = user_data.identifier.strip()

    if "@" in identifier:
        user = _get_user_by_email(session, identifier.lower())
    else:
        user = _get_user_by_username(session, identifier)

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username/email or password",
        )

    # Short-lived access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    # Long-lived refresh token stored in HttpOnly cookie
    refresh_token = create_refresh_token(user.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        # secure=True   # enable in production with HTTPS
    )

    return Token(access_token=access_token, token_type="bearer")

@auth_router.post("/auth/token", response_model=Token)
def oauth_token(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
    ):
    # OAuth2 standard: form.username + form.password
    identifier = (form.username or "").strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="Missing username/identifier")

    if "@" in identifier:
        user = _get_user_by_email(session, identifier.lower())
    else:
        user = _get_user_by_username(session, identifier)

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # keep refresh token cookie behavior (optional)
    if response is not None:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
        )

    return Token(access_token=access_token, token_type="bearer")


# ---------- get current user ----------

@auth_router.get("/auth/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user


# ---------- update current user ----------

@auth_router.put("/auth/users/me", response_model=UserRead)
def update_current_user(
    user_update: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    updated = False

    # email update
    if user_update.email and user_update.email != current_user.email:
        email = user_update.email.lower().strip()
        _ensure_unique_email(session, email)
        current_user.email = email
        updated = True

    # username update
    if user_update.username and user_update.username != current_user.username:
        username = _slugify(user_update.username)
        _ensure_unique_username(session, username)
        current_user.username = username
        updated = True

    # full_name update
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
        updated = True

    # password update
    if user_update.password:
        current_user.hashed_password = hash_password(user_update.password)
        updated = True

    if updated:
        # current_user.updated_at = datetime.now(timezone.utc)
        session.add(current_user)
        session.commit()
        session.refresh(current_user)

    return current_user


# ---------- refresh access token using refresh_token cookie ----------

@auth_router.post("/auth/refresh", response_model=Token)
def refresh_access_token(
    response: Response,
    refresh_token: str = Cookie(default=None),
    session: Session = Depends(get_session),
):
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Missing refresh token",
        )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Invalid token type",
            )

        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
            )

        user_id = int(sub)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    # New access token
    new_access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    # (Optional) rotate refresh token
    new_refresh_token = create_refresh_token(user.id)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        samesite="lax",
        # secure=True  # enable with HTTPS
    )

    return Token(access_token=new_access_token, token_type="bearer")


# ---------- logout: clear refresh token cookie ----------

@auth_router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out"}
