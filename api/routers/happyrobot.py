# api/routers/happyrobot.py
"""
HappyRobot integration endpoints for conversational AI agent.
These endpoints are designed to be called by HappyRobot tools during conversations.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from api.deps import require_api_key, get_db
from api.services.conversation_manager import ConversationManager
from api.services.call_persistence import CallPersistenceService

router = APIRouter()

# Request/Response models for HappyRobot integration
class StartCallRequest(BaseModel):
    call_id: str = Field(..., description="Unique call identifier from HappyRobot")
    caller_phone: Optional[str] = Field(None, description="Caller's phone number")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional call metadata")

class VerifyMCRequest(BaseModel):
    call_id: str
    mc_number: str = Field(..., description="Motor Carrier number to verify")

class SearchLoadsRequest(BaseModel):
    call_id: str
    equipment_type: str = Field(..., description="Equipment type (Dry Van, Refrigerated, Flatbed)")
    origin: Optional[str] = Field(None, description="Origin state or preference")
    destination: Optional[str] = Field(None, description="Destination state or preference")

class NegotiateRequest(BaseModel):
    call_id: str
    carrier_offer: float = Field(..., description="Carrier's rate offer")

class EndCallRequest(BaseModel):
    call_id: str
    reason: str = Field(..., description="Reason for ending call")
    sentiment: Optional[str] = Field(None, description="Detected sentiment")

@router.post("/happyrobot/start-call")
async def start_call(
    request: StartCallRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Initialize a new carrier call conversation.
    Called when HappyRobot agent receives an inbound call.
    """
    try:
        conversation_manager = ConversationManager(db)
        result = conversation_manager.start_conversation(request.call_id)
        
        return {
            "ok": True,
            "data": result
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to start conversation: {str(e)}"
        }

@router.post("/happyrobot/verify-mc")
async def verify_mc(
    request: VerifyMCRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Verify carrier MC number with FMCSA.
    Returns verification status and next conversation step.
    """
    try:
        conversation_manager = ConversationManager(db)
        
        # Auto-initialize conversation if it doesn't exist
        if request.call_id not in conversation_manager.conversations:
            conversation_manager.start_conversation(request.call_id)
        
        result = conversation_manager.process_mc_number(
            request.call_id, 
            request.mc_number
        )
        
        return {
            "ok": True,
            "data": result
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"MC verification failed: {str(e)}"
        }

@router.post("/happyrobot/search-loads")
async def search_loads(
    request: SearchLoadsRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Search for loads and present the best match.
    Returns load details formatted for voice presentation.
    """
    try:
        conversation_manager = ConversationManager(db)
        
        # Auto-initialize conversation if it doesn't exist
        if request.call_id not in conversation_manager.conversations:
            conversation_manager.start_conversation(request.call_id)
        
        result = conversation_manager.search_and_present_loads(
            call_id=request.call_id,
            equipment_type=request.equipment_type,
            origin=request.origin,
            destination=request.destination
        )
        
        return {
            "ok": True,
            "data": result
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Load search failed: {str(e)}"
        }

@router.post("/happyrobot/negotiate")
async def negotiate(
    request: NegotiateRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Handle carrier negotiation offer.
    Returns accept/counter/reject decision with appropriate response.
    """
    try:
        conversation_manager = ConversationManager(db)
        
        # Auto-initialize conversation if it doesn't exist
        if request.call_id not in conversation_manager.conversations:
            conversation_manager.start_conversation(request.call_id)
        
        result = conversation_manager.handle_negotiation(
            request.call_id,
            request.carrier_offer
        )
        
        return {
            "ok": True,
            "data": result
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Negotiation failed: {str(e)}"
        }

@router.post("/happyrobot/end-call")
async def end_call(
    request: EndCallRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Complete the call and persist all conversation data.
    Returns comprehensive call summary for HappyRobot.
    """
    try:
        conversation_manager = ConversationManager(db)
        persistence_service = CallPersistenceService(db)
        
        # Get conversation summary
        summary = conversation_manager.get_conversation_summary(request.call_id)
        
        # Persist to database
        call_data = {
            "call_id": request.call_id,
            "mc": summary.get("mc_number"),
            "carrier_name": summary.get("carrier_name"),
            "fmcsa_status": summary.get("fmcsa_status"),
            "load_id": summary.get("presented_load", {}).get("load_id"),
            "listed_rate": summary.get("presented_load", {}).get("total_rate"),
            "final_rate": summary.get("final_rate"),
            "last_offer": summary.get("last_offer"),
            "negotiation_rounds": summary.get("negotiation_rounds"),
            "outcome": summary.get("outcome"),
            "sentiment": request.sentiment or summary.get("sentiment"),
            "extracted_json": summary.get("extracted_data"),
            "notes": request.reason
        }
        
        persistence_result = persistence_service.save_call(call_data)
        
        return {
            "ok": True,
            "data": {
                "call_summary": summary,
                "persistence_result": persistence_result,
                "classification": {
                    "outcome": summary.get("outcome"),
                    "sentiment": summary.get("sentiment"),
                    "success": summary.get("outcome") == "accepted"
                }
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to end call: {str(e)}"
        }

@router.get("/happyrobot/call-status/{call_id}")
async def get_call_status(
    call_id: str,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Get current conversation status and context.
    Useful for debugging and call monitoring.
    """
    try:
        conversation_manager = ConversationManager(db)
        summary = conversation_manager.get_conversation_summary(call_id)
        
        return {
            "ok": True,
            "data": summary
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to get call status: {str(e)}"
        }