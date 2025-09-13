# Enhanced api/services/metrics_service.py
"""
Comprehensive metrics calculation service for freight brokerage KPI dashboard.
Focuses on metrics that matter to freight brokers and logistics companies.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text, desc
from api.models import Call, Load
import json

class MetricsService:
    """Service for calculating comprehensive freight brokerage KPI metrics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_summary_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get basic summary metrics for the API endpoint.
        """
        dashboard_data = self.get_dashboard_metrics(days)
        return dashboard_data["overview"]
    
    def get_dashboard_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive dashboard metrics optimized for freight brokers.
        
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
    
    def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent calls for dashboard display.
        """
        recent_calls = self.db.query(Call).order_by(desc(Call.created_at)).limit(limit).all()
        
        calls_data = []
        for call in recent_calls:
            # Parse extracted JSON to get equipment type and route information
            equipment_type = None
            origin_preference = None
            destination_preference = None
            if call.extracted_json:
                try:
                    data = json.loads(call.extracted_json) if isinstance(call.extracted_json, str) else call.extracted_json
                    equipment_type = data.get("equipment_type")
                    origin_preference = data.get("origin_preference")
                    destination_preference = data.get("destination_preference")
                except:
                    pass
            
            calls_data.append({
                "id": call.id,
                "call_id": call.call_id,
                "carrier_mc": call.carrier_mc,
                "carrier_name": call.carrier_name,
                "outcome": call.outcome,
                "sentiment": call.sentiment,
                "final_rate": call.final_rate,
                "negotiation_rounds": call.negotiation_rounds or 0,
                "equipment_type": equipment_type,
                "origin_preference": origin_preference,
                "destination_preference": destination_preference,
                "call_duration_seconds": call.call_duration_seconds,
                "created_at": call.created_at.isoformat() if call.created_at else None,
                "fmcsa_status": call.fmcsa_status
            })
        
        return calls_data
    
    def get_detailed_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get detailed metrics with additional insights.
        """
        dashboard_data = self.get_dashboard_metrics(days)
        
        # Add additional detailed analysis
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        all_calls = self.db.query(Call).filter(
            Call.created_at >= start_date,
            Call.created_at <= end_date
        ).all()
        
        detailed_data = dashboard_data.copy()
        detailed_data["detailed_analysis"] = {
            "negotiation_analysis": self._get_negotiation_analysis(all_calls),
            "time_analysis": self._get_time_analysis(all_calls),
            "conversion_funnel": self._get_conversion_funnel(all_calls)
        }
        
        return detailed_data
    
    def _get_overview_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """High-level overview metrics for freight brokerage dashboard."""
        total_calls = len(calls)
        successful_calls = len([c for c in calls if c.outcome == "accepted"])
        completed_calls = len([c for c in calls if c.outcome in ["accepted", "rejected", "no_agreement"]])
        
        # Key freight brokerage KPIs
        load_booking_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        completion_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Revenue from successful calls
        total_revenue = sum([c.final_rate or 0 for c in calls if c.outcome == "accepted" and c.final_rate])
        
        # Average call duration (in minutes for better UX)
        durations = [c.call_duration_seconds for c in calls if c.call_duration_seconds]
        avg_duration_minutes = (sum(durations) / len(durations) / 60) if durations else 0
        
        # Carrier verification rate (important for compliance)
        verified_calls = len([c for c in calls if c.fmcsa_status and c.fmcsa_status != "failed"])
        verification_rate = (verified_calls / total_calls * 100) if total_calls > 0 else 0
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "verified_calls": verified_calls,
            "load_booking_rate": round(load_booking_rate, 1),
            "completion_rate": round(completion_rate, 1),
            "total_revenue": round(total_revenue, 2),
            "avg_call_duration_minutes": round(avg_duration_minutes, 1),
            "verification_rate": round(verification_rate, 1),
            "revenue_per_call": round(total_revenue / total_calls, 2) if total_calls > 0 else 0
        }
    
    def _get_performance_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """Agent and system performance metrics for freight operations."""
        
        # Outcome breakdown with freight-specific categories
        outcome_counts = {}
        for call in calls:
            outcome = call.outcome or "rejected"  # Use consistent default
            # Consolidate no_agreement and rejected into rejected
            if outcome in ["no_agreement", "no-agreement"]:
                outcome = "rejected"
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        
        # Sentiment breakdown (important for customer satisfaction)
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for call in calls:
            sentiment = call.sentiment or "neutral"
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        # Negotiation effectiveness (key freight brokerage metric)
        negotiated_calls = [c for c in calls if (c.negotiation_rounds or 0) > 0]
        negotiated_successes = [c for c in negotiated_calls if c.outcome == "accepted"]
        negotiation_success_rate = (len(negotiated_successes) / len(negotiated_calls) * 100) if negotiated_calls else 0
        
        # Average negotiation rounds (efficiency metric)
        rounds = [c.negotiation_rounds for c in calls if c.negotiation_rounds and c.negotiation_rounds > 0]
        avg_negotiation_rounds = sum(rounds) / len(rounds) if rounds else 0
        
        # Quick conversion rate (calls that convert without negotiation)
        quick_conversions = len([c for c in calls if c.outcome == "accepted" and (c.negotiation_rounds or 0) == 0])
        quick_conversion_rate = (quick_conversions / len(calls) * 100) if calls else 0
        
        return {
            "outcome_breakdown": outcome_counts,
            "sentiment_breakdown": sentiment_counts,
            "negotiation_success_rate": round(negotiation_success_rate, 1),
            "avg_negotiation_rounds": round(avg_negotiation_rounds, 1),
            "quick_conversion_rate": round(quick_conversion_rate, 1),
            "calls_requiring_negotiation": len(negotiated_calls),
            "first_call_close_rate": round(quick_conversion_rate, 1)  # Alternative name for same metric
        }
    
    def _get_financial_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """Financial metrics crucial for freight brokerage profitability."""
        successful_calls = [c for c in calls if c.outcome == "accepted" and c.final_rate]
        
        if not successful_calls:
            return {
                "total_revenue": 0,
                "average_deal_size": 0,
                "revenue_per_call": 0,
                "deals_by_size": {"small": 0, "medium": 0, "large": 0, "premium": 0},
                "rate_analysis": {"min_deal": 0, "max_deal": 0, "median_deal": 0, "total_deals": 0}
            }
        
        revenues = [c.final_rate for c in successful_calls]
        total_revenue = sum(revenues)
        avg_deal_size = total_revenue / len(revenues)
        revenue_per_call = total_revenue / len(calls) if calls else 0
        
        # Deal size categories (freight industry standards)
        deals_by_size = {"small": 0, "medium": 0, "large": 0, "premium": 0}
        for revenue in revenues:
            if revenue < 1000:
                deals_by_size["small"] += 1
            elif revenue < 2500:
                deals_by_size["medium"] += 1
            elif revenue < 5000:
                deals_by_size["large"] += 1
            else:
                deals_by_size["premium"] += 1
        
        # Rate analysis
        sorted_revenues = sorted(revenues)
        rate_analysis = {
            "min_deal": min(revenues),
            "max_deal": max(revenues),
            "median_deal": sorted_revenues[len(sorted_revenues)//2],
            "total_deals": len(successful_calls),
            "avg_deal": round(avg_deal_size, 2)
        }
        
        # Revenue growth indicators
        if len(successful_calls) >= 2:
            recent_deals = sorted(successful_calls, key=lambda x: x.created_at, reverse=True)[:len(successful_calls)//2]
            older_deals = sorted(successful_calls, key=lambda x: x.created_at, reverse=True)[len(successful_calls)//2:]
            
            recent_avg = sum(d.final_rate for d in recent_deals) / len(recent_deals)
            older_avg = sum(d.final_rate for d in older_deals) / len(older_deals) if older_deals else recent_avg
            
            revenue_trend = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        else:
            revenue_trend = 0
        
        return {
            "total_revenue": round(total_revenue, 2),
            "average_deal_size": round(avg_deal_size, 2),
            "revenue_per_call": round(revenue_per_call, 2),
            "deals_by_size": deals_by_size,
            "rate_analysis": rate_analysis,
            "revenue_trend_percent": round(revenue_trend, 1)
        }
    
    def _get_operational_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """Operational efficiency metrics for freight operations."""
        
        # Equipment type performance (critical for freight matching)
        equipment_stats = {}
        for call in calls:
            if call.extracted_json:
                try:
                    data = json.loads(call.extracted_json) if isinstance(call.extracted_json, str) else call.extracted_json
                    equipment = data.get("equipment_type")
                    if equipment:
                        if equipment not in equipment_stats:
                            equipment_stats[equipment] = {"total": 0, "successful": 0, "revenue": 0}
                        equipment_stats[equipment]["total"] += 1
                        if call.outcome == "accepted":
                            equipment_stats[equipment]["successful"] += 1
                            if call.final_rate:
                                equipment_stats[equipment]["revenue"] += call.final_rate
                except:
                    pass
        
        # Calculate success rates and revenue by equipment
        for equipment, stats in equipment_stats.items():
            stats["success_rate"] = (stats["successful"] / stats["total"] * 100) if stats["total"] > 0 else 0
            stats["avg_revenue"] = (stats["revenue"] / stats["successful"]) if stats["successful"] > 0 else 0
        
        # FMCSA verification stats (compliance metric)
        verified_calls = [c for c in calls if c.fmcsa_status and c.fmcsa_status != "failed"]
        verification_rate = (len(verified_calls) / len(calls) * 100) if calls else 0
        
        # Peak activity analysis (for staffing decisions)
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
        
        # Call duration analysis
        durations = [c.call_duration_seconds for c in calls if c.call_duration_seconds]
        if durations:
            avg_duration = sum(durations) / len(durations)
            successful_durations = [c.call_duration_seconds for c in calls if c.call_duration_seconds and c.outcome == "accepted"]
            avg_successful_duration = sum(successful_durations) / len(successful_durations) if successful_durations else avg_duration
        else:
            avg_duration = 0
            avg_successful_duration = 0
        
        return {
            "equipment_performance": equipment_stats,
            "verification_rate": round(verification_rate, 1),
            "peak_activity": {
                "peak_hour": f"{peak_hour[0]}:00",
                "peak_hour_calls": peak_hour[1],
                "peak_day": peak_day[0],
                "peak_day_calls": peak_day[1],
                "hourly_distribution": hourly_activity,
                "daily_distribution": daily_activity
            },
            "call_efficiency": {
                "avg_call_duration_minutes": round(avg_duration / 60, 1) if avg_duration else 0,
                "avg_successful_call_duration_minutes": round(avg_successful_duration / 60, 1) if avg_successful_duration else 0,
                "total_call_time_hours": round(sum(durations) / 3600, 1) if durations else 0
            }
        }
    
    def _get_carrier_metrics(self, calls: List[Call]) -> Dict[str, Any]:
        """Carrier-related insights and relationship metrics."""
        
        # Unique carriers and performance
        unique_carriers = set()
        carrier_performance = {}
        
        for call in calls:
            if call.carrier_mc:
                unique_carriers.add(call.carrier_mc)
                
                if call.carrier_mc not in carrier_performance:
                    carrier_performance[call.carrier_mc] = {
                        "name": call.carrier_name or f"MC-{call.carrier_mc}",
                        "total_calls": 0,
                        "successful_calls": 0,
                        "total_revenue": 0,
                        "last_call_date": call.created_at
                    }
                
                stats = carrier_performance[call.carrier_mc]
                stats["total_calls"] += 1
                
                if call.created_at and (not stats["last_call_date"] or call.created_at > stats["last_call_date"]):
                    stats["last_call_date"] = call.created_at
                
                if call.outcome == "accepted":
                    stats["successful_calls"] += 1
                    if call.final_rate:
                        stats["total_revenue"] += call.final_rate
        
        # Calculate success rates and sort by performance
        for mc, stats in carrier_performance.items():
            stats["success_rate"] = (stats["successful_calls"] / stats["total_calls"] * 100) if stats["total_calls"] > 0 else 0
            stats["avg_deal_size"] = (stats["total_revenue"] / stats["successful_calls"]) if stats["successful_calls"] > 0 else 0
        
        # Get top performers (by revenue and success rate)
        top_carriers = sorted(
            carrier_performance.items(), 
            key=lambda x: (x[1]["total_revenue"], x[1]["success_rate"]), 
            reverse=True
        )[:10]
        
        # Carrier relationship metrics
        repeat_carriers = len([mc for mc, stats in carrier_performance.items() if stats["total_calls"] > 1])
        new_carriers = len(unique_carriers) - repeat_carriers
        
        # Loyalty metrics
        highly_engaged_carriers = len([mc for mc, stats in carrier_performance.items() if stats["total_calls"] >= 3])
        
        return {
            "unique_carriers": len(unique_carriers),
            "repeat_carriers": repeat_carriers,
            "new_carriers": new_carriers,
            "highly_engaged_carriers": highly_engaged_carriers,
            "carrier_retention_rate": round((repeat_carriers / len(unique_carriers) * 100), 1) if unique_carriers else 0,
            "top_performers": [
                {
                    "mc": mc,
                    "name": stats["name"],
                    "calls": stats["total_calls"],
                    "success_rate": round(stats["success_rate"], 1),
                    "total_revenue": round(stats["total_revenue"], 2),
                    "avg_deal_size": round(stats["avg_deal_size"], 2),
                    "last_call": stats["last_call_date"].strftime("%Y-%m-%d") if stats["last_call_date"] else "Unknown"
                }
                for mc, stats in top_carriers
            ]
        }
    
    def _get_trend_data(self, calls: List[Call], days: int) -> Dict[str, Any]:
        """Trend analysis for charts and performance tracking."""
        
        # Daily trends
        daily_stats = {}
        for call in calls:
            if call.created_at:
                date_key = call.created_at.strftime("%Y-%m-%d")
                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        "total": 0, 
                        "successful": 0, 
                        "revenue": 0, 
                        "avg_duration": [],
                        "negotiations": 0
                    }
                
                daily_stats[date_key]["total"] += 1
                if call.outcome == "accepted":
                    daily_stats[date_key]["successful"] += 1
                    if call.final_rate:
                        daily_stats[date_key]["revenue"] += call.final_rate
                
                if call.call_duration_seconds:
                    daily_stats[date_key]["avg_duration"].append(call.call_duration_seconds)
                
                if call.negotiation_rounds and call.negotiation_rounds > 0:
                    daily_stats[date_key]["negotiations"] += 1
        
        # Process daily averages
        for date_key, stats in daily_stats.items():
            if stats["avg_duration"]:
                stats["avg_duration_minutes"] = sum(stats["avg_duration"]) / len(stats["avg_duration"]) / 60
            else:
                stats["avg_duration_minutes"] = 0
            del stats["avg_duration"]  # Remove the raw data
        
        # Convert to arrays for charting
        dates = sorted(daily_stats.keys())
        daily_calls = [daily_stats[date]["total"] for date in dates]
        daily_successes = [daily_stats[date]["successful"] for date in dates]
        daily_revenue = [round(daily_stats[date]["revenue"], 2) for date in dates]
        daily_success_rates = [
            (daily_stats[date]["successful"] / daily_stats[date]["total"] * 100) 
            if daily_stats[date]["total"] > 0 else 0 
            for date in dates
        ]
        
        # Weekly aggregation for longer periods
        weekly_stats = {}
        if days > 14:
            for date_str in dates:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                week_key = date_obj.strftime("%Y-W%U")  # Year-Week format
                
                if week_key not in weekly_stats:
                    weekly_stats[week_key] = {"total": 0, "successful": 0, "revenue": 0}
                
                weekly_stats[week_key]["total"] += daily_stats[date_str]["total"]
                weekly_stats[week_key]["successful"] += daily_stats[date_str]["successful"]
                weekly_stats[week_key]["revenue"] += daily_stats[date_str]["revenue"]
        
        return {
            "daily_trends": {
                "dates": dates,
                "calls": daily_calls,
                "successes": daily_successes,
                "revenue": daily_revenue,
                "success_rates": [round(rate, 1) for rate in daily_success_rates]
            },
            "weekly_trends": {
                "weeks": list(weekly_stats.keys()),
                "calls": [weekly_stats[week]["total"] for week in weekly_stats.keys()],
                "successes": [weekly_stats[week]["successful"] for week in weekly_stats.keys()],
                "revenue": [round(weekly_stats[week]["revenue"], 2) for week in weekly_stats.keys()]
            } if weekly_stats else None,
            "summary": {
                "total_days_with_activity": len([d for d in daily_calls if d > 0]),
                "best_day": {
                    "date": dates[daily_calls.index(max(daily_calls))] if daily_calls else None,
                    "calls": max(daily_calls) if daily_calls else 0
                },
                "best_revenue_day": {
                    "date": dates[daily_revenue.index(max(daily_revenue))] if daily_revenue else None,
                    "revenue": max(daily_revenue) if daily_revenue else 0
                }
            }
        }
    
    def _get_negotiation_analysis(self, calls: List[Call]) -> Dict[str, Any]:
        """Detailed negotiation performance analysis."""
        negotiated_calls = [c for c in calls if c.negotiation_rounds and c.negotiation_rounds > 0]
        
        if not negotiated_calls:
            return {"no_data": True}
        
        # Round-by-round success rates
        round_success = {}
        for call in negotiated_calls:
            rounds = call.negotiation_rounds
            if rounds not in round_success:
                round_success[rounds] = {"total": 0, "successful": 0}
            
            round_success[rounds]["total"] += 1
            if call.outcome == "accepted":
                round_success[rounds]["successful"] += 1
        
        # Calculate success rates by round
        for rounds, stats in round_success.items():
            stats["success_rate"] = (stats["successful"] / stats["total"] * 100)
        
        return {
            "total_negotiations": len(negotiated_calls),
            "negotiation_success_rate": len([c for c in negotiated_calls if c.outcome == "accepted"]) / len(negotiated_calls) * 100,
            "avg_rounds": sum(c.negotiation_rounds for c in negotiated_calls) / len(negotiated_calls),
            "success_by_round": round_success,
            "quick_wins": len([c for c in calls if c.outcome == "accepted" and (c.negotiation_rounds or 0) == 0])
        }
    
    def _get_time_analysis(self, calls: List[Call]) -> Dict[str, Any]:
        """Time-based analysis for operational insights."""
        if not calls:
            return {"no_data": True}
        
        # Hour of day analysis
        hourly_success = {}
        for call in calls:
            if call.created_at:
                hour = call.created_at.hour
                if hour not in hourly_success:
                    hourly_success[hour] = {"total": 0, "successful": 0}
                
                hourly_success[hour]["total"] += 1
                if call.outcome == "accepted":
                    hourly_success[hour]["successful"] += 1
        
        # Calculate success rates by hour
        for hour, stats in hourly_success.items():
            stats["success_rate"] = (stats["successful"] / stats["total"] * 100) if stats["total"] > 0 else 0
        
        # Find best performing hours
        best_hours = sorted(
            [(hour, stats["success_rate"]) for hour, stats in hourly_success.items() if stats["total"] >= 2],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "hourly_performance": hourly_success,
            "best_performing_hours": [{"hour": hour, "success_rate": rate} for hour, rate in best_hours],
            "total_hours_active": len(hourly_success)
        }
    
    def _get_conversion_funnel(self, calls: List[Call]) -> Dict[str, Any]:
        """Conversion funnel analysis for freight brokerage process."""
        if not calls:
            return {"no_data": True}
        
        # Define the stages of the freight brokerage funnel
        total_calls = len(calls)
        
        # Stage 1: MC Verification
        mc_collected = len([c for c in calls if c.carrier_mc])
        mc_verified = len([c for c in calls if c.fmcsa_status and c.fmcsa_status != "failed"])
        
        # Stage 2: Load Matching (calls with extracted equipment data)
        equipment_collected = 0
        for call in calls:
            if call.extracted_json:
                try:
                    data = json.loads(call.extracted_json) if isinstance(call.extracted_json, str) else call.extracted_json
                    if data.get("equipment_type"):
                        equipment_collected += 1
                except:
                    pass
        
        # Stage 3: Negotiation Started
        negotiations_started = len([c for c in calls if c.negotiation_rounds and c.negotiation_rounds > 0])
        
        # Stage 4: Final Conversion
        conversions = len([c for c in calls if c.outcome == "accepted"])
        
        # Calculate conversion rates between stages
        funnel_data = {
            "total_calls": total_calls,
            "stages": {
                "initial_contact": {
                    "count": total_calls,
                    "percentage": 100.0,
                    "description": "Total inbound calls"
                },
                "mc_collected": {
                    "count": mc_collected,
                    "percentage": (mc_collected / total_calls * 100) if total_calls > 0 else 0,
                    "description": "MC numbers collected"
                },
                "mc_verified": {
                    "count": mc_verified,
                    "percentage": (mc_verified / total_calls * 100) if total_calls > 0 else 0,
                    "description": "Carriers verified with FMCSA"
                },
                "load_matching": {
                    "count": equipment_collected,
                    "percentage": (equipment_collected / total_calls * 100) if total_calls > 0 else 0,
                    "description": "Equipment/location preferences collected"
                },
                "negotiations": {
                    "count": negotiations_started,
                    "percentage": (negotiations_started / total_calls * 100) if total_calls > 0 else 0,
                    "description": "Price negotiations initiated"
                },
                "conversions": {
                    "count": conversions,
                    "percentage": (conversions / total_calls * 100) if total_calls > 0 else 0,
                    "description": "Loads successfully booked"
                }
            }
        }
        
        # Identify the biggest drop-off points
        stage_names = list(funnel_data["stages"].keys())
        drop_offs = []
        
        for i in range(len(stage_names) - 1):
            current_stage = funnel_data["stages"][stage_names[i]]
            next_stage = funnel_data["stages"][stage_names[i + 1]]
            
            drop_off_percentage = current_stage["percentage"] - next_stage["percentage"]
            drop_offs.append({
                "from_stage": stage_names[i],
                "to_stage": stage_names[i + 1],
                "drop_off_percentage": round(drop_off_percentage, 1),
                "calls_lost": current_stage["count"] - next_stage["count"]
            })
        
        # Find the biggest opportunity for improvement
        biggest_drop_off = max(drop_offs, key=lambda x: x["drop_off_percentage"]) if drop_offs else None
        
        funnel_data["drop_off_analysis"] = {
            "all_drop_offs": drop_offs,
            "biggest_opportunity": biggest_drop_off
        }
        
        return funnel_data