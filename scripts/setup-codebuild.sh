#!/bin/bash

# Setup script for AWS CodeBuild
# This script helps create the necessary IAM role and CodeBuild project

set -e

echo "Setting up CodeBuild for Spool Backend..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "Using AWS Account: $ACCOUNT_ID"
echo "Using Region: $REGION"

# Create IAM role for CodeBuild
echo "Creating IAM role for CodeBuild..."

cat > /tmp/codebuild-trust-policy.json <<EOF
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
EOF

aws iam create-role \
    --role-name codebuild-spool-backend-service-role \
    --assume-role-policy-document file:///tmp/codebuild-trust-policy.json \
    || echo "Role already exists"

# Attach necessary policies
echo "Attaching policies to IAM role..."

cat > /tmp/codebuild-policy.json <<EOF
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
EOF

aws iam put-role-policy \
    --role-name codebuild-spool-backend-service-role \
    --policy-name codebuild-spool-backend-policy \
    --policy-document file:///tmp/codebuild-policy.json

# Update CodeBuild project configuration
echo "Updating CodeBuild project configuration..."
sed -i.bak "s/YOUR_ACCOUNT_ID/${ACCOUNT_ID}/g" ../codebuild-project.json

# Create Parameter Store entry for OpenAI API key
echo "Setting up Parameter Store..."
echo "Please enter your OpenAI API key:"
read -s OPENAI_API_KEY

aws ssm put-parameter \
    --name "/spool/openai-api-key" \
    --value "$OPENAI_API_KEY" \
    --type "SecureString" \
    --overwrite \
    || echo "Parameter already exists"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create the CodeBuild project:"
echo "   aws codebuild create-project --cli-input-json file://codebuild-project.json"
echo ""
echo "2. Set up GitHub webhook:"
echo "   - Go to your GitHub repository settings"
echo "   - Add a webhook for CodeBuild"
echo "   - Or use: aws codebuild import-source-credentials --token <github-token> --server-type GITHUB --auth-type PERSONAL_ACCESS_TOKEN"
echo ""
echo "3. Start a build:"
echo "   aws codebuild start-build --project-name spool-backend-build"

# Clean up
rm -f /tmp/codebuild-trust-policy.json /tmp/codebuild-policy.json 