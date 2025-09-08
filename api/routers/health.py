from fastapi import APIRouter
from api.schemas import BaseResponse

router = APIRouter()

@router.get("/health", response_model=BaseResponse)
async def health_check():
    """
    Health check endpoint - no authentication required.
    """
    return BaseResponse(
        ok=True,
        data={
            "status": "healthy",
            "service": "Inbound Carrier Sales Agent API",
            "version": "1.0.0"
        }
    )
