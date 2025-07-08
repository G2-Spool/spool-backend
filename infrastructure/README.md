# Spool Voice Interview Infrastructure

This directory contains the infrastructure code for deploying the voice interview service using AWS ECS.

## Architecture Overview

The system consists of:

1. **Interview Service** - Python FastAPI service with voice agent capabilities
   - Speech-to-text using Moonshine
   - Text-to-speech using Kokoro
   - LLM integration with GPT-4
   - WebSocket support for real-time audio streaming

2. **LangFlow Service** - Visual workflow automation for processing interview data
   - Persistent storage using EFS
   - Service discovery for internal communication

3. **Infrastructure Components**
   - ECS Fargate cluster for containerized services
   - Application Load Balancer for external access
   - Service Discovery for internal service communication
   - EFS for persistent LangFlow storage
   - CloudWatch for logging and monitoring

## Local Development

### Prerequisites
- Docker and Docker Compose
- Node.js 18+
- Python 3.11+
- AWS CLI configured
- OpenAI API key

### Running Locally

1. **Set up environment variables**:
   ```bash
   export OPENAI_API_KEY=your-api-key
   ```

2. **Start services**:
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

3. **Access services**:
   - Interview API: http://localhost:8080
   - LangFlow UI: http://localhost:7860
   - Next.js App: http://localhost:3000

### Testing Voice Interview

1. Open the onboarding flow in your Next.js app
2. Click "Start Voice" to begin voice interview
3. Speak naturally about your interests
4. The system will detect and display interests in real-time

## AWS Deployment

### Prerequisites
- AWS Account with appropriate permissions
- AWS CDK installed (`npm install -g aws-cdk`)
- GitHub repository with secrets configured

### Initial Setup

1. **Configure GitHub Secrets**:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `OPENAI_API_KEY`

2. **Deploy Infrastructure**:
   ```bash
   cd infrastructure/cdk
   npm install
   cdk deploy SpoolEcsStack
   ```

3. **Update Frontend Configuration**:
   After deployment, update your `.env.local` with the ALB URL:
   ```
   NEXT_PUBLIC_INTERVIEW_API_URL=https://your-alb-url.amazonaws.com/interview
   ```

### Deployment Process

The GitHub Actions workflow automatically deploys on push to main:

1. **Infrastructure Deployment**: Updates CDK stack if changed
2. **Interview Service**: Builds and deploys if service files changed
3. **LangFlow Service**: Updates if commit message contains `[langflow]`

### Manual Deployment

Deploy interview service:
```bash
cd services/interview
docker build -t spool-interview .
# Push to ECR and update ECS service
```

## Cost Breakdown

Estimated monthly costs:
- ALB: ~$20
- Interview Service (0.5 vCPU): ~$6 (10 hours/day)
- LangFlow Service (1 vCPU): ~$29 (24 hours/day)
- EFS Storage: ~$1
- CloudWatch Logs: ~$5
- **Total**: ~$61/month

## Architecture Decisions

1. **ECS over Lambda**: Chosen for WebSocket support and long-running connections
2. **Fargate over EC2**: Serverless containers for easier management
3. **Service Discovery**: Enables services to find each other without hardcoded IPs
4. **EFS for LangFlow**: Persistent storage for flows across container restarts
5. **Auto-scaling**: Interview service scales 0-5 tasks based on CPU usage

## Monitoring

### CloudWatch Dashboards
- ECS service health
- ALB request metrics
- Container logs

### Health Checks
- ALB health checks on `/health` endpoints
- ECS task health monitoring
- Service discovery health status

## Troubleshooting

### Common Issues

1. **Voice not working**: Check browser permissions for microphone
2. **WebSocket connection failed**: Verify ALB WebSocket support is enabled
3. **Service discovery issues**: Check security group rules
4. **LangFlow not persisting**: Verify EFS mount is successful

### Debug Commands

```bash
# Check ECS services
aws ecs describe-services --cluster spool-mvp --services interview-service langflow-service

# View logs
aws logs tail /ecs/interview-service --follow
aws logs tail /ecs/langflow-service --follow

# Test health endpoints
curl http://alb-url/interview/health
curl http://alb-url/langflow/health
```

## Security Considerations

1. **Secrets Management**: OpenAI API key stored in AWS Secrets Manager
2. **Network Security**: Private subnets for containers, public for ALB only
3. **Encryption**: EFS encryption at rest, TLS for data in transit
4. **IAM Roles**: Least privilege access for ECS tasks

## Future Enhancements

1. **HTTPS**: Add ACM certificate and HTTPS listener
2. **WAF**: Add Web Application Firewall for additional security
3. **Multi-region**: Deploy to multiple regions for lower latency
4. **Caching**: Add ElastiCache for session management
5. **CI/CD**: Add automated testing in deployment pipeline 