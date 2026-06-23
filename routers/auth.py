import os
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from core.mongo_db import get_db
import stripe

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
        "is_premium": False,
        "memory": [] # Will store past resumes/audits here
    }
    users_collection.insert_one(user_doc)
    
    access_token = create_access_token(data={"sub": user_id})
    return {"access_token": access_token, "token_type": "bearer", "user": {"user_id": user_id, "username": user.username, "email": user.email, "is_premium": False}}

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
    return {"access_token": access_token, "token_type": "bearer", "user": {"user_id": db_user["user_id"], "username": db_user["username"], "email": db_user["email"], "is_premium": db_user.get("is_premium", False)}}


stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")

class PaymentPayload(BaseModel):
    cardholder: str
    card_number: str
    expiry: str
    cvv: str

@router.post("/upgrade_premium")
def upgrade_premium(payment: PaymentPayload, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    if not payment.card_number or len(payment.card_number) < 12:
        raise HTTPException(status_code=400, detail="Invalid payment details")

    try:
        # If we have a real test key, we could create a PaymentMethod and PaymentIntent.
        # However, since we are accepting raw card details (not PCI compliant for prod),
        # we will mock the Stripe API call here if the key is the placeholder.
        if stripe.api_key == "sk_test_placeholder":
            # Simulate Stripe latency and success
            pass
        else:
            # In a real scenario using Elements, we'd receive a PaymentMethod ID, not raw cards.
            # Here we mock the server-side integration structure:
            stripe.PaymentIntent.create(
                amount=4900, # $49.00
                currency="usd",
                payment_method_types=["card"],
                description=f"Premium VIP Upgrade for user {user_id}"
            )
            # We would normally confirm the intent here, but without a real frontend token, 
            # we just ensure the Stripe SDK initializes and runs without crashing.
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe Payment Error: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Payment Processing Error")
        
    db.users.update_one({"user_id": user_id}, {"$set": {"is_premium": True}})
    
    return {"status": "success", "message": "Premium VIP Clearance Activated via Stripe"}
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
        
    user_doc["is_premium"] = user_doc.get("is_premium", False)
    return user_doc

class ChangePasswordPayload(BaseModel):
    old_password: str
    new_password: str

@router.post("/change_password")
def change_password(payload: ChangePasswordPayload, user_id: str = Depends(get_current_user)):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    user_doc = db.users.find_one({"user_id": user_id})
    if not user_doc or not verify_password(payload.old_password, user_doc["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid old password")
        
    new_hash = get_password_hash(payload.new_password)
    db.users.update_one({"user_id": user_id}, {"$set": {"hashed_password": new_hash}})
    
    return {"status": "success", "message": "Password changed successfully"}
