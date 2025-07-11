# CodeBuild Automatic Trigger Setup

## Overview

The `spool-exercise-service-build` CodeBuild project is now configured to automatically trigger builds when code is pushed to the GitHub repository. Due to GitHub OAuth limitations with webhooks, we've implemented an EventBridge-based solution using AWS CodeConnections.

## Current Configuration

### CodeBuild Project
- **Project Name**: `spool-exercise-service-build`
- **Source**: GitHub repository `https://github.com/G2-Spool/spool-exercise-service`
- **Authentication**: AWS CodeConnections (connection: `Spool`)
- **Build Status Reporting**: Enabled

### EventBridge Rule
- **Rule Name**: `spool-exercise-service-github-trigger`
- **Triggers On**:
  - Push to any branch
  - Pull request merge
- **Target**: CodeBuild project `spool-exercise-service-build`

### IAM Configuration
- **ShpoolBot User**: Added `CodeConnectionsAccess` inline policy for webhook management
- **EventBridge Role**: `EventBridgeCodeBuildRole-spool-exercise-service-build` with permissions to start builds

## How It Works

1. Developer pushes code to GitHub repository
2. GitHub notifies AWS CodeConnections about the push event
3. CodeConnections generates an EventBridge event
4. EventBridge rule catches the event and triggers CodeBuild
5. CodeBuild pulls the latest code and builds the Docker image
6. Built image is pushed to ECR repository

## Testing the Setup

To test if automatic builds are working:

```bash
# Make a small change to the repository
echo "# Test commit" >> README.md
git add README.md
git commit -m "Test automatic build trigger"
git push origin main

# Check if build was triggered
aws codebuild list-builds-for-project \
  --project-name spool-exercise-service-build \
  --region us-east-1 \
  --max-items 1
```

## Monitoring Builds

### AWS Console
1. Go to CodeBuild console: https://console.aws.amazon.com/codesuite/codebuild/projects
2. Select `spool-exercise-service-build`
3. View build history and logs

### CLI Commands
```bash
# List recent builds
aws codebuild list-builds-for-project \
  --project-name spool-exercise-service-build \
  --region us-east-1

# Get build details
aws codebuild batch-get-builds \
  --ids <build-id> \
  --region us-east-1

# View build logs (CloudWatch)
aws logs tail /aws/codebuild/spool-exercise-service-build --follow
```

## Troubleshooting

### Build Not Triggering
1. Check EventBridge rule is enabled:
   ```bash
   aws events describe-rule --name spool-exercise-service-github-trigger --region us-east-1
   ```

2. Verify CodeConnections is working:
   ```bash
   aws codeconnections get-connection \
     --connection-arn arn:aws:codeconnections:us-east-1:560281064968:connection/181bfd6a-5a13-4065-a6e1-6981a86ea629
   ```

3. Check EventBridge rule metrics in CloudWatch

### Build Failures
1. Check build logs in CodeBuild console
2. Common issues:
   - ECR login failures: Check IAM permissions
   - Docker build errors: Review Dockerfile
   - Push failures: Verify ECR repository exists

## Manual Build Trigger

If automatic triggers fail, you can manually start a build:

```bash
aws codebuild start-build \
  --project-name spool-exercise-service-build \
  --region us-east-1
```

## Alternative: GitHub Webhooks

If you prefer to use GitHub webhooks directly:

1. Go to https://github.com/G2-Spool/spool-exercise-service/settings/hooks
2. Click "Add webhook"
3. Get webhook URL from CodeBuild:
   ```bash
   aws codebuild batch-get-projects --names spool-exercise-service-build \
     --query 'projects[0].webhook.url' --output text
   ```
4. Configure webhook:
   - Payload URL: (from step 3)
   - Content type: `application/json`
   - Events: Select "Pushes" and "Pull requests"

## Maintenance

### Update Trigger Configuration
```bash
# Update EventBridge rule
aws events put-rule \
  --name spool-exercise-service-github-trigger \
  --event-pattern '{"source":["aws.codeconnections"],...}' \
  --region us-east-1
```

### Disable/Enable Triggers
```bash
# Disable
aws events disable-rule --name spool-exercise-service-github-trigger --region us-east-1

# Enable
aws events enable-rule --name spool-exercise-service-github-trigger --region us-east-1
```

### Delete Trigger Setup
```bash
# Remove EventBridge rule
aws events remove-targets --rule spool-exercise-service-github-trigger --ids 1 --region us-east-1
aws events delete-rule --name spool-exercise-service-github-trigger --region us-east-1

# Delete IAM role
aws iam delete-role-policy \
  --role-name EventBridgeCodeBuildRole-spool-exercise-service-build \
  --policy-name CodeBuildStartBuildPolicy
aws iam delete-role --role-name EventBridgeCodeBuildRole-spool-exercise-service-build
```

## Security Considerations

- CodeConnections uses OAuth for secure GitHub access
- Build status is reported back to GitHub PRs
- ECR images are scanned for vulnerabilities
- All build logs are stored in CloudWatch
- IAM roles follow least privilege principle

## Next Steps

1. Configure build notifications (SNS/Slack)
2. Add build caching for faster builds
3. Implement multi-stage builds for optimization
4. Set up automatic ECS deployment after successful builds