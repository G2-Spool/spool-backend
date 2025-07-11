#!/bin/bash

# Script to set up EventBridge rule for CodeBuild automatic triggers
# This is an alternative to webhooks when GitHub OAuth issues prevent webhook creation

set -e

PROJECT_NAME="spool-exercise-service-build"
REGION="us-east-1"
RULE_NAME="spool-exercise-service-github-trigger"
CONNECTION_ARN="arn:aws:codeconnections:us-east-1:560281064968:connection/181bfd6a-5a13-4065-a6e1-6981a86ea629"

echo "Setting up EventBridge rule for CodeBuild project: $PROJECT_NAME"
echo "=================================================="

# Get CodeBuild project ARN
PROJECT_ARN=$(aws codebuild batch-get-projects --names $PROJECT_NAME --region $REGION --query 'projects[0].arn' --output text)
echo "CodeBuild Project ARN: $PROJECT_ARN"

# Get the service role ARN
SERVICE_ROLE_ARN=$(aws codebuild batch-get-projects --names $PROJECT_NAME --region $REGION --query 'projects[0].serviceRole' --output text)
echo "Service Role ARN: $SERVICE_ROLE_ARN"

# Create EventBridge rule for GitHub push events
echo ""
echo "Creating EventBridge rule..."

# Create the event pattern
EVENT_PATTERN=$(cat <<EOF
{
  "source": ["aws.codeconnections"],
  "detail-type": ["CodeConnections Repository State Change"],
  "detail": {
    "event": ["push", "pullRequestMerged"],
    "connectionArn": ["$CONNECTION_ARN"],
    "repositoryName": ["G2-Spool/spool-exercise-service"]
  }
}
EOF
)

# Create the rule
aws events put-rule \
    --name "$RULE_NAME" \
    --description "Trigger CodeBuild for spool-exercise-service on GitHub push" \
    --event-pattern "$EVENT_PATTERN" \
    --state ENABLED \
    --region $REGION

echo "✅ EventBridge rule created"

# Add CodeBuild as target
echo ""
echo "Adding CodeBuild project as target..."

# Create role assume policy document
ASSUME_ROLE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)

# Create role policy document
ROLE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codebuild:StartBuild"
      ],
      "Resource": "$PROJECT_ARN"
    }
  ]
}
EOF
)

# Check if role exists
ROLE_NAME="EventBridgeCodeBuildRole-$PROJECT_NAME"
ROLE_EXISTS=$(aws iam get-role --role-name $ROLE_NAME 2>/dev/null || echo "NOT_EXISTS")

if [ "$ROLE_EXISTS" = "NOT_EXISTS" ]; then
    echo "Creating IAM role for EventBridge..."
    
    # Create the role
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$ASSUME_ROLE_POLICY" \
        --description "Role for EventBridge to trigger CodeBuild"
    
    # Attach the policy
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "CodeBuildStartBuildPolicy" \
        --policy-document "$ROLE_POLICY"
    
    echo "✅ IAM role created"
    
    # Wait for role to be available
    echo "Waiting for role to be available..."
    sleep 10
else
    echo "✅ IAM role already exists"
fi

# Get the role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

# Add target to the rule
aws events put-targets \
    --rule "$RULE_NAME" \
    --targets "Id"="1","Arn"="$PROJECT_ARN","RoleArn"="$ROLE_ARN" \
    --region $REGION

echo "✅ CodeBuild project added as target"

# Alternative: Manual webhook setup instructions
echo ""
echo "=================================================="
echo "EventBridge rule setup complete!"
echo ""
echo "The rule will trigger builds on:"
echo "- Push to any branch"
echo "- Pull request merge"
echo ""
echo "If you prefer to use GitHub webhooks instead:"
echo "1. Go to https://github.com/G2-Spool/spool-exercise-service/settings/hooks"
echo "2. Click 'Add webhook'"
echo "3. Use the webhook URL from CodeBuild console"
echo "4. Set content type to 'application/json'"
echo "5. Select events: Push, Pull Request"
echo ""
echo "To test the EventBridge rule:"
echo "1. Make a small change to the repository"
echo "2. Push the change to GitHub"
echo "3. Check CodeBuild console for triggered build"
echo ""
echo "To view the rule:"
echo "aws events describe-rule --name $RULE_NAME --region $REGION"