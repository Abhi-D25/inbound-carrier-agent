from fastapi import APIRouter, Depends, HTTPException
from api.deps import require_api_key, get_db
from api.schemas import CallPersistRequest, CallPersistResponse
from api.services.call_persistence import CallPersistenceService
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any

class CallSaveRequest(BaseModel):
    call_id: str
    load_id: Optional[str] = None
    mc: str
    carrier_name: Optional[str] = None
    fmcsa_status: Optional[str] = None
    initial_rate: Optional[float] = None
    current_rate: Optional[float] = None
    listed_rate: Optional[float] = None
    final_rate: Optional[float] = None
    last_offer: Optional[float] = None
    negotiation_rounds: Optional[int] = 0
    outcome: str = "no_agreement"
    sentiment: Optional[str] = None
    extracted_json: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    call_duration_seconds: Optional[int] = None
    notes: Optional[str] = None

router = APIRouter()

@router.post("/calls", response_model=CallPersistResponse)
async def save_call(
    call_data: CallSaveRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Save call data to database.
    
    Saves comprehensive call information including:
    - Call metadata (ID, timestamps, duration)
    - Carrier information (MC, name, FMCSA status)
    - Load information (load_id, rates)
    - Negotiation details (rounds, offers, outcome)
    - Sentiment and extracted data
    """
    try:
        persistence_service = CallPersistenceService(db)
        result = persistence_service.save_call(call_data.dict())
        
        return CallPersistResponse(
            ok=True,
            data=result
        )
        
    except Exception as e:
        return CallPersistResponse(
            ok=False,
            error=f"Failed to save call: {str(e)}"
        )

@router.get("/calls/{call_id}")
async def get_call(
    call_id: str,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific call by ID.
    """
    try:
        persistence_service = CallPersistenceService(db)
        call_data = persistence_service.get_call(call_id)
        
        if not call_data:
            raise HTTPException(status_code=404, detail="Call not found")
        
        return {
            "ok": True,
            "data": call_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to retrieve call: {str(e)}"
        }

@router.get("/calls/carrier/{carrier_mc}")
async def get_calls_by_carrier(
    carrier_mc: str,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Get all calls for a specific carrier.
    """
    try:
        persistence_service = CallPersistenceService(db)
        calls = persistence_service.get_calls_by_carrier(carrier_mc)
        
        return {
            "ok": True,
            "data": {
                "carrier_mc": carrier_mc,
                "calls": calls,
                "total": len(calls)
            }
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to retrieve calls: {str(e)}"
        }

@router.post("/calls/legacy", response_model=CallPersistResponse)
async def persist_call_legacy(
    call_request: CallPersistRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Legacy endpoint for call persistence (uses old schema).
    """
    try:
        # Convert legacy request to new format
        call_data = {
            "call_id": call_request.call_id,
            "load_id": call_request.load_id,
            "mc": call_request.carrier_mc,
            "carrier_name": call_request.carrier_name,
            "initial_rate": call_request.initial_rate,
            "current_rate": call_request.current_rate,
            "negotiation_rounds": call_request.negotiation_round,
            "outcome": call_request.status,
            "call_duration_seconds": call_request.call_duration_seconds,
            "notes": call_request.notes
        }
        
        persistence_service = CallPersistenceService(db)
        result = persistence_service.save_call(call_data)
        
        return CallPersistResponse(
            ok=True,
            data=result
        )
        
    except Exception as e:
        return CallPersistResponse(
            ok=False,
            error=f"Failed to save call: {str(e)}"
        )
