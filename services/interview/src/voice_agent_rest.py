import os
import asyncio
from typing import Callable, Optional, Tuple
import numpy as np
from fastrtc import Stream, AudioHandler
from langchain.chat_models import init_chat_model
import httpx
import json
import re
from datetime import datetime

from .models import InterviewSession


class InterviewHandler(AudioHandler):
    """Audio handler for interview conversations using FastRTC"""
    
    def __init__(self, session: InterviewSession, on_interest_detected: Optional[Callable] = None):
        super().__init__()
        self.session = session
        self.on_interest_detected = on_interest_detected
        
        # Initialize models
        self.llm_model = init_chat_model("openai:gpt-4.1-nano-2025-04-14")
        
        # Interview context and prompts
        self.system_prompt = """You are a friendly interview assistant helping to learn about a student's interests and hobbies.
        Your goal is to have a natural conversation and discover:
        1. What interests and hobbies they have
        2. What they enjoy most about each interest
        3. How these interests might relate to their learning goals
        
        Be conversational, ask follow-up questions, and show genuine interest in their responses.
        When you identify a clear interest or hobby, mark it with [INTEREST: name] in your response.
        Keep responses concise and natural for voice conversation."""
        
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # HTTP client for updating transcript
        self.http_client = httpx.AsyncClient()
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8080")
    
    async def process(self, audio: Tuple[int, np.ndarray]) -> np.ndarray:
        """Process incoming audio and generate response"""
        try:
            # Get STT and TTS models from stream
            stt_model = self.stream.stt_model
            tts_model = self.stream.tts_model
            
            # Convert audio to text
            user_text = stt_model.stt(audio)
            
            # Update transcript via REST API
            await self._update_transcript("user_transcript", user_text)
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_text
            })
            
            # Get LLM response
            response = await self.llm_model.ainvoke(self.conversation_history)
            response_text = response.content
            
            # Check for interests in the response
            interests = self._extract_interests(response_text)
            for interest in interests:
                if self.on_interest_detected:
                    await self.on_interest_detected(interest)
                
                # Send interest detection via REST
                await self._update_transcript("interest_detected", interest=interest)
            
            # Clean response for TTS
            clean_response = self._clean_response_for_tts(response_text)
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            # Update assistant transcript
            await self._update_transcript("assistant_transcript", clean_response)
            
            # Generate TTS audio
            audio_chunks = []
            for audio_chunk in tts_model.stream_tts_sync(clean_response):
                audio_chunks.append(audio_chunk)
            
            # Combine and return audio
            if audio_chunks:
                return np.concatenate(audio_chunks)
            else:
                return np.array([], dtype=np.float32)
                
        except Exception as e:
            print(f"Error processing audio: {e}")
            # Return silence on error
            return np.zeros(16000, dtype=np.float32)  # 1 second of silence
    
    async def _update_transcript(self, transcript_type: str, text: str = None, interest: str = None):
        """Update transcript via REST API"""
        try:
            data = {"type": transcript_type}
            if text:
                data["text"] = text
            if interest:
                data["interest"] = interest
            
            await self.http_client.post(
                f"{self.api_base_url}/api/interview/{self.session.session_id}/transcript",
                json=data
            )
        except Exception as e:
            print(f"Error updating transcript: {e}")
    
    def _extract_interests(self, text: str) -> list[str]:
        """Extract interests marked with [INTEREST: name] from text"""
        interests = []
        pattern = r'\[INTEREST:\s*([^\]]+)\]'
        matches = re.findall(pattern, text)
        
        for match in matches:
            interest = match.strip()
            if interest:
                interests.append(interest)
        
        return interests
    
    def _clean_response_for_tts(self, text: str) -> str:
        """Remove markers and clean text for TTS"""
        # Remove [INTEREST: ...] markers
        text = re.sub(r'\[INTEREST:[^\]]+\]', '', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()


class VoiceAgent:
    def __init__(self):
        """Initialize the voice agent with STT, TTS, and LLM models"""
        # Models are initialized within the Stream
        pass
    
    def create_interview_stream(self, session: InterviewSession, on_interest_detected: Optional[Callable] = None) -> Stream:
        """Create a FastRTC stream for the interview session"""
        
        # Create the interview handler
        handler = InterviewHandler(session, on_interest_detected)
        
        # Get TURN credentials
        turn_server = os.getenv("TURN_SERVER", "turn.spool.education")
        
        # Create and configure the stream
        stream = Stream(
            handler=handler,
            modality="audio",
            mode="duplex",
            stt_model="moonshine-tiny",
            tts_model="kokoro-tiny",
            api_key=os.getenv("OPENAI_API_KEY"),
            rtc_configuration={
                "iceServers": [
                    {"urls": ["stun:stun.l.google.com:19302"]},
                    {
                        "urls": [f"turn:{turn_server}:3478"],
                        "username": "dynamic",  # Will be replaced by frontend with time-limited credentials
                        "credential": "dynamic"
                    }
                ]
            }
        )
        
        return stream