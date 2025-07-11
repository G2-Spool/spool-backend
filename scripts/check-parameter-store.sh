#!/bin/bash

# Script to check AWS Parameter Store for necessary configurations
# This helps verify all required parameters are in place for the Lambda integration

set -e

echo "Checking AWS Parameter Store for spool-interview-service configurations..."
echo "============================================================"

# Function to check parameter
check_parameter() {
    local param_name=$1
    local description=$2
    
    echo -n "Checking $param_name ($description)... "
    
    value=$(aws ssm get-parameter --name "$param_name" --with-decryption --query 'Parameter.Value' --output text 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$value" = "NOT_FOUND" ]; then
        echo "❌ NOT FOUND"
        return 1
    else
        echo "✅ EXISTS"
        return 0
    fi
}

# Track missing parameters
missing_params=()

echo ""
echo "Checking Lambda-related parameters:"
echo "-----------------------------------"

# Check for Lambda function configuration
if ! check_parameter "/spool/lambda/create-thread/function-name" "Lambda function name"; then
    missing_params+=("/spool/lambda/create-thread/function-name")
fi

if ! check_parameter "/spool/lambda/create-thread/region" "Lambda region"; then
    missing_params+=("/spool/lambda/create-thread/region")
fi

echo ""
echo "Checking database parameters:"
echo "-----------------------------"

# Check for RDS parameters
if ! check_parameter "/spool/rds/host" "RDS hostname"; then
    missing_params+=("/spool/rds/host")
fi

if ! check_parameter "/spool/rds/port" "RDS port"; then
    missing_params+=("/spool/rds/port")
fi

if ! check_parameter "/spool/rds/database" "Database name"; then
    missing_params+=("/spool/rds/database")
fi

if ! check_parameter "/spool/rds/username" "Database username"; then
    missing_params+=("/spool/rds/username")
fi

if ! check_parameter "/spool/rds/password" "Database password"; then
    missing_params+=("/spool/rds/password")
fi

echo ""
echo "Checking Cognito parameters:"
echo "----------------------------"

# Check for Cognito parameters
if ! check_parameter "/spool/cognito/user-pool-id" "Cognito User Pool ID"; then
    missing_params+=("/spool/cognito/user-pool-id")
fi

if ! check_parameter "/spool/cognito/client-id" "Cognito Client ID"; then
    missing_params+=("/spool/cognito/client-id")
fi

echo ""
echo "Checking API Gateway parameters:"
echo "--------------------------------"

# Check for API Gateway parameters
if ! check_parameter "/spool/api/gateway-url" "API Gateway URL"; then
    missing_params+=("/spool/api/gateway-url")
fi

if ! check_parameter "/spool/api/api-key" "API Key"; then
    missing_params+=("/spool/api/api-key")
fi

echo ""
echo "Checking ECS/ECR parameters:"
echo "----------------------------"

# Check for ECS/ECR parameters
if ! check_parameter "/spool/ecs/cluster-name" "ECS Cluster name"; then
    missing_params+=("/spool/ecs/cluster-name")
fi

if ! check_parameter "/spool/ecr/repository-uri" "ECR Repository URI"; then
    missing_params+=("/spool/ecr/repository-uri")
fi

echo ""
echo "============================================================"
echo "Summary:"
echo ""

if [ ${#missing_params[@]} -eq 0 ]; then
    echo "✅ All checked parameters exist in Parameter Store!"
else
    echo "❌ Missing parameters (${#missing_params[@]}):"
    echo ""
    for param in "${missing_params[@]}"; do
        echo "  - $param"
    done
    echo ""
    echo "To add missing parameters, use:"
    echo "aws ssm put-parameter --name <parameter-name> --value <value> --type SecureString"
fi

echo ""
echo "Note: Some parameters might not be required for your specific setup."
echo "The Lambda integration specifically needs:"
echo "- Cognito User Pool ID (for authentication)"
echo "- AWS credentials (usually provided by IAM role)"
echo ""
echo "The Lambda function name is hardcoded as 'spool-create-thread' in the integration."