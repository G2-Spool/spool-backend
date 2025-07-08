# Spool Backend Setup Guide

## Quick Start

### 1. Repository Setup

```bash
# Clone the repository
git clone https://github.com/your-org/spool-backend.git
cd spool-backend

# Create and configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Local Development

```bash
# Install dependencies (if you want to run CDK locally)
npm install

# Start services with Docker Compose
docker-compose -f docker-compose.dev.yml up

# Services will be available at:
# - Interview API: http://localhost:8080
# - LangFlow UI: http://localhost:7860
```

### 3. AWS Deployment

#### Option A: Automated with CodeBuild

1. **Set up CodeBuild**:
   ```bash
   cd scripts
   chmod +x setup-codebuild.sh
   ./setup-codebuild.sh
   ```

2. **Create GitHub connection**:
   - Go to AWS CodeBuild console
   - Create a GitHub OAuth connection
   - Or use: `aws codebuild import-source-credentials`

3. **Create CodeBuild project**:
   ```bash
   aws codebuild create-project --cli-input-json file://codebuild-project.json
   ```

4. **Push to trigger build**:
   ```bash
   git push origin main
   ```

#### Option B: Manual Deployment

1. **Deploy infrastructure**:
   ```bash
   cd infrastructure/cdk
   npm install
   npx cdk bootstrap  # First time only
   npx cdk deploy SpoolEcsStack
   ```

2. **Build and push Docker image**:
   ```bash
   # Get ECR login
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com

   # Build and tag
   cd services/interview
   docker build -t spool-interview .
   docker tag spool-interview:latest [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/spool-interview:latest

   # Push
   docker push [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/spool-interview:latest
   ```

3. **Update ECS service** (if needed):
   ```bash
   aws ecs update-service --cluster spool-mvp --service interview-service --force-new-deployment
   ```

## Configuration

### Required Environment Variables

1. **AWS Parameter Store** (for production):
   ```bash
   aws ssm put-parameter \
     --name "/spool/openai-api-key" \
     --value "sk-your-openai-api-key" \
     --type "SecureString"
   ```

2. **CodeBuild Environment Variables**:
   - `AWS_DEFAULT_REGION`: Your AWS region
   - `AWS_ACCOUNT_ID`: Your AWS account ID
   - `ECR_REPOSITORY_INTERVIEW`: ECR repository name (default: spool-interview)
   - `ECS_CLUSTER_NAME`: ECS cluster name (default: spool-mvp)
   - `ECS_SERVICE_INTERVIEW`: Interview service name (default: interview-service)
   - `ECS_SERVICE_LANGFLOW`: LangFlow service name (default: langflow-service)

### Frontend Connection

After deploying the backend:

1. Get the ALB URL:
   ```bash
   aws elbv2 describe-load-balancers --names spool-alb --query 'LoadBalancers[0].DNSName' --output text
   ```

2. Update frontend `.env.local`:
   ```env
   NEXT_PUBLIC_INTERVIEW_API_URL=https://[ALB-DNS-NAME]
   ```

## Troubleshooting

### Common Issues

1. **CodeBuild fails with permissions error**:
   - Ensure the IAM role has all required permissions
   - Check that ECR repository exists or role can create it

2. **ECS tasks failing to start**:
   - Check CloudWatch logs: `/ecs/interview-service`
   - Verify OpenAI API key in Parameter Store
   - Check security group rules

3. **WebSocket connection fails**:
   - Ensure ALB target group has stickiness enabled
   - Check security group allows WebSocket traffic
   - Verify CORS settings if frontend is on different domain

### Monitoring

- **CloudWatch Logs**: 
  - `/ecs/interview-service`
  - `/ecs/langflow-service`
  - `/aws/codebuild/spool-backend`

- **ECS Console**: Check service health and task status

- **Application Load Balancer**: Monitor target health

## Cost Optimization

- Use auto-scaling to reduce costs during low usage
- Consider spot instances for development environments
- Monitor CloudWatch metrics to right-size containers 