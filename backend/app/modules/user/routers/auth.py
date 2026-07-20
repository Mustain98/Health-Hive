# app/routers/auth.py
from datetime import datetime, timezone
import os
import re
import secrets
import uuid

import httpx

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Cookie,
    Body
)
from fastapi.security import OAuth2PasswordRequestForm

from jose import jwt, JWTError
from sqlmodel import Session, select

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

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
from app.modules.user.models import User
from app.modules.user.schemas import UserLogin, UserRegister, UserUpdate, UserPasswordUpdate
from app.modules.user.schemas import Token

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

@auth_router.post("/auth/register", response_model=User)
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


# ---------- Google sign-in ----------

def _issue_login(response: Response, user: User) -> Token:
    """Issue the access token + refresh cookie, exactly like password login."""
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(user.id)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        # secure=True  # enable in production with HTTPS
    )
    return Token(access_token=access_token, token_type="bearer")


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


@auth_router.post("/auth/google", response_model=Token)
def google_sign_in(
    response: Response,
    code: str = Body(..., embed=True, description="Google OAuth authorization code"),
    redirect_uri: str = Body(..., embed=True, description="The redirect_uri used to obtain the code"),
    session: Session = Depends(get_session),
):
    """Redirect (authorization-code) flow: exchange the code for a Google ID token, verify
    it, then log the user in — creating the account on first use and linking to an existing
    account with the same verified email."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")

    # Exchange the one-time code for tokens (server-side, with the client secret).
    try:
        token_resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        token_resp.raise_for_status()
        id_tok = token_resp.json().get("id_token")
    except httpx.HTTPError:
        raise HTTPException(status_code=401, detail="Google authorization failed")

    if not id_tok:
        raise HTTPException(status_code=401, detail="Google authorization failed")

    try:
        claims = google_id_token.verify_oauth2_token(
            id_tok, google_requests.Request(), client_id
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    email = (claims.get("email") or "").lower().strip()
    if not email or not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account has no verified email")

    user = _get_user_by_email(session, email)
    if user is None:
        # First sign-in: create a linked account with an unusable random password.
        # The user can set a real password later via /auth/users/me/set-password.
        user = User(
            email=email,
            username=_generate_username(session, email),
            full_name=claims.get("name"),
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            has_password=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    return _issue_login(response, user)


# ---------- get current user ----------

@auth_router.get("/auth/me", response_model=User)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user


# ---------- update current user ----------

@auth_router.put("/auth/users/me", response_model=UserUpdate)
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

    if updated:
        # current_user.updated_at = datetime.now(timezone.utc)
        session.add(current_user)
        session.commit()
        session.refresh(current_user)

    return current_user

@auth_router.put("/auth/users/me/password", status_code=200)
def update_password(
    user_pass_update: UserPasswordUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(user_pass_update.old_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong password")

    current_user.hashed_password = hash_password(user_pass_update.new_password)

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return {"detail": "Password updated"}


@auth_router.post("/auth/users/me/set-password", status_code=200)
def set_password(
    new_password: str = Body(..., embed=True, min_length=1),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Set the FIRST password for an account created via Google (which holds only a
    random hash) so it can also use email/password login. Once a real password exists,
    changing it goes through /auth/users/me/password (old + new)."""
    if current_user.has_password:
        raise HTTPException(
            status_code=400,
            detail="This account already has a password — use change password instead.",
        )
    current_user.hashed_password = hash_password(new_password)
    current_user.has_password = True
    session.add(current_user)
    session.commit()
    return {"detail": "Password set"}


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

        user_id = uuid.UUID(str(sub))
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

    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,  # if you rotate
        "token_type": "bearer",
    }



# ---------- logout: clear refresh token cookie ----------

@auth_router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out"}
