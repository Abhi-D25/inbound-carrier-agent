"""
Load search and ranking service.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from api.models import Load
from api.schemas import LoadSearchRequest

class LoadSearchService:
    """Service for searching and ranking loads."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_loads(self, search_request: LoadSearchRequest) -> dict:
        """
        Search for loads with filtering and ranking.
        
        Args:
            search_request: Search criteria
            
        Returns:
            Dictionary with loads list and total count
        """
        # Build query
        query = self.db.query(Load).filter(Load.is_active == True)
        
        # Apply filters
        if search_request.origin_state:
            query = query.filter(Load.origin_state.ilike(f"%{search_request.origin_state}%"))
        
        if search_request.destination_state:
            query = query.filter(Load.destination_state.ilike(f"%{search_request.destination_state}%"))
        
        if search_request.equipment_type:
            query = query.filter(Load.equipment_type.ilike(f"%{search_request.equipment_type}%"))
        
        if search_request.min_rate:
            query = query.filter(Load.rate_per_mile >= search_request.min_rate)
        
        if search_request.max_rate:
            query = query.filter(Load.rate_per_mile <= search_request.max_rate)
        
        # Get total count
        total_count = query.count()
        
        # Apply ranking and limit
        loads = self._rank_and_limit_loads(query, search_request.limit)
        
        return {
            "loads": loads,
            "total": total_count,
            "filters_applied": {
                "origin_state": search_request.origin_state,
                "destination_state": search_request.destination_state,
                "equipment_type": search_request.equipment_type,
                "min_rate": search_request.min_rate,
                "max_rate": search_request.max_rate,
                "limit": search_request.limit
            }
        }
    
    def _rank_and_limit_loads(self, query, limit: int) -> List[dict]:
        """
        Rank loads by profitability and other factors, then apply limit.
        
        Ranking criteria:
        1. Higher rate per mile (profitability)
        2. Shorter distance (efficiency)
        3. Recent pickup date (urgency)
        """
        # Order by rate per mile (desc), then by miles (asc), then by pickup date (asc)
        ordered_query = query.order_by(
            Load.rate_per_mile.desc(),
            Load.miles.asc(),
            Load.pickup_date.asc()
        )
        
        # Apply limit
        loads = ordered_query.limit(limit).all()
        
        # Convert to dictionaries with ranking info
        ranked_loads = []
        for i, load in enumerate(loads, 1):
            load_dict = {
                "id": load.id,
                "load_id": load.load_id,
                "origin_city": load.origin_city,
                "origin_state": load.origin_state,
                "destination_city": load.destination_city,
                "destination_state": load.destination_state,
                "pickup_date": load.pickup_date.isoformat(),
                "delivery_date": load.delivery_date.isoformat(),
                "equipment_type": load.equipment_type,
                "weight": load.weight,
                "miles": load.miles,
                "rate_per_mile": load.rate_per_mile,
                "total_rate": load.total_rate,
                "commodity": load.commodity,
                "special_requirements": load.special_requirements,
                "broker_name": load.broker_name,
                "broker_mc": load.broker_mc,
                "rank": i,
                "profitability_score": self._calculate_profitability_score(load)
            }
            ranked_loads.append(load_dict)
        
        return ranked_loads
    
    def _calculate_profitability_score(self, load: Load) -> float:
        """
        Calculate a profitability score for ranking.
        Higher score = more profitable/desirable load.
        """
        # Base score from rate per mile
        base_score = load.rate_per_mile
        
        # Bonus for shorter distances (more efficient)
        distance_bonus = max(0, (1000 - load.miles) / 1000) * 0.5
        
        # Bonus for higher total rate
        rate_bonus = min(load.total_rate / 2000, 1.0) * 0.3
        
        return round(base_score + distance_bonus + rate_bonus, 2)
