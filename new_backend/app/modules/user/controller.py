from sqlmodel import Session
from fastapi import HTTPException, status
from app.modules.user.schema import (
    TokenResponse,
    UpdatePassword,
    UserLogin,
    UserRegister,
    UserDataUpdate,
    UserDataRead,
    UserUpdate,
    UserRead,
)
from app.modules.user.service import (
    get_user_by_email,
    get_user_by_identifier,
    get_user_by_username,
    getuserdata,
    deactivate_user,
)
from app.modules.user.model import User, UserData
from app.core.security import hash_password, verify_password, create_access_token
from typing import Optional


def register_controller(session: Session, data: UserRegister) -> User:
    existing_email = get_user_by_email(session, data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    existing_username = get_user_by_username(session, data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = User(
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return user

def login_controller(session: Session, data: UserLogin) -> TokenResponse:
    user = get_user_by_identifier(session, data.identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    verified = verify_password(data.password, user.password)

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )
    
    return TokenResponse(
        access_token=create_access_token(
            user.id,
            user.username,
            user.email,
            user.role.value,
        )
    )

def get_my_data_controller(
    session: Session,
    me: User,
) -> Optional[UserData]:
    return getuserdata(session, me.id)

def update_me_controller(data: UserUpdate, session: Session, me: User,) -> UserRead:
    if data.email:
        existing_email = get_user_by_email(session, data.email)
        if existing_email and existing_email.id != me.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        me.email = data.email

    if data.username:
        existing_username = get_user_by_username(session, data.username)
        if existing_username and existing_username.id != me.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        me.username = data.username

    session.add(me)
    session.commit()
    session.refresh(me)

    return me

def update_password_controller(
    session: Session,
    me: User,
    data: UpdatePassword,
):
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )

    if not verify_password(data.old_password, me.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Old password is incorrect",
        )

    me.password = hash_password(data.new_password)
    session.add(me)
    session.commit()
    session.refresh(me)

    return {"message": "Password updated successfully"}

def update_user_data(session: Session, me: User, data: UserDataUpdate) -> UserData:

    user_data=getuserdata(session,me.id)

    if not user_data:
        user_data=UserData(user_id=me.id)

    update_data=data.model_dump(exclude_unset=True)

    for key,value in update_data.items():
        setattr(user_data,key,value)

    session.add(user_data)
    session.commit()
    session.refresh(user_data)

    return user_data

def deactivate_me_controller(
    session: Session,
    me: User,
):
    deactivate_user(
        session=session,
        user=me,
    )

    return {"message": "User deactivated successfully"}