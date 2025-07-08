import os
import asyncio
from typing import Callable, Optional
import numpy as np
from fastrtc import Stream, ReplyOnPause, get_stt_model, get_tts_model
from langchain.chat_models import init_chat_model
from fastapi import WebSocket
import json

from .models import InterviewSession


class VoiceAgent:
    def __init__(self):
        """Initialize the voice agent with STT, TTS, and LLM models"""
        self.stt_model = get_stt_model()  # Moonshine
        self.tts_model = get_tts_model()  # Kokoro
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
        
        self.conversation_history = []
    
    async def handle_interview_session(
        self,
        websocket: WebSocket,
        session: InterviewSession,
        on_interest_detected: Optional[Callable] = None
    ):
        """Handle a complete interview session via WebSocket"""
        
        # Initialize the conversation
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Create the stream handler
        async def process_audio(audio: tuple[int, np.ndarray]):
            """Process incoming audio and generate response"""
            try:
                # Convert audio to text
                user_text = self.stt_model.stt(audio)
                
                # Add to transcript
                session.transcript.append({
                    "speaker": "user",
                    "text": user_text,
                    "timestamp": asyncio.get_event_loop().time()
                })
                
                # Send transcription to frontend
                await websocket.send_json({
                    "type": "user_transcript",
                    "text": user_text
                })
                
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
                    if on_interest_detected:
                        await on_interest_detected(interest)
                    
                    # Send interest detection to frontend
                    await websocket.send_json({
                        "type": "interest_detected",
                        "interest": interest
                    })
                
                # Clean response for TTS
                clean_response = self._clean_response_for_tts(response_text)
                
                # Add to conversation history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text
                })
                
                # Add to transcript
                session.transcript.append({
                    "speaker": "assistant",
                    "text": clean_response,
                    "timestamp": asyncio.get_event_loop().time()
                })
                
                # Send assistant response to frontend
                await websocket.send_json({
                    "type": "assistant_transcript",
                    "text": clean_response
                })
                
                # Generate TTS audio
                audio_chunks = []
                for audio_chunk in self.tts_model.stream_tts_sync(clean_response):
                    audio_chunks.append(audio_chunk)
                
                # Combine and send audio
                if audio_chunks:
                    combined_audio = np.concatenate(audio_chunks)
                    await websocket.send_bytes(combined_audio.tobytes())
                
            except Exception as e:
                print(f"Error processing audio: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
        
        # Set up the RTC stream
        stream = Stream(
            handler=ReplyOnPause(process_audio),
            modality="audio",
            mode="send-receive",
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
            }
        )
        
        # Handle WebSocket messages
        try:
            while True:
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Handle audio data
                        audio_data = np.frombuffer(message["bytes"], dtype=np.int16)
                        await process_audio((16000, audio_data))  # Assuming 16kHz sample rate
                    elif "text" in message:
                        # Handle control messages
                        data = json.loads(message["text"])
                        if data.get("type") == "end_interview":
                            break
                        elif data.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                
                elif message["type"] == "websocket.disconnect":
                    break
                    
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            # Clean up
            pass
    
    def _extract_interests(self, text: str) -> list[str]:
        """Extract interests marked with [INTEREST: name] from text"""
        interests = []
        import re
        
        pattern = r'\[INTEREST:\s*([^\]]+)\]'
        matches = re.findall(pattern, text)
        
        for match in matches:
            interest = match.strip()
            if interest:
                interests.append(interest)
        
        return interests
    
    def _clean_response_for_tts(self, text: str) -> str:
        """Remove markers and clean text for TTS"""
        import re
        
        # Remove [INTEREST: ...] markers
        text = re.sub(r'\[INTEREST:[^\]]+\]', '', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip() 