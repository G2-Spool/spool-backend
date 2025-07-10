# API Gateway Setup for Spool Voice Interview Service

## Overview

This guide explains how to deploy the REST-based FastRTC voice interview service with AWS API Gateway integration.

## Architecture

```
[React Frontend] --> [API Gateway] --> [ALB] --> [ECS Service with FastRTC]
                           |
                           v
                    [TURN Server]
```

## Key Components

### 1. FastRTC REST Endpoints (Auto-generated)

When the interview starts, FastRTC automatically creates these endpoints:
- `POST /api/interview/{session_id}/rtc/offer` - Submit WebRTC offer
- `POST /api/interview/{session_id}/rtc/answer` - Receive WebRTC answer  
- `POST /api/interview/{session_id}/rtc/ice-candidate` - Exchange ICE candidates

### 2. Additional REST Endpoints

- `POST /api/interview/start` - Start new interview session
- `GET /api/interview/{session_id}/status` - Get session status
- `GET /api/interview/{session_id}/ice-servers` - Get TURN credentials
- `POST /api/interview/{session_id}/transcript` - Update transcript
- `GET /api/interview/{session_id}/results` - Get interview results
- `POST /api/interview/{session_id}/end` - End interview session

### 3. API Gateway Configuration

The CDK stack creates:
- HTTP API (v2) with CORS enabled
- VPC Link for private ALB access
- Routes proxying `/api/interview/*` to the ALB
- Automatic SSL/TLS termination

## Deployment Steps

### 1. Update Environment Variables

```bash
# In your .env file or AWS Secrets Manager
OPENAI_API_KEY=your-api-key
TURN_SECRET=your-turn-secret
TURN_SERVER=turn.spool.education
```

### 2. Build and Push Docker Image

```bash
cd spool-interview-service
./build-and-push.sh
```

### 3. Deploy CDK Stack

```bash
cd infrastructure/cdk
npm install
cdk deploy SpoolEcsStack
```

### 4. Deploy TURN Server

```bash
# On a separate EC2 instance
docker-compose -f docker-compose.turn.yml up -d
```

### 5. Update Frontend Configuration

```typescript
// In your React app's api config
const API_BASE_URL = 'https://your-api-gateway-id.execute-api.region.amazonaws.com';
```

## Testing

### 1. Test Health Endpoint

```bash
curl https://your-api-gateway-id.execute-api.region.amazonaws.com/api/interview/health
```

### 2. Start Interview Session

```bash
curl -X POST https://your-api-gateway-id.execute-api.region.amazonaws.com/api/interview/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user"}'
```

### 3. Test WebRTC Connection

Use the provided React component (`VoiceInterviewPageREST.tsx`) to test the full WebRTC flow.

## Security Considerations

1. **CORS**: Configure allowed origins in production
2. **TURN Authentication**: Uses time-limited credentials
3. **API Gateway**: Add authentication/authorization as needed
4. **VPC**: Backend services remain in private subnets

## Monitoring

- CloudWatch Logs: `/ecs/interview-service`
- ECS Container Insights: CPU/Memory metrics
- API Gateway Metrics: Request count, latency, errors

## Troubleshooting

### Connection Issues
1. Check Security Groups allow traffic from API Gateway
2. Verify TURN server is accessible
3. Check browser console for WebRTC errors

### Audio Issues
1. Ensure microphone permissions granted
2. Check audio format compatibility
3. Verify STT/TTS models loaded correctly

### Performance
1. Enable ECS auto-scaling
2. Use CloudFront for static assets
3. Monitor API Gateway throttling limits