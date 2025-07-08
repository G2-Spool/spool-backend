import os
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
import httpx
from datetime import datetime

from .voice_agent import VoiceAgent
from .langflow_client import LangflowClient
from .models import InterviewSession, InterestData

app = FastAPI(title="Spool Interview Service")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
langflow_client = LangflowClient()
voice_agent = VoiceAgent()

# Store active sessions
active_sessions: Dict[str, InterviewSession] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Check Langflow health
    if not await langflow_client.health_check():
        print("Warning: Langflow service is not responding")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    langflow_healthy = await langflow_client.health_check()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "interview": "healthy",
            "langflow": "healthy" if langflow_healthy else "unhealthy"
        }
    }


@app.post("/api/interview/start")
async def start_interview(user_id: str):
    """Start a new interview session"""
    session_id = f"interview_{user_id}_{datetime.utcnow().timestamp()}"
    
    session = InterviewSession(
        session_id=session_id,
        user_id=user_id,
        started_at=datetime.utcnow(),
        interests=[]
    )
    
    active_sessions[session_id] = session
    
    return {
        "session_id": session_id,
        "status": "started",
        "message": "Interview session started. Connect via WebSocket to begin voice interaction."
    }


@app.websocket("/ws/interview/{session_id}")
async def websocket_interview(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for voice interview"""
    await websocket.accept()
    
    if session_id not in active_sessions:
        await websocket.send_json({
            "error": "Invalid session ID"
        })
        await websocket.close()
        return
    
    session = active_sessions[session_id]
    
    try:
        # Send initial greeting
        await websocket.send_json({
            "type": "greeting",
            "message": "Hi! I'm here to learn about your interests and hobbies. Let's have a conversation about what you enjoy doing!"
        })
        
        # Handle voice interaction
        await voice_agent.handle_interview_session(
            websocket=websocket,
            session=session,
            on_interest_detected=lambda interest: handle_interest_detected(session, interest)
        )
        
    except WebSocketDisconnect:
        print(f"Session {session_id} disconnected")
    except Exception as e:
        print(f"Error in session {session_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        # Save session data
        await save_session_data(session)


async def handle_interest_detected(session: InterviewSession, interest: str):
    """Handle when a new interest is detected"""
    if interest not in [i.name for i in session.interests]:
        session.interests.append(InterestData(
            name=interest,
            detected_at=datetime.utcnow()
        ))
        print(f"New interest detected: {interest}")


async def save_session_data(session: InterviewSession):
    """Save session data and send to Langflow for processing"""
    try:
        # Prepare data for Langflow
        interview_data = {
            "user_id": session.user_id,
            "session_id": session.session_id,
            "interests": [
                {
                    "name": interest.name,
                    "details": interest.details,
                    "detected_at": interest.detected_at.isoformat()
                }
                for interest in session.interests
            ],
            "transcript": session.transcript,
            "duration": (datetime.utcnow() - session.started_at).total_seconds()
        }
        
        # Send to Langflow for processing
        result = await langflow_client.process_interview(interview_data)
        print(f"Interview data processed: {result}")
        
    except Exception as e:
        print(f"Error saving session data: {e}")


@app.get("/api/interview/{session_id}/results")
async def get_interview_results(session_id: str):
    """Get the results of an interview session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    return {
        "session_id": session_id,
        "user_id": session.user_id,
        "interests": [
            {
                "name": interest.name,
                "details": interest.details
            }
            for interest in session.interests
        ],
        "duration": (datetime.utcnow() - session.started_at).total_seconds()
    }


@app.post("/api/interview/{session_id}/end")
async def end_interview(session_id: str):
    """End an interview session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    session.ended_at = datetime.utcnow()
    
    # Save and process the session
    await save_session_data(session)
    
    # Remove from active sessions
    del active_sessions[session_id]
    
    return {
        "status": "completed",
        "message": "Interview session ended successfully"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 