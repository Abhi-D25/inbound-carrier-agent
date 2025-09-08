from fastapi import APIRouter, Depends
from api.deps import require_api_key
from api.schemas import NegotiationRequest, NegotiationResponse
from api.services.negotiation_policy import NegotiationPolicy
from pydantic import BaseModel

class NegotiationEvaluateRequest(BaseModel):
    listed_rate: float
    offer: float
    round: int = 1

router = APIRouter()

@router.post("/negotiation/evaluate", response_model=NegotiationResponse)
async def evaluate_negotiation(
    request: NegotiationEvaluateRequest,
    api_key: str = Depends(require_api_key)
):
    """
    Evaluate negotiation and provide counter offer.
    
    Policy:
    - Target = listed rate (100%)
    - Floor = 93% of listed rate
    - Accept if offer >= target
    - Counter if offer >= floor and rounds < max
    - Reject if offer < floor or max rounds reached
    """
    try:
        policy = NegotiationPolicy()
        result = policy.evaluate_offer(
            listed_rate=request.listed_rate,
            offer=request.offer,
            round_number=request.round
        )
        
        return NegotiationResponse(
            ok=True,
            data=result
        )
        
    except Exception as e:
        return NegotiationResponse(
            ok=False,
            error=f"Negotiation evaluation failed: {str(e)}"
        )

@router.get("/negotiation/summary")
async def get_negotiation_summary(
    listed_rate: float,
    api_key: str = Depends(require_api_key)
):
    """
    Get negotiation parameters summary for a given listed rate.
    """
    try:
        policy = NegotiationPolicy()
        summary = policy.get_negotiation_summary(listed_rate)
        
        return {
            "ok": True,
            "data": summary
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to get negotiation summary: {str(e)}"
        }
