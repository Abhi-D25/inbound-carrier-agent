from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from api.routers import health, loads, fmcsa, negotiation, calls, metrics
from api.db import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Inbound Carrier Sales Agent API",
    description="Backend API for carrier sales agent with load management and negotiation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(loads.router, prefix="/api", tags=["loads"])
app.include_router(fmcsa.router, prefix="/api", tags=["fmcsa"])
app.include_router(negotiation.router, prefix="/api", tags=["negotiation"])
app.include_router(calls.router, prefix="/api", tags=["calls"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])

# Serve dashboard static files
if os.path.exists("dash"):
    app.mount("/dash", StaticFiles(directory="dash"), name="dashboard")

@app.get("/")
async def root():
    return {"message": "Inbound Carrier Sales Agent API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
