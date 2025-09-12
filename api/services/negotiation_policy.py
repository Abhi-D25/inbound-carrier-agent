"""
Enhanced negotiation policy service with carrier-aware counter-offers.
"""
from typing import Dict, Any
from enum import Enum

class NegotiationOutcome(Enum):
    ACCEPT = "accept"
    COUNTER = "counter"
    REJECT = "reject"
    MAX_ROUNDS_REACHED = "max_rounds_reached"

class NegotiationPolicy:
    """Policy engine for load negotiations with intelligent counter-offers."""
    
    def __init__(self):
        self.max_rounds = 3  # Maximum 3 rounds of negotiation
        self.target_multiplier = 1.0  # Target equals listed rate (100%)
        self.floor_multiplier = 0.93  # Floor equals 93% of listed rate
        self.acceptance_threshold = 0.95  # Accept if carrier offer is >= 95% of listed rate
    
    def evaluate_offer(self, listed_rate: float, offer: float, round_number: int) -> Dict[str, Any]:
        """
        Evaluate a carrier's offer with intelligent negotiation strategy.
        
        Key improvements:
        1. Never counter with less than the carrier's current offer
        2. Accept reasonable offers (>= 95% of listed rate) immediately
        3. Make smaller concessions as rounds progress
        4. Consider the carrier's offer when making counter-offers
        
        Args:
            listed_rate: The original listed rate for the load
            offer: The carrier's current offer
            round_number: Current negotiation round (1-based)
            
        Returns:
            Dictionary with evaluation result
        """
        target_rate = listed_rate * self.target_multiplier
        floor_rate = listed_rate * self.floor_multiplier
        acceptance_threshold_rate = listed_rate * self.acceptance_threshold
        
        # Accept immediately if offer meets acceptance threshold (95% of listed)
        if offer >= acceptance_threshold_rate:
            return {
                "outcome": NegotiationOutcome.ACCEPT.value,
                "message": f"Offer accepted at ${offer:.2f}",
                "target_rate": target_rate,
                "floor_rate": floor_rate,
                "counter_offer": None,
                "round": round_number,
                "max_rounds": self.max_rounds,
                "accepted_rate": offer
            }
        
        # Reject if offer is below floor rate
        if offer < floor_rate:
            if round_number >= self.max_rounds:
                return {
                    "outcome": NegotiationOutcome.REJECT.value,
                    "message": f"Cannot accept below our minimum rate of ${floor_rate:.2f}",
                    "target_rate": target_rate,
                    "floor_rate": floor_rate,
                    "counter_offer": None,
                    "round": round_number,
                    "max_rounds": self.max_rounds
                }
            else:
                # Counter with floor rate as minimum
                counter_offer = self._calculate_intelligent_counter(
                    listed_rate, offer, round_number, floor_rate
                )
                return {
                    "outcome": NegotiationOutcome.COUNTER.value,
                    "message": f"Counter offer: ${counter_offer:.2f}",
                    "target_rate": target_rate,
                    "floor_rate": floor_rate,
                    "counter_offer": counter_offer,
                    "round": round_number,
                    "max_rounds": self.max_rounds
                }
        
        # Check if we've reached max rounds
        if round_number >= self.max_rounds:
            # On the last round, accept if it's above floor
            if offer >= floor_rate:
                return {
                    "outcome": NegotiationOutcome.ACCEPT.value,
                    "message": f"Final round - accepting offer at ${offer:.2f}",
                    "target_rate": target_rate,
                    "floor_rate": floor_rate,
                    "counter_offer": None,
                    "round": round_number,
                    "max_rounds": self.max_rounds,
                    "accepted_rate": offer
                }
            else:
                return {
                    "outcome": NegotiationOutcome.REJECT.value,
                    "message": "Maximum negotiation rounds reached",
                    "target_rate": target_rate,
                    "floor_rate": floor_rate,
                    "counter_offer": None,
                    "round": round_number,
                    "max_rounds": self.max_rounds
                }
        
        # Calculate intelligent counter-offer
        counter_offer = self._calculate_intelligent_counter(
            listed_rate, offer, round_number, floor_rate
        )
        
        # CRITICAL FIX: Never counter with less than the carrier's offer
        if counter_offer <= offer:
            # Accept the carrier's offer if our counter would be less
            return {
                "outcome": NegotiationOutcome.ACCEPT.value,
                "message": f"Accepting your offer at ${offer:.2f}",
                "target_rate": target_rate,
                "floor_rate": floor_rate,
                "counter_offer": None,
                "round": round_number,
                "max_rounds": self.max_rounds,
                "accepted_rate": offer
            }
        
        return {
            "outcome": NegotiationOutcome.COUNTER.value,
            "message": f"Counter offer: ${counter_offer:.2f}",
            "target_rate": target_rate,
            "floor_rate": floor_rate,
            "counter_offer": counter_offer,
            "round": round_number,
            "max_rounds": self.max_rounds
        }
    
    def _calculate_intelligent_counter(self, listed_rate: float, carrier_offer: float, 
                                      round_number: int, floor_rate: float) -> float:
        """
        Calculate an intelligent counter-offer that considers the carrier's offer.
        
        Strategy:
        - Round 1: Try for 98% of listed rate, but not less than carrier offer + 5%
        - Round 2: Try for 96% of listed rate, but not less than carrier offer + 3%
        - Round 3: Meet halfway between carrier offer and our minimum acceptable
        
        Args:
            listed_rate: Original listed rate
            carrier_offer: Carrier's current offer
            round_number: Current round
            floor_rate: Our minimum acceptable rate
            
        Returns:
            Counter offer amount rounded to nearest $10
        """
        if round_number == 1:
            # First round: aim high but be reasonable
            ideal_counter = listed_rate * 0.98
            min_counter = carrier_offer * 1.05  # At least 5% above their offer
            
        elif round_number == 2:
            # Second round: show flexibility
            ideal_counter = listed_rate * 0.96
            min_counter = carrier_offer * 1.03  # At least 3% above their offer
            
        else:
            # Final rounds: meet halfway if possible
            if carrier_offer >= floor_rate:
                # Meet halfway between their offer and our target
                ideal_counter = (carrier_offer + listed_rate * 0.95) / 2
            else:
                ideal_counter = floor_rate
            min_counter = carrier_offer * 1.01  # Small increment
        
        # Choose the higher of ideal counter or minimum counter
        counter = max(ideal_counter, min_counter)
        
        # But never go below our floor rate
        counter = max(counter, floor_rate)
        
        # And never exceed the listed rate
        counter = min(counter, listed_rate)
        
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
        acceptance_threshold = listed_rate * self.acceptance_threshold
        
        return {
            "listed_rate": listed_rate,
            "target_rate": target_rate,
            "floor_rate": floor_rate,
            "acceptance_threshold": acceptance_threshold,
            "max_rounds": self.max_rounds,
            "policy": {
                "target_multiplier": self.target_multiplier,
                "floor_multiplier": self.floor_multiplier,
                "acceptance_threshold_multiplier": self.acceptance_threshold,
                "strategy": "Intelligent negotiation with carrier-aware counter-offers",
                "description": "Accept >= 95% immediately, never counter below carrier offer, meet halfway in final rounds"
            }
        }