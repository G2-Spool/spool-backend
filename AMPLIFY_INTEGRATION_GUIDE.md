# 🔗 Amplify Frontend Integration with REST-based FastRTC

## Overview

This guide shows how to integrate the REST-based FastRTC voice interview service with your AWS Amplify frontend application.

## 🏗️ **Architecture Overview**

```
[Amplify Frontend] --> [API Gateway] --> [ECS FastRTC Service]
                  \                   /
                   --> [TURN Server] --
```

## 📋 **Prerequisites**

1. ✅ REST-based FastRTC service deployed via CDK
2. ✅ API Gateway URL from CDK deployment
3. ✅ Amplify app with React frontend
4. ✅ TURN server deployed and accessible

## 🔧 **Step 1: Configure API Endpoints**

### Update Amplify Environment Variables

In your Amplify console, add these environment variables:

```bash
# Amplify Console > App Settings > Environment Variables
REACT_APP_INTERVIEW_API_URL=https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com
REACT_APP_TURN_SERVER=turn.spool.education
```

### Update `src/config/api.ts`

```typescript
// src/config/api.ts
export const config = {
  // Existing Amplify config...
  API: {
    endpoints: [
      {
        name: "RestApi",
        endpoint: "https://api.spool.education" // Your existing API
      },
      {
        name: "InterviewApi", // NEW: Voice interview API
        endpoint: process.env.REACT_APP_INTERVIEW_API_URL || "http://localhost:8080",
        region: "us-east-1"
      }
    ]
  }
};

// Export specific endpoints
export const INTERVIEW_API_BASE = process.env.REACT_APP_INTERVIEW_API_URL || "http://localhost:8080";
export const TURN_SERVER = process.env.REACT_APP_TURN_SERVER || "turn.spool.education";
```

## 🎤 **Step 2: Install Required Dependencies**

Add WebRTC and audio processing dependencies:

```bash
npm install --save \
  @types/webrtc \
  recordrtc \
  audio-recorder-polyfill \
  uuid
```

## 🔧 **Step 3: Create Voice Interview Service**

### `src/services/voiceInterview.service.ts`

