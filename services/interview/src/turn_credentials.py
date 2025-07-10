"""
TURN server credential generator for WebRTC
Generates time-limited credentials using HMAC-SHA1
"""

import os
import time
import hmac
import hashlib
import base64
from typing import Dict, List, Any
from datetime import datetime, timedelta


class TurnCredentialGenerator:
    """Generate time-limited TURN server credentials"""
    
    def __init__(
        self,
        turn_secret: str = None,
        turn_server_ip: str = None,
        default_ttl: int = 86400  # 24 hours
    ):
        self.turn_secret = turn_secret or os.getenv(
            'TURN_STATIC_AUTH_SECRET',
            'spool-turn-secret-key-change-in-production'
        )
        self.turn_server_ip = turn_server_ip or os.getenv('TURN_SERVER_IP', 'localhost')
        self.default_ttl = default_ttl
        
        # Warn if using default secret
        if self.turn_secret == 'spool-turn-secret-key-change-in-production':
            import warnings
            warnings.warn(
                "Using default TURN secret. Change TURN_STATIC_AUTH_SECRET in production!",
                UserWarning
            )
    
    def generate_credentials(self, username: str, ttl: int = None) -> Dict[str, Any]:
        """
        Generate time-limited TURN credentials
        
        Args:
            username: Base username for the credential
            ttl: Time to live in seconds (default: 24 hours)
            
        Returns:
            Dictionary containing ICE servers configuration
        """
        ttl = ttl or self.default_ttl
        
        # Calculate expiry timestamp
        timestamp = int(time.time()) + ttl
        
        # Create username with timestamp
        turn_username = f"{timestamp}:{username}"
        
        # Generate password using HMAC-SHA1
        password = base64.b64encode(
            hmac.new(
                self.turn_secret.encode('utf-8'),
                turn_username.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode('utf-8')
        
        # Return ICE servers configuration
        return {
            "iceServers": [
                {
                    "urls": f"stun:{self.turn_server_ip}:3478"
                },
                {
                    "urls": [
                        f"turn:{self.turn_server_ip}:3478?transport=udp",
                        f"turn:{self.turn_server_ip}:3478?transport=tcp",
                        f"turns:{self.turn_server_ip}:5349?transport=tcp"
                    ],
                    "username": turn_username,
                    "credential": password
                }
            ],
            "validUntil": datetime.fromtimestamp(timestamp).isoformat()
        }
    
    def generate_credentials_for_session(
        self,
        session_id: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate credentials for a specific session
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            
        Returns:
            Dictionary containing ICE servers configuration
        """
        # Create a unique username combining session and user
        username = f"{session_id}"
        if user_id:
            username = f"{user_id}_{session_id}"
        
        return self.generate_credentials(username)
    
    def validate_credentials(self, username: str, password: str) -> bool:
        """
        Validate TURN credentials (for testing)
        
        Args:
            username: TURN username with timestamp
            password: Base64 encoded password
            
        Returns:
            True if credentials are valid and not expired
        """
        try:
            # Extract timestamp from username
            timestamp_str, _ = username.split(':', 1)
            timestamp = int(timestamp_str)
            
            # Check if expired
            if timestamp < time.time():
                return False
            
            # Regenerate password
            expected_password = base64.b64encode(
                hmac.new(
                    self.turn_secret.encode('utf-8'),
                    username.encode('utf-8'),
                    hashlib.sha1
                ).digest()
            ).decode('utf-8')
            
            return password == expected_password
            
        except (ValueError, IndexError):
            return False


# Singleton instance
_credential_generator = None


def get_turn_credentials(username: str = None, session_id: str = None) -> Dict[str, Any]:
    """
    Get TURN credentials for WebRTC connection
    
    Args:
        username: Optional username
        session_id: Optional session ID
        
    Returns:
        ICE servers configuration with TURN credentials
    """
    global _credential_generator
    
    if _credential_generator is None:
        _credential_generator = TurnCredentialGenerator()
    
    if session_id:
        return _credential_generator.generate_credentials_for_session(
            session_id=session_id,
            user_id=username
        )
    else:
        username = username or f"user_{int(time.time())}"
        return _credential_generator.generate_credentials(username)


# Example usage
if __name__ == "__main__":
    import json
    import sys
    
    # CLI usage
    if len(sys.argv) > 1:
        username = sys.argv[1]
        ttl = int(sys.argv[2]) if len(sys.argv) > 2 else 86400
        
        generator = TurnCredentialGenerator()
        credentials = generator.generate_credentials(username, ttl)
        
        print("\nGenerated TURN Credentials:")
        print("==========================")
        print(json.dumps(credentials, indent=2))
        print(f"\nNote: These credentials will expire at: {credentials['validUntil']}")
    else:
        # Test the generator
        generator = TurnCredentialGenerator()
        
        # Generate credentials
        creds = generator.generate_credentials("alice")
        print("Test credentials:", json.dumps(creds, indent=2))
        
        # Validate credentials
        ice_server = creds["iceServers"][1]
        is_valid = generator.validate_credentials(
            ice_server["username"],
            ice_server["credential"]
        )
        print(f"\nCredentials valid: {is_valid}")