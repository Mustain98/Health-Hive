from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select
from app.modules.user.model import User, UserData
from app.modules.user.schema import UserLogin, UserRegister


def normalize_identifier(identifier: str) -> str:
    return identifier.strip()


def is_email(identifier: str) -> bool:
    return "@" in identifier and "." in identifier


def get_user_by_identifier(
    session: Session,
    identifier: str,
) -> User | None:
    identifier = normalize_identifier(identifier)

    if is_email(identifier):
        return get_user_by_email(session, identifier.lower())

    return get_user_by_username(session, identifier)


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(
        select(User).where(User.username == username)
    ).first()

def get_user_by_email(session: Session, email: str,) -> User | None:
    return session.exec(
        select(User).where(func.lower(User.email) == email.lower())
    ).first()

def getuserdata(session:Session,user_id:str):
    return session.get(UserData,user_id)

def deactivate_user(
    session: Session,
    user: User,
) -> None:
    user.is_active = False

    session.add(user)
    session.commit()


