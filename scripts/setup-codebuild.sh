#!/bin/bash

# Convenient wrapper script that sets the AWS profile and runs the setup

export AWS_PROFILE=spool
export AWS_PAGER=""

echo "Using AWS profile: $AWS_PROFILE"
echo "Running CodeBuild setup..."
echo ""

# Run the main setup script
./scripts/setup-codebuild-working.sh
