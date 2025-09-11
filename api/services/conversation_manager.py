# api/services/conversation_manager.py
"""
Conversation state manager for HappyRobot agent integration.
Handles the flow: MC verification → Load search → Negotiation → Transfer
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
from sqlalchemy.orm import Session
from api.services.fmcsa_client import FMCSAClient
from api.services.loads_search import LoadSearchService
from api.services.negotiation_policy import NegotiationPolicy
from api.schemas import LoadSearchRequest

class ConversationState(Enum):
    GREETING = "greeting"
    MC_COLLECTION = "mc_collection"
    MC_VERIFICATION = "mc_verification"
    LOAD_SEARCH = "load_search"
    LOAD_PRESENTATION = "load_presentation"
    NEGOTIATION = "negotiation"
    AGREEMENT = "agreement"
    TRANSFER = "transfer"
    COMPLETE = "complete"
    FAILED = "failed"

class ConversationManager:
    """Manages conversation state and flow for carrier calls."""
    
    def __init__(self, db: Session):
        self.db = db
        self.fmcsa_client = FMCSAClient()
        self.load_service = LoadSearchService(db)
        self.negotiation_policy = NegotiationPolicy()
        
        # Simple file-based conversation storage for the assessment
        self.conversations_file = Path("conversations.json")
        self._load_conversations()
    
    def _load_conversations(self):
        """Load conversations from file."""
        try:
            if self.conversations_file.exists():
                with open(self.conversations_file, 'r') as f:
                    data = json.load(f)
                    # Convert state strings back to enum values
                    for call_id, conversation in data.items():
                        if isinstance(conversation.get("state"), str):
                            try:
                                conversation["state"] = ConversationState(conversation["state"])
                            except ValueError:
                                conversation["state"] = ConversationState.GREETING
                    self.conversations = data
            else:
                self.conversations = {}
        except Exception as e:
            print(f"Error loading conversations: {e}")
            self.conversations = {}
    
    def _save_conversations(self):
        """Save conversations to file."""
        try:
            # Convert enum values to strings for JSON serialization
            data_to_save = {}
            for call_id, conversation in self.conversations.items():
                conv_copy = conversation.copy()
                if hasattr(conv_copy.get("state"), 'value'):
                    conv_copy["state"] = conv_copy["state"].value
                data_to_save[call_id] = conv_copy
            
            with open(self.conversations_file, 'w') as f:
                json.dump(data_to_save, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving conversations: {e}")
    
    def start_conversation(self, call_id: str) -> Dict[str, Any]:
        """Initialize a new conversation."""
        self.conversations[call_id] = {
            "call_id": call_id,
            "state": ConversationState.GREETING,
            "data": {},
            "negotiation_rounds": 0,
            "created_at": self._get_timestamp()
        }
        self._save_conversations()
        
        return {
            "call_id": call_id,
            "state": ConversationState.GREETING.value,
            "message": "Hello! Thank you for calling. I'm here to help you find loads. May I please get your MC number?",
            "next_action": "collect_mc"
        }
    
    def process_mc_number(self, call_id: str, mc_number: str) -> Dict[str, Any]:
        """Process MC number verification."""
        conversation = self.conversations.get(call_id)
        if not conversation:
            # Auto-initialize if conversation doesn't exist
            self.start_conversation(call_id)
            conversation = self.conversations[call_id]
        
        # Verify with FMCSA
        verification = self.fmcsa_client.verify_carrier(mc_number)
        
        conversation["data"]["mc_number"] = mc_number
        conversation["data"]["fmcsa_verification"] = verification
        
        if verification["eligible"]:
            conversation["state"] = ConversationState.LOAD_SEARCH
            conversation["data"]["carrier_name"] = verification["carrier_name"]
            self._save_conversations()
            
            return {
                "call_id": call_id,
                "state": ConversationState.LOAD_SEARCH.value,
                "verified": True,
                "carrier_name": verification["carrier_name"],
                "message": f"Great! I've verified {verification['carrier_name']}. What type of equipment do you have and where are you looking to go?",
                "next_action": "collect_equipment_and_location"
            }
        else:
            conversation["state"] = ConversationState.FAILED
            self._save_conversations()
            return {
                "call_id": call_id,
                "state": ConversationState.FAILED.value,
                "verified": False,
                "reason": verification["reason"],
                "message": f"I'm sorry, but I'm unable to work with your carrier at this time. {verification['reason']}",
                "next_action": "end_call"
            }
    
    def search_and_present_loads(self, call_id: str, equipment_type: str, 
                                origin: str = None, destination: str = None) -> Dict[str, Any]:
        """Search for loads and present the best match."""
        conversation = self.conversations.get(call_id)
        if not conversation:
            # Auto-initialize if conversation doesn't exist
            self.start_conversation(call_id)
            conversation = self.conversations[call_id]
        
        # Search for loads
        search_request = LoadSearchRequest(
            equipment_type=equipment_type,
            origin_state=origin,
            destination_state=destination,
            limit=5
        )
        
        search_results = self.load_service.search_loads(search_request)
        loads = search_results["loads"]
        
        if not loads:
            conversation["state"] = ConversationState.FAILED
            self._save_conversations()
            return {
                "call_id": call_id,
                "state": ConversationState.FAILED.value,
                "message": "I don't have any matching loads available right now. Let me transfer you to our load planning team.",
                "next_action": "transfer_to_planning"
            }
        
        # Present the best load
        best_load = loads[0]
        conversation["data"]["presented_load"] = best_load
        conversation["data"]["equipment_type"] = equipment_type
        conversation["state"] = ConversationState.LOAD_PRESENTATION
        self._save_conversations()
        
        return {
            "call_id": call_id,
            "state": ConversationState.LOAD_PRESENTATION.value,
            "load": best_load,
            "message": self._format_load_presentation(best_load),
            "next_action": "await_response"
        }
    
    def handle_negotiation(self, call_id: str, carrier_offer: float) -> Dict[str, Any]:
        """Handle negotiation round."""
        conversation = self.conversations.get(call_id)
        if not conversation:
            return {"error": "Conversation not found"}
        
        # Check if load was presented
        presented_load = conversation["data"].get("presented_load")
        if not presented_load:
            return {
                "call_id": call_id,
                "state": ConversationState.FAILED.value,
                "outcome": "error",
                "message": "Please search for a load first before negotiating.",
                "next_action": "search_loads"
            }
        
        listed_rate = presented_load["total_rate"]
        
        conversation["negotiation_rounds"] += 1
        round_number = conversation["negotiation_rounds"]
        
        # Evaluate offer
        evaluation = self.negotiation_policy.evaluate_offer(
            listed_rate=listed_rate,
            offer=carrier_offer,
            round_number=round_number
        )
        
        conversation["data"]["last_offer"] = carrier_offer
        conversation["data"]["negotiation_history"] = conversation["data"].get("negotiation_history", [])
        conversation["data"]["negotiation_history"].append({
            "round": round_number,
            "carrier_offer": carrier_offer,
            "evaluation": evaluation
        })
        
        if evaluation["outcome"] == "accept":
            conversation["state"] = ConversationState.AGREEMENT
            conversation["data"]["final_rate"] = carrier_offer
            self._save_conversations()
            
            return {
                "call_id": call_id,
                "state": ConversationState.AGREEMENT.value,
                "outcome": "accepted",
                "final_rate": carrier_offer,
                "message": f"Excellent! I can accept your offer of ${carrier_offer:,.2f}. Let me transfer you to our sales team to finalize the paperwork.",
                "next_action": "transfer_to_sales"
            }
        
        elif evaluation["outcome"] == "counter":
            conversation["state"] = ConversationState.NEGOTIATION
            counter_offer = evaluation["counter_offer"]
            self._save_conversations()
            
            return {
                "call_id": call_id,
                "state": ConversationState.NEGOTIATION.value,
                "outcome": "counter",
                "counter_offer": counter_offer,
                "round": round_number,
                "max_rounds": evaluation["max_rounds"],
                "message": f"I can offer ${counter_offer:,.2f}. What do you think?",
                "next_action": "await_counter_response"
            }
        
        else:  # reject or max_rounds_reached
            conversation["state"] = ConversationState.FAILED
            self._save_conversations()
            
            return {
                "call_id": call_id,
                "state": ConversationState.FAILED.value,
                "outcome": "rejected",
                "reason": evaluation["message"],
                "message": f"I understand, but I can't go higher than that. {evaluation['message']}. Thank you for your time.",
                "next_action": "end_call"
            }
    
    def get_conversation_summary(self, call_id: str) -> Dict[str, Any]:
        """Get comprehensive conversation data for persistence."""
        conversation = self.conversations.get(call_id)
        if not conversation:
            return {"error": "Conversation not found"}
        
        data = conversation["data"]
        
        return {
            "call_id": call_id,
            "final_state": conversation["state"].value if hasattr(conversation["state"], 'value') else str(conversation["state"]),
            "mc_number": data.get("mc_number"),
            "carrier_name": data.get("carrier_name"),
            "fmcsa_status": data.get("fmcsa_verification", {}).get("status"),
            "equipment_type": data.get("equipment_type"),
            "presented_load": data.get("presented_load"),
            "negotiation_rounds": conversation["negotiation_rounds"],
            "final_rate": data.get("final_rate"),
            "last_offer": data.get("last_offer"),
            "negotiation_history": data.get("negotiation_history", []),
            "outcome": self._determine_outcome(conversation),
            "sentiment": self._analyze_sentiment(conversation),
            "extracted_data": self._extract_structured_data(conversation)
        }
    
    def _format_load_presentation(self, load: Dict[str, Any]) -> str:
        """Format load details for presentation."""
        return (
            f"I found a great load for you! {load['commodity']} from {load['origin_city']}, {load['origin_state']} "
            f"to {load['destination_city']}, {load['destination_state']}. "
            f"Pickup {load['pickup_date'][:10]}, delivery {load['delivery_date'][:10]}. "
            f"{load['miles']:.0f} miles, {load['weight']:,.0f} pounds. "
            f"We're offering ${load['total_rate']:,.2f} total. Are you interested?"
        )
    
    def _determine_outcome(self, conversation: Dict[str, Any]) -> str:
        """Determine final call outcome."""
        state = conversation["state"]
        if state == ConversationState.AGREEMENT:
            return "accepted"
        elif state == ConversationState.FAILED:
            return "rejected"
        elif state == ConversationState.TRANSFER:
            return "transferred"
        else:
            return "incomplete"
    
    def _analyze_sentiment(self, conversation: Dict[str, Any]) -> str:
        """Analyze conversation sentiment (simplified)."""
        # Simplified sentiment analysis based on outcome
        outcome = self._determine_outcome(conversation)
        if outcome == "accepted":
            return "positive"
        elif outcome == "rejected":
            return "negative"
        else:
            return "neutral"
    
    def _extract_structured_data(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data for reporting."""
        data = conversation["data"]
        return {
            "equipment_type": data.get("equipment_type"),
            "origin_preference": data.get("origin_preference"),
            "destination_preference": data.get("destination_preference"),
            "rate_sensitivity": self._calculate_rate_sensitivity(conversation),
            "negotiation_aggressiveness": self._calculate_negotiation_aggressiveness(conversation)
        }
    
    def _calculate_rate_sensitivity(self, conversation: Dict[str, Any]) -> str:
        """Calculate how sensitive carrier is to rates."""
        rounds = conversation["negotiation_rounds"]
        if rounds == 0:
            return "unknown"
        elif rounds == 1:
            return "low"
        elif rounds <= 2:
            return "medium"
        else:
            return "high"
    
    def _calculate_negotiation_aggressiveness(self, conversation: Dict[str, Any]) -> str:
        """Calculate negotiation aggressiveness."""
        history = conversation["data"].get("negotiation_history", [])
        if not history:
            return "unknown"
        
        # Analyze gap between offers and listed rate
        first_offer = history[0]["carrier_offer"]
        presented_load = conversation["data"].get("presented_load")
        if not presented_load:
            return "unknown"
            
        listed_rate = presented_load["total_rate"]
        gap_percentage = (listed_rate - first_offer) / listed_rate * 100
        
        if gap_percentage > 15:
            return "aggressive"
        elif gap_percentage > 5:
            return "moderate"
        else:
            return "conservative"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"