#!/usr/bin/env python3
"""
Simple script to run the FastAPI server with environment variables.
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ.setdefault("API_KEY", "test-api-key-123")
os.environ.setdefault("DATABASE_URL", "sqlite:///./carrier_agent.db")
os.environ.setdefault("FMCSA_API_KEY", "your-fmcsa-api-key-here")
os.environ.setdefault("FMCSA_BASE_URL", "https://mobile.fmcsa.dot.gov/qc/services/carriers")
os.environ.setdefault("DEBUG", "True")

if __name__ == "__main__":
    import uvicorn
    
    print("Starting Inbound Carrier Sales Agent API...")
    print("Health check: http://localhost:8000/api/health")
    print("API Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
