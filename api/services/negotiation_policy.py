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
        self.max_rounds = 3
        self.target_multiplier = 1.0  # Target equals listed rate
        self.floor_multiplier = 0.93  # Floor equals 93% of listed rate
    
    def evaluate_offer(self, listed_rate: float, offer: float, round_number: int) -> Dict[str, Any]:
        """
        Evaluate a carrier's offer and determine the response.
        
        Policy:
        - Target = listed rate (100%)
        - Floor = 93% of listed rate
        - Accept if offer >= target
        - Counter if offer >= floor and rounds < max
        - Reject if offer < floor or max rounds reached
        
        Args:
            listed_rate: The original listed rate for the load
            offer: The carrier's current offer
            round_number: Current negotiation round (1-based)
            
        Returns:
            Dictionary with evaluation result
        """
        target_rate = listed_rate * self.target_multiplier
        floor_rate = listed_rate * self.floor_multiplier
        
        # Check if max rounds reached
        if round_number >= self.max_rounds:
            return {
                "outcome": NegotiationOutcome.MAX_ROUNDS_REACHED.value,
                "message": f"Maximum rounds ({self.max_rounds}) reached",
                "target_rate": target_rate,
                "floor_rate": floor_rate,
                "counter_offer": None,
                "round": round_number,
                "max_rounds": self.max_rounds
            }
        
        # Accept if offer meets or exceeds target
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
        
        # Reject if offer below floor
        if offer < floor_rate:
            return {
                "outcome": NegotiationOutcome.REJECT.value,
                "message": f"Offer rejected - below floor rate (${floor_rate:.2f})",
                "target_rate": target_rate,
                "floor_rate": floor_rate,
                "counter_offer": None,
                "round": round_number,
                "max_rounds": self.max_rounds
            }
        
        # Counter offer - between floor and target
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
    
    def _calculate_counter_offer(self, listed_rate: float, current_offer: float, round_number: int) -> float:
        """
        Calculate a counter offer based on the current offer and round.
        
        Strategy:
        - Round 1: Counter at 95% of listed rate
        - Round 2: Counter at 97% of listed rate  
        - Round 3: Counter at 99% of listed rate
        """
        if round_number == 1:
            return listed_rate * 0.95
        elif round_number == 2:
            return listed_rate * 0.97
        else:
            return listed_rate * 0.99
    
    def get_negotiation_summary(self, listed_rate: float) -> Dict[str, Any]:
        """
        Get a summary of the negotiation parameters for a load.
        
        Args:
            listed_rate: The original listed rate for the load
            
        Returns:
            Dictionary with negotiation parameters
        """
        return {
            "listed_rate": listed_rate,
            "target_rate": listed_rate * self.target_multiplier,
            "floor_rate": listed_rate * self.floor_multiplier,
            "max_rounds": self.max_rounds,
            "policy": {
                "target_multiplier": self.target_multiplier,
                "floor_multiplier": self.floor_multiplier,
                "description": "Accept at target (100%), counter between floor (93%) and target, reject below floor"
            }
        }
