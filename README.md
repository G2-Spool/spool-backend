# Spool Backend Services

Backend services for the Spool learning companion application, including the voice interview service and infrastructure as code.

**Status:** ✅ Deployed to CodeBuild

## Architecture

This repository contains:

- **Interview Service** - Voice-enabled interview agent for collecting student interests
- **Infrastructure** - AWS CDK code for deploying services to ECS
- **CI/CD** - AWS CodeBuild configuration for automated deployments

## Services

### Interview Service
- FastAPI application with WebSocket support
- Voice processing using FastRTC (Moonshine STT, Kokoro TTS)
- GPT-4 powered conversational agent
- Real-time interest detection and processing

### LangFlow Integration
- Visual workflow automation for processing interview data
- Persistent storage using AWS EFS
- Service discovery for internal communication

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Node.js 18+ (for CDK)
- AWS CLI configured
- OpenAI API key

### Running Locally

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/spool-backend.git
   cd spool-backend
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Start services**:
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

4. **Access services**:
   - Interview API: http://localhost:8080
   - Interview Health: http://localhost:8080/health
   - LangFlow UI: http://localhost:7860

## Deployment

### AWS Infrastructure

The infrastructure is deployed using AWS CDK to create:
- ECS Fargate cluster
- Application Load Balancer
- Service Discovery namespace
- EFS for persistent storage
- CloudWatch logging

### CodeBuild Pipeline

The repository includes a `buildspec.yml` for AWS CodeBuild that:
1. Builds Docker images
2. Pushes to Amazon ECR
3. Updates ECS services
4. Optionally updates CDK infrastructure

### Manual Deployment

1. **Deploy infrastructure**:
   ```bash
   cd infrastructure/cdk
   npm install
   npx cdk deploy SpoolEcsStack
   ```

2. **Build and push Docker image**:
   ```bash
   cd services/interview
   docker build -t spool-interview .
   # Tag and push to ECR
   ```

## API Documentation

### Interview Service Endpoints

- `POST /api/interview/start` - Start a new interview session
- `WS /ws/interview/{session_id}` - WebSocket connection for voice interview
- `GET /api/interview/{session_id}/results` - Get interview results
- `POST /api/interview/{session_id}/end` - End interview session

### WebSocket Protocol

The interview WebSocket accepts:
- Audio data (binary) - 16-bit PCM audio at 16kHz
- Control messages (JSON):
  - `{"type": "end_interview"}` - End the session
  - `{"type": "ping"}` - Keep-alive

Responses include:
- `{"type": "user_transcript", "text": "..."}` - User speech transcription
- `{"type": "assistant_transcript", "text": "..."}` - Assistant response
- `{"type": "interest_detected", "interest": "..."}` - Detected interest
- Audio data (binary) - TTS audio response

## Environment Variables

### Interview Service
- `OPENAI_API_KEY` - OpenAI API key for GPT-4
- `LANGFLOW_URL` - URL for LangFlow service (default: http://langflow.spool.local:7860)
- `ENV` - Environment (development/production)

### Infrastructure
- `AWS_PROFILE` - AWS profile to use for deployment
- `CDK_DEFAULT_ACCOUNT` - AWS account ID
- `CDK_DEFAULT_REGION` - AWS region (default: us-east-1)

## Project Structure

```
spool-backend/
├── services/
│   └── interview/          # Voice interview service
│       ├── src/            # Python source code
│       ├── Dockerfile
│       └── requirements.txt
├── infrastructure/
│   ├── cdk/                # AWS CDK infrastructure
│   └── README.md
├── docker-compose.dev.yml  # Local development setup
├── buildspec.yml           # AWS CodeBuild configuration
└── README.md
```

## Monitoring

### Health Checks
- Interview service: `/health`
- LangFlow service: `/health`

### Logging
- CloudWatch Logs: `/ecs/interview-service` and `/ecs/langflow-service`
- Local logs: Available in Docker Compose output

## Security

- Secrets stored in AWS Secrets Manager
- Network isolation using VPC and security groups
- HTTPS termination at ALB
- IAM roles with least privilege

## Contributing

1. Create a feature branch
2. Make your changes
3. Test locally using Docker Compose
4. Submit a pull request

## License

[Your License Here] 