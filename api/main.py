# api/main.py - Updated version
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# Import all routers including the new HappyRobot integration
from api.routers import health, loads, fmcsa, negotiation, calls, metrics, happyrobot
from api.db import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Inbound Carrier Sales Agent API",
    description="Backend API for carrier sales agent with load management and negotiation. Integrated with HappyRobot AI platform.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - configure for production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(loads.router, prefix="/api", tags=["loads"])
app.include_router(fmcsa.router, prefix="/api", tags=["fmcsa"])
app.include_router(negotiation.router, prefix="/api", tags=["negotiation"])
app.include_router(calls.router, prefix="/api", tags=["calls"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])

# *** NEW: HappyRobot integration endpoints ***
app.include_router(happyrobot.router, prefix="/api", tags=["happyrobot"])

# Serve dashboard static files if they exist
if os.path.exists("dash"):
    app.mount("/dash", StaticFiles(directory="dash"), name="dashboard")

@app.get("/")
async def root():
    return {
        "message": "Inbound Carrier Sales Agent API", 
        "version": "1.0.0",
        "status": "ready",
        "integrations": ["HappyRobot AI Platform"],
        "endpoints": {
            "health": "/api/health",
            "docs": "/docs",
            "happyrobot_integration": "/api/happyrobot/*"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)