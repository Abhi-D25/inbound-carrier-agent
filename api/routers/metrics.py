from fastapi import APIRouter, Depends, Query
from api.deps import require_api_key, get_db
from api.schemas import MetricsSummaryResponse
from api.services.metrics_service import MetricsService
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    days: int = Query(30, description="Number of days to analyze"),
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Get KPI metrics summary from calls data.
    """
    try:
        metrics_service = MetricsService(db)
        metrics = metrics_service.get_summary_metrics(days)
        
        return MetricsSummaryResponse(
            ok=True,
            data=metrics
        )
    except Exception as e:
        return MetricsSummaryResponse(
            ok=False,
            error=f"Failed to calculate metrics: {str(e)}"
        )

@router.get("/metrics/detailed")
async def get_detailed_metrics(
    days: int = Query(30, description="Number of days to analyze"),
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Get detailed metrics with trends and breakdowns.
    """
    try:
        metrics_service = MetricsService(db)
        metrics = metrics_service.get_detailed_metrics(days)
        
        return {
            "ok": True,
            "data": metrics
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to calculate detailed metrics: {str(e)}"
        }