# Inbound Carrier Sales Agent Backend

A FastAPI-based backend service for an Inbound Carrier Sales Agent that provides APIs for load management, carrier verification, negotiation, and call tracking.

## Features

- **Load Management**: Search and filter available loads
- **Carrier Verification**: FMCSA API integration for carrier validation
- **Negotiation Engine**: Automated negotiation with 3-round cap
- **Call Tracking**: Persist and analyze call data
- **Metrics Dashboard**: KPI tracking and reporting
- **API Authentication**: Secure API key-based authentication

## Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)

### Installation

1. Clone the repository
2. Create and activate virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables:
   ```bash
   export API_KEY="your-secret-api-key-here"
   export DATABASE_URL="sqlite:///./carrier_agent.db"
   export FMCSA_API_KEY="your-fmcsa-api-key-here"
   ```

5. Run the server:
   ```bash
   python3 run_server.py
   ```

The server will start on `http://localhost:8000`

## API Endpoints

### Health Check
- `GET /api/health` - No authentication required

### Loads
- `POST /api/loads/search` - Search available loads (requires API key)

### FMCSA
- `POST /api/fmcsa/verify` - Verify carrier with FMCSA (requires API key)

### Negotiation
- `POST /api/negotiation/evaluate` - Evaluate negotiation and counter offer (requires API key)

### Calls
- `POST /api/calls` - Persist call data (requires API key)

### Metrics
- `GET /api/metrics/summary` - Get KPI metrics summary (requires API key)

## Authentication

All endpoints except `/api/health` require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/metrics/summary
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
api/
├── main.py              # FastAPI application
├── deps.py              # Dependencies (auth, db)
├── db.py                # Database configuration
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
└── routers/             # API route handlers
    ├── health.py
    ├── loads.py
    ├── fmcsa.py
    ├── negotiation.py
    ├── calls.py
    └── metrics.py

services/                # Business logic services
seed/                    # Database seeding
dash/                    # Dashboard UI
tests/                   # Test files
infra/                   # Docker configuration
```

## Development

The project uses:
- **FastAPI** for the web framework
- **SQLAlchemy** for ORM
- **SQLite** for local development (PostgreSQL for production)
- **Pydantic** for data validation
- **Uvicorn** as ASGI server

## Next Steps

This is the initial scaffold. The following features are planned:
- [ ] Implement load search and ranking logic
- [ ] Add FMCSA API integration
- [ ] Build negotiation policy engine
- [ ] Create metrics calculation service
- [ ] Add database seeding
- [ ] Build dashboard UI
- [ ] Add Docker configuration
- [ ] Write comprehensive tests
