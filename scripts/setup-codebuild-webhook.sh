#!/bin/bash

# Script to set up CodeBuild webhook for automatic builds on push
# This script should be run by a user with appropriate GitHub OAuth permissions

set -e

PROJECT_NAME="spool-exercise-service-build"
REGION="us-east-1"

echo "Setting up CodeBuild webhook for project: $PROJECT_NAME"
echo "============================================"

# Function to check if webhook exists
check_webhook() {
    echo "Checking if webhook already exists..."
    WEBHOOK=$(aws codebuild batch-get-projects --names $PROJECT_NAME --region $REGION --query 'projects[0].webhook.url' --output text 2>/dev/null || echo "None")
    
    if [ "$WEBHOOK" != "None" ] && [ "$WEBHOOK" != "null" ]; then
        echo "✅ Webhook already exists: $WEBHOOK"
        return 0
    else
        echo "❌ No webhook found"
        return 1
    fi
}

# Function to create webhook
create_webhook() {
    echo ""
    echo "Creating webhook..."
    
    # Try to create webhook with filter groups for push events
    if aws codebuild create-webhook \
        --project-name $PROJECT_NAME \
        --region $REGION \
        --filter-groups '[[{"type":"EVENT","pattern":"PUSH,PULL_REQUEST_MERGED"}]]' 2>/dev/null; then
        
        echo "✅ Webhook created successfully!"
        return 0
    else
        echo "❌ Failed to create webhook with filter groups, trying without..."
        
        # Try without filter groups (will trigger on all events)
        if aws codebuild create-webhook \
            --project-name $PROJECT_NAME \
            --region $REGION 2>/dev/null; then
            
            echo "✅ Webhook created successfully (triggers on all events)!"
            return 0
        else
            echo "❌ Failed to create webhook"
            return 1
        fi
    fi
}

# Function to update webhook
update_webhook() {
    echo ""
    echo "Updating webhook filter groups..."
    
    if aws codebuild update-webhook \
        --project-name $PROJECT_NAME \
        --region $REGION \
        --filter-groups '[[{"type":"EVENT","pattern":"PUSH,PULL_REQUEST_MERGED"}]]' 2>/dev/null; then
        
        echo "✅ Webhook updated successfully!"
        return 0
    else
        echo "❌ Failed to update webhook"
        return 1
    fi
}

# Main execution
echo ""
echo "Prerequisites:"
echo "- Ensure you have GitHub OAuth permissions configured"
echo "- The CodeBuild project must have 'reportBuildStatus' enabled"
echo ""

# Check if webhook exists
if check_webhook; then
    echo ""
    echo "Webhook already configured. Would you like to update it? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        update_webhook
    fi
else
    # Create webhook
    create_webhook
fi

# Display final webhook configuration
echo ""
echo "Final webhook configuration:"
echo "---------------------------"
aws codebuild batch-get-projects --names $PROJECT_NAME --region $REGION --query 'projects[0].webhook' --output json

echo ""
echo "============================================"
echo "Setup complete!"
echo ""
echo "The webhook will trigger builds on:"
echo "- Push to any branch"
echo "- Pull request merge"
echo ""
echo "To test the webhook:"
echo "1. Make a small change to the repository"
echo "2. Push the change to GitHub"
echo "3. Check CodeBuild console for triggered build"
echo ""
echo "If the webhook creation failed due to OAuth issues:"
echo "1. Ensure the GitHub connection is properly configured"
echo "2. You may need to manually add the webhook in GitHub:"
echo "   - Go to repository Settings > Webhooks"
echo "   - Add webhook URL from CodeBuild project"
echo "   - Set content type to 'application/json'"
echo "   - Select events: Push, Pull Request"