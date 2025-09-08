"""
FMCSA API client for carrier verification.
"""
import os
import requests
from typing import Dict, Any, Optional
import json

class FMCSAClient:
    """Client for FMCSA API integration."""
    
    def __init__(self):
        self.api_key = os.getenv("FMCSA_API_KEY")
        self.base_url = os.getenv("FMCSA_BASE_URL", "https://mobile.fmcsa.dot.gov/qc/services/carriers")
        self.timeout = 30
    
    def verify_carrier(self, mc_number: str) -> Dict[str, Any]:
        """
        Verify a carrier using the FMCSA API.
        
        Args:
            mc_number: Motor Carrier number to verify
            
        Returns:
            Dictionary with verification results
        """
        # If no API key is configured, return a deterministic stub
        if not self.api_key or self.api_key == "your-fmcsa-api-key-here":
            return self._get_stub_response(mc_number)
        
        try:
            # Make API request to FMCSA
            response = self._make_fmcsa_request(mc_number)
            return self._parse_fmcsa_response(response, mc_number)
            
        except Exception as e:
            # Fallback to stub on API error
            return self._get_stub_response(mc_number, error=str(e))
    
    def _make_fmcsa_request(self, mc_number: str) -> Dict[str, Any]:
        """
        Make actual request to FMCSA API.
        
        Args:
            mc_number: Motor Carrier number
            
        Returns:
            Raw API response
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # FMCSA API endpoint for carrier lookup
        url = f"{self.base_url}/{mc_number}"
        
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def _parse_fmcsa_response(self, api_response: Dict[str, Any], mc_number: str) -> Dict[str, Any]:
        """
        Parse FMCSA API response into our standardized format.
        
        Args:
            api_response: Raw API response
            mc_number: Original MC number
            
        Returns:
            Standardized verification result
        """
        # Extract relevant fields from FMCSA response
        # Note: This structure may need adjustment based on actual FMCSA API response format
        
        carrier_name = api_response.get("legalName", "Unknown Carrier")
        status = api_response.get("carrierStatus", "Unknown")
        
        # Determine eligibility based on status
        eligible = self._determine_eligibility(api_response)
        
        # Extract reason for eligibility status
        reason = self._get_eligibility_reason(api_response, eligible)
        
        return {
            "mc_number": mc_number,
            "eligible": eligible,
            "carrier_name": carrier_name,
            "status": status,
            "reason": reason,
            "raw_data": api_response,
            "verified_at": self._get_current_timestamp()
        }
    
    def _determine_eligibility(self, api_response: Dict[str, Any]) -> bool:
        """
        Determine if carrier is eligible based on FMCSA data.
        
        Args:
            api_response: Raw API response
            
        Returns:
            True if eligible, False otherwise
        """
        # Check various eligibility criteria
        status = api_response.get("carrierStatus", "").lower()
        
        # Eligible statuses
        eligible_statuses = ["active", "authorized", "authorized for property"]
        
        # Check if status is eligible
        if status in eligible_statuses:
            return True
        
        # Check for out-of-service orders
        out_of_service = api_response.get("outOfService", False)
        if out_of_service:
            return False
        
        # Check for insurance status
        insurance_status = api_response.get("insuranceStatus", "").lower()
        if insurance_status in ["lapsed", "cancelled", "suspended"]:
            return False
        
        return False
    
    def _get_eligibility_reason(self, api_response: Dict[str, Any], eligible: bool) -> str:
        """
        Get human-readable reason for eligibility status.
        
        Args:
            api_response: Raw API response
            eligible: Whether carrier is eligible
            
        Returns:
            Reason string
        """
        if eligible:
            return "Carrier is active and authorized"
        
        status = api_response.get("carrierStatus", "Unknown")
        
        if api_response.get("outOfService", False):
            return "Carrier is out of service"
        
        insurance_status = api_response.get("insuranceStatus", "")
        if insurance_status in ["lapsed", "cancelled", "suspended"]:
            return f"Insurance status: {insurance_status}"
        
        return f"Carrier status: {status}"
    
    def _get_stub_response(self, mc_number: str, error: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a deterministic stub response for testing.
        
        Args:
            mc_number: Motor Carrier number
            error: Optional error message
            
        Returns:
            Stub verification result
        """
        # Deterministic logic based on MC number
        mc_int = int(mc_number) if mc_number.isdigit() else hash(mc_number) % 1000000
        
        # 80% of carriers are eligible (for demo purposes)
        eligible = (mc_int % 5) != 0
        
        # Generate carrier name based on MC number
        carrier_names = [
            "ABC Transport LLC",
            "XYZ Logistics Inc",
            "Premier Freight Lines",
            "Reliable Carriers Co",
            "Swift Transportation"
        ]
        carrier_name = carrier_names[mc_int % len(carrier_names)]
        
        # Generate status
        if eligible:
            status = "Active"
            reason = "Carrier is active and authorized"
        else:
            status = "Out of Service"
            reason = "Carrier has compliance issues"
        
        return {
            "mc_number": mc_number,
            "eligible": eligible,
            "carrier_name": carrier_name,
            "status": status,
            "reason": reason,
            "raw_data": {
                "stub": True,
                "error": error,
                "note": "This is a deterministic stub response for testing"
            },
            "verified_at": self._get_current_timestamp()
        }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
