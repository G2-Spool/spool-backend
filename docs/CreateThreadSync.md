# CreateThread Lambda Integration Guide for spool-interview-service

## Overview

This document provides detailed instructions for integrating the spool-interview-service (ECS) with the CreateThread Lambda function. The integration enables automatic creation of learning threads in the RDS database when users complete interview sessions in "thread" mode.

## Lambda Function Details

### Function Information
- **Function Name**: `spool-create-thread`
- **Function ARN**: `arn:aws:lambda:us-east-1:560281064968:function:spool-create-thread`
- **Runtime**: Node.js 18.x
- **Handler**: `src/index.handler`
- **Region**: us-east-1
- **Status**: ✅ **DEPLOYED** (Last updated: 2025-07-11)

### VPC Configuration
- **VPC ID**: vpc-e5a7949f (same as ECS services)
- **Subnets**: 
  - subnet-1b789f7d
  - subnet-0fb16901
- **Security Group**: sg-b969c293

### Environment Variables
- `COGNITO_USER_POOL_ID`: us-east-1_H7Kti5MPI

## Integration Architecture

```
User → InterviewModal → API Gateway → spool-interview-service (ECS)
                                              ↓
                                    [Thread Mode Detection]
                                              ↓
                                    Invoke CreateThread Lambda
                                              ↓
                                    Save to RDS learning_paths table
```

## Required Changes for spool-interview-service

### 1. Add Lambda Client Dependency

Add the AWS SDK Lambda client to your package.json:

```json
{
  "dependencies": {
    "@aws-sdk/client-lambda": "^3.x.x"
  }
}
```

### 2. Add Lambda Invocation Code

Create a new module for Lambda integration:

```javascript
// lambdaIntegration.js
const { LambdaClient, InvokeCommand } = require("@aws-sdk/client-lambda");

class LambdaIntegration {
  constructor() {
    this.lambdaClient = new LambdaClient({ 
      region: process.env.AWS_REGION || "us-east-1" 
    });
    this.functionName = "spool-create-thread";
  }

  /**
   * Creates a learning thread by invoking the CreateThread Lambda
   * @param {Object} interviewData - Interview session data
   * @returns {Promise<Object>} Created thread data
   */
  async createThreadFromInterview(interviewData) {
    try {
      console.log(`[Lambda Integration] Creating thread from interview session: ${interviewData.sessionId}`);
      
      // Extract thread data from interview
      const threadPayload = this.transformInterviewToThread(interviewData);
      
      // Prepare Lambda invocation
      const command = new InvokeCommand({
        FunctionName: this.functionName,
        InvocationType: "RequestResponse",
        Payload: JSON.stringify({
          httpMethod: "POST",
          path: "/create",
          headers: {
            "Content-Type": "application/json",
            // Pass the user's JWT token if available
            "Authorization": interviewData.authToken || ""
          },
          body: JSON.stringify(threadPayload)
        })
      });

      // Invoke Lambda
      const response = await this.lambdaClient.send(command);
      
      // Parse response
      const responsePayload = JSON.parse(Buffer.from(response.Payload).toString());
      
      if (response.StatusCode !== 200) {
        throw new Error(`Lambda invocation failed: ${responsePayload.errorMessage || 'Unknown error'}`);
      }

      const result = JSON.parse(responsePayload.body);
      console.log(`[Lambda Integration] Thread created successfully: ${result.threadId}`);
      
      return result;
    } catch (error) {
      console.error('[Lambda Integration] Failed to create thread:', error);
      throw error;
    }
  }

  /**
   * Transforms interview data into thread format
   * @param {Object} interviewData - Interview session data
   * @returns {Object} Thread data for Lambda
   */
  transformInterviewToThread(interviewData) {
    const { studentId, messages, extractedInterests, mode, purpose } = interviewData;
    
    // Extract the main question/topic from the conversation
    const userMessages = messages.filter(m => m.role === 'user');
    const primaryQuestion = userMessages[0]?.content || 'Learning exploration';
    
    // Generate a title from the conversation
    const title = this.generateThreadTitle(messages);
    
    // Extract concepts and subjects from the conversation
    const analysis = this.analyzeConversation(messages);
    
    return {
      userId: studentId,
      title: title,
      description: primaryQuestion,
      interests: extractedInterests || [],
      concepts: analysis.concepts || [],
      subjects: analysis.subjects || [],
      topics: analysis.topics || [],
      status: 'active',
      metadata: {
        source: 'interview',
        sessionId: interviewData.sessionId,
        mode: mode,
        purpose: purpose
      }
    };
  }

  /**
   * Generates a thread title from conversation
   * @param {Array} messages - Conversation messages
   * @returns {string} Thread title
   */
  generateThreadTitle(messages) {
    const userMessages = messages.filter(m => m.role === 'user');
    if (userMessages.length === 0) return 'New Learning Thread';
    
    // Use first user message, truncated to reasonable length
    const firstMessage = userMessages[0].content;
    const title = firstMessage.length > 100 
      ? firstMessage.substring(0, 97) + '...'
      : firstMessage;
    
    return title;
  }

  /**
   * Analyzes conversation to extract academic concepts
   * @param {Array} messages - Conversation messages
   * @returns {Object} Analysis with subjects, topics, concepts
   */
  analyzeConversation(messages) {
    // This is a simplified version - enhance with NLP if needed
    const analysis = {
      subjects: [],
      topics: [],
      concepts: []
    };

    const conversationText = messages
      .map(m => m.content)
      .join(' ')
      .toLowerCase();

    // Subject detection
    const subjectKeywords = {
      'Mathematics': ['math', 'calculus', 'algebra', 'geometry', 'statistics'],
      'Physics': ['physics', 'force', 'energy', 'motion', 'quantum'],
      'Chemistry': ['chemistry', 'chemical', 'molecule', 'reaction', 'element'],
      'Biology': ['biology', 'cell', 'dna', 'evolution', 'organism'],
      'Computer Science': ['programming', 'algorithm', 'code', 'software', 'computer'],
      'History': ['history', 'historical', 'civilization', 'war', 'revolution'],
      'Literature': ['literature', 'novel', 'poetry', 'writing', 'author']
    };

    // Check for subject keywords
    for (const [subject, keywords] of Object.entries(subjectKeywords)) {
      if (keywords.some(keyword => conversationText.includes(keyword))) {
        analysis.subjects.push(subject);
      }
    }

    // Extract key concepts (simplified - enhance as needed)
    if (conversationText.includes('calculus')) {
      analysis.concepts.push('Derivatives', 'Integrals');
      analysis.topics.push('Calculus');
    }
    
    if (conversationText.includes('physics')) {
      analysis.concepts.push('Motion', 'Forces');
      analysis.topics.push('Mechanics');
    }

    // Default if nothing detected
    if (analysis.subjects.length === 0) {
      analysis.subjects.push('General Learning');
    }

    return analysis;
  }
}

module.exports = LambdaIntegration;
```

