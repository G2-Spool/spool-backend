#!/bin/bash

# Working setup script for AWS CodeBuild
# This script creates the necessary IAM role and CodeBuild project

set -e

# Fix AWS CLI pager issue
export AWS_PAGER=""

echo "Setting up CodeBuild for Spool Backend..."

# Get current AWS account ID
echo "Getting AWS Account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$ACCOUNT_ID" ]; then
    echo "Error: Could not retrieve AWS Account ID. Please check your AWS credentials."
    exit 1
fi

echo "Using AWS Account: $ACCOUNT_ID"
echo "Using Region: ${AWS_DEFAULT_REGION:-us-east-1}"

# Create IAM role trust policy
echo "Creating IAM role trust policy..."
cat > /tmp/codebuild-trust-policy.json <<EOP
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOP

# Create IAM role
echo "Creating IAM role..."
if aws iam get-role --role-name codebuild-spool-backend-service-role >/dev/null 2>&1; then
    echo "Role already exists, skipping creation"
else
    aws iam create-role \
        --role-name codebuild-spool-backend-service-role \
        --assume-role-policy-document file:///tmp/codebuild-trust-policy.json
    echo "IAM role created successfully"
fi

# Create IAM policy
echo "Creating IAM policy document..."
cat > /tmp/codebuild-policy.json <<EOP
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${AWS_DEFAULT_REGION:-us-east-1}:${ACCOUNT_ID}:log-group:/aws/codebuild/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:CreateRepository",
        "ecr:DescribeRepositories"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:RegisterTaskDefinition",
        "ecs:DescribeTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:${AWS_DEFAULT_REGION:-us-east-1}:${ACCOUNT_ID}:parameter/spool/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::cdktoolkit-stagingbucket-*/*"
    }
  ]
}
EOP

echo "Attaching policy to role..."
aws iam put-role-policy \
    --role-name codebuild-spool-backend-service-role \
    --policy-name codebuild-spool-backend-policy \
    --policy-document file:///tmp/codebuild-policy.json

echo "IAM policy attached successfully"

# Update CodeBuild project configuration
echo "Updating CodeBuild project configuration..."
if [ -f "codebuild-project.json" ]; then
    sed -i.bak "s/YOUR_ACCOUNT_ID/${ACCOUNT_ID}/g" codebuild-project.json
    echo "CodeBuild project configuration updated"
else
    echo "Warning: codebuild-project.json not found"
fi

# Create the CodeBuild project
echo "Creating CodeBuild project..."
if aws codebuild batch-get-projects --names spool-backend-build >/dev/null 2>&1; then
    echo "CodeBuild project already exists, skipping creation"
else
    aws codebuild create-project --cli-input-json file://codebuild-project.json
    echo "CodeBuild project created successfully"
fi

echo ""
echo "Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Create Parameter Store entry for OpenAI API key:"
echo "   aws ssm put-parameter --name \"/spool/openai-api-key\" --value \"YOUR_OPENAI_API_KEY\" --type \"SecureString\""
echo ""
echo "2. Set up GitHub webhook (via GitHub or AWS Console)"
echo ""
echo "3. Start a build:"
echo "   aws codebuild start-build --project-name spool-backend-build"
echo ""
echo "Policy files saved in /tmp/ for reference"
