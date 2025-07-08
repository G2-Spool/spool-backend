#!/bin/bash

# Monitor CodeBuild progress
export AWS_PROFILE=spool
export AWS_PAGER=""

BUILD_ID="spool-backend-build:4f90cb8c-ba17-4fed-82d1-b0d7986312aa"

echo "🚀 Monitoring CodeBuild deployment..."
echo "Build ID: $BUILD_ID"
echo ""

while true; do
    STATUS=$(aws codebuild batch-get-builds --ids $BUILD_ID --query 'builds[0].{BuildStatus:buildStatus,CurrentPhase:currentPhase}' --output text)
    BUILD_STATUS=$(echo $STATUS | awk '{print $1}')
    CURRENT_PHASE=$(echo $STATUS | awk '{print $2}')
    
    echo "$(date): Status: $BUILD_STATUS | Phase: $CURRENT_PHASE"
    
    if [ "$BUILD_STATUS" = "SUCCEEDED" ] || [ "$BUILD_STATUS" = "FAILED" ] || [ "$BUILD_STATUS" = "STOPPED" ]; then
        echo ""
        echo "🎉 Build completed with status: $BUILD_STATUS"
        break
    fi
    
    sleep 30
done

echo ""
echo "Final build details:"
aws codebuild batch-get-builds --ids $BUILD_ID --query 'builds[0].{BuildStatus:buildStatus,CurrentPhase:currentPhase,StartTime:startTime,EndTime:endTime}' --output table
