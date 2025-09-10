#!/usr/bin/env python3
"""
Simple script to run the FastAPI server with environment variables.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
load_dotenv()

# Debug: Print the API_KEY to see what's loaded
print(f"API_KEY from environment: {os.getenv('API_KEY')}")

# Set environment variables (only if not already set)
os.environ.setdefault("API_KEY", "test-api-key-123")
os.environ.setdefault("DATABASE_URL", "sqlite:///./carrier_agent.db")
os.environ.setdefault("FMCSA_API_KEY", "your-fmcsa-api-key-here")
os.environ.setdefault("FMCSA_BASE_URL", "https://mobile.fmcsa.dot.gov/qc/services/carriers")
os.environ.setdefault("DEBUG", "True")

if __name__ == "__main__":
    import uvicorn
    
    port = 8001  # Use a different port to avoid conflicts
    print("Starting Inbound Carrier Sales Agent API...")
    print(f"Health check: http://localhost:{port}/api/health")
    print(f"API Documentation: http://localhost:{port}/docs")
    print(f"Using API_KEY: {os.getenv('API_KEY')}")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )