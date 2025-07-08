#!/bin/bash

set -e

# Configuration
ECR_REPOSITORY="560281064968.dkr.ecr.us-east-1.amazonaws.com/spool-interview"
AWS_REGION="us-east-1"
CLUSTER_NAME="spool-mvp"
SERVICE_NAME="spool-interview-service"
TASK_FAMILY="spool-interview-task"

echo "🚀 Starting ECS deployment for Spool Interview Service"

# Step 1: Create CloudWatch Log Group
echo "📋 Creating CloudWatch Log Group..."
aws logs create-log-group --log-group-name "/ecs/spool-interview" --region "$AWS_REGION" 2>/dev/null || echo "Log group already exists"

# Step 2: Create ECS Task Execution Role if it doesn't exist
echo "🔑 Checking ECS Task Execution Role..."
aws iam get-role --role-name ecsTaskExecutionRole 2>/dev/null || {
    echo "Creating ECS Task Execution Role..."
    aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'
    aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
}

# Step 3: Create ECS Task Role if it doesn't exist
echo "🔑 Checking ECS Task Role..."
aws iam get-role --role-name ecsTaskRole 2>/dev/null || {
    echo "Creating ECS Task Role..."
    aws iam create-role --role-name ecsTaskRole --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'
}

# Step 4: Register the task definition
echo "📝 Registering ECS Task Definition..."
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Step 5: Check if service exists
echo "🔍 Checking if service exists..."
if aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" --query 'services[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo "📦 Updating existing service..."
    aws ecs update-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" --task-definition "$TASK_FAMILY"
else
    echo "🆕 Creating new service..."
    aws ecs create-service --cli-input-json file://ecs-service-config.json
fi

# Step 6: Wait for service to be stable
echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME"

# Step 7: Get service status
echo "📊 Service Status:"
aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" --query 'services[0].{Status:status,Running:runningCount,Pending:pendingCount,Desired:desiredCount}' --output table

# Step 8: Get task public IP
echo "🌐 Getting task public IP..."
TASK_ARN=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" --query 'taskArns[0]' --output text)
if [ "$TASK_ARN" != "None" ] && [ "$TASK_ARN" != "" ]; then
    ENI_ID=$(aws ecs describe-tasks --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN" --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
    if [ "$ENI_ID" != "None" ] && [ "$ENI_ID" != "" ]; then
        PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids "$ENI_ID" --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
        echo "✅ Service deployed successfully!"
        echo "🔗 Public IP: $PUBLIC_IP"
        echo "🔗 Health Check: http://$PUBLIC_IP:8080/health"
        echo "🔗 WebSocket: ws://$PUBLIC_IP:8080/ws/interview/{session_id}"
    else
        echo "⚠️ Could not retrieve network interface ID"
    fi
else
    echo "⚠️ No tasks running yet"
fi

echo "🎉 Deployment completed!" 