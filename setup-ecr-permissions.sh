#!/bin/bash

set -e

USER_NAME="ShpoolBot"
POLICY_NAME="ECRFullAccess"

echo "🔐 Setting up ECR permissions for user: $USER_NAME"

# Create ECR policy
cat > ecr-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:DescribeRepositories",
                "ecr:DescribeImages",
                "ecr:BatchDeleteImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Create IAM policy
echo "📋 Creating IAM policy..."
aws iam create-policy --policy-name "$POLICY_NAME" --policy-document file://ecr-policy.json 2>/dev/null || echo "Policy already exists"

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach policy to user
echo "🔗 Attaching policy to user..."
aws iam attach-user-policy --user-name "$USER_NAME" --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME"

# Clean up
rm ecr-policy.json

echo "✅ ECR permissions setup completed!"
echo "🔗 User '$USER_NAME' now has ECR access"
echo ""
echo "Next steps:"
echo "1. Run './build-and-push.sh' to build and push the Docker image"
echo "2. Run './deploy-ecs-service.sh' to deploy the ECS service" 