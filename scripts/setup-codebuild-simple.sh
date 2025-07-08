#!/bin/bash

# Simplified setup script for AWS CodeBuild
# This script creates the necessary IAM role and helps with CodeBuild setup

set -e

echo "Setting up CodeBuild for Spool Backend..."

# Set default values
ACCOUNT_ID=${AWS_ACCOUNT_ID:-""}
REGION=${AWS_DEFAULT_REGION:-us-east-1}

# If ACCOUNT_ID is not set, try to get it
if [ -z "$ACCOUNT_ID" ]; then
    echo "Please provide your AWS Account ID:"
    read ACCOUNT_ID
fi

echo "Using AWS Account: $ACCOUNT_ID"
echo "Using Region: $REGION"

# Create IAM role trust policy
echo "Creating IAM role trust policy..."
cat > /tmp/codebuild-trust-policy.json <<EOFINNER
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
EOFINNER

# Create IAM role
echo "Creating IAM role..."
echo "Run this command:"
echo "aws iam create-role --role-name codebuild-spool-backend-service-role --assume-role-policy-document file:///tmp/codebuild-trust-policy.json"
echo ""

# Create IAM policy
echo "Creating IAM policy document..."
cat > /tmp/codebuild-policy.json <<EOFINNER
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
      "Resource": "arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:/aws/codebuild/*"
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
      "Resource": "arn:aws:ssm:${REGION}:${ACCOUNT_ID}:parameter/spool/*"
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
EOFINNER

echo ""
echo "Attach the policy to the role:"
echo "aws iam put-role-policy --role-name codebuild-spool-backend-service-role --policy-name codebuild-spool-backend-policy --policy-document file:///tmp/codebuild-policy.json"
echo ""

# Update CodeBuild project configuration
echo "Updating CodeBuild project configuration..."
sed -i.bak "s/YOUR_ACCOUNT_ID/${ACCOUNT_ID}/g" ../codebuild-project.json

echo ""
echo "Next steps:"
echo "1. Create Parameter Store entry for OpenAI API key:"
echo "   aws ssm put-parameter --name \"/spool/openai-api-key\" --value \"YOUR_OPENAI_API_KEY\" --type \"SecureString\""
echo ""
echo "2. Create the CodeBuild project:"
echo "   aws codebuild create-project --cli-input-json file://codebuild-project.json"
echo ""
echo "3. Set up GitHub webhook (via GitHub or AWS Console)"
echo ""
echo "4. Start a build:"
echo "   aws codebuild start-build --project-name spool-backend-build"
echo ""
echo "Policy files saved in /tmp/ for reference"
