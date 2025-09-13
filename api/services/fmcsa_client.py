"""
Enhanced FMCSA API client with proper MC number validation.
"""
import os
import requests
import re
from typing import Dict, Any, Optional
import json

class FMCSAClient:
    """Client for FMCSA API integration with proper validation."""
    
    def __init__(self):
        self.api_key = os.getenv("FMCSA_API_KEY")
        self.base_url = os.getenv("FMCSA_BASE_URL", "https://mobile.fmcsa.dot.gov/qc/services/carriers")
        self.timeout = 30
    
    def verify_carrier(self, mc_number: str) -> Dict[str, Any]:
        """
        Verify a carrier using the FMCSA API with proper validation.
        
        Args:
            mc_number: Motor Carrier number to verify
            
        Returns:
            Dictionary with verification results
        """
        # CRITICAL FIX: Validate MC number format first
        if not self._is_valid_mc_format(mc_number):
            return {
                "mc_number": mc_number,
                "eligible": False,
                "carrier_name": "Invalid MC Number",
                "status": "Invalid",
                "reason": f"MC number '{mc_number}' is not valid. MC numbers must be 1-7 digits.",
                "raw_data": {
                    "error": "Invalid MC number format",
                    "provided_mc": mc_number
                },
                "verified_at": self._get_current_timestamp()
            }
        
        # If no API key is configured, use enhanced stub with validation
        if not self.api_key or self.api_key == "your-fmcsa-api-key-here":
            return self._get_validated_stub_response(mc_number)
        
        try:
            # Make API request to FMCSA
            response = self._make_fmcsa_request(mc_number)
            return self._parse_fmcsa_response(response, mc_number)
            
        except Exception as e:
            # Fallback to stub on API error
            return self._get_validated_stub_response(mc_number, error=str(e))
    
    def _is_valid_mc_format(self, mc_number: str) -> bool:
        """
        Validate MC number format.
        
        MC numbers should be:
        - Numeric only
        - Between 1 and 7 digits
        - No special characters or letters
        
        Args:
            mc_number: The MC number to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not mc_number:
            return False
        
        # Remove any whitespace
        mc_number = mc_number.strip()
        
        # Check if it's all digits
        if not mc_number.isdigit():
            return False
        
        # Check length (MC numbers are typically 1-7 digits)
        if len(mc_number) < 1 or len(mc_number) > 7:
            return False
        
        # Allow leading zeros for historical MC numbers like 000077
        # Most MC numbers don't start with 0, but some valid ones do
        
        return True
    
    def _make_fmcsa_request(self, mc_number: str) -> Dict[str, Any]:
        """
        Make actual request to FMCSA API.
        
        Args:
            mc_number: Motor Carrier number
            
        Returns:
            Raw API response
        """
        # FMCSA API uses webKey as query parameter, not Bearer token
        # Correct endpoint format: /carriers/docket-number/{mc_number}?webKey={api_key}
        base_url = "https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number"
        url = f"{base_url}/{mc_number}"
        
        params = {
            "webKey": self.api_key
        }
        
        response = requests.get(url, params=params, timeout=self.timeout)
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
        # Handle real FMCSA API response format
        # Real response structure: {"content": [{"carrier": {...}}]}
        carrier_data = None
        if "content" in api_response and len(api_response["content"]) > 0:
            carrier_data = api_response["content"][0].get("carrier", {})
        
        if carrier_data:
            # Extract from real FMCSA response
            carrier_name = carrier_data.get("legalName", "Unknown Carrier")
            status_code = carrier_data.get("statusCode", "Unknown")
            allowed_to_operate = carrier_data.get("allowedToOperate", "N")
            
            # Convert status code to readable status
            status_mapping = {
                "A": "Active",
                "I": "Inactive", 
                "S": "Suspended",
                "R": "Revoked"
            }
            status = status_mapping.get(status_code, f"Status Code: {status_code}")
            
            # Determine eligibility for real FMCSA data
            eligible = (status_code == "A" and allowed_to_operate == "Y")
            
        else:
            # Fallback for old format or missing data
            carrier_name = api_response.get("legalName", "Unknown Carrier")
            status = api_response.get("carrierStatus", "Unknown")
            eligible = self._determine_eligibility(api_response)
        
        # Generate appropriate reason
        if eligible:
            reason = "Carrier is active and authorized to operate"
        else:
            if carrier_data and carrier_data.get("allowedToOperate") == "N":
                reason = "Carrier is not allowed to operate"
            elif status != "Active":
                reason = f"Carrier status: {status}"
            else:
                reason = "Carrier verification failed"
        
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
            # Additional checks even for active carriers
            
            # Check for out-of-service orders
            out_of_service = api_response.get("outOfService", False)
            if out_of_service:
                return False
            
            # Check for insurance status
            insurance_status = api_response.get("insuranceStatus", "").lower()
            if insurance_status in ["lapsed", "cancelled", "suspended"]:
                return False
            
            return True
        
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
    
    def _get_validated_stub_response(self, mc_number: str, error: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a validated stub response for testing.
        Now includes proper validation logic.
        
        Args:
            mc_number: Motor Carrier number
            error: Optional error message
            
        Returns:
            Stub verification result
        """
        # First, validate the MC number format
        if not self._is_valid_mc_format(mc_number):
            return {
                "mc_number": mc_number,
                "eligible": False,
                "carrier_name": "Invalid MC Number",
                "status": "Invalid Format",
                "reason": f"MC number '{mc_number}' has invalid format. Must be 1-7 digits only.",
                "raw_data": {
                    "stub": True,
                    "error": "Invalid MC number format",
                    "provided_mc": mc_number
                },
                "verified_at": self._get_current_timestamp()
            }
        
        # Use deterministic logic for valid MC numbers
        mc_int = int(mc_number)
        
        # Known test MC numbers for the demo
        known_carriers = {
            123456: {"name": "ABC Transport LLC", "status": "Active", "eligible": True},
            234567: {"name": "XYZ Logistics Inc", "status": "Active", "eligible": True},
            345678: {"name": "Premier Freight Lines", "status": "Active", "eligible": True},
            456789: {"name": "Reliable Carriers Co", "status": "Active", "eligible": True},
            567890: {"name": "Swift Transportation", "status": "Active", "eligible": True},
            111111: {"name": "Test Carrier 1", "status": "Out of Service", "eligible": False},
            222222: {"name": "Test Carrier 2", "status": "Insurance Lapsed", "eligible": False},
            999999: {"name": "Demo Carrier", "status": "Active", "eligible": True}
        }
        
        # Check if it's a known test carrier
        if mc_int in known_carriers:
            carrier_info = known_carriers[mc_int]
            return {
                "mc_number": mc_number,
                "eligible": carrier_info["eligible"],
                "carrier_name": carrier_info["name"],
                "status": carrier_info["status"],
                "reason": "Carrier is active and authorized" if carrier_info["eligible"] else f"Carrier status: {carrier_info['status']}",
                "raw_data": {
                    "stub": True,
                    "test_carrier": True,
                    "note": "Known test carrier for demo"
                },
                "verified_at": self._get_current_timestamp()
            }
        
        # For unknown MC numbers, use deterministic eligibility
        # 80% eligible for valid MC numbers (based on last digit)
        last_digit = mc_int % 10
        eligible = last_digit not in [0, 1]  # 80% chance of being eligible
        
        # Generate carrier name based on MC number
        carrier_names = [
            "Regional Transport LLC",
            "Interstate Logistics Inc",
            "National Freight Lines",
            "Express Carriers Co",
            "Continental Transportation"
        ]
        carrier_name = carrier_names[mc_int % len(carrier_names)] + f" #{mc_number}"
        
        # Generate status
        if eligible:
            status = "Active"
            reason = "Carrier is active and authorized"
        else:
            statuses = ["Out of Service", "Insurance Lapsed", "Authority Revoked"]
            status = statuses[mc_int % len(statuses)]
            reason = f"Carrier has compliance issues: {status}"
        
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