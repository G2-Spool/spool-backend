# AWS Permissions Required for Spool Interview Service Deployment

## Overview

The AWS user account needs specific permissions to deploy the Spool interview service infrastructure. The current error shows that the `ShpoolBot` user lacks CloudFormation permissions.

## Required AWS Permissions

### 1. CloudFormation Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:CreateChangeSet",
                "cloudformation:CreateStack",
                "cloudformation:UpdateStack",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeStacks",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStackResources",
                "cloudformation:GetTemplate",
                "cloudformation:ListStacks",
                "cloudformation:TagResource",
                "cloudformation:UntagResource"
            ],
            "Resource": "*"
        }
    ]
}
```

### 2. CDK Bootstrap Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:AttachRolePolicy",
                "iam:PutRolePolicy",
                "iam:PassRole",
                "iam:GetRole",
                "iam:CreatePolicy",
                "iam:GetPolicy",
                "iam:GetPolicyVersion",
                "iam:ListPolicyVersions",
                "s3:CreateBucket",
                "s3:PutBucketPolicy",
                "s3:PutBucketVersioning",
                "s3:PutEncryptionConfiguration",
                "s3:PutBucketPublicAccessBlock",
                "ecr:CreateRepository",
                "ecr:PutRepositoryPolicy",
                "ssm:PutParameter"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. ECS and VPC Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateVpc",
                "ec2:CreateSubnet",
                "ec2:CreateInternetGateway",
                "ec2:CreateNatGateway",
                "ec2:CreateRouteTable",
                "ec2:CreateRoute",
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:AuthorizeSecurityGroupEgress",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeInternetGateways",
                "ec2:DescribeNatGateways",
                "ec2:DescribeRouteTables",
                "ec2:DescribeSecurityGroups",
                "ec2:AllocateAddress",
                "ecs:CreateCluster",
                "ecs:CreateService",
                "ecs:CreateTaskDefinition",
                "ecs:RegisterTaskDefinition",
                "ecs:DescribeClusters",
                "ecs:DescribeServices",
                "ecs:DescribeTaskDefinition",
                "elasticloadbalancing:CreateLoadBalancer",
                "elasticloadbalancing:CreateTargetGroup",
                "elasticloadbalancing:CreateListener",
                "elasticloadbalancing:DescribeLoadBalancers",
                "elasticloadbalancing:DescribeTargetGroups",
                "elasticloadbalancing:DescribeListeners"
            ],
            "Resource": "*"
        }
    ]
}
```

### 4. API Gateway and Secrets Manager
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "apigateway:POST",
                "apigateway:GET",
                "apigateway:PUT",
                "apigateway:DELETE",
                "apigateway:PATCH",
                "secretsmanager:CreateSecret",
                "secretsmanager:UpdateSecret",
                "secretsmanager:DescribeSecret",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutRetentionPolicy",
                "efs:CreateFileSystem",
                "efs:CreateMountTarget",
                "efs:DescribeFileSystems",
                "servicediscovery:CreatePrivateDnsNamespace",
                "servicediscovery:CreateService"
            ],
            "Resource": "*"
        }
    ]
}
```

## Quick Permission Fix

### Option 1: Attach AWS Managed Policy (Quick & Easy)
Attach the `AdministratorAccess` policy to the `ShpoolBot` user temporarily:

```bash
aws iam attach-user-policy \
  --user-name ShpoolBot \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

### Option 2: Create Custom Policy (Recommended for Production)
Create a custom policy with only the required permissions above.

## Deploy Without CDK (Alternative Approach)

If AWS permissions are limited, you can deploy manually:

### 1. Create ECR Repository
```bash
aws ecr create-repository --repository-name spool/interview-service
```

### 2. Build and Push Docker Image
```bash
# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 560281064968.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t 560281064968.dkr.ecr.us-east-1.amazonaws.com/spool/interview-service:latest -f services/interview/Dockerfile services/interview
docker push 560281064968.dkr.ecr.us-east-1.amazonaws.com/spool/interview-service:latest
```

### 3. Use Existing Infrastructure
If you already have:
- A VPC
- An ECS cluster
- An ALB

You can create a new ECS service using the AWS Console or CLI pointing to your Docker image.

## Testing Without Full Deployment

### Local Testing with Docker Compose
```bash
# Test the REST FastRTC service locally
cd spool-interview-service
docker-compose -f docker-compose.dev.yml up --build
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8080/health

# Start interview
curl -X POST http://localhost:8080/api/interview/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test"}'
```

## Next Steps

1. **Get AWS Permissions**: Work with your AWS admin to get the required permissions
2. **Alternative Deployment**: Use the manual deployment approach if CDK is restricted
3. **Local Testing**: Test the FastRTC implementation locally first
4. **Incremental Deployment**: Deploy components one by one if full CDK deployment isn't possible

The REST-based FastRTC implementation is complete and ready to deploy once the AWS permissions are resolved!