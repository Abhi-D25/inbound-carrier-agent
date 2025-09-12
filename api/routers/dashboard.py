from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from api.deps import get_db
from api.services.metrics_service import MetricsService
from sqlalchemy.orm import Session
import json
from typing import Dict, Any

router = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Serve the enhanced dashboard with comprehensive freight broker metrics.
    Auto-refreshes every 30 seconds to show real-time updates.
    """
    try:
        # Get comprehensive metrics
        metrics_service = MetricsService(db)
        
        # Get all dashboard data
        dashboard_data = metrics_service.get_dashboard_metrics(days)
        recent_calls = metrics_service.get_recent_calls(20)  # Get more for the table
        
        # Calculate additional KPIs specific to freight brokers
        enhanced_metrics = calculate_enhanced_metrics(dashboard_data, recent_calls)
        
        # Prepare template data
        template_data = {
            "request": request,
            "dashboard_data": dashboard_data,
            "enhanced_metrics": enhanced_metrics,
            "recent_calls": recent_calls,
            "days": days,
            # Convert to JSON for JavaScript
            "dashboard_data_json": json.dumps({
                "dashboard": dashboard_data,
                "recent_calls": recent_calls,
                "enhanced_metrics": enhanced_metrics
            }, default=str)
        }
        
        # Use the dashboard template
        return templates.TemplateResponse("dashboard.html", template_data)
        
    except Exception as e:
        # Return error page with helpful debugging info
        error_data = {
            "request": request,
            "error": str(e),
            "days": days,
            "debug_info": "Check that the database is seeded and the API is running"
        }
        return templates.TemplateResponse("dashboard.html", error_data)

@router.get("/api/dashboard-data")
async def get_dashboard_data_api(
    days: int = Query(7),
    db: Session = Depends(get_db)
):
    """
    API endpoint for AJAX dashboard updates.
    Called by the dashboard every 30 seconds for real-time updates.
    """
    try:
        metrics_service = MetricsService(db)
        dashboard_data = metrics_service.get_dashboard_metrics(days)
        recent_calls = metrics_service.get_recent_calls(20)
        
        # Calculate enhanced metrics
        enhanced_metrics = calculate_enhanced_metrics(dashboard_data, recent_calls)
        
        return {
            "ok": True,
            "data": {
                "dashboard": dashboard_data,
                "recent_calls": recent_calls,
                "enhanced_metrics": enhanced_metrics
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }

def calculate_enhanced_metrics(dashboard_data: Dict[str, Any], recent_calls: list) -> Dict[str, Any]:
    """
    Calculate additional KPIs that freight brokers care about.
    """
    overview = dashboard_data.get("overview", {})
    performance = dashboard_data.get("performance", {})
    financial = dashboard_data.get("financial", {})
    
    # Calculate first-call resolution rate
    first_call_resolution = 0
    if recent_calls:
        quick_wins = [c for c in recent_calls if c.get("negotiation_rounds", 0) <= 1 and c.get("outcome") == "accepted"]
        first_call_resolution = (len(quick_wins) / len(recent_calls) * 100) if recent_calls else 0
    
    # Calculate equipment match efficiency
    equipment_requests = {}
    for call in recent_calls:
        equipment = call.get("equipment_type")
        if equipment:
            if equipment not in equipment_requests:
                equipment_requests[equipment] = {"total": 0, "successful": 0}
            equipment_requests[equipment]["total"] += 1
            if call.get("outcome") == "accepted":
                equipment_requests[equipment]["successful"] += 1
    
    # Calculate lost opportunity cost
    rejected_calls = [c for c in recent_calls if c.get("outcome") in ["rejected", "no_agreement"]]
    avg_deal_size = financial.get("average_deal_size", 0)
    lost_opportunity = len(rejected_calls) * avg_deal_size
    
    return {
        "first_call_resolution_rate": round(first_call_resolution, 1),
        "equipment_match_rates": equipment_requests,
        "lost_opportunity_cost": round(lost_opportunity, 2),
        "carrier_satisfaction_score": calculate_satisfaction_score(recent_calls),
        "peak_performance_hours": identify_peak_hours(recent_calls),
        "negotiation_effectiveness": calculate_negotiation_effectiveness(recent_calls)
    }

def calculate_satisfaction_score(calls: list) -> float:
    """
    Calculate carrier satisfaction based on sentiment analysis.
    """
    if not calls:
        return 0.0
    
    sentiment_scores = {"positive": 100, "neutral": 60, "negative": 0}
    total_score = 0
    valid_calls = 0
    
    for call in calls:
        sentiment = call.get("sentiment")
        if sentiment in sentiment_scores:
            total_score += sentiment_scores[sentiment]
            valid_calls += 1
    
    return round(total_score / valid_calls, 1) if valid_calls > 0 else 0.0

def identify_peak_hours(calls: list) -> Dict[str, Any]:
    """
    Identify peak performance hours for staffing optimization.
    """
    hourly_stats = {}
    
    for call in calls:
        if call.get("created_at"):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(call["created_at"].replace("Z", "+00:00"))
                hour = dt.hour
                
                if hour not in hourly_stats:
                    hourly_stats[hour] = {"total": 0, "successful": 0}
                
                hourly_stats[hour]["total"] += 1
                if call.get("outcome") == "accepted":
                    hourly_stats[hour]["successful"] += 1
            except:
                continue
    
    # Find best performing hour
    best_hour = None
    best_success_rate = 0
    
    for hour, stats in hourly_stats.items():
        if stats["total"] >= 2:  # Minimum calls for statistical relevance
            success_rate = stats["successful"] / stats["total"]
            if success_rate > best_success_rate:
                best_success_rate = success_rate
                best_hour = hour
    
    return {
        "best_hour": best_hour,
        "best_hour_success_rate": round(best_success_rate * 100, 1),
        "hourly_distribution": hourly_stats
    }

def calculate_negotiation_effectiveness(calls: list) -> Dict[str, Any]:
    """
    Analyze negotiation patterns and effectiveness.
    """
    negotiated_calls = [c for c in calls if c.get("negotiation_rounds", 0) > 0]
    
    if not negotiated_calls:
        return {
            "avg_rounds_to_close": 0,
            "negotiation_success_rate": 0,
            "optimal_rounds": 0
        }
    
    successful_negotiations = [c for c in negotiated_calls if c.get("outcome") == "accepted"]
    
    # Calculate average rounds for successful deals
    avg_rounds = 0
    if successful_negotiations:
        total_rounds = sum(c.get("negotiation_rounds", 0) for c in successful_negotiations)
        avg_rounds = total_rounds / len(successful_negotiations)
    
    # Find optimal negotiation rounds (most successful)
    rounds_success = {}
    for call in negotiated_calls:
        rounds = call.get("negotiation_rounds", 0)
        if rounds not in rounds_success:
            rounds_success[rounds] = {"total": 0, "successful": 0}
        rounds_success[rounds]["total"] += 1
        if call.get("outcome") == "accepted":
            rounds_success[rounds]["successful"] += 1
    
    optimal_rounds = 0
    best_rate = 0
    for rounds, stats in rounds_success.items():
        if stats["total"] > 0:
            success_rate = stats["successful"] / stats["total"]
            if success_rate > best_rate:
                best_rate = success_rate
                optimal_rounds = rounds
    
    return {
        "avg_rounds_to_close": round(avg_rounds, 1),
        "negotiation_success_rate": round(len(successful_negotiations) / len(negotiated_calls) * 100, 1),
        "optimal_rounds": optimal_rounds,
        "rounds_breakdown": rounds_success
    }
