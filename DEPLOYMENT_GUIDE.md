# Complete Deployment Guide for Spool Voice Interview Service (REST/FastRTC)

## Overview

This guide provides step-by-step instructions to deploy the REST-based FastRTC voice interview service on AWS.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Docker installed locally
- Node.js 18+ and npm
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- An AWS account with permissions to create ECS, ALB, API Gateway resources

## Step 1: Prepare the Code

### 1.1 Update the Main Application File

The service now uses `main_rest.py` instead of the WebSocket version:

```bash
cd spool-interview-service/services/interview/src
# Ensure main_rest.py and voice_agent_rest.py are in place
```

### 1.2 Update Requirements

Ensure `requirements.txt` includes:
```
fastrtc[vad,stt,tts]==0.0.23
fastapi==0.115.12
uvicorn==0.34.2
# ... other dependencies
```

## Step 2: Build and Push Docker Image

### 2.1 Create ECR Repository (if not exists)

```bash
aws ecr create-repository --repository-name spool/interview-service --region us-east-1
```

### 2.2 Build and Push

```bash
cd spool-interview-service

# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [YOUR_ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 \
  -t [YOUR_ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/spool/interview-service:latest \
  -f services/interview/Dockerfile \
  --push \
  services/interview
```

## Step 3: Deploy Infrastructure with CDK

### 3.1 Install Dependencies

```bash
cd infrastructure/cdk
npm install
```

### 3.2 Bootstrap CDK (first time only)

```bash
cdk bootstrap aws://[YOUR_ACCOUNT_ID]/us-east-1
```

### 3.3 Deploy the Stack

```bash
cdk deploy SpoolEcsStack
```

This will create:
- VPC with public/private subnets
- ECS Cluster
- ALB (Application Load Balancer)
- ECS Service for the interview application
- API Gateway v2 with VPC Link
- All necessary security groups and IAM roles

### 3.4 Note the Outputs

After deployment, note these outputs:
- `ApiGatewayUrl`: Your API endpoint
- `AlbUrl`: Internal ALB URL (for debugging)

## Step 4: Deploy TURN Server

### 4.1 Launch EC2 Instance

Launch an EC2 instance for the TURN server:
- Instance type: t3.small (minimum)
- Security Group: Open ports 3478 (TCP/UDP), 49152-65535 (UDP)
- Elastic IP: Assign for stable external IP

### 4.2 Install Docker on EC2

```bash
# SSH into your EC2 instance
ssh ec2-user@your-turn-server-ip

# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 4.3 Deploy TURN Server

```bash
# Copy turn configuration files to EC2
scp docker-compose.turn.yml turnserver.conf ec2-user@your-turn-server-ip:~/

# On EC2 instance
export EXTERNAL_IP=your-elastic-ip
export TURN_SECRET=your-secure-turn-secret

docker-compose -f docker-compose.turn.yml up -d
```

## Step 5: Configure Environment Variables

### 5.1 Update ECS Task Definition

Update these environment variables in your ECS task:

```bash
# Via AWS Console or CLI
OPENAI_API_KEY=your-openai-api-key
TURN_SERVER=your-turn-server-ip
TURN_SECRET=your-secure-turn-secret
API_BASE_URL=https://your-api-gateway-url
```

### 5.2 Store Secrets in AWS Secrets Manager

```bash
# Create secret for OpenAI API Key
aws secretsmanager create-secret \
  --name spool/openai-api-key \
  --secret-string "your-openai-api-key"

# Create secret for TURN
aws secretsmanager create-secret \
  --name spool/turn-secret \
  --secret-string "your-secure-turn-secret"
```

## Step 6: Update Frontend

### 6.1 Update API Configuration

In your React frontend:

```typescript
// src/config/api.ts
export const API_BASE_URL = 'https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com';
```

### 6.2 Replace Voice Interview Page

Replace the WebSocket-based VoiceInterviewPage with the new REST-based version:

```bash
# In your frontend directory
cp VoiceInterviewPageREST.tsx src/pages/VoiceInterviewPage.tsx
```

### 6.3 Build and Deploy Frontend

```bash
npm run build
# Deploy to your hosting service (S3, CloudFront, etc.)
```

## Step 7: Testing

### 7.1 Test API Gateway

```bash
# Health check
curl https://your-api-gateway-url/api/interview/health

# Start session
curl -X POST https://your-api-gateway-url/api/interview/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user"}'
```

### 7.2 Test TURN Server

```bash
# From EC2 instance
docker logs spool-turn-server
```

### 7.3 Test Full Flow

1. Open your React application
2. Navigate to Voice Interview page
3. Click "Start Voice Interview"
4. Grant microphone permissions
5. Speak to test the voice interaction

## Step 8: Monitoring and Maintenance

### 8.1 CloudWatch Logs

Monitor logs in CloudWatch:
- `/ecs/interview-service` - Application logs
- API Gateway execution logs

### 8.2 ECS Auto-scaling

The CDK stack includes auto-scaling configuration:
- Min: 0 tasks
- Max: 5 tasks
- Target CPU: 70%

### 8.3 TURN Server Monitoring

```bash
# Check TURN server status
docker ps
docker logs spool-turn-server

# Monitor connections
docker exec spool-turn-server turnadmin -l
```

## Troubleshooting

### Issue: WebRTC Connection Fails

1. Check TURN server is accessible:
   ```bash
   nc -zv your-turn-server-ip 3478
   ```

2. Verify security groups allow UDP traffic

3. Check browser console for ICE candidate errors

### Issue: No Audio

1. Check microphone permissions in browser
2. Verify FastRTC models loaded (check ECS logs)
3. Test with different audio sample rates

### Issue: API Gateway 504 Timeout

1. Increase ALB health check grace period
2. Check ECS task is healthy
3. Verify security group rules

## Security Best Practices

1. **API Gateway**: Add API key or JWT authentication
2. **TURN Server**: Regularly rotate credentials
3. **HTTPS Only**: Ensure all traffic uses TLS
4. **CORS**: Restrict to your domain in production
5. **Secrets**: Use AWS Secrets Manager for all sensitive data

## Cost Optimization

1. Use Fargate Spot for non-production environments
2. Enable ECS task auto-scaling to scale down during low usage
3. Use CloudFront for caching static assets
4. Monitor API Gateway usage to avoid throttling charges

## Next Steps

1. Add authentication to API Gateway
2. Implement session persistence in DynamoDB
3. Add CloudFront distribution for better performance
4. Set up CI/CD pipeline with CodePipeline
5. Implement comprehensive logging and monitoring