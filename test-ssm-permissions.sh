#!/bin/bash

# Test script to check SSM permissions

export AWS_PROFILE=spool
export AWS_PAGER=""

echo "Testing SSM permissions..."
echo "Account: $(aws sts get-caller-identity --query Account --output text)"
echo "User: $(aws sts get-caller-identity --query Arn --output text)"
echo ""

echo "Testing describe-parameters..."
if aws ssm describe-parameters --parameter-filters "Key=Name,Values=/spool/" >/dev/null 2>&1; then
    echo "✅ describe-parameters: PASS"
else
    echo "❌ describe-parameters: FAIL"
fi

echo ""
echo "Testing put-parameter (dry run)..."
if aws ssm put-parameter --name "/spool/test-param" --value "test" --type "String" --dry-run >/dev/null 2>&1; then
    echo "✅ put-parameter: PASS"
else
    echo "❌ put-parameter: FAIL - Need to grant SSM permissions"
    echo ""
    echo "Go to AWS Console → IAM → Users → ShpoolBot → Add permissions"
    echo "Attach policy: AmazonSSMFullAccess"
fi

echo ""
echo "Once permissions are granted, run:"
echo "aws ssm put-parameter --name '/spool/openai-api-key' --value 'YOUR_API_KEY' --type 'SecureString'"
