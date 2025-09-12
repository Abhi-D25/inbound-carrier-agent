"""
Negotiation policy service for evaluating offers and counter-offers.
"""
from typing import Dict, Any
from enum import Enum

class NegotiationOutcome(Enum):
    ACCEPT = "accept"
    COUNTER = "counter"
    REJECT = "reject"
    MAX_ROUNDS_REACHED = "max_rounds_reached"

class NegotiationPolicy:
    """Policy engine for load negotiations."""
    
    def __init__(self):
        self.max_rounds = 4  # Allow 4 rounds: 2 standard counters + 1 floor rate + 1 reject
        self.target_multiplier = 1.0  # Target equals listed rate (100%)
        self.floor_multiplier = 0.93  # Floor equals 93% of listed rate
    
    def evaluate_offer(self, listed_rate: float, offer: float, round_number: int) -> Dict[str, Any]:
        """
        Evaluate a carrier's offer with 4-round negotiation strategy.
        
        Strategy:
        - Round 1: Counter at 97% of listed rate (higher initial counter)
        - Round 2: Counter at 95% of listed rate (slight decrease to show flexibility)
        - Round 3: Counter with floor rate (93%) as final offer
        - Round 4+: Reject any further negotiations
        - Accept immediately if offer >= target at any point
        
        Args:
            listed_rate: The original listed rate for the load
            offer: The carrier's current offer
            round_number: Current negotiation round (1-based)
            
        Returns:
            Dictionary with evaluation result
        """
        target_rate = listed_rate * self.target_multiplier
        floor_rate = listed_rate * self.floor_multiplier
        
        # Accept immediately if offer meets or exceeds target (any round)
        if offer >= target_rate:
            return {
                "outcome": NegotiationOutcome.ACCEPT.value,
                "message": "Offer accepted - meets target rate",
                "target_rate": target_rate,
                "floor_rate": floor_rate,
                "counter_offer": None,
                "round": round_number,
                "max_rounds": self.max_rounds
            }
        
        # Handle negotiation rounds
        if round_number <= 2:
            # Rounds 1-2: Always counter with standard progression
            counter_offer = self._calculate_counter_offer(listed_rate, offer, round_number)
            
            return {
                "outcome": NegotiationOutcome.COUNTER.value,
                "message": f"Counter offer: ${counter_offer:.2f}",
                "target_rate": target_rate,
                "floor_rate": floor_rate,
                "counter_offer": counter_offer,
                "round": round_number,
                "max_rounds": self.max_rounds
            }
        
        elif round_number == 3:
            # Round 3: Final counter with floor rate
            counter_offer = self._round_to_nearest_10(floor_rate)
            
            return {
                "outcome": NegotiationOutcome.COUNTER.value,
                "message": f"Final offer: ${counter_offer:.2f} - this is our absolute minimum",
                "target_rate": target_rate,
                "floor_rate": floor_rate,
                "counter_offer": counter_offer,
                "round": round_number,
                "max_rounds": self.max_rounds,
                "is_final_offer": True
            }
        
        else:
            # Round 4+: No more negotiations, reject
            return {
                "outcome": NegotiationOutcome.REJECT.value,
                "message": f"We've reached our maximum negotiations. Cannot accept below ${floor_rate:.2f}",
                "target_rate": target_rate,
                "floor_rate": floor_rate,
                "counter_offer": None,
                "round": round_number,
                "max_rounds": self.max_rounds
            }
    
    def _calculate_counter_offer(self, listed_rate: float, current_offer: float, round_number: int) -> float:
        """
        Calculate counter offer for rounds 1-2.
        Round 3 uses floor rate, so this method only handles rounds 1-2.
        
        Strategy:
        - Round 1: Counter at 97% of listed rate (higher initial counter)
        - Round 2: Counter at 95% of listed rate (slight decrease to show flexibility)
        
        Args:
            listed_rate: Original listed rate
            current_offer: Carrier's current offer (not used in calculation but available)
            round_number: Current round (1 or 2)
            
        Returns:
            Counter offer amount rounded to nearest $10
        """
        if round_number == 1:
            counter = listed_rate * 0.97  # 97% of listed rate - start higher
        elif round_number == 2:
            counter = listed_rate * 0.95  # 95% of listed rate - slight decrease
        else:
            # Should not reach here for round 3+ but fallback
            counter = listed_rate * self.floor_multiplier
    
        return self._round_to_nearest_10(counter)
    
    def _round_to_nearest_10(self, amount: float) -> float:
        """Round amount to nearest $10."""
        return round(amount / 10) * 10
    
    def get_negotiation_summary(self, listed_rate: float) -> Dict[str, Any]:
        """
        Get a summary of the negotiation parameters for a load.
        
        Args:
            listed_rate: The original listed rate for the load
            
        Returns:
            Dictionary with negotiation parameters
        """
        target_rate = listed_rate * self.target_multiplier
        floor_rate = listed_rate * self.floor_multiplier
        round_1_counter = self._round_to_nearest_10(listed_rate * 0.97)
        round_2_counter = self._round_to_nearest_10(listed_rate * 0.95)
        round_3_counter = self._round_to_nearest_10(floor_rate)
        
        return {
            "listed_rate": listed_rate,
            "target_rate": target_rate,
            "floor_rate": floor_rate,
            "max_rounds": self.max_rounds,
            "negotiation_progression": {
                "round_1_counter": round_1_counter,
                "round_2_counter": round_2_counter,
                "round_3_counter": round_3_counter,
                "round_4_outcome": "reject"
            },
            "policy": {
                "target_multiplier": self.target_multiplier,
                "floor_multiplier": self.floor_multiplier,
                "strategy": "4-round negotiation with decreasing counters ending at floor rate",
                "description": "Counter at 97%, 95%, then floor rate (93%), then reject"
            }
        }