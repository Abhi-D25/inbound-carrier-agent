from fastapi import HTTPException, Depends, Header
from typing import Optional, Generator
import os
from api.db import SessionLocal

def require_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Dependency to require API key authentication.
    Checks for X-API-Key header and validates against environment variable.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Please provide X-API-Key header."
        )
    
    # Get expected API key from environment
    expected_api_key = os.getenv("API_KEY")
    if not expected_api_key:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: API_KEY not set"
        )
    
    if x_api_key != expected_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return x_api_key

def get_db() -> Generator:
    """
    Dependency to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
