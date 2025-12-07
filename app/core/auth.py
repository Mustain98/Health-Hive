from argon2 import PasswordHasher
from jose import jwt,JWTError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.user import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

password_hasher= PasswordHasher()
SECRET_KEY = "MusTaj2611998"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1

security= HTTPBearer()

def hash_password(password:str):
    print("in hash password",password)
    return password_hasher.hash(password)

def verify_password(plain_password:str,hash_password:str):
    try:
        password_hasher.verify(hash_password,plain_password)
        return True
    except Exception as e:
        print("Password verification Falied: ",e)
        return False
    
def create_access_token(data:dict):
    to_encode=data.copy()
    expire=datetime.now(timezone.utc)+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp":expire})
    encoded_jwt=jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(auth:HTTPAuthorizationCredentials=Depends(security),session:Session=Depends(get_session)):
    credentials_exception=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Couldnot validate credentials",
        headers={"www-Authenticate":"Bearer"},
    )
    token=auth.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = str(payload.get("sub"))
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception
    return user
