import os
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastrtc import Stream
import numpy as np
import httpx
from datetime import datetime
import sys
import traceback
import hashlib
import hmac
import time

from .voice_agent_rest import VoiceAgent
from .langflow_client import LangflowClient
from .models import InterviewSession, InterestData

# Configure Python path
sys.path.insert(0, '/app/src')

app = FastAPI(title="Spool Interview Service - REST/FastRTC")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients with error handling
langflow_client = None
voice_agent = None

# Store active sessions and streams
active_sessions: Dict[str, InterviewSession] = {}
active_streams: Dict[str, Stream] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global langflow_client, voice_agent
    
    try:
        print("Starting up Spool Interview Service (REST/FastRTC)...")
        
        # Initialize LangFlow client
        langflow_client = LangflowClient()
        print("LangFlow client initialized")
        
        # Initialize voice agent
        voice_agent = VoiceAgent()
        print("Voice agent initialized (REST mode)")
        
        # Check Langflow health
        if langflow_client and not await langflow_client.health_check():
            print("Warning: Langflow service is not responding")
        
        print("Startup completed successfully!")
        
    except Exception as e:
        print(f"Error during startup: {e}")
        traceback.print_exc()
        # Don't raise - let the service start even if some components fail


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        langflow_healthy = False
        if langflow_client:
            try:
                langflow_healthy = await langflow_client.health_check()
            except Exception as e:
                print(f"Langflow health check failed: {e}")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "interview": "healthy",
                "langflow": "healthy" if langflow_healthy else "unhealthy",
                "voice_agent": "healthy" if voice_agent else "unhealthy"
            }
        }
    except Exception as e:
        print(f"Health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Spool Interview Service (REST/FastRTC) is running", "version": "2.0.0"}


@app.post("/api/interview/start")
async def start_interview(user_id: str):
    """Start a new interview session with REST-based FastRTC"""
    try:
        session_id = f"interview_{user_id}_{datetime.utcnow().timestamp()}"
        
        session = InterviewSession(
            session_id=session_id,
            user_id=user_id,
            started_at=datetime.utcnow(),
            interests=[]
        )
        
        active_sessions[session_id] = session
        
        # Create RTC stream for this session
        if voice_agent:
            stream = voice_agent.create_interview_stream(
                session,
                on_interest_detected=lambda interest: asyncio.create_task(handle_interest_detected(session, interest))
            )
            active_streams[session_id] = stream
            
            # Mount the stream to create REST endpoints
            # This creates: /offer, /answer, /ice-candidate endpoints
            stream.mount(app, prefix=f"/api/interview/{session_id}/rtc")
        
        return {
            "session_id": session_id,
            "status": "started",
            "message": "Interview session started. Use REST endpoints for WebRTC signaling.",
            "rtc_endpoints": {
                "offer": f"/api/interview/{session_id}/rtc/offer",
                "answer": f"/api/interview/{session_id}/rtc/answer",
                "ice_candidate": f"/api/interview/{session_id}/rtc/ice-candidate"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/interview/{session_id}/status")
async def get_interview_status(session_id: str):
    """Get the current status of an interview session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    stream_active = session_id in active_streams
    
    return {
        "session_id": session_id,
        "status": "active" if stream_active else "initialized",
        "started_at": session.started_at.isoformat(),
        "interests_detected": len(session.interests),
        "greeting": "Hi! I'm here to learn about your interests and hobbies. Let's have a conversation about what you enjoy doing!"
    }


@app.post("/api/interview/{session_id}/transcript")
async def update_transcript(session_id: str, request: Request):
    """Update transcript data for the session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    data = await request.json()
    session = active_sessions[session_id]
    
    if data.get("type") == "user_transcript":
        session.transcript.append({
            "speaker": "user",
            "text": data.get("text"),
            "timestamp": datetime.utcnow().isoformat()
        })
    elif data.get("type") == "assistant_transcript":
        session.transcript.append({
            "speaker": "assistant",
            "text": data.get("text"),
            "timestamp": datetime.utcnow().isoformat()
        })
    elif data.get("type") == "interest_detected":
        interest = data.get("interest")
        await handle_interest_detected(session, interest)
    
    return {"status": "updated"}


@app.get("/api/interview/{session_id}/ice-servers")
async def get_ice_servers(session_id: str):
    """Get ICE servers including TURN credentials"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Generate time-limited TURN credentials
    turn_secret = os.getenv("TURN_SECRET", "spool-turn-secret-2024")
    turn_server = os.getenv("TURN_SERVER", "turn.spool.education")
    
    # Create time-limited username
    expiry = int(time.time()) + 3600  # 1 hour from now
    username = f"{expiry}:spool_{session_id[:8]}"
    
    # Generate credential using HMAC-SHA1
    credential = hmac.new(
        turn_secret.encode(),
        username.encode(),
        hashlib.sha1
    ).digest().hex()
    
    return {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {
                "urls": [f"turn:{turn_server}:3478"],
                "username": username,
                "credential": credential
            }
        ]
    }


async def handle_interest_detected(session: InterviewSession, interest: str):
    """Handle when a new interest is detected"""
    try:
        if interest not in [i.name for i in session.interests]:
            session.interests.append(InterestData(
                name=interest,
                detected_at=datetime.utcnow()
            ))
            print(f"New interest detected: {interest}")
    except Exception as e:
        print(f"Error handling interest detection: {e}")


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
        
        # Send to Langflow for processing if available
        if langflow_client:
            result = await langflow_client.process_interview(interview_data)
            print(f"Interview data processed: {result}")
        else:
            print("LangFlow client not available, skipping processing")
        
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
    
    # Clean up stream if exists
    if session_id in active_streams:
        # Stream cleanup is handled by FastRTC
        del active_streams[session_id]
    
    # Remove from active sessions
    del active_sessions[session_id]
    
    return {
        "status": "completed",
        "message": "Interview session ended successfully"
    }


if __name__ == "__main__":
    import uvicorn
    print("Starting Spool Interview Service (REST/FastRTC)...")
    uvicorn.run(app, host="0.0.0.0", port=8080)