"""
Call persistence service for saving call data.
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from api.models import Call

class CallPersistenceService:
    """Service for persisting call data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save call data to the database.
        
        Args:
            call_data: Dictionary containing call information
            
        Returns:
            Dictionary with saved call information
        """
        try:
            # Extract and validate required fields
            call_id = call_data.get("call_id")
            if not call_id:
                raise ValueError("call_id is required")
            
            # Check if call already exists
            existing_call = self.db.query(Call).filter(Call.call_id == call_id).first()
            if existing_call:
                # Update existing call
                call = existing_call
                self._update_call_fields(call, call_data)
            else:
                # Create new call
                call = Call()
                self._set_call_fields(call, call_data)
                self.db.add(call)
            
            # Commit to database
            self.db.commit()
            self.db.refresh(call)
            
            return {
                "call_id": call.call_id,
                "id": call.id,
                "status": "saved",
                "message": "Call data saved successfully"
            }
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to save call: {str(e)}")
    
    def _set_call_fields(self, call: Call, call_data: Dict[str, Any]) -> None:
        """Set fields for a new call."""
        call.call_id = call_data.get("call_id")
        call.load_id = call_data.get("load_id")
        call.carrier_mc = call_data.get("mc") or call_data.get("carrier_mc")
        call.carrier_name = call_data.get("carrier_name")
        call.fmcsa_status = call_data.get("fmcsa_status")
        call.initial_rate = call_data.get("initial_rate")
        call.current_rate = call_data.get("current_rate")
        call.listed_rate = call_data.get("listed_rate")
        call.final_rate = self._safe_float(call_data.get("final_rate"))
        call.last_offer = call_data.get("last_offer")
        call.negotiation_rounds = self._safe_int(call_data.get("negotiation_rounds"))
        call.outcome = call_data.get("outcome", "no_agreement")
        call.sentiment = call_data.get("sentiment")
        call.extracted_json = self._serialize_json(call_data.get("extracted_json"))
        call.started_at = self._parse_datetime(call_data.get("started_at"))
        call.ended_at = self._parse_datetime(call_data.get("ended_at"))
        call.call_duration_seconds = call_data.get("call_duration_seconds")
        call.notes = call_data.get("notes")
    
    def _update_call_fields(self, call: Call, call_data: Dict[str, Any]) -> None:
        """Update fields for an existing call."""
        # Only update fields that are provided
        if "load_id" in call_data:
            call.load_id = call_data["load_id"]
        if "carrier_name" in call_data:
            call.carrier_name = call_data["carrier_name"]
        if "fmcsa_status" in call_data:
            call.fmcsa_status = call_data["fmcsa_status"]
        if "initial_rate" in call_data:
            call.initial_rate = call_data["initial_rate"]
        if "current_rate" in call_data:
            call.current_rate = call_data["current_rate"]
        if "listed_rate" in call_data:
            call.listed_rate = call_data["listed_rate"]
        if "final_rate" in call_data:
            call.final_rate = call_data["final_rate"]
        if "last_offer" in call_data:
            call.last_offer = call_data["last_offer"]
        if "negotiation_rounds" in call_data:
            call.negotiation_rounds = call_data["negotiation_rounds"]
        if "outcome" in call_data:
            call.outcome = call_data["outcome"]
        if "sentiment" in call_data:
            call.sentiment = call_data["sentiment"]
        if "extracted_json" in call_data:
            call.extracted_json = self._serialize_json(call_data["extracted_json"])
        if "started_at" in call_data:
            call.started_at = self._parse_datetime(call_data["started_at"])
        if "ended_at" in call_data:
            call.ended_at = self._parse_datetime(call_data["ended_at"])
        if "call_duration_seconds" in call_data:
            call.call_duration_seconds = call_data["call_duration_seconds"]
        if "notes" in call_data:
            call.notes = call_data["notes"]
    
    def _serialize_json(self, data: Any) -> Optional[str]:
        """Serialize JSON data to string."""
        if data is None:
            return None
        if isinstance(data, str):
            return data
        return json.dumps(data)
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not date_str:
            return None
        try:
            # Handle ISO format with Z suffix
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None
    
    def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a call by ID.
        
        Args:
            call_id: Call ID to retrieve
            
        Returns:
            Call data dictionary or None if not found
        """
        call = self.db.query(Call).filter(Call.call_id == call_id).first()
        if not call:
            return None
        
        return {
            "id": call.id,
            "call_id": call.call_id,
            "load_id": call.load_id,
            "carrier_mc": call.carrier_mc,
            "carrier_name": call.carrier_name,
            "fmcsa_status": call.fmcsa_status,
            "initial_rate": call.initial_rate,
            "current_rate": call.current_rate,
            "listed_rate": call.listed_rate,
            "final_rate": call.final_rate,
            "last_offer": call.last_offer,
            "negotiation_rounds": call.negotiation_rounds,
            "outcome": call.outcome,
            "sentiment": call.sentiment,
            "extracted_json": call.extracted_json,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "call_duration_seconds": call.call_duration_seconds,
            "notes": call.notes,
            "created_at": call.created_at.isoformat(),
            "updated_at": call.updated_at.isoformat()
        }
    
    def get_calls_by_carrier(self, carrier_mc: str) -> list:
        """
        Get all calls for a specific carrier.
        
        Args:
            carrier_mc: Carrier MC number
            
        Returns:
            List of call data dictionaries
        """
        calls = self.db.query(Call).filter(Call.carrier_mc == carrier_mc).all()
        return [self.get_call(call.call_id) for call in calls if call]

    def _safe_float(self, value) -> Optional[float]:
        """Convert value to float, handling empty strings and None."""
        if value is None or value == "" or value == "null":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value) -> Optional[int]:
        """Convert value to int, handling empty strings and None."""
        if value is None or value == "" or value == "null":
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0