# api/services/metrics_service.py
"""
Metrics calculation service for KPI dashboard.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from api.models import Call, Load

class MetricsService:
    """Service for calculating KPI metrics from call data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_summary_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary for the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with all KPI metrics
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get calls in date range
        calls_query = self.db.query(Call).filter(
            Call.created_at >= start_date,
            Call.created_at <= end_date
        )
        
        # Basic call metrics
        total_calls = calls_query.count()
        completed_calls = calls_query.filter(Call.outcome.in_(["accepted", "rejected"])).count()
        successful_calls = calls_query.filter(Call.outcome == "accepted").count()
        
        # Calculate rates
        acceptance_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        completion_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Duration metrics
        duration_stats = self._calculate_duration_stats(calls_query)
        
        # Negotiation metrics
        negotiation_stats = self._calculate_negotiation_stats(calls_query)
        
        # Revenue metrics
        revenue_stats = self._calculate_revenue_stats(calls_query)
        
        # Carrier metrics
        carrier_stats = self._calculate_carrier_stats(calls_query)
        
        # Time-based metrics
        time_stats = self._calculate_time_based_stats(calls_query, days)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "call_metrics": {
                "total_calls": total_calls,
                "completed_calls": completed_calls,
                "successful_calls": successful_calls,
                "acceptance_rate": round(acceptance_rate, 2),
                "completion_rate": round(completion_rate, 2)
            },
            "duration_metrics": duration_stats,
            "negotiation_metrics": negotiation_stats,
            "revenue_metrics": revenue_stats,
            "carrier_metrics": carrier_stats,
            "time_metrics": time_stats
        }
    
    def _calculate_duration_stats(self, calls_query) -> Dict[str, Any]:
        """Calculate call duration statistics."""
        durations = [
            call.call_duration_seconds 
            for call in calls_query.all() 
            if call.call_duration_seconds is not None
        ]
        
        if not durations:
            return {
                "average_duration_seconds": 0,
                "average_duration_minutes": 0,
                "min_duration_seconds": 0,
                "max_duration_seconds": 0,
                "total_call_time_minutes": 0
            }
        
        avg_duration = sum(durations) / len(durations)
        total_time = sum(durations)
        
        return {
            "average_duration_seconds": round(avg_duration, 1),
            "average_duration_minutes": round(avg_duration / 60, 1),
            "min_duration_seconds": min(durations),
            "max_duration_seconds": max(durations),
            "total_call_time_minutes": round(total_time / 60, 1)
        }
    
    def _calculate_negotiation_stats(self, calls_query) -> Dict[str, Any]:
        """Calculate negotiation-related statistics."""
        all_calls = calls_query.all()
        
        negotiation_rounds = [
            call.negotiation_rounds 
            for call in all_calls 
            if call.negotiation_rounds is not None
        ]
        
        if not negotiation_rounds:
            return {
                "average_negotiation_rounds": 0,
                "max_negotiation_rounds": 0,
                "calls_with_negotiation": 0,
                "negotiation_success_rate": 0
            }
        
        calls_with_negotiation = len([r for r in negotiation_rounds if r > 0])
        negotiated_and_accepted = len([
            call for call in all_calls 
            if call.negotiation_rounds > 0 and call.outcome == "accepted"
        ])
        
        negotiation_success_rate = (
            negotiated_and_accepted / calls_with_negotiation * 100
        ) if calls_with_negotiation > 0 else 0
        
        return {
            "average_negotiation_rounds": round(sum(negotiation_rounds) / len(negotiation_rounds), 2),
            "max_negotiation_rounds": max(negotiation_rounds),
            "calls_with_negotiation": calls_with_negotiation,
            "negotiation_success_rate": round(negotiation_success_rate, 2)
        }
    
    def _calculate_revenue_stats(self, calls_query) -> Dict[str, Any]:
        """Calculate revenue-related statistics."""
        successful_calls = calls_query.filter(Call.outcome == "accepted").all()
        
        if not successful_calls:
            return {
                "total_revenue": 0,
                "average_deal_size": 0,
                "average_rate_per_mile": 0,
                "revenue_per_call": 0
            }
        
        # Calculate revenue from successful calls
        revenues = []
        rates_per_mile = []
        
        for call in successful_calls:
            if call.final_rate:
                revenues.append(call.final_rate)
                
                # Calculate rate per mile if we have load data
                if call.load and call.load.miles:
                    rate_per_mile = call.final_rate / call.load.miles
                    rates_per_mile.append(rate_per_mile)
        
        total_revenue = sum(revenues)
        avg_deal_size = sum(revenues) / len(revenues) if revenues else 0
        avg_rate_per_mile = sum(rates_per_mile) / len(rates_per_mile) if rates_per_mile else 0
        
        # Revenue per call (including unsuccessful calls)
        total_calls = calls_query.count()
        revenue_per_call = total_revenue / total_calls if total_calls > 0 else 0
        
        return {
            "total_revenue": round(total_revenue, 2),
            "average_deal_size": round(avg_deal_size, 2),
            "average_rate_per_mile": round(avg_rate_per_mile, 2),
            "revenue_per_call": round(revenue_per_call, 2)
        }
    
    def _calculate_carrier_stats(self, calls_query) -> Dict[str, Any]:
        """Calculate carrier-related statistics."""
        all_calls = calls_query.all()
        
        # Unique carriers
        unique_carriers = set(call.carrier_mc for call in all_calls if call.carrier_mc)
        
        # FMCSA verification stats
        verified_calls = [call for call in all_calls if call.fmcsa_status]
        verification_statuses = [call.fmcsa_status for call in verified_calls]
        
        active_carriers = len([s for s in verification_statuses if s.lower() == "active"])
        verification_success_rate = (
            active_carriers / len(verification_statuses) * 100
        ) if verification_statuses else 0
        
        # Repeat carriers
        carrier_call_counts = {}
        for call in all_calls:
            if call.carrier_mc:
                carrier_call_counts[call.carrier_mc] = carrier_call_counts.get(call.carrier_mc, 0) + 1
        
        repeat_carriers = len([mc for mc, count in carrier_call_counts.items() if count > 1])
        
        return {
            "unique_carriers": len(unique_carriers),
            "repeat_carriers": repeat_carriers,
            "verification_success_rate": round(verification_success_rate, 2),
            "most_active_carriers": self._get_top_carriers(carrier_call_counts, 5)
        }
    
    def _calculate_time_based_stats(self, calls_query, days: int) -> Dict[str, Any]:
        """Calculate time-based patterns."""
        all_calls = calls_query.all()
        
        # Calls by day of week
        calls_by_day = {}
        calls_by_hour = {}
        
        for call in all_calls:
            if call.created_at:
                day_name = call.created_at.strftime("%A")
                hour = call.created_at.hour
                
                calls_by_day[day_name] = calls_by_day.get(day_name, 0) + 1
                calls_by_hour[hour] = calls_by_hour.get(hour, 0) + 1
        
        # Peak hours
        peak_hour = max(calls_by_hour.items(), key=lambda x: x[1]) if calls_by_hour else (0, 0)
        peak_day = max(calls_by_day.items(), key=lambda x: x[1]) if calls_by_day else ("", 0)
        
        return {
            "calls_by_day": calls_by_day,
            "calls_by_hour": calls_by_hour,
            "peak_hour": f"{peak_hour[0]}:00 ({peak_hour[1]} calls)",
            "peak_day": f"{peak_day[0]} ({peak_day[1]} calls)"
        }
    
    def _get_top_carriers(self, carrier_counts: dict, limit: int) -> List[Dict[str, Any]]:
        """Get top carriers by call volume."""
        sorted_carriers = sorted(carrier_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"mc_number": mc, "call_count": count}
            for mc, count in sorted_carriers[:limit]
        ]
    
    def get_detailed_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get detailed metrics with breakdowns and trends.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Detailed metrics with trends and breakdowns
        """
        base_metrics = self.get_summary_metrics(days)
        
        # Add trend analysis
        trend_metrics = self._calculate_trends(days)
        
        # Add outcome breakdown
        outcome_breakdown = self._get_outcome_breakdown(days)
        
        # Add load type analysis
        load_analysis = self._get_load_type_analysis(days)
        
        return {
            **base_metrics,
            "trends": trend_metrics,
            "outcome_breakdown": outcome_breakdown,
            "load_analysis": load_analysis
        }
    
    def _calculate_trends(self, days: int) -> Dict[str, Any]:
        """Calculate week-over-week trends."""
        current_period = self.get_summary_metrics(days // 2)  # Last half of period
        previous_period = self._get_period_metrics(days, days // 2)  # Previous half
        
        # Calculate percentage changes
        trends = {}
        for key in ["total_calls", "successful_calls", "acceptance_rate"]:
            current = current_period["call_metrics"][key]
            previous = previous_period["call_metrics"][key]
            
            if previous > 0:
                change = ((current - previous) / previous) * 100
                trends[f"{key}_change"] = round(change, 1)
            else:
                trends[f"{key}_change"] = 0
        
        return trends
    
    def _get_period_metrics(self, total_days: int, offset_days: int) -> Dict[str, Any]:
        """Get metrics for a specific period offset."""
        end_date = datetime.utcnow() - timedelta(days=offset_days)
        start_date = end_date - timedelta(days=total_days // 2)
        
        calls_query = self.db.query(Call).filter(
            Call.created_at >= start_date,
            Call.created_at <= end_date
        )
        
        total_calls = calls_query.count()
        successful_calls = calls_query.filter(Call.outcome == "accepted").count()
        acceptance_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        
        return {
            "call_metrics": {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "acceptance_rate": acceptance_rate
            }
        }
    
    def _get_outcome_breakdown(self, days: int) -> Dict[str, Any]:
        """Get detailed breakdown of call outcomes."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        outcome_counts = (
            self.db.query(Call.outcome, func.count(Call.id))
            .filter(Call.created_at >= start_date)
            .group_by(Call.outcome)
            .all()
        )
        
        sentiment_counts = (
            self.db.query(Call.sentiment, func.count(Call.id))
            .filter(Call.created_at >= start_date)
            .filter(Call.sentiment.isnot(None))
            .group_by(Call.sentiment)
            .all()
        )
        
        return {
            "outcomes": {outcome: count for outcome, count in outcome_counts},
            "sentiments": {sentiment: count for sentiment, count in sentiment_counts}
        }
    
    def _get_load_type_analysis(self, days: int) -> Dict[str, Any]:
        """Analyze performance by load type."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get calls with associated loads
        calls_with_loads = (
            self.db.query(Call)
            .join(Load, Call.load_id == Load.load_id)
            .filter(Call.created_at >= start_date)
            .all()
        )
        
        equipment_stats = {}
        for call in calls_with_loads:
            equipment = call.load.equipment_type
            if equipment not in equipment_stats:
                equipment_stats[equipment] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "total_revenue": 0
                }
            
            equipment_stats[equipment]["total_calls"] += 1
            if call.outcome == "accepted":
                equipment_stats[equipment]["successful_calls"] += 1
                if call.final_rate:
                    equipment_stats[equipment]["total_revenue"] += call.final_rate
        
        # Calculate success rates
        for equipment, stats in equipment_stats.items():
            if stats["total_calls"] > 0:
                stats["success_rate"] = round(
                    (stats["successful_calls"] / stats["total_calls"]) * 100, 2
                )
            else:
                stats["success_rate"] = 0
        
        return {
            "equipment_performance": equipment_stats,
            "best_performing_equipment": max(
                equipment_stats.items(), 
                key=lambda x: x[1]["success_rate"]
            )[0] if equipment_stats else None
        }