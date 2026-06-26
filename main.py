import os
import random
import string
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from database import execute_query
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from models import UserRegister, UserLogin, URLCreate, TokenRefresh
from database import get_redis

security = HTTPBearer()

app = FastAPI(title="URL Shortener API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_tables():
    execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            email VARCHAR(200) UNIQUE NOT NULL,
            password VARCHAR(200) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            original_url TEXT NOT NULL,
            short_code VARCHAR(20) UNIQUE NOT NULL,
            clicks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS clicks (
            id SERIAL PRIMARY KEY,
            url_id INTEGER REFERENCES urls(id),
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("Tables ready")

create_tables()

def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def get_current_user(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["user_id"]

@app.get("/")
def root():
    return {"message": "URL Shortener API"}

@app.post("/register")
def register(user: UserRegister):
    existing = execute_query(
        "SELECT id FROM users WHERE email = %s",
        (user.email,),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(user.password)
    execute_query(
        "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
        (user.name, user.email, hashed)
    )
    return {"message": "Account created successfully"}

@app.post("/login")
def login(credentials: UserLogin):
    rate_key = f"login_attempts:{credentials.email}"
    check_rate_limit(rate_key, max_requests=5, window_seconds=60)
    
    user = execute_query(
        "SELECT id, password FROM users WHERE email = %s",
        (credentials.email,),
        fetch="one"
    )
    if not user or not verify_password(credentials.password, user[1]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token(user[0])
    refresh_token = create_refresh_token(user[0])
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/refresh")
def refresh_token(body: TokenRefresh):
    payload = verify_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    new_access_token = create_access_token(payload["user_id"])
    return {"access_token": new_access_token, "token_type": "bearer"}

@app.post("/urls")
def create_url(url: URLCreate, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = get_current_user(f"Bearer {credentials.credentials}")
    short_code = url.custom_code if url.custom_code else generate_short_code()
    existing = execute_query(
        "SELECT id FROM urls WHERE short_code = %s",
        (short_code,),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail="Short code already taken")
    execute_query(
        "INSERT INTO urls (user_id, original_url, short_code) VALUES (%s, %s, %s)",
        (user_id, url.original_url, short_code)
    )
    return {
        "message": "URL created",
        "short_code": short_code,
        "short_url": f"http://localhost:8002/{short_code}"
    }

@app.get("/urls")
def get_my_urls(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = get_current_user(f"Bearer {credentials.credentials}")
    rows = execute_query(
        "SELECT id, original_url, short_code, clicks, created_at FROM urls WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
        fetch="all"
    )
    urls = []
    for row in rows:
        urls.append({
            "id": row[0],
            "original_url": row[1],
            "short_code": row[2],
            "clicks": row[3],
            "created_at": str(row[4])
        })
    return {"urls": urls}

@app.get("/{short_code}")
def redirect_url(short_code: str):
    r = get_redis()
    cache_key = f"url:{short_code}"
    
    cached_url = r.get(cache_key)
    if cached_url:
        try:
            execute_query("UPDATE urls SET clicks = clicks + 1 WHERE short_code = %s", (short_code,))
        except Exception:
            pass
        return RedirectResponse(url=cached_url)
    
    row = execute_query(
        "SELECT id, original_url FROM urls WHERE short_code = %s",
        (short_code,),
        fetch="one"
    )
    if not row:
        raise HTTPException(status_code=404, detail="URL not found")
    
    r.set(cache_key, row[1], ex=3600)
    
    try:
        execute_query("UPDATE urls SET clicks = clicks + 1 WHERE id = %s", (row[0],))
        execute_query("INSERT INTO clicks (url_id) VALUES (%s)", (row[0],))
    except Exception:
        pass
    
    return RedirectResponse(url=row[1])



def check_rate_limit(key: str, max_requests: int, window_seconds: int):
    r = get_redis()
    current = r.get(key)
    if current is None:
        r.set(key, 1, ex=window_seconds)
        return
    if int(current) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many requests, please try again later")
    r.incr(key)
