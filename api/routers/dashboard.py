from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from api.deps import get_db
from api.services.metrics_service import MetricsService
from sqlalchemy.orm import Session
import json

router = APIRouter()

# Initialize templates (we'll create the template)
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Serve the dashboard page with server-side rendered data.
    No API keys exposed to frontend.
    """
    try:
        # Get metrics data server-side
        metrics_service = MetricsService(db)
        dashboard_data = metrics_service.get_dashboard_metrics(days)
        detailed_data = metrics_service.get_detailed_metrics(days)
        recent_calls = metrics_service.get_recent_calls(10)
        
        # Prepare data for template
        template_data = {
            "request": request,
            "dashboard_data": dashboard_data,
            "detailed_data": detailed_data,
            "recent_calls": recent_calls,
            "days": days,
            # Convert to JSON for JavaScript usage
            "dashboard_data_json": json.dumps(dashboard_data),
            "recent_calls_json": json.dumps(recent_calls)
        }
        
        return templates.TemplateResponse("dashboard.html", template_data)
        
    except Exception as e:
        # Return error page
        error_data = {
            "request": request,
            "error": str(e),
            "days": days
        }
        return templates.TemplateResponse("dashboard_error.html", error_data)

@router.get("/api/dashboard-data")
async def get_dashboard_data_api(
    days: int = Query(30),
    db: Session = Depends(get_db)
):
    """
    Internal API endpoint for AJAX updates (no auth needed since it's internal).
    This is called by the dashboard page itself, not external clients.
    """
    try:
        metrics_service = MetricsService(db)
        dashboard_data = metrics_service.get_dashboard_metrics(days)
        recent_calls = metrics_service.get_recent_calls(10)
        
        return {
            "ok": True,
            "data": {
                "dashboard": dashboard_data,
                "recent_calls": recent_calls
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }