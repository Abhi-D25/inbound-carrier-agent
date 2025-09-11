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
        Search for loads with improved location matching.
        
        Args:
            search_request: Search criteria
            
        Returns:
            Dictionary with loads list and total count
        """
        # Build query
        query = self.db.query(Load).filter(Load.is_active == True)
        
        # Apply equipment filter first (most specific)
        if search_request.equipment_type:
            query = query.filter(Load.equipment_type.ilike(f"%{search_request.equipment_type}%"))
        
        # Improved origin state matching
        if search_request.origin_state:
            origin_pattern = self._normalize_state_input(search_request.origin_state)
            query = query.filter(
                or_(
                    Load.origin_state.ilike(f"%{origin_pattern}%"),
                    Load.origin_city.ilike(f"%{origin_pattern}%")
                )
            )
        
        # Improved destination state matching  
        if search_request.destination_state:
            dest_pattern = self._normalize_state_input(search_request.destination_state)
            query = query.filter(
                or_(
                    Load.destination_state.ilike(f"%{dest_pattern}%"),
                    Load.destination_city.ilike(f"%{dest_pattern}%")
                )
            )
        
        # Apply rate filters
        if search_request.min_rate:
            query = query.filter(Load.rate_per_mile >= search_request.min_rate)
        
        if search_request.max_rate:
            query = query.filter(Load.rate_per_mile <= search_request.max_rate)
        
        # Get total count before ranking
        total_count = query.count()
        
        # Apply ranking and limit
        loads = self._rank_and_limit_loads(query, search_request.limit)
        
        return {
            "loads": loads,
            "total": total_count,
            "search_summary": self._create_search_summary(search_request, loads),
            "filters_applied": {
                "origin_state": search_request.origin_state,
                "destination_state": search_request.destination_state,
                "equipment_type": search_request.equipment_type,
                "min_rate": search_request.min_rate,
                "max_rate": search_request.max_rate,
                "limit": search_request.limit
            }
        }
    
    def _normalize_state_input(self, location_input: str) -> str:
        """
        Normalize location input to handle both state names and abbreviations.
        
        Args:
            location_input: User input for location (state name, abbreviation, or city)
            
        Returns:
            Normalized location string for database matching
        """
        if not location_input:
            return ""
        
        # State name to abbreviation mapping
        state_mapping = {
            "texas": "TX", "georgia": "GA", "california": "CA", "florida": "FL",
            "illinois": "IL", "colorado": "CO", "tennessee": "TN", "washington": "WA",
            "oregon": "OR", "arizona": "AZ", "new york": "NY", "nevada": "NV",
            "north carolina": "NC", "south carolina": "SC", "alabama": "AL",
            "mississippi": "MS", "louisiana": "LA", "arkansas": "AR", "oklahoma": "OK",
            "kansas": "KS", "nebraska": "NE", "missouri": "MO", "iowa": "IA",
            "minnesota": "MN", "wisconsin": "WI", "michigan": "MI", "indiana": "IN",
            "ohio": "OH", "kentucky": "KY", "pennsylvania": "PA", "new jersey": "NJ",
            "virginia": "VA", "west virginia": "WV", "maryland": "MD", "delaware": "DE"
        }
        
        location_lower = location_input.lower().strip()
        
        # If it's a full state name, convert to abbreviation
        if location_lower in state_mapping:
            return state_mapping[location_lower]
        
        # If it's already an abbreviation (2 letters), return uppercase
        if len(location_input.strip()) == 2:
            return location_input.upper()
        
        # If it's a city name or other input, return as-is for city matching
        return location_input.title()
    
    def _create_search_summary(self, search_request, loads) -> dict:
        """
        Create a summary of search results for better agent responses.
        
        Args:
            search_request: Original search criteria
            loads: Found loads
            
        Returns:
            Summary dictionary with helpful information for the agent
        """
        if not loads:
            # Provide helpful suggestions when no loads found
            suggestions = []
            if search_request.equipment_type:
                suggestions.append(f"Try different equipment types (we also have Refrigerated, Flatbed loads)")
            if search_request.origin_state and search_request.destination_state:
                suggestions.append("Consider nearby states for pickup or delivery")
            elif search_request.origin_state:
                suggestions.append("Try expanding your delivery destination options")
            elif search_request.destination_state:
                suggestions.append("Try expanding your pickup location options")
            else:
                suggestions.append("Check back later - we get new loads frequently")
            
            return {
                "message": "No loads found matching your exact criteria",
                "suggestions": suggestions,
                "alternative_search": "Would you like me to search with broader criteria?"
            }
        
        # Group by route for better presentation
        routes = {}
        equipment_types = set()
        for load in loads:
            route_key = f"{load['origin_city']}, {load['origin_state']} → {load['destination_city']}, {load['destination_state']}"
            if route_key not in routes:
                routes[route_key] = []
            routes[route_key].append(load)
            equipment_types.add(load['equipment_type'])
        
        # Calculate rate statistics
        rates = [load['total_rate'] for load in loads]
        rate_stats = {
            "min": min(rates),
            "max": max(rates),
            "avg": round(sum(rates) / len(rates), 2)
        }
        
        return {
            "message": f"Found {len(loads)} matching load{'s' if len(loads) > 1 else ''}",
            "available_routes": list(routes.keys()),
            "equipment_types": list(equipment_types),
            "rate_range": rate_stats,
            "best_load": loads[0] if loads else None,  # Highest ranked load
            "pickup_dates": [load['pickup_date'][:10] for load in loads[:3]]  # Next 3 pickup dates
        }
    
    def _rank_and_limit_loads(self, query, limit: int) -> List[dict]:
        """
        Rank loads by profitability and other factors, then apply limit.
        
        Ranking criteria:
        1. Higher rate per mile (profitability) - 60% weight
        2. Shorter distance (efficiency) - 25% weight  
        3. Recent pickup date (urgency) - 15% weight
        
        Args:
            query: SQLAlchemy query object
            limit: Maximum number of results to return
            
        Returns:
            List of ranked load dictionaries
        """
        # Order by rate per mile (desc), then by miles (asc), then by pickup date (asc)
        ordered_query = query.order_by(
            Load.rate_per_mile.desc(),
            Load.miles.asc(),
            Load.pickup_date.asc()
        )
        
        # Apply limit
        loads = ordered_query.limit(limit).all()
        
        # Convert to dictionaries with ranking info and score
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
                "profitability_score": self._calculate_profitability_score(load),
                # Additional fields for agent presentation
                "route_summary": f"{load.origin_city}, {load.origin_state} → {load.destination_city}, {load.destination_state}",
                "pickup_date_formatted": load.pickup_date.strftime("%B %d, %Y"),
                "delivery_date_formatted": load.delivery_date.strftime("%B %d, %Y"),
                "weight_formatted": f"{load.weight:,.0f} lbs",
                "rate_formatted": f"${load.total_rate:,.2f}"
            }
            ranked_loads.append(load_dict)
        
        return ranked_loads
    
    def _calculate_profitability_score(self, load: Load) -> float:
        """
        Calculate a profitability score for ranking.
        Higher score = more profitable/desirable load.
        
        Args:
            load: Load model instance
            
        Returns:
            Profitability score (higher is better)
        """
        # Base score from rate per mile (primary factor)
        base_score = load.rate_per_mile
        
        # Bonus for shorter distances (more efficient, quicker turnaround)
        # Normalize distance bonus: shorter distances get higher bonus
        distance_bonus = max(0, (1500 - load.miles) / 1500) * 0.5
        
        # Bonus for higher total rate (absolute revenue)
        # Cap the bonus at reasonable rate levels
        rate_bonus = min(load.total_rate / 3000, 1.0) * 0.3
        
        # Small bonus for reasonable weight (not too heavy, not too light)
        # Optimal weight range: 25,000 - 45,000 lbs
        optimal_weight_min, optimal_weight_max = 25000, 45000
        if optimal_weight_min <= load.weight <= optimal_weight_max:
            weight_bonus = 0.2
        elif load.weight < optimal_weight_min:
            weight_bonus = (load.weight / optimal_weight_min) * 0.2
        else:  # Over optimal weight
            weight_bonus = max(0, (60000 - load.weight) / 15000) * 0.2
        
        total_score = base_score + distance_bonus + rate_bonus + weight_bonus
        return round(total_score, 2)