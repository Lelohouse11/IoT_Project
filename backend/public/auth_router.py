"""Authentication router for driver profiles (drivers PWA)."""

from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import base64
import os
from backend.shared import config, database

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
        expire = datetime.utcnow() + timedelta(minutes=30)
    
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

def verify_token(token: str) -> dict:
    """Verify the token and return the payload data."""
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
            
        return data
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------------------------------------------------------

class DriverRegister(BaseModel):
    username: str
    email: str
    password: str
    license_plate: Optional[str] = None

class DriverLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    email: str
    driver_id: int
    license_plate: Optional[str] = None

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(driver: DriverRegister):
    """Register a new driver profile (no whitelist required)."""
    
    # Check if driver already exists
    conn = database.get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM driver_profiles WHERE email = %s", (driver.email,))
        existing_driver = cursor.fetchone()
        if existing_driver:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        cursor.execute("SELECT * FROM driver_profiles WHERE username = %s", (driver.username,))
        existing_username = cursor.fetchone()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Hash password and insert
        hashed_pwd = hash_password(driver.password)
        cursor.execute(
            "INSERT INTO driver_profiles (username, email, password_hash, license_plate) VALUES (%s, %s, %s, %s)",
            (driver.username, driver.email, hashed_pwd, driver.license_plate)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return {"message": "Driver account created successfully"}

@router.post("/login", response_model=Token)
def login(driver: DriverLogin):
    """Login a driver and return JWT token."""
    conn = database.get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM driver_profiles WHERE email = %s", (driver.email,))
        db_driver = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not db_driver or not verify_password(driver.password, db_driver["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={
            "sub": db_driver["email"],
            "driver_id": db_driver["id"],
            "username": db_driver["username"]
        },
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": db_driver["username"],
        "email": db_driver["email"],
        "driver_id": db_driver["id"],
        "license_plate": db_driver["license_plate"]
    }

@router.post("/refresh", response_model=Token)
def refresh_token(authorization: str = Header(None)):
    """Refresh an existing token with a new 30-minute expiration."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    # Get fresh driver data from database
    conn = database.get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM driver_profiles WHERE email = %s", (payload["sub"],))
        db_driver = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    
    if not db_driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Create new token with fresh expiration
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={
            "sub": db_driver["email"],
            "driver_id": db_driver["id"],
            "username": db_driver["username"]
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": db_driver["username"],
        "email": db_driver["email"],
        "driver_id": db_driver["id"],
        "license_plate": db_driver["license_plate"]
    }

@router.delete("/account")
def delete_account(authorization: str = Header(None)):
    """Delete the authenticated driver's account."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    conn = database.get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor()
    try:
        # Delete the driver profile
        cursor.execute("DELETE FROM driver_profiles WHERE id = %s", (payload["driver_id"],))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Driver not found")
    finally:
        cursor.close()
        conn.close()
    
    return {"message": "Account deleted successfully"}
