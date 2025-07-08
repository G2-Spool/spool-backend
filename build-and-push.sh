#!/bin/bash

set -e

# Configuration
ECR_REPOSITORY="560281064968.dkr.ecr.us-east-1.amazonaws.com/spool-interview"
AWS_REGION="us-east-1"
IMAGE_TAG="latest"

echo "🏗️ Building and pushing Docker image to ECR"

# Step 1: Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REPOSITORY"

# Step 2: Build the Docker image
echo "🏗️ Building Docker image..."
cd services/interview
docker build -t "$ECR_REPOSITORY:$IMAGE_TAG" .

# Step 3: Tag the image (already done in build)
echo "🏷️ Image tagged as: $ECR_REPOSITORY:$IMAGE_TAG"

# Step 4: Push the image to ECR
echo "📤 Pushing image to ECR..."
docker push "$ECR_REPOSITORY:$IMAGE_TAG"

# Step 5: Clean up local image (optional)
echo "🧹 Cleaning up local image..."
docker rmi "$ECR_REPOSITORY:$IMAGE_TAG" || echo "Local image cleanup skipped"

echo "✅ Docker image successfully pushed to ECR!"
echo "🔗 Image URI: $ECR_REPOSITORY:$IMAGE_TAG"
echo ""
echo "Next steps:"
echo "1. Run './deploy-ecs-service.sh' to deploy the service"
echo "2. Or run 'aws ecs update-service --cluster spool-mvp --service spool-interview-service --force-new-deployment' to update existing service" 