### 3. Update Interview Service Handler

Modify your interview completion handler to invoke the Lambda when in thread mode:

```javascript
// In your interview service message handler
const LambdaIntegration = require('./lambdaIntegration');
const lambdaIntegration = new LambdaIntegration();

async function handleInterviewMessage(sessionId, message, mode) {
  // ... existing interview logic ...
  
  // Check if interview is complete and in thread mode
  if (isInterviewComplete && (mode === 'thread' || session.mode === 'thread')) {
    try {
      // Prepare interview data
      const interviewData = {
        sessionId: sessionId,
        studentId: session.studentId,
        messages: session.messages,
        extractedInterests: session.interests,
        mode: session.mode || mode,
        purpose: session.purpose || 'create_learning_thread',
        authToken: session.authToken // If you store the user's JWT
      };
      
      // Create thread via Lambda
      const thread = await lambdaIntegration.createThreadFromInterview(interviewData);
      
      // Add thread info to response
      response.threadId = thread.threadId;
      response.threadCreated = true;
      
      console.log(`Thread created for session ${sessionId}: ${thread.threadId}`);
    } catch (error) {
      console.error(`Failed to create thread for session ${sessionId}:`, error);
      // Don't fail the interview response, just log the error
      response.threadCreationError = error.message;
    }
  }
  
  return response;
}
```

### 4. IAM Permissions

