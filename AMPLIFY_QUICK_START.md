# 🚀 Quick Start: Amplify + FastRTC Integration

## 1️⃣ **Add to Amplify Environment Variables**

In Amplify Console > App Settings > Environment Variables:

```
REACT_APP_INTERVIEW_API_URL = https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com
REACT_APP_TURN_SERVER = your-turn-server-ip
```

## 2️⃣ **Install Dependencies**

```bash
npm install --save @types/webrtc recordrtc audio-recorder-polyfill uuid
```

## 3️⃣ **Copy Files to Your Frontend**

Copy these files from the implementation:

```bash
# Copy the service
cp src/services/voiceInterview.service.ts your-frontend/src/services/

# Copy the WebRTC hook  
cp src/hooks/useWebRTC.ts your-frontend/src/hooks/

# Copy the updated voice interview page
cp src/pages/VoiceInterviewPageREST.tsx your-frontend/src/pages/VoiceInterviewPage.tsx
```

## 4️⃣ **Update API Configuration**

Add to your `src/config/api.ts`:

```typescript
export const INTERVIEW_API_BASE = process.env.REACT_APP_INTERVIEW_API_URL || "http://localhost:8080";
export const TURN_SERVER = process.env.REACT_APP_TURN_SERVER || "turn.spool.education";
```

## 5️⃣ **Deploy**

```bash
git add .
git commit -m "Add REST-based FastRTC voice interview integration"
git push origin main

# Amplify will auto-deploy
```

## 6️⃣ **Test**

1. Go to your Amplify app URL
2. Navigate to Voice Interview page  
3. Click "Start Voice Interview"
4. Grant microphone permissions
5. Start speaking!

That's it! Your Amplify app now has voice interview capabilities with REST-based FastRTC! 🎤✨