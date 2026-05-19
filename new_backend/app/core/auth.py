from sqlmodel import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session
from app.core.config import SECRET_KEY, ALGORITHM
from app.core.database import get_session
from app.modules.user.model import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
        token:str=Depends(oauth2_scheme),
        session:Session=Depends(get_session),
    )->User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )
    try:
        payload=jwt.decode(token,SECRET_KEY,ALGORITHM)
        user_id=payload.get("sub")
        if user_id==None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user=session.get(User,user_id)

    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    
    return user
