from fastapi import APIRouter, Depends
from api.deps import require_api_key
from api.schemas import FMCSAVerifyRequest, FMCSAVerifyResponse
from api.services.fmcsa_client import FMCSAClient
from pydantic import BaseModel

class FMCSAVerifyMCRequest(BaseModel):
    mc: str

router = APIRouter()

@router.post("/fmcsa/verify", response_model=FMCSAVerifyResponse)
async def verify_carrier(
    request: FMCSAVerifyMCRequest,
    api_key: str = Depends(require_api_key)
):
    """
    Verify carrier using FMCSA API.
    
    Returns normalized response with:
    - eligible: boolean
    - carrier_name: string
    - status: string
    - reason: string
    """
    try:
        fmcsa_client = FMCSAClient()
        result = fmcsa_client.verify_carrier(request.mc)
        
        return FMCSAVerifyResponse(
            ok=True,
            data=result
        )
        
    except Exception as e:
        return FMCSAVerifyResponse(
            ok=False,
            error=f"FMCSA verification failed: {str(e)}"
        )

@router.post("/fmcsa/verify/legacy", response_model=FMCSAVerifyResponse)
async def verify_carrier_legacy(
    verify_request: FMCSAVerifyRequest,
    api_key: str = Depends(require_api_key)
):
    """
    Legacy endpoint for FMCSA verification (uses mc_number field).
    """
    try:
        fmcsa_client = FMCSAClient()
        result = fmcsa_client.verify_carrier(verify_request.mc_number)
        
        return FMCSAVerifyResponse(
            ok=True,
            data=result
        )
        
    except Exception as e:
        return FMCSAVerifyResponse(
            ok=False,
            error=f"FMCSA verification failed: {str(e)}"
        )
