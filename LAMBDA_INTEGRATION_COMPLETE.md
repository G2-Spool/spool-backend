# Lambda Integration Complete Guide

## Overview

This document describes the complete integration between the spool-interview-service (ECS) and the spool-create-thread Lambda function, using LangGraph for voice interview orchestration instead of LangFlow.

## Architecture

```
User → Amplify Frontend → API Gateway → spool-interview-service (ECS)
                                              ↓
                                    [LangGraph Voice Interview]
                                              ↓
                                    [Thread Mode Detection]
                                              ↓
                                    Invoke CreateThread Lambda
                                              ↓
                                    Save to RDS learning_paths table
```

## Key Changes Implemented

### 1. LangGraph Integration

**Replaced LangFlow with pure LangGraph implementation:**

- Created `langgraph_interview.py` with a state-based interview orchestration graph
- Implements interview stages: greeting, exploration, deep_dive, wrap_up
- Automatic interest extraction and concept detection
- Thread creation preparation when in "thread" mode

**Key features:**
- State management for conversation flow
- Interest detection with [INTEREST: name] markers
- Academic concept extraction
- Automatic thread summary generation

### 2. FastRTC Voice Integration

**Updated `voice_agent.py` to use FastRTC with LangGraph:**

```python
# Uses Moonshine STT and Kokoro TTS models
stt_model = get_stt_model()  # Moonshine
tts_model = get_tts_model()  # Kokoro

# LangGraph orchestrates the conversation
interview_graph = InterviewGraph(llm_model=self.llm_model)
```

### 3. Lambda Integration

**Created `lambda_integration.py` for thread creation:**

- Invokes `spool-create-thread` Lambda function
- Transforms interview data to thread format
- Analyzes conversation for subjects, topics, and concepts
- Handles authentication via JWT tokens

### 4. Updated Main Service

**Modified `main.py` to support thread mode:**

- Added mode parameter to `/api/interview/start` endpoint
- Integrated Lambda invocation in `save_session_data`
- Returns thread information in results

## Configuration Updates

### 1. Dependencies Added

```txt
boto3>=1.34.0  # For Lambda invocation
# LangGraph and LangChain dependencies already present
```

### 2. Environment Variables

Added to `ecs-task-definition.json`:
```json
{
    "name": "AWS_REGION",
    "value": "us-east-1"
},
{
    "name": "LAMBDA_FUNCTION_NAME",
    "value": "spool-create-thread"
}
```

### 3. IAM Permissions

Created `iam-lambda-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": "arn:aws:lambda:us-east-1:560281064968:function:spool-create-thread"
    }
  ]
}
```

## API Endpoints

### Start Interview
```
POST /api/interview/start
{
    "user_id": "cognito-user-id",
    "mode": "thread",  // Optional: "thread" to create learning thread
    "purpose": "create_learning_thread",  // Optional
    "auth_token": "JWT-token"  // Optional: for authentication
}
```

### Get Results
```
GET /api/interview/{session_id}/results

Response includes:
{
    "session_id": "...",
    "user_id": "...",
    "interests": [...],
    "duration": 120.5,
    "thread_id": "uuid",  // If thread was created
    "thread_created": true
}
```

## Deployment Steps

1. **Apply IAM Permissions:**
   ```bash
   cd scripts
   ./setup-lambda-permissions.sh
   ```

2. **Build and Push Docker Image:**
   ```bash
   ./build-and-push.sh
   ```

3. **Deploy ECS Service:**
   ```bash
   ./deploy-ecs-service.sh
   ```

4. **Test the Integration:**
   ```bash
   # Test Lambda invocation
   aws lambda invoke \
     --function-name spool-create-thread \
     --payload '{"httpMethod":"POST","path":"/create","body":"{\"userId\":\"test\",\"title\":\"Test\"}"}' \
     response.json
   ```

## Testing the Full Flow

1. **Start an interview in thread mode:**
   ```bash
   curl -X POST http://your-api-gateway/api/interview/start \
     -H "Content-Type: application/json" \
     -d '{"user_id": "test-user", "mode": "thread"}'
   ```

2. **Have a conversation about interests**
   - The LangGraph orchestration will guide the conversation
   - Interests will be automatically detected
   - Concepts and subjects will be extracted

3. **End the interview:**
   ```bash
   curl -X POST http://your-api-gateway/api/interview/{session_id}/end
   ```

4. **Check results:**
   ```bash
   curl http://your-api-gateway/api/interview/{session_id}/results
   ```

## Monitoring

### CloudWatch Logs
- **ECS Service:** `/ecs/spool-interview`
- **Lambda Function:** `/aws/lambda/spool-create-thread`

### Key Metrics
- Interview completion rate
- Thread creation success rate
- Interest detection accuracy
- Lambda invocation latency

## Troubleshooting

### Common Issues

1. **Lambda Timeout**
   - Check VPC configuration
   - Verify security groups allow traffic
   - Increase Lambda timeout if needed

2. **Permission Denied**
   - Run `setup-lambda-permissions.sh`
   - Verify ECS task role has lambda:InvokeFunction permission

3. **Thread Not Created**
   - Check if mode="thread" is set
   - Verify Lambda is accessible from ECS
   - Check CloudWatch logs for errors

## Security Considerations

1. **Authentication:** JWT tokens passed to Lambda
2. **Authorization:** Lambda verifies user permissions
3. **Data Validation:** All inputs validated before processing
4. **Network Security:** VPC isolated, TLS encryption

## Future Enhancements

1. **Multi-language Support:** Add language detection and translation
2. **Advanced Analytics:** Track conversation quality metrics
3. **Personalization:** Adapt interview style based on user preferences
4. **Integration with other services:** Connect to recommendation engine

## Support

For issues or questions:
- Check CloudWatch logs for errors
- Review this documentation
- Contact the infrastructure team for AWS-related issues