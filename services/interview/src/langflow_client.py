import httpx
import os
from typing import Optional, Dict, Any


class LangflowClient:
    """Client for communicating with the Langflow service"""
    
    def __init__(self):
        # Use service discovery in production
        if os.getenv("ENV") == "production":
            self.base_url = "http://langflow.spool.local:7860"
        else:
            self.base_url = os.getenv("LANGFLOW_URL", "http://localhost:7860")
        
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def health_check(self) -> bool:
        """Check if Langflow service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    async def process_interview(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send interview data to Langflow for processing"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/run",
                json={
                    "input_value": interview_data,
                    "output_type": "chat",
                    "tweaks": {}
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error processing interview in Langflow: {e}")
            return {"error": str(e)}
    
    async def create_flow(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new flow in Langflow"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/flows",
                json=flow_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating flow: {e}")
            return {"error": str(e)}
    
    async def get_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific flow by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/flows/{flow_id}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting flow: {e}")
            return None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose() 