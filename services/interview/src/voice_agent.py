import os
import asyncio
from typing import Callable, Optional, Dict, List
import numpy as np
from fastrtc import Stream, ReplyOnPause, AudioHandler, get_stt_model, get_tts_model
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json
import httpx
from datetime import datetime

from .models import InterviewSession
from .turn_credentials import get_turn_credentials
from .langgraph_interview import InterviewGraph, InterviewState


class InterviewHandler(AudioHandler):
    """Custom audio handler for interview conversations using LangGraph"""
    
    def __init__(
        self,
        session: InterviewSession,
        stt_model,
        tts_model,
        interview_graph: InterviewGraph,
        on_interest_detected: Optional[Callable] = None,
        api_base_url: str = "http://localhost:8080"
    ):
        self.session = session
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.interview_graph = interview_graph
        self.on_interest_detected = on_interest_detected
        self.api_base_url = api_base_url
        
        # Initialize conversation history for LangGraph
        self.conversation_history: List[BaseMessage] = []
    
    async def process(self, audio: tuple[int, np.ndarray]) -> np.ndarray:
        """Process incoming audio and generate response using LangGraph"""
        try:
            # Convert audio to text using STT
            sample_rate, audio_data = audio
            user_text = self.stt_model.stt((sample_rate, audio_data))
            
            # Skip empty or very short inputs
            if not user_text or len(user_text.strip()) < 2:
                return np.array([], dtype=np.float32)
            
            # Add to transcript
            transcript_entry = {
                "speaker": "user",
                "text": user_text,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.session.transcript.append(transcript_entry)
            
            # Update transcript via API
            await self._update_transcript(transcript_entry)
            
            # Process through LangGraph
            result = await self.interview_graph.process_message(
                user_message=user_text,
                conversation_history=self.conversation_history,
                mode=self.session.metadata.get("mode"),
                user_info={
                    "user_id": self.session.user_id,
                    "session_id": self.session.session_id
                }
            )
            
            # Update conversation history
            self.conversation_history.append(HumanMessage(content=user_text))
            if result["response"]:
                self.conversation_history.append(AIMessage(content=result["response"]))
            
            # Handle detected interests
            for interest in result.get("interests", []):
                if self.on_interest_detected:
                    await self.on_interest_detected(interest["name"])
            
            # Store concepts in session metadata
            if result.get("concepts"):
                if "concepts" not in self.session.metadata:
                    self.session.metadata["concepts"] = []
                self.session.metadata["concepts"].extend(result["concepts"])
            
            # Check if we should prepare for thread creation
            if result.get("should_create_thread"):
                self.session.metadata["prepare_thread"] = True
                if result.get("thread_summary"):
                    self.session.metadata["thread_summary"] = result["thread_summary"]
            
            # Clean response for TTS
            clean_response = self._clean_response_for_tts(result["response"])
            
            # Add to transcript
            assistant_entry = {
                "speaker": "assistant",
                "text": clean_response,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.session.transcript.append(assistant_entry)
            
            # Update transcript via API
            await self._update_transcript(assistant_entry)
            
            # Generate TTS audio
            audio_chunks = []
            for audio_chunk in self.tts_model.stream_tts_sync(clean_response):
                audio_chunks.append(audio_chunk)
            
            # Combine audio chunks
            if audio_chunks:
                combined_audio = np.concatenate(audio_chunks)
                return combined_audio
            else:
                return np.array([], dtype=np.float32)
                
        except Exception as e:
            print(f"Error processing audio: {e}")
            import traceback
            traceback.print_exc()
            # Return silence on error
            return np.zeros(16000, dtype=np.float32)  # 1 second of silence
    
    def _clean_response_for_tts(self, text: str) -> str:
        """Remove markers and clean text for TTS"""
        import re
        
        if not text:
            return ""
        
        # Remove [INTEREST: ...] markers
        text = re.sub(r'\[INTEREST:[^\]]+\]', '', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    async def _update_transcript(self, entry: Dict):
        """Update transcript via REST API"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.api_base_url}/api/interview/{self.session.session_id}/transcript",
                    json={"entry": entry}
                )
        except Exception as e:
            print(f"Error updating transcript: {e}")


class VoiceAgent:
    def __init__(self):
        """Initialize the voice agent with STT, TTS, and LangGraph models"""
        self.stt_model = get_stt_model()  # Moonshine
        self.tts_model = get_tts_model()  # Kokoro
        
        # Initialize LLM for LangGraph
        self.llm_model = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14"),
            temperature=0.7
        )
        
        # Initialize LangGraph interview orchestration
        self.interview_graph = InterviewGraph(llm_model=self.llm_model)
    
    async def create_interview_stream(
        self,
        session: InterviewSession,
        on_interest_detected: Optional[Callable] = None
    ) -> Stream:
        """Create an RTC stream for the interview session"""
        
        # Create custom handler for this interview
        handler = InterviewHandler(
            session=session,
            stt_model=self.stt_model,
            tts_model=self.tts_model,
            interview_graph=self.interview_graph,
            on_interest_detected=on_interest_detected
        )
        
        # Get TURN credentials for this session
        turn_config = get_turn_credentials(
            username=session.user_id,
            session_id=session.session_id
        )
        
        # Create the stream with ReplyOnPause wrapper and TURN configuration
        stream = Stream(
            handler=ReplyOnPause(handler.process),
            modality="audio",
            mode="send-receive",
            rtc_configuration=turn_config  # This includes both STUN and TURN servers
        )
        
        return stream