Ensure your ECS task role has permission to invoke the Lambda function. Add this policy to your ECS task role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:us-east-1:560281064968:function:spool-create-thread"
    }
  ]
}
```

## Lambda Function Endpoints

The Lambda function supports these operations:

### 1. Create Thread
- **Method**: POST
- **Path**: `/create`
- **Payload**:
```json
{
  "userId": "cognito-user-id",
  "title": "Thread title",
  "description": "Main question or topic",
  "interests": ["array", "of", "interests"],
  "concepts": ["array", "of", "concepts"],
  "subjects": ["array", "of", "subjects"],
  "topics": ["array", "of", "topics"],
  "status": "active",
  "metadata": {
    "source": "interview",
    "sessionId": "session-123"
  }
}
```

### 2. Get Thread
- **Method**: GET
- **Path**: `/thread/{threadId}`

### 3. List Threads
- **Method**: GET
- **Path**: `/threads?userId={userId}&limit={limit}`

### 4. Update Thread
- **Method**: PUT
- **Path**: `/thread/{threadId}`

## Error Handling

The Lambda function returns standardized error responses:

```json
{
  "statusCode": 400,
  "body": {
    "error": "Validation error",
    "message": "Missing required field: title"
  }
}
```

Handle these errors appropriately in the interview service:

```javascript
if (responsePayload.statusCode >= 400) {
  const error = JSON.parse(responsePayload.body);
  console.error(`Lambda error: ${error.message}`);
  // Handle specific error cases
}
```

## Monitoring and Debugging

### CloudWatch Logs
- **Log Group**: `/aws/lambda/spool-create-thread`
- **Log Stream**: One per Lambda execution

### Key Log Messages to Monitor
```
[INFO] Creating thread for user: {userId}
[INFO] Thread created successfully: {threadId}
[ERROR] Failed to connect to RDS: {error}
[ERROR] Validation failed: {details}
```

### X-Ray Tracing
Enable X-Ray tracing in your ECS service to trace the full request flow:
1. Interview service receives request
2. Lambda invocation
3. RDS database write
4. Response back to client

## Testing the Integration

### 1. Test Lambda Directly
```bash
aws lambda invoke \
  --function-name spool-create-thread \
  --payload '{"httpMethod":"POST","path":"/create","body":"{\"userId\":\"test-user\",\"title\":\"Test Thread\",\"description\":\"Testing Lambda\"}"}' \
  response.json

cat response.json
```

### 2. Test from Interview Service
Send a test interview completion in thread mode and verify:
1. Lambda is invoked (check CloudWatch logs)
2. Thread is created in RDS
3. Response includes threadId

### 3. End-to-End Test
1. Open the app and navigate to /courses
2. Click "Create Thread"
3. Have a conversation about an academic topic
4. Verify thread is created and user is redirected

## Troubleshooting

### Common Issues

1. **Lambda Timeout**
   - Default timeout is 30s
   - If RDS connection is slow, increase timeout
   - Check VPC routing and security groups

2. **Permission Denied**
   - Verify ECS task role has lambda:InvokeFunction permission
   - Check Lambda execution role has RDS access

3. **Network Issues**
   - Ensure Lambda and ECS are in same VPC
   - Security group must allow traffic between services
   - RDS security group must allow Lambda connections

4. **Cold Start Delays**
   - First invocation may be slow due to VPC ENI creation
   - Consider reserved concurrency for consistent performance

## Performance Optimization

1. **Connection Pooling**: Lambda reuses database connections across invocations
2. **Batch Processing**: Consider batching multiple thread creations
3. **Async Processing**: For non-critical paths, use async invocation
4. **Caching**: Cache user data to reduce Cognito lookups

## Security Considerations

1. **Authentication**: Always pass user's JWT token to Lambda
2. **Authorization**: Lambda verifies user permissions via Cognito
3. **Data Validation**: Lambda validates all input data
4. **Encryption**: All data in transit uses TLS
5. **VPC Isolation**: Lambda runs in private subnets

## Deployment Notes

### Fixed Issues (2025-07-11)
- **UUID Module Error**: Fixed by updating the deployment script to properly include node_modules in the Lambda package
- **VPC Configuration**: Successfully configured with ECS VPC for RDS access
- **Testing**: Lambda is responding correctly with proper authentication checks

### Current Status
- ✅ Lambda deployed and operational
- ✅ VPC configured for RDS access
- ✅ Authentication via Cognito working
- ✅ Error handling implemented
- ⏳ Awaiting spool-interview-service integration
- ⏳ API Gateway routing pending

## Support and Maintenance

- **Lambda Dashboard**: Monitor function metrics in AWS Console
- **CloudWatch Logs**: `/aws/lambda/spool-create-thread`
- **Alarms**: Set up CloudWatch alarms for errors and latency
- **Updates**: Deploy updates using `./scripts/deploy-with-vpc.sh`
- **Rollback**: Lambda supports versioning for quick rollbacks

## Conclusion

This integration enables seamless thread creation from interview sessions. The Lambda function is deployed and ready for integration with the spool-interview-service. Follow the implementation steps in this document to complete the integration on the ECS service side.