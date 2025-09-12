"""
Load search and ranking service with enhanced city and state matching.
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from api.models import Load
from api.schemas import LoadSearchRequest

class LoadSearchService:
    """Service for searching and ranking loads with city and state prioritization."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_loads(self, search_request: LoadSearchRequest) -> dict:
        """
        Enhanced search for loads with city and state matching priority.
        
        Matching Priority:
        1. Exact city + state match (100 points)
        2. City match (any state) (60-80 points)
        3. State match (any city) (40-70 points)
        4. Equipment type only (20+ points)
        
        Args:
            search_request: Search criteria with city/state preferences
            
        Returns:
            Dictionary with ranked loads and search metadata
        """
        # Build base query
        query = self.db.query(Load).filter(Load.is_active == True)
        
        # Apply equipment filter first (most important)
        if search_request.equipment_type:
            query = query.filter(Load.equipment_type.ilike(f"%{search_request.equipment_type}%"))
        
        # Apply rate filters
        if search_request.min_rate:
            query = query.filter(Load.rate_per_mile >= search_request.min_rate)
        if search_request.max_rate:
            query = query.filter(Load.rate_per_mile <= search_request.max_rate)
        
        # Get all matching loads and score them
        all_loads = query.all()
        scored_loads = []
        
        for load in all_loads:
            location_score = self._calculate_location_score(load, search_request)
            if location_score > 0:  # Only include loads with some relevance
                scored_loads.append((load, location_score))
        
        # Sort by location score (desc), then by profitability score (desc)
        scored_loads.sort(key=lambda x: (-x[1], -x[0].rate_per_mile))
        
        # Apply limit and convert to dictionaries
        limited_loads = scored_loads[:search_request.limit]
        ranked_loads = []
        
        for i, (load, location_score) in enumerate(limited_loads, 1):
            profitability_score = self._calculate_profitability_score(load)
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
                "location_match_score": location_score,
                "profitability_score": profitability_score,
                # Additional formatted fields for presentation
                "route_summary": f"{load.origin_city}, {load.origin_state} → {load.destination_city}, {load.destination_state}",
                "pickup_date_formatted": load.pickup_date.strftime("%B %d, %Y"),
                "delivery_date_formatted": load.delivery_date.strftime("%B %d, %Y"),
                "weight_formatted": f"{load.weight:,.0f} lbs",
                "rate_formatted": f"${load.total_rate:,.2f}",
                "match_quality": self._get_match_quality_description(location_score)
            }
            ranked_loads.append(load_dict)
        
        return {
            "loads": ranked_loads,
            "total": len(scored_loads),
            "search_summary": self._create_enhanced_search_summary(search_request, ranked_loads),
            "filters_applied": {
                "origin_city": search_request.origin_city,
                "origin_state": search_request.origin_state,
                "destination_city": search_request.destination_city,
                "destination_state": search_request.destination_state,
                "equipment_type": search_request.equipment_type,
                "min_rate": search_request.min_rate,
                "max_rate": search_request.max_rate,
                "limit": search_request.limit
            }
        }
    
    def _calculate_location_score(self, load: Load, search_request: LoadSearchRequest) -> float:
        """
        Calculate location matching score based on city and state preferences.
        
        Scoring System:
        - Exact city + state match: 100 points
        - City match (different state): 60 points  
        - State match (different city): 40 points
        - Only city specified + match: 80 points
        - Only state specified + match: 70 points
        - No location preference: 50 points (neutral)
        - Equipment match only: 20 points minimum
        
        Args:
            load: Load model instance
            search_request: Search criteria
            
        Returns:
            Location match score (0-100)
        """
        # Origin scoring
        origin_score = self._calculate_single_location_score(
            load.origin_city, load.origin_state,
            search_request.origin_city, search_request.origin_state
        )
        
        # Destination scoring
        dest_score = self._calculate_single_location_score(
            load.destination_city, load.destination_state,
            search_request.destination_city, search_request.destination_state
        )
        
        # Combined score (average of origin and destination)
        total_score = (origin_score + dest_score) / 2
        
        # Minimum score threshold - only return loads with some relevance
        return total_score if total_score >= 20 else 0
    
    def _calculate_single_location_score(self, load_city: str, load_state: str, 
                                       requested_city: Optional[str], requested_state: Optional[str]) -> float:
        """Calculate score for a single location (origin OR destination)."""
        if requested_city and requested_state:
            # Both city and state specified
            city_match = load_city.lower() == requested_city.lower() if requested_city else False
            state_match = load_state.upper() == requested_state.upper() if requested_state else False
            
            if city_match and state_match:
                return 100  # Perfect match
            elif city_match:
                return 60   # City match, wrong state
            elif state_match:
                return 40   # State match, wrong city
            else:
                return 0    # No match
        elif requested_city:
            # Only city specified
            if load_city.lower() == requested_city.lower():
                return 80
            else:
                return 0
        elif requested_state:
            # Only state specified
            if load_state.upper() == requested_state.upper():
                return 70
            else:
                return 0
        else:
            # No location preference specified
            return 50
    
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
    
    def _get_match_quality_description(self, score: float) -> str:
        """Get human-readable match quality description."""
        if score >= 90:
            return "Exact match"
        elif score >= 70:
            return "Great match"
        elif score >= 50:
            return "Good match"
        elif score >= 30:
            return "Partial match"
        else:
            return "Equipment match"
    
    def _create_enhanced_search_summary(self, search_request: LoadSearchRequest, loads: List[dict]) -> dict:
        """
        Create enhanced search summary with location matching insights.
        
        Args:
            search_request: Original search criteria
            loads: Found and ranked loads
            
        Returns:
            Summary dictionary with helpful information for the agent
        """
        if not loads:
            return {
                "message": f"No {search_request.equipment_type or 'available'} loads found matching your preferences",
                "suggestions": self._get_location_suggestions(search_request),
                "alternative_search": "Would you like me to search with broader criteria?",
                "search_criteria": self._format_search_criteria(search_request)
            }
        
        best_load = loads[0]
        match_quality = best_load["match_quality"]
        
        # Analyze match types
        exact_matches = len([l for l in loads if l["location_match_score"] >= 90])
        great_matches = len([l for l in loads if 70 <= l["location_match_score"] < 90])
        good_matches = len([l for l in loads if 50 <= l["location_match_score"] < 70])
        
        # Calculate rate statistics
        rates = [load['total_rate'] for load in loads]
        rate_stats = {
            "min": min(rates),
            "max": max(rates),
            "avg": round(sum(rates) / len(rates), 2)
        }
        
        return {
            "message": f"Found {len(loads)} matching {search_request.equipment_type or 'available'} load{'s' if len(loads) > 1 else ''}",
            "best_match_quality": match_quality,
            "match_breakdown": {
                "exact_matches": exact_matches,
                "great_matches": great_matches,
                "good_matches": good_matches,
                "total_matches": len(loads)
            },
            "best_load": {
                "route": best_load['route_summary'],
                "rate": best_load['rate_formatted'],
                "pickup": best_load['pickup_date_formatted'],
                "match_quality": match_quality
            },
            "rate_range": rate_stats,
            "search_criteria": self._format_search_criteria(search_request),
            "pickup_dates": [load['pickup_date_formatted'] for load in loads[:3]]
        }
    
    def _get_location_suggestions(self, search_request: LoadSearchRequest) -> List[str]:
        """Provide helpful suggestions when no loads are found."""
        suggestions = []
        
        if search_request.origin_city and search_request.destination_city:
            suggestions.append(f"Try nearby cities to {search_request.origin_city} or {search_request.destination_city}")
        elif search_request.origin_state and search_request.destination_state:
            suggestions.append(f"Consider loads from other cities in {search_request.origin_state} to {search_request.destination_state}")
        
        if search_request.equipment_type:
            # Suggest alternative equipment types
            equipment_alternatives = {
                "Dry Van": ["Refrigerated", "Flatbed"],
                "Refrigerated": ["Dry Van"], 
                "Flatbed": ["Dry Van", "Step Deck"]
            }
            alternatives = equipment_alternatives.get(search_request.equipment_type, ["Dry Van", "Refrigerated"])
            suggestions.append(f"Consider {' or '.join(alternatives)} loads")
        
        suggestions.extend([
            "Check different pickup/delivery dates",
            "Expand your delivery radius",
            "Consider partial loads or team drivers"
        ])
        
        return suggestions
    
    def _format_search_criteria(self, search_request: LoadSearchRequest) -> str:
        """Format search criteria for human-readable display."""
        criteria_parts = []
        
        if search_request.equipment_type:
            criteria_parts.append(f"{search_request.equipment_type} equipment")
        
        # Origin formatting
        if search_request.origin_city and search_request.origin_state:
            criteria_parts.append(f"from {search_request.origin_city}, {search_request.origin_state}")
        elif search_request.origin_city:
            criteria_parts.append(f"from {search_request.origin_city}")
        elif search_request.origin_state:
            criteria_parts.append(f"from {search_request.origin_state}")
        
        # Destination formatting
        if search_request.destination_city and search_request.destination_state:
            criteria_parts.append(f"to {search_request.destination_city}, {search_request.destination_state}")
        elif search_request.destination_city:
            criteria_parts.append(f"to {search_request.destination_city}")
        elif search_request.destination_state:
            criteria_parts.append(f"to {search_request.destination_state}")
        
        # Rate criteria
        if search_request.min_rate and search_request.max_rate:
            criteria_parts.append(f"${search_request.min_rate:.2f}-${search_request.max_rate:.2f}/mile")
        elif search_request.min_rate:
            criteria_parts.append(f"min ${search_request.min_rate:.2f}/mile")
        elif search_request.max_rate:
            criteria_parts.append(f"max ${search_request.max_rate:.2f}/mile")
        
        return " ".join(criteria_parts) if criteria_parts else "any available loads"
    
    def get_nearby_loads(self, search_request: LoadSearchRequest, radius_miles: int = 100) -> dict:
        """
        Find loads within a certain radius of the requested locations.
        This is a simplified version - in production you'd use geographical distance calculations.
        
        Args:
            search_request: Original search criteria
            radius_miles: Search radius in miles
            
        Returns:
            Dictionary with nearby loads
        """
        # For this implementation, we'll expand the search to nearby states
        # In production, you'd use proper geographical calculations
        
        expanded_request = LoadSearchRequest(
            origin_state=search_request.origin_state,
            destination_state=search_request.destination_state,
            equipment_type=search_request.equipment_type,
            min_rate=search_request.min_rate,
            max_rate=search_request.max_rate,
            limit=search_request.limit * 2  # Get more results for nearby search
        )
        
        return self.search_loads(expanded_request)