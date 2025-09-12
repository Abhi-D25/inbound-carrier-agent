# Enhanced api/services/metrics_service.py
"""
Comprehensive metrics calculation service for KPI dashboard.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text
from api.models import Call, Load

class MetricsService:
    """Service for calculating comprehensive KPI metrics from call data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive dashboard metrics optimized for display.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with all dashboard metrics organized by category
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get calls in date range
        calls_query = self.db.query(Call).filter(
            Call.created_at >= start_date,
            Call.created_at <= end_date
        )
        
        all_calls = calls_query.all()
        
        return {
            "period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "days": days
            },
            "overview": self._get_overview_metrics(all_calls),
            "performance": self._get_performance_metrics(all_calls),
            "financial": self._get_financial_metrics(all_calls),
            "operational": self._get_operational_metrics(all_calls),
            "carrier_insights": self._get_carrier_metrics(all_calls),
            "trends": self._get_trend_data(all_calls, days)
        }
    
    def _get_overview_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """High-level overview metrics for the dashboard header."""
        total_calls = len(calls)
        successful_calls = len([c for c in calls if c.outcome == "accepted"])
        completed_calls = len([c for c in calls if c.outcome in ["accepted", "rejected", "no_agreement"]])
        
        # Calculate rates
        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        completion_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Total revenue from successful calls
        total_revenue = sum([c.final_rate or 0 for c in calls if c.outcome == "accepted" and c.final_rate])
        
        # Average call duration
        durations = [c.call_duration_seconds for c in calls if c.call_duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": round(success_rate, 1),
            "completion_rate": round(completion_rate, 1),
            "total_revenue": round(total_revenue, 2),
            "avg_call_duration_minutes": round(avg_duration / 60, 1) if avg_duration else 0
        }
    
    def _get_performance_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """Agent and system performance metrics."""
        
        # Outcome breakdown
        outcome_counts = {}
        for call in calls:
            outcome = call.outcome or "unknown"
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        
        # Sentiment breakdown
        sentiment_counts = {}
        for call in calls:
            sentiment = call.sentiment or "neutral"
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        # Negotiation effectiveness
        negotiated_calls = [c for c in calls if (c.negotiation_rounds or 0) > 0]
        negotiated_successes = [c for c in negotiated_calls if c.outcome == "accepted"]
        negotiation_success_rate = (len(negotiated_successes) / len(negotiated_calls) * 100) if negotiated_calls else 0
        
        # Average negotiation rounds
        rounds = [c.negotiation_rounds for c in calls if c.negotiation_rounds]
        avg_negotiation_rounds = sum(rounds) / len(rounds) if rounds else 0
        
        return {
            "outcome_breakdown": outcome_counts,
            "sentiment_breakdown": sentiment_counts,
            "negotiation_success_rate": round(negotiation_success_rate, 1),
            "avg_negotiation_rounds": round(avg_negotiation_rounds, 1),
            "calls_with_negotiation": len(negotiated_calls)
        }
    
    def _get_financial_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """Financial and revenue-related metrics."""
        successful_calls = [c for c in calls if c.outcome == "accepted" and c.final_rate]
        
        if not successful_calls:
            return {
                "total_revenue": 0,
                "average_deal_size": 0,
                "revenue_per_call": 0,
                "deals_by_size": {"small": 0, "medium": 0, "large": 0},
                "rate_analysis": {}
            }
        
        revenues = [c.final_rate for c in successful_calls]
        total_revenue = sum(revenues)
        avg_deal_size = total_revenue / len(revenues)
        revenue_per_call = total_revenue / len(calls) if calls else 0
        
        # Deal size categories
        deals_by_size = {"small": 0, "medium": 0, "large": 0}
        for revenue in revenues:
            if revenue < 1500:
                deals_by_size["small"] += 1
            elif revenue < 3000:
                deals_by_size["medium"] += 1
            else:
                deals_by_size["large"] += 1
        
        # Rate analysis
        rate_analysis = {
            "min_deal": min(revenues),
            "max_deal": max(revenues),
            "median_deal": sorted(revenues)[len(revenues)//2],
            "total_deals": len(successful_calls)
        }
        
        return {
            "total_revenue": round(total_revenue, 2),
            "average_deal_size": round(avg_deal_size, 2),
            "revenue_per_call": round(revenue_per_call, 2),
            "deals_by_size": deals_by_size,
            "rate_analysis": rate_analysis
        }
    
    def _get_operational_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """Operational efficiency and equipment metrics."""
        
        # Equipment type performance
        equipment_stats = {}
        for call in calls:
            if call.extracted_json:
                import json
                try:
                    data = json.loads(call.extracted_json) if isinstance(call.extracted_json, str) else call.extracted_json
                    equipment = data.get("equipment_type")
                    if equipment:
                        if equipment not in equipment_stats:
                            equipment_stats[equipment] = {"total": 0, "successful": 0}
                        equipment_stats[equipment]["total"] += 1
                        if call.outcome == "accepted":
                            equipment_stats[equipment]["successful"] += 1
                except:
                    pass
        
        # Calculate success rates by equipment
        for equipment, stats in equipment_stats.items():
            stats["success_rate"] = (stats["successful"] / stats["total"] * 100) if stats["total"] > 0 else 0
        
        # FMCSA verification stats
        verified_calls = [c for c in calls if c.fmcsa_status]
        verification_rate = (len(verified_calls) / len(calls) * 100) if calls else 0
        
        # Peak activity analysis
        hourly_activity = {}
        daily_activity = {}
        
        for call in calls:
            if call.created_at:
                hour = call.created_at.hour
                day = call.created_at.strftime("%A")
                
                hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
                daily_activity[day] = daily_activity.get(day, 0) + 1
        
        peak_hour = max(hourly_activity.items(), key=lambda x: x[1]) if hourly_activity else (0, 0)
        peak_day = max(daily_activity.items(), key=lambda x: x[1]) if daily_activity else ("", 0)
        
        return {
            "equipment_performance": equipment_stats,
            "verification_rate": round(verification_rate, 1),
            "peak_activity": {
                "peak_hour": f"{peak_hour[0]}:00 ({peak_hour[1]} calls)",
                "peak_day": f"{peak_day[0]} ({peak_day[1]} calls)",
                "hourly_distribution": hourly_activity,
                "daily_distribution": daily_activity
            }
        }
    
    def _get_carrier_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """Carrier-related insights and patterns."""
        
        # Unique carriers
        unique_carriers = set()
        carrier_performance = {}
        
        for call in calls:
            if call.carrier_mc:
                unique_carriers.add(call.carrier_mc)
                
                if call.carrier_mc not in carrier_performance:
                    carrier_performance[call.carrier_mc] = {
                        "name": call.carrier_name or "Unknown",
                        "total_calls": 0,
                        "successful_calls": 0,
                        "total_revenue": 0
                    }
                
                stats = carrier_performance[call.carrier_mc]
                stats["total_calls"] += 1
                
                if call.outcome == "accepted":
                    stats["successful_calls"] += 1
                    if call.final_rate:
                        stats["total_revenue"] += call.final_rate
        
        # Calculate success rates and sort by performance
        for mc, stats in carrier_performance.items():
            stats["success_rate"] = (stats["successful_calls"] / stats["total_calls"] * 100) if stats["total_calls"] > 0 else 0
        
        # Get top performers
        top_carriers = sorted(
            carrier_performance.items(), 
            key=lambda x: (x[1]["successful_calls"], x[1]["total_revenue"]), 
            reverse=True
        )[:5]
        
        # Repeat vs new carriers
        repeat_carriers = len([mc for mc, stats in carrier_performance.items() if stats["total_calls"] > 1])
        
        return {
            "unique_carriers": len(unique_carriers),
            "repeat_carriers": repeat_carriers,
            "new_carriers": len(unique_carriers) - repeat_carriers,
            "top_performers": [
                {
                    "mc": mc,
                    "name": stats["name"],
                    "calls": stats["total_calls"],
                    "success_rate": round(stats["success_rate"], 1),
                    "revenue": round(stats["total_revenue"], 2)
                }
                for mc, stats in top_carriers
            ]
        }
    
    def _get_trend_data(self, calls: List[Call], days: int) -> Dict[str, Any]:
        """Trend analysis for charts and graphs."""
        
        # Daily trends
        daily_stats = {}
        for call in calls:
            date_key = call.created_at.strftime("%Y-%m-%d")
            if date_key not in daily_stats:
                daily_stats[date_key] = {"total": 0, "successful": 0, "revenue": 0}
            
            daily_stats[date_key]["total"] += 1
            if call.outcome == "accepted":
                daily_stats[date_key]["successful"] += 1
                if call.final_rate:
                    daily_stats[date_key]["revenue"] += call.final_rate
        
        # Convert to arrays for charting
        dates = sorted(daily_stats.keys())
        daily_calls = [daily_stats[date]["total"] for date in dates]
        daily_successes = [daily_stats[date]["successful"] for date in dates]
        daily_revenue = [round(daily_stats[date]["revenue"], 2) for date in dates]
        
        return {
            "daily_trends": {
                "dates": dates,
                "calls": daily_calls,
                "successes": daily_successes,
                "revenue": daily_revenue
            },
            "summary": {
                "total_days_with_activity": len([d for d in daily_calls if d > 0]),
                "best_day": {
                    "date": dates[daily_calls.index(max(daily_calls))] if daily_calls else None,
                    "calls": max(daily_calls) if daily_calls else 0
                }
            }
        }