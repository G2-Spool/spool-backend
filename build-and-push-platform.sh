#!/bin/bash

set -e

# Configuration
ECR_REPOSITORY="560281064968.dkr.ecr.us-east-1.amazonaws.com/spool-interview"
AWS_REGION="us-east-1"
IMAGE_TAG="latest"

echo "🏗️ Building and pushing Docker image to ECR with platform specification"

# Step 1: Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REPOSITORY"

# Step 2: Ensure buildx is available and create a builder
echo "🔧 Setting up Docker buildx..."
docker buildx create --use --name multiarch-builder || docker buildx use multiarch-builder

# Step 3: Build the Docker image for linux/amd64
echo "🏗️ Building Docker image for linux/amd64 platform..."
cd services/interview

# Build and push in one step for multi-arch support
docker buildx build \
    --platform linux/amd64 \
    -t "$ECR_REPOSITORY:$IMAGE_TAG" \
    --push \
    .

echo "✅ Docker image successfully built and pushed to ECR!"
echo "🔗 Image URI: $ECR_REPOSITORY:$IMAGE_TAG"
echo "🎯 Platform: linux/amd64"
echo ""
echo "Next steps:"
echo "1. Run './deploy-ecs-service.sh' to deploy the service"
echo "2. Or run 'aws ecs update-service --cluster spool-mvp --service spool-interview-service --force-new-deployment' to update existing service"