import os
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from core.mongo_db import get_db

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "phantom-cv-super-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(authorization: str = Header(None)):
    if not authorization:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except Exception:
        return None

@router.post("/register")
def register_user(user: UserCreate):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    users_collection = db.users
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user_id = str(uuid.uuid4())
    user_doc = {
        "user_id": user_id,
        "username": user.username,
        "email": user.email,
        "hashed_password": get_password_hash(user.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "memory": [] # Will store past resumes/audits here
    }
    users_collection.insert_one(user_doc)
    
    access_token = create_access_token(data={"sub": user_id})
    return {"access_token": access_token, "token_type": "bearer", "user": {"user_id": user_id, "username": user.username, "email": user.email}}

@router.post("/login")
def login_user(user: UserLogin):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    users_collection = db.users
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    access_token = create_access_token(data={"sub": db_user["user_id"]})
    return {"access_token": access_token, "token_type": "bearer", "user": {"user_id": db_user["user_id"], "username": db_user["username"], "email": db_user["email"]}}

@router.get("/me")
def read_users_me(user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    user_doc = db.users.find_one({"user_id": user_id}, {"_id": 0, "hashed_password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    return user_doc
