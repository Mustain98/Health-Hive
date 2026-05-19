from sqlmodel import Session
from schema import UserLogin,UserRegister,UserDataUpdate,UserDataRead,UserUpdate,UserRead
from service import get_user_by_email,get_user_by_identifier,get_user_by_username,getuserdata,deactivate_user
from fastapi import HTTPException,status
from model import User,UserData
from app.core.security import hash_password,verify_password,create_access_token
from typing import Optional



def register_controller(session:Session,data:UserRegister)->User:
    existing_email=get_user_by_email(session,data.email)
    existing_username=get_user_by_username(session,data.username)
    if existing_email or existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user=User(
        username=data.username,
        email=data.email,
        password=hash_password(data.password)
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return user



def login_controller(session:Session,data:UserLogin)->str:
    user=get_user_by_identifier(data.identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    verified=verify_password(data.password,user.password)

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )
    
    return create_access_token(user.id,user.username,user.email,user.role.value)

def get_my_data_controller(
    session: Session,
    me: User,
) -> Optional[UserData]:
    return getuserdata(UserData, me.id)

def update_me_controller(data:UserUpdate,session:Session,me:User,)->UserRead:
    user_email=get_user_by_email(session,data.email)
    user_username=get_user_by_username(session,data.username)
    if user_username or user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already used",
        )
    if data.email:
        me.email=data.email
    if data.username:
        me.username=data.username

def update_user_data(session:Session,me:User,data:UserDataUpdate)->UserData:

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