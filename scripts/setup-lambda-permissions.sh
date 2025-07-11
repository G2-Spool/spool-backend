#!/bin/bash

# Script to add Lambda invocation permissions to ECS task role
# This allows the spool-interview-service to invoke the spool-create-thread Lambda function

set -e

echo "Setting up Lambda invocation permissions for ECS task role..."

# Variables
POLICY_NAME="SpoolECSLambdaInvokePolicy"
ROLE_NAME="ecsTaskRole"
POLICY_FILE="../iam-lambda-policy.json"

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if the policy already exists
echo "Checking if policy already exists..."
EXISTING_POLICY=$(aws iam list-attached-role-policies --role-name $ROLE_NAME --query "AttachedPolicies[?PolicyName=='$POLICY_NAME'].PolicyArn" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_POLICY" ]; then
    echo "Policy already attached to role. Updating..."
    # Get the policy ARN
    POLICY_ARN=$EXISTING_POLICY
    
    # Create a new policy version
    aws iam create-policy-version \
        --policy-arn "$POLICY_ARN" \
        --policy-document file://$POLICY_FILE \
        --set-as-default
    
    echo "Policy updated successfully!"
else
    echo "Creating new policy..."
    # Create the policy
    POLICY_ARN=$(aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://$POLICY_FILE \
        --description "Allows ECS tasks to invoke spool-create-thread Lambda function" \
        --query 'Policy.Arn' \
        --output text)
    
    echo "Attaching policy to role..."
    # Attach the policy to the role
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "$POLICY_ARN"
    
    echo "Policy attached successfully!"
fi

echo ""
echo "✅ Lambda invocation permissions configured successfully!"
echo "Policy ARN: $POLICY_ARN"
echo ""
echo "The ECS task role can now invoke the spool-create-thread Lambda function."
echo ""
echo "Next steps:"
echo "1. Redeploy the ECS service to pick up the new permissions"
echo "2. Test the Lambda integration from the interview service"