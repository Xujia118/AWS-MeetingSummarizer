# RAG-Enhanced Meeting Summarizer - Deployment Guide

## Overview

This guide walks you through deploying the enhanced Meeting Summarizer application with RAG (Retrieval Augmented Generation) capabilities using AWS OpenSearch Serverless and Bedrock.

## Prerequisites

### 1. AWS Account Setup
- AWS CLI configured with appropriate permissions
- AWS CDK installed (`npm install -g aws-cdk`)
- Python 3.8+ installed

### 2. Bedrock Model Access
Enable access to the following models in AWS Bedrock console:
- **Amazon Titan Embed Text v1** (for embeddings)
- **Anthropic Claude 3 Haiku** (for text generation)

To enable model access:
1. Go to AWS Bedrock console
2. Navigate to "Model access" in the left sidebar
3. Request access for the required models
4. Wait for approval (usually immediate for these models)

### 3. Required Permissions
Your AWS user/role needs permissions for:
- CDK deployment (CloudFormation, IAM, Lambda, S3, etc.)
- OpenSearch Serverless
- Bedrock model invocation
- SQS, DynamoDB, API Gateway

## Installation Steps

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd hello-cdk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install CDK dependencies
pip install -r requirements.txt
```

### 2. Install Lambda Dependencies
```bash
cd lambda
pip install -r requirements.txt -t .
cd ..
```

### 3. Bootstrap CDK (if first time)
```bash
cdk bootstrap
```

### 4. Deploy the Application
```bash
# Deploy all stacks
cdk deploy --all

# Or deploy individually
cdk deploy SharedResourcesStack
cdk deploy InputStack
cdk deploy AIStack
cdk deploy StorageStack
cdk deploy VectorStack
cdk deploy APIStack
```

## Post-Deployment Configuration

### 1. Note API Gateway URL
After deployment, note the API Gateway URL from the output:
```
APIStack.AudioAPIEndpoint = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/
```

### 2. Update Test Script
Edit `test_rag.py` and replace the API_BASE_URL with your actual URL:
```python
API_BASE_URL = "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod"
```

### 3. Verify OpenSearch Collection
1. Go to OpenSearch Serverless console
2. Verify the "meeting-vectors" collection is created
3. Check that the collection is in "Active" state

## Testing the Application

### 1. Upload Audio File
Use your existing frontend or API client to upload an audio file:
```bash
curl -X POST https://your-api-url/prod/audios \
  -H "Content-Type: application/json" \
  -d '{"filename": "meeting.mp3"}'
```

### 2. Wait for Processing
The workflow will:
1. Generate presigned URL for upload
2. Transcribe the audio
3. Generate summary
4. Create embeddings
5. Store in OpenSearch

### 3. Test RAG Queries
```bash
python test_rag.py
```

Or use curl:
```bash
curl -X POST https://your-api-url/prod/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What were the main action items discussed?",
    "max_results": 5
  }'
```

## API Endpoints

### Existing Endpoints
- `POST /audios` - Upload audio files
- `GET /summaries/{meeting_id}` - Get meeting summary
- `POST /emails` - Send summary via email

### New RAG Endpoint
- `POST /query` - Query meetings using natural language

**Request Format:**
```json
{
  "query": "What decisions were made about the budget?",
  "meeting_id": "optional-filter-by-meeting",
  "max_results": 5
}
```

**Response Format:**
```json
{
  "query": "What decisions were made about the budget?",
  "response": "Based on your meetings, the budget decisions were...",
  "sources": [
    {
      "meeting_id": "meeting-123",
      "content_type": "transcript",
      "score": 0.85,
      "snippet": "Budget discussion excerpt..."
    }
  ]
}
```

## Monitoring and Troubleshooting

### CloudWatch Logs
Monitor the following log groups:
- `/aws/lambda/ProcessTranscript`
- `/aws/lambda/GenerateEmbeddings`
- `/aws/lambda/RAGQuery`
- `/aws/apigateway/AudioAPI`

### Common Issues

#### 1. Bedrock Access Denied
**Error:** `AccessDeniedException` when calling Bedrock
**Solution:** Ensure model access is enabled in Bedrock console

#### 2. OpenSearch Connection Failed
**Error:** Connection timeout to OpenSearch
**Solution:** Check security policies and network configuration

#### 3. Embedding Generation Fails
**Error:** Lambda timeout or memory issues
**Solution:** Increase Lambda timeout/memory or reduce text chunk size

#### 4. No Search Results
**Error:** RAG queries return empty results
**Solution:** Verify embeddings are being generated and stored

### Debugging Steps
1. Check CloudWatch logs for errors
2. Verify OpenSearch collection health
3. Test individual Lambda functions
4. Check IAM permissions
5. Validate Bedrock model access

## Cost Optimization

### OpenSearch Serverless
- Automatically scales based on usage
- No minimum charges
- Pay only for what you use

### Bedrock Usage
- Monitor token usage in CloudWatch
- Consider using smaller models for development
- Implement query caching for frequent requests

### Lambda Optimization
- Right-size memory allocation
- Use provisioned concurrency for consistent performance
- Monitor cold start times

## Security Considerations

### Data Protection
- All data encrypted at rest and in transit
- OpenSearch uses AWS-managed encryption
- Lambda environment variables are encrypted

### Access Control
- IAM roles follow least privilege principle
- API Gateway can be enhanced with authentication
- Consider adding API keys for production use

### Network Security
- OpenSearch collection allows public access (can be restricted)
- Lambda functions run in AWS managed VPC
- Consider VPC endpoints for enhanced security

## Scaling Considerations

### High Volume Processing
- SQS queues handle traffic spikes
- Lambda automatically scales
- OpenSearch Serverless scales automatically

### Performance Optimization
- Implement connection pooling for OpenSearch
- Use Lambda layers for shared dependencies
- Consider caching frequent queries

## Cleanup

To remove all resources:
```bash
cdk destroy --all
```

**Warning:** This will delete all data including:
- Meeting transcripts and summaries
- Vector embeddings
- DynamoDB data
- S3 bucket contents

## Support and Maintenance

### Regular Tasks
1. Monitor CloudWatch metrics
2. Review cost reports
3. Update Lambda dependencies
4. Check Bedrock model updates

### Backup Strategy
- S3 bucket versioning enabled
- DynamoDB point-in-time recovery
- OpenSearch data can be exported if needed

For additional support, refer to:
- AWS Documentation
- CloudWatch logs and metrics
- AWS Support (if applicable)
