#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SpoolEcsStack } from '../lib/spool-ecs-stack';
import { AwsSolutionsChecks } from 'cdk-nag';
import { Aspects } from 'aws-cdk-lib';

const app = new cdk.App();
const stack = new SpoolEcsStack(app, 'SpoolEcsStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
});

// Apply CDK Nag checks
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));