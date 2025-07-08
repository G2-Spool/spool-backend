import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as efs from 'aws-cdk-lib/aws-efs';
import * as servicediscovery from 'aws-cdk-lib/aws-servicediscovery';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export class SpoolEcsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC for our containers
    const vpc = new ec2.Vpc(this, 'SpoolVpc', {
      maxAzs: 2,
      natGateways: 1,
    });

    // ECS Cluster
    const cluster = new ecs.Cluster(this, 'SpoolCluster', {
      vpc,
      containerInsights: true,
      clusterName: 'spool-mvp',
    });

    // Service Discovery Namespace
    const namespace = new servicediscovery.PrivateDnsNamespace(this, 'SpoolNamespace', {
      name: 'spool.local',
      vpc,
      description: 'Service discovery for Spool services',
    });

    // EFS for LangFlow persistence
    const langflowFileSystem = new efs.FileSystem(this, 'LangflowStorage', {
      vpc,
      performanceMode: efs.PerformanceMode.GENERAL_PURPOSE,
      encrypted: true,
      lifecyclePolicy: efs.LifecyclePolicy.AFTER_30_DAYS,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For development
    });

    // Security Groups
    const albSecurityGroup = new ec2.SecurityGroup(this, 'AlbSecurityGroup', {
      vpc,
      description: 'Security group for ALB',
      allowAllOutbound: true,
    });

    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow HTTPS'
    );

    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'Allow HTTP'
    );

    const interviewSecurityGroup = new ec2.SecurityGroup(this, 'InterviewSecurityGroup', {
      vpc,
      description: 'Security group for Interview service',
      allowAllOutbound: true,
    });

    const langflowSecurityGroup = new ec2.SecurityGroup(this, 'LangflowSecurityGroup', {
      vpc,
      description: 'Security group for Langflow service',
      allowAllOutbound: true,
    });

    // Allow ALB to reach services
    interviewSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(8080),
      'Allow from ALB'
    );

    langflowSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(7860),
      'Allow from ALB'
    );

    // Allow services to communicate
    interviewSecurityGroup.addIngressRule(
      langflowSecurityGroup,
      ec2.Port.allTraffic(),
      'Allow from Langflow'
    );

    langflowSecurityGroup.addIngressRule(
      interviewSecurityGroup,
      ec2.Port.allTraffic(),
      'Allow from Interview'
    );

    // ALB
    const alb = new elbv2.ApplicationLoadBalancer(this, 'SpoolAlb', {
      vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
    });

    // Secrets for OpenAI API Key
    const openaiApiKey = new secretsmanager.Secret(this, 'OpenAIApiKey', {
      description: 'OpenAI API Key for voice agent',
      secretName: 'spool/openai-api-key',
    });

    // Task Definitions
    const interviewTaskDefinition = new ecs.FargateTaskDefinition(this, 'InterviewTaskDef', {
      memoryLimitMiB: 1024,
      cpu: 512,
    });

    const langflowTaskDefinition = new ecs.FargateTaskDefinition(this, 'LangflowTaskDef', {
      memoryLimitMiB: 2048,
      cpu: 1024,
    });

    // Add EFS volume to Langflow task
    langflowTaskDefinition.addVolume({
      name: 'langflow-storage',
      efsVolumeConfiguration: {
        fileSystemId: langflowFileSystem.fileSystemId,
        transitEncryption: 'ENABLED',
      },
    });

    // Log Groups
    const interviewLogGroup = new logs.LogGroup(this, 'InterviewLogGroup', {
      logGroupName: '/ecs/interview-service',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const langflowLogGroup = new logs.LogGroup(this, 'LangflowLogGroup', {
      logGroupName: '/ecs/langflow-service',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Interview Container
    const interviewContainer = interviewTaskDefinition.addContainer('interview', {
      image: ecs.ContainerImage.fromAsset('../../services/interview'),
      environment: {
        LANGFLOW_URL: 'http://langflow.spool.local:7860',
        ENV: 'production',
      },
      secrets: {
        OPENAI_API_KEY: ecs.Secret.fromSecretsManager(openaiApiKey),
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'interview',
        logGroup: interviewLogGroup,
      }),
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8080/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
      },
    });

    interviewContainer.addPortMappings({
      containerPort: 8080,
      protocol: ecs.Protocol.TCP,
    });

    // Langflow Container
    const langflowContainer = langflowTaskDefinition.addContainer('langflow', {
      image: ecs.ContainerImage.fromRegistry('langflowai/langflow:latest'),
      environment: {
        LANGFLOW_DATABASE_URL: 'sqlite:////mnt/efs/langflow.db',
        LANGFLOW_WORKERS: '2',
        LANGFLOW_AUTO_LOGIN: 'false',
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'langflow',
        logGroup: langflowLogGroup,
      }),
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:7860/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
      },
    });

    langflowContainer.addPortMappings({
      containerPort: 7860,
      protocol: ecs.Protocol.TCP,
    });

    langflowContainer.addMountPoints({
      sourceVolume: 'langflow-storage',
      containerPath: '/mnt/efs',
      readOnly: false,
    });

    // Target Groups
    const interviewTargetGroup = new elbv2.ApplicationTargetGroup(this, 'InterviewTargetGroup', {
      vpc,
      port: 8080,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 2,
      },
    });

    const langflowTargetGroup = new elbv2.ApplicationTargetGroup(this, 'LangflowTargetGroup', {
      vpc,
      port: 7860,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 2,
      },
    });

    // ALB Listeners
    const listener = alb.addListener('Listener', {
      port: 80,
      defaultAction: elbv2.ListenerAction.fixedResponse(404, {
        contentType: 'text/plain',
        messageBody: 'Not Found',
      }),
    });

    listener.addTargetGroups('InterviewTarget', {
      targetGroups: [interviewTargetGroup],
      conditions: [elbv2.ListenerCondition.pathPatterns(['/interview/*', '/api/interview/*'])],
      priority: 1,
    });

    listener.addTargetGroups('LangflowTarget', {
      targetGroups: [langflowTargetGroup],
      conditions: [elbv2.ListenerCondition.pathPatterns(['/langflow/*', '/api/langflow/*'])],
      priority: 2,
    });

    // Interview Service
    const interviewService = new ecs.FargateService(this, 'InterviewService', {
      cluster,
      taskDefinition: interviewTaskDefinition,
      desiredCount: 1,
      serviceName: 'interview-service',
      securityGroups: [interviewSecurityGroup],
      cloudMapOptions: {
        name: 'interview',
        cloudMapNamespace: namespace,
      },
    });

    interviewService.registerLoadBalancerTargets({
      containerName: 'interview',
      containerPort: 8080,
      newTargetGroupId: 'InterviewECS',
      targetGroupArn: interviewTargetGroup.targetGroupArn,
    });

    // Auto-scaling for Interview Service
    const interviewScaling = interviewService.autoScaleTaskCount({
      minCapacity: 0,
      maxCapacity: 5,
    });

    interviewScaling.scaleOnCpuUtilization('CpuScaling', {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // Langflow Service
    const langflowService = new ecs.FargateService(this, 'LangflowService', {
      cluster,
      taskDefinition: langflowTaskDefinition,
      desiredCount: 1,
      serviceName: 'langflow-service',
      securityGroups: [langflowSecurityGroup],
      cloudMapOptions: {
        name: 'langflow',
        cloudMapNamespace: namespace,
      },
    });

    langflowService.registerLoadBalancerTargets({
      containerName: 'langflow',
      containerPort: 7860,
      newTargetGroupId: 'LangflowECS',
      targetGroupArn: langflowTargetGroup.targetGroupArn,
    });

    // Grant EFS permissions to Langflow
    langflowFileSystem.grantReadWrite(langflowTaskDefinition.taskRole);

    // Outputs
    new cdk.CfnOutput(this, 'AlbUrl', {
      value: alb.loadBalancerDnsName,
      description: 'ALB URL',
    });

    new cdk.CfnOutput(this, 'InterviewEndpoint', {
      value: `http://${alb.loadBalancerDnsName}/interview`,
      description: 'Interview Service Endpoint',
    });

    new cdk.CfnOutput(this, 'LangflowEndpoint', {
      value: `http://${alb.loadBalancerDnsName}/langflow`,
      description: 'Langflow Service Endpoint',
    });
  }
} 