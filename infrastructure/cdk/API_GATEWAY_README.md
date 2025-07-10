# API Gateway Configuration for Spool Interview Service

This document explains the AWS CDK configuration for API Gateway v2 that proxies requests to the ECS-hosted FastRTC application.

## Architecture Overview

```
[React Frontend] 
    ↓ HTTPS
[API Gateway v2]
    ↓ VPC Link
[Application Load Balancer]
    ↓ Internal
[ECS Services]
    ├── Interview Service (FastRTC)
    └── Langflow Service
```

## Key Features

### 1. API Gateway v2 (HTTP API)
- Modern, cost-effective HTTP API
- Built-in CORS support
- Lower latency than REST API
- Automatic request validation

### 2. VPC Link Integration
- Secure connection to private ALB
- No internet exposure for backend services
- Traffic stays within AWS network

### 3. CORS Configuration
```typescript
corsPreflight: {
    allowOrigins: ['*'], // Update for production
    allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key'],
    allowMethods: [GET, POST, PUT, DELETE, OPTIONS],
    allowCredentials: true,
    maxAge: Duration.days(1)
}
```

### 4. Route Configuration
- `/api/interview/*` → Interview Service
- `/api/langflow/*` → Langflow Service
- `/api/*` → General catch-all

## Deployment

### Prerequisites
1. AWS CDK CLI installed
2. AWS credentials configured
3. Node.js and npm installed

### Deploy the Stack
```bash
cd infrastructure/cdk
npm install
npm run build
cdk deploy
```

### Stack Outputs
After deployment, you'll get:
- `ApiGatewayUrl`: Base URL for API Gateway
- `ApiGatewayInterviewEndpoint`: Interview service endpoint
- `AlbUrl`: Internal ALB URL (for debugging)

## Frontend Integration

### Update Frontend Configuration
```javascript
// src/config/api.ts
const API_GATEWAY_URL = 'https://xxxxxx.execute-api.region.amazonaws.com';

export const API_ENDPOINTS = {
    interview: {
        start: `${API_GATEWAY_URL}/api/interview/start`,
        offer: (sessionId) => `${API_GATEWAY_URL}/api/interview/${sessionId}/rtc/offer`,
        answer: (sessionId) => `${API_GATEWAY_URL}/api/interview/${sessionId}/rtc/answer`,
        iceCandidate: (sessionId) => `${API_GATEWAY_URL}/api/interview/${sessionId}/rtc/ice-candidate`,
        iceServers: (sessionId) => `${API_GATEWAY_URL}/api/interview/${sessionId}/ice-servers`,
        status: (sessionId) => `${API_GATEWAY_URL}/api/interview/${sessionId}/status`,
        results: (sessionId) => `${API_GATEWAY_URL}/api/interview/${sessionId}/results`,
        end: (sessionId) => `${API_GATEWAY_URL}/api/interview/${sessionId}/end`
    }
};
```

### WebRTC Connection with TURN
```javascript
// Get ICE servers configuration
const response = await fetch(API_ENDPOINTS.interview.iceServers(sessionId));
const iceConfig = await response.json();

// Create peer connection with TURN servers
const pc = new RTCPeerConnection({
    iceServers: iceConfig.iceServers
});
```

## Security Considerations

### 1. API Gateway Security
- Enable API key requirement for production
- Configure usage plans and throttling
- Use AWS WAF for additional protection

### 2. CORS Configuration
- Replace wildcard origins with specific domains
- Validate allowed headers
- Consider removing credentials for public APIs

### 3. VPC Security
- ALB in private subnets only
- Security groups restrict traffic flow
- VPC Link ensures private connectivity

## Monitoring and Logging

### CloudWatch Integration
- API Gateway access logs
- Execution logs for debugging
- Custom metrics for monitoring

### Enable Access Logging
```typescript
const logGroup = new logs.LogGroup(this, 'ApiGatewayLogs');

new apigatewayv2.HttpApi(this, 'SpoolHttpApi', {
    // ... other config
    defaultStage: {
        accessLogSettings: {
            destinationArn: logGroup.logGroupArn,
            format: apigatewayv2.AccessLogFormat.jsonWithStandardFields()
        }
    }
});
```

## Cost Optimization

### API Gateway v2 Pricing
- $1.00 per million requests
- No monthly fees
- Data transfer charges apply

### Cost Saving Tips
1. Use caching where appropriate
2. Enable compression
3. Optimize payload sizes
4. Monitor usage patterns

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Check allowed origins match frontend URL
   - Verify preflight configuration
   - Check browser console for specific errors

2. **502 Bad Gateway**
   - Verify ECS services are healthy
   - Check ALB target groups
   - Review VPC Link configuration

3. **Connection Timeouts**
   - Check security group rules
   - Verify VPC Link is active
   - Review ALB health checks

### Debug Commands
```bash
# Check API Gateway
aws apigatewayv2 get-apis

# Check VPC Link status
aws apigatewayv2 get-vpc-links

# View CloudWatch logs
aws logs tail /aws/apigateway/{api-id}/{stage}
```

## Production Checklist

- [ ] Update CORS origins to specific domains
- [ ] Enable API key authentication
- [ ] Configure custom domain name
- [ ] Set up CloudWatch alarms
- [ ] Enable AWS WAF
- [ ] Configure request throttling
- [ ] Set up API Gateway caching
- [ ] Enable CloudWatch logs
- [ ] Configure backup and disaster recovery
- [ ] Document API endpoints and usage

## Next Steps

1. **Custom Domain**: Configure Route 53 and ACM certificate
2. **Authentication**: Integrate with AWS Cognito
3. **Rate Limiting**: Configure usage plans
4. **Monitoring**: Set up CloudWatch dashboards
5. **API Documentation**: Generate OpenAPI spec