```typescript
import { API } from 'aws-amplify';
import { INTERVIEW_API_BASE } from '../config/api';

export interface InterviewSession {
  session_id: string;
  status: string;
  rtc_endpoints: {
    offer: string;
    answer: string;
    ice_candidate: string;
  };
}

export interface ICEServersResponse {
  iceServers: RTCIceServer[];
}

export interface TranscriptEntry {
  speaker: 'user' | 'assistant';
  text: string;
  timestamp: string;
}

export interface InterviewResults {
  session_id: string;
  user_id: string;
  interests: Array<{
    name: string;
    details?: string;
  }>;
  duration: number;
}

class VoiceInterviewService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = INTERVIEW_API_BASE;
  }

  // Start new interview session
  async startInterview(userId: string): Promise<InterviewSession> {
    try {
      const response = await fetch(`${this.baseUrl}/api/interview/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start interview: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error starting interview:', error);
      throw error;
    }
  }

  // Get ICE servers including TURN credentials
  async getICEServers(sessionId: string): Promise<ICEServersResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/interview/${sessionId}/ice-servers`);
      
      if (!response.ok) {
        throw new Error(`Failed to get ICE servers: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting ICE servers:', error);
      throw error;
    }
  }

  // Get interview session status
  async getSessionStatus(sessionId: string) {
    try {
      const response = await fetch(`${this.baseUrl}/api/interview/${sessionId}/status`);
      
      if (!response.ok) {
        throw new Error(`Failed to get session status: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting session status:', error);
      throw error;
    }
  }

  // Update transcript
  async updateTranscript(sessionId: string, data: any) {
    try {
      const response = await fetch(`${this.baseUrl}/api/interview/${sessionId}/transcript`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error(`Failed to update transcript: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating transcript:', error);
      throw error;
    }
  }

  // Get interview results
  async getInterviewResults(sessionId: string): Promise<InterviewResults> {
    try {
      const response = await fetch(`${this.baseUrl}/api/interview/${sessionId}/results`);
      
      if (!response.ok) {
        throw new Error(`Failed to get interview results: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting interview results:', error);
      throw error;
    }
  }

  // End interview session
  async endInterview(sessionId: string) {
    try {
      const response = await fetch(`${this.baseUrl}/api/interview/${sessionId}/end`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to end interview: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error ending interview:', error);
      throw error;
    }
  }

  // Make WebRTC offer
  async makeOffer(sessionId: string, offer: RTCSessionDescriptionInit) {
    try {
      const response = await fetch(`${this.baseUrl}/api/interview/${sessionId}/rtc/offer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sdp: offer.sdp,
          type: offer.type,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to make offer: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error making offer:', error);
      throw error;
    }
  }

  // Send ICE candidate
  async sendICECandidate(sessionId: string, candidate: RTCIceCandidate) {
    try {
      const response = await fetch(`${this.baseUrl}/api/interview/${sessionId}/rtc/ice-candidate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          candidate: candidate.candidate,
          sdpMLineIndex: candidate.sdpMLineIndex,
          sdpMid: candidate.sdpMid,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to send ICE candidate: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error sending ICE candidate:', error);
      throw error;
    }
  }
}

export const voiceInterviewService = new VoiceInterviewService();
```

## 🎬 **Step 4: Create WebRTC Hook**

### `src/hooks/useWebRTC.ts`

```typescript
import { useState, useRef, useCallback, useEffect } from 'react';
import { voiceInterviewService } from '../services/voiceInterview.service';

interface UseWebRTCProps {
  sessionId: string;
  onTranscript?: (transcript: string, speaker: 'user' | 'assistant') => void;
  onInterestDetected?: (interest: string) => void;
  onStatusChange?: (status: string) => void;
}

export const useWebRTC = ({ 
  sessionId, 
  onTranscript, 
  onInterestDetected, 
  onStatusChange 
}: UseWebRTCProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<RTCPeerConnectionState>('new');
  
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);

  const initializeWebRTC = useCallback(async () => {
    try {
      onStatusChange?.('Initializing WebRTC...');

      // Get ICE servers including TURN credentials
      const { iceServers } = await voiceInterviewService.getICEServers(sessionId);
      
      // Create peer connection
      const pc = new RTCPeerConnection({
        iceServers,
        iceCandidatePoolSize: 10,
      });

      peerConnectionRef.current = pc;

      // Set up event handlers
      pc.onicecandidate = async (event) => {
        if (event.candidate) {
          try {
            await voiceInterviewService.sendICECandidate(sessionId, event.candidate);
          } catch (error) {
            console.error('Failed to send ICE candidate:', error);
          }
        }
      };

      pc.ontrack = (event) => {
        console.log('Received remote track:', event);
        if (event.streams[0] && remoteAudioRef.current) {
          remoteAudioRef.current.srcObject = event.streams[0];
          remoteAudioRef.current.play().catch(e => 
            console.error('Error playing remote audio:', e)
          );
        }
      };

      pc.onconnectionstatechange = () => {
        const state = pc.connectionState;
        setConnectionState(state);
        onStatusChange?.(`Connection: ${state}`);
        
        if (state === 'connected') {
          setIsConnected(true);
        } else if (state === 'disconnected' || state === 'failed') {
          setIsConnected(false);
        }
      };

      pc.oniceconnectionstatechange = () => {
        console.log('ICE connection state:', pc.iceConnectionState);
      };

      // Get user media
      onStatusChange?.('Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });

      localStreamRef.current = stream;

      // Add audio track to peer connection
      stream.getTracks().forEach(track => {
        pc.addTrack(track, stream);
      });

      // Create and send offer
      onStatusChange?.('Creating WebRTC offer...');
      const offer = await pc.createOffer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: false,
      });

      await pc.setLocalDescription(offer);

      // Send offer to server and get answer
      const answer = await voiceInterviewService.makeOffer(sessionId, offer);
      
      await pc.setRemoteDescription(new RTCSessionDescription(answer));

      onStatusChange?.('WebRTC connection established!');

      return pc;
    } catch (error) {
      console.error('Failed to initialize WebRTC:', error);
      onStatusChange?.(`Error: ${error.message}`);
      throw error;
    }
  }, [sessionId, onStatusChange]);

  const disconnect = useCallback(() => {
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }

    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }

    setIsConnected(false);
    setConnectionState('closed');
  }, []);

  const setRemoteAudioElement = useCallback((element: HTMLAudioElement | null) => {
    remoteAudioRef.current = element;
  }, []);

  return {
    isConnected,
    connectionState,
    initializeWebRTC,
    disconnect,
    setRemoteAudioElement,
  };
};
```

## 🎯 **Step 5: Update Voice Interview Page**

### Replace existing `src/pages/VoiceInterviewPage.tsx`:

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { useAuthenticator } from '@aws-amplify/ui-react';
import { Button } from '../components/atoms/Button';
import { Card } from '../components/atoms/Card';
import { ChatBubble } from '../components/molecules/ChatBubble';
import { InterestBubble } from '../components/molecules/InterestBubble';
import { voiceInterviewService, TranscriptEntry } from '../services/voiceInterview.service';
import { useWebRTC } from '../hooks/useWebRTC';

const VoiceInterviewPage: React.FC = () => {
  const { user } = useAuthenticator();
  const [isInterviewing, setIsInterviewing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [interests, setInterests] = useState<string[]>([]);
  const [status, setStatus] = useState<string>('Ready to start');
  const [error, setError] = useState<string | null>(null);
  
  const audioRef = useRef<HTMLAudioElement>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  const { 
    isConnected, 
    connectionState, 
    initializeWebRTC, 
    disconnect, 
    setRemoteAudioElement 
  } = useWebRTC({
    sessionId: sessionId || '',
    onTranscript: (text, speaker) => {
      const entry: TranscriptEntry = {
        speaker,
        text,
        timestamp: new Date().toISOString()
      };
      setTranscript(prev => [...prev, entry]);
    },
    onInterestDetected: (interest) => {
      setInterests(prev => [...prev, interest]);
    },
    onStatusChange: setStatus,
  });

  // Set up remote audio element
  useEffect(() => {
    if (audioRef.current) {
      setRemoteAudioElement(audioRef.current);
    }
  }, [setRemoteAudioElement]);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  // Poll for transcript updates and interests
  useEffect(() => {
    if (!sessionId || !isConnected) return;

    const pollInterval = setInterval(async () => {
      try {
        const results = await voiceInterviewService.getInterviewResults(sessionId);
        const newInterests = results.interests.map(i => i.name);
        
        // Update interests if changed
        if (newInterests.length !== interests.length) {
          setInterests(newInterests);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [sessionId, isConnected, interests.length]);

  const startInterview = async () => {
    try {
      setError(null);
      setStatus('Starting interview...');
      
      // Start interview session
      const session = await voiceInterviewService.startInterview(
        user?.username || 'anonymous'
      );
      
      setSessionId(session.session_id);
      setIsInterviewing(true);
      
      // Get initial greeting
      const statusResponse = await voiceInterviewService.getSessionStatus(session.session_id);
      if (statusResponse.greeting) {
        setTranscript([{
          speaker: 'assistant',
          text: statusResponse.greeting,
          timestamp: new Date().toISOString()
        }]);
      }
      
      // Initialize WebRTC connection
      await initializeWebRTC();
      
    } catch (error) {
      console.error('Failed to start interview:', error);
      setError(`Failed to start interview: ${error.message}`);
      setStatus('Failed to start interview');
      setIsInterviewing(false);
    }
  };

  const endInterview = async () => {
    try {
      setStatus('Ending interview...');
      
      // Disconnect WebRTC
      disconnect();
      
      // End session on server
      if (sessionId) {
        await voiceInterviewService.endInterview(sessionId);
      }
      
      setIsInterviewing(false);
      setStatus('Interview completed!');
    } catch (error) {
      console.error('Failed to end interview:', error);
      setError(`Error ending interview: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Voice Interview</h1>
        
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Main Interview Area */}
          <div className="md:col-span-2">
            <Card className="h-[600px] flex flex-col">
              <div className="p-4 border-b">
                <h2 className="text-xl font-semibold">Interview Chat</h2>
                <div className="flex items-center space-x-2 mt-1">
                  <div className={`w-3 h-3 rounded-full ${
                    isConnected ? 'bg-green-500' : 'bg-gray-400'
                  }`} />
                  <p className="text-sm text-gray-600">{status}</p>
                </div>
                {connectionState !== 'new' && (
                  <p className="text-xs text-gray-500">
                    WebRTC: {connectionState}
                  </p>
                )}
              </div>
              
              {/* Transcript Area */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {transcript.map((entry, index) => (
                  <ChatBubble
                    key={index}
                    message={entry.text}
                    isUser={entry.speaker === 'user'}
                    timestamp={new Date(entry.timestamp).toLocaleTimeString()}
                  />
                ))}
                <div ref={transcriptEndRef} />
              </div>
              
              {/* Controls */}
              <div className="p-4 border-t">
                {!isInterviewing ? (
                  <Button
                    onClick={startInterview}
                    className="w-full"
                    variant="primary"
                    disabled={!!error}
                  >
                    Start Voice Interview
                  </Button>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center justify-center space-x-2">
                      <div className={`w-3 h-3 rounded-full animate-pulse ${
                        isConnected ? 'bg-green-500' : 'bg-red-500'
                      }`} />
                      <span className="text-sm text-gray-600">
                        {isConnected ? 'Connected & Recording...' : 'Connecting...'}
                      </span>
                    </div>
                    <Button
                      onClick={endInterview}
                      className="w-full"
                      variant="secondary"
                    >
                      End Interview
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          </div>
          
          {/* Interests Sidebar */}
          <div>
            <Card className="h-[600px] flex flex-col">
              <div className="p-4 border-b">
                <h2 className="text-xl font-semibold">Detected Interests</h2>
                <p className="text-sm text-gray-600 mt-1">
                  {interests.length} interest{interests.length !== 1 ? 's' : ''} found
                </p>
              </div>
              
              <div className="flex-1 overflow-y-auto p-4">
                {interests.length === 0 ? (
                  <p className="text-gray-500 text-center mt-8">
                    Interests will appear here as they are detected during the conversation
                  </p>
                ) : (
                  <div className="space-y-2">
                    {interests.map((interest, index) => (
                      <InterestBubble key={index} interest={interest} />
                    ))}
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
        
        {/* Hidden audio element for remote audio playback */}
        <audio ref={audioRef} className="hidden" autoPlay />
      </div>
    </div>
  );
};

export default VoiceInterviewPage;
```

## 🚀 **Step 6: Deploy to Amplify**

### Update `amplify.yml` build settings:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: build
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
  customHeaders:
    - pattern: '**'
      headers:
        - key: 'Permissions-Policy'
          value: 'microphone=(self)'
        - key: 'Feature-Policy'
          value: 'microphone "self"'
```

### Set Environment Variables in Amplify Console:

1. Go to **Amplify Console** > Your App > **Environment Variables**
2. Add:
   ```
   REACT_APP_INTERVIEW_API_URL = https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com
   REACT_APP_TURN_SERVER = your-turn-server-ip
   ```

## 🔐 **Step 7: Configure CORS (If Needed)**

If you get CORS errors, update your CDK stack CORS configuration:

```typescript
// In spool-ecs-stack.ts
corsPreflight: {
  allowOrigins: [
    'https://main.your-amplify-domain.amplifyapp.com', // Your Amplify domain
    'https://app.spool.education', // Custom domain if you have one
    'http://localhost:3000' // For local development
  ],
  allowHeaders: ['Content-Type', 'Authorization', 'X-Amz-Date', 'X-Api-Key'],
  allowMethods: [
    apigatewayv2.CorsHttpMethod.GET,
    apigatewayv2.CorsHttpMethod.POST,
    apigatewayv2.CorsHttpMethod.OPTIONS,
  ],
  allowCredentials: true,
  maxAge: cdk.Duration.days(1),
},
```

## 🧪 **Step 8: Test the Integration**

### Local Testing:
```bash
# In your frontend directory
npm start

# Visit http://localhost:3000 and test the voice interview
```

### Production Testing:
1. Deploy to Amplify: `amplify publish`
2. Visit your Amplify app URL
3. Navigate to Voice Interview page
4. Test the voice functionality

## 🔍 **Troubleshooting**

### Common Issues:

1. **CORS Errors**: Update allowOrigins in CDK stack
2. **Microphone Access**: Ensure HTTPS and proper permissions
3. **WebRTC Connection Fails**: Check TURN server accessibility
4. **Audio Not Playing**: Verify autoplay policies and user interaction

### Debug Commands:
```bash
# Check API connectivity
curl https://your-api-gateway-url/api/interview/health

# Test TURN server
telnet your-turn-server-ip 3478
```

## 📋 **Summary**

✅ **Service Layer**: Voice interview service with REST API calls  
✅ **WebRTC Hook**: Reusable hook for WebRTC connection management  
✅ **Updated Component**: Voice interview page with Amplify integration  
✅ **Environment Config**: Proper API endpoint configuration  
✅ **Deployment**: Amplify build configuration with environment variables  

Your Amplify frontend is now fully integrated with the REST-based FastRTC voice interview service! 🎉