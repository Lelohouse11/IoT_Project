"""Authentication router handling user registration, login, and token verification."""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import base64
import os
from backend import config, database

router = APIRouter()

# --- Standard Lib Security Helpers (No external packages) ---

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2 (Standard Library)."""
    salt = os.urandom(16)
    # 100,000 iterations of SHA256
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    # Return format: salt_hex:hash_hex
    return salt.hex() + ":" + pwd_hash.hex()

def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verify a password against the stored hash."""
    try:
        salt_hex, hash_hex = stored_password.split(":")
        salt = bytes.fromhex(salt_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt, 100000)
        return hmac.compare_digest(pwd_hash.hex(), hash_hex)
    except ValueError:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a simple signed token using HMAC (Standard Library)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Add expiration as string timestamp
    to_encode.update({"exp": expire.isoformat()})
    
    # 1. Encode payload to Base64
    json_str = json.dumps(to_encode)
    payload_b64 = base64.urlsafe_b64encode(json_str.encode()).decode().rstrip("=")
    
    # 2. Sign the payload
    signature = hmac.new(
        config.SECRET_KEY.encode(), 
        payload_b64.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    # 3. Return format: payload.signature
    return f"{payload_b64}.{signature}"

def verify_token(token: str) -> str:
    """Verify the token and return the email (sub)."""
    try:
        payload_b64, signature = token.split(".")
        
        # Verify signature
        expected_signature = hmac.new(
            config.SECRET_KEY.encode(), 
            payload_b64.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid token signature")
            
        # Decode payload
        # Add padding if needed
        padding = '=' * (4 - len(payload_b64) % 4)
        json_str = base64.urlsafe_b64decode(payload_b64 + padding).decode()
        data = json.loads(json_str)
        
        # Check expiration
        expire = datetime.fromisoformat(data["exp"])
        if datetime.utcnow() > expire:
            raise HTTPException(status_code=401, detail="Token expired")
            
        return data["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------------------------------------------------------

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    email: str

def get_password_hash(password):
    return hash_password(password)

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister):
    # 1. Check Whitelist
    if user.email not in config.WHITELISTED_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not in whitelist."
        )

    # 2. Check if user already exists
    conn = database.get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
        existing_user = cursor.fetchone()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # 3. Hash password and insert
        hashed_pwd = get_password_hash(user.password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (user.username, user.email, hashed_pwd)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return {"message": "User created successfully"}

@router.post("/login", response_model=Token)
def login(user: UserLogin):
    conn = database.get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
        db_user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["email"]}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": db_user["username"],
        "email": db_user["email"]
    }

@router.delete("/delete_account")
def delete_account(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    email = verify_token(token)
    
    conn = database.get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
    finally:
        cursor.close()
        conn.close()
        
    return {"message": "Account deleted successfully"}
