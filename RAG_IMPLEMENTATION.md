# RAG (Retrieval Augmented Generation) Implementation

This document describes the RAG functionality added to the Meeting Summarizer application, enabling users to query their meeting content using natural language.

## Overview

The RAG implementation allows users to:
- Ask natural language questions about their meetings
- Search across all meetings semantically
- Get contextual answers based on meeting transcripts and summaries
- Discover insights across multiple meetings

## Architecture

### New Components Added

1. **VectorStack** (`hello_cdk/vector_stack.py`)
   - AWS OpenSearch Serverless collection for vector storage
   - Lambda functions for embedding generation and RAG queries
   - Security policies and access controls

2. **Lambda Functions**
   - `generate_embeddings.py`: Processes meeting data and creates vector embeddings
   - `rag_query.py`: Handles user queries and generates contextual responses

3. **Enhanced Workflow**
   ```
   Audio → Transcribe → Process → Summary → DynamoDB
                                    ↓
                          Generate Embeddings → OpenSearch
                                    ↓
   User Query → RAG Search → Context Retrieval → Claude Response
   ```

## Data Flow

### Embedding Generation
1. After transcript processing, meeting data is sent to the embedding queue
2. `generate_embeddings.py` processes the queue messages
3. Text is chunked for optimal embedding generation
4. Amazon Titan generates embeddings for transcript chunks and summaries
5. Embeddings are stored in OpenSearch with metadata

### Query Processing
1. User submits a natural language query via API
2. `rag_query.py` generates an embedding for the query
3. OpenSearch performs semantic similarity search
4. Relevant context is retrieved and ranked
5. Claude generates a response using the retrieved context

## API Endpoints

### New Endpoint: POST /query

**Request Body:**
```json
{
  "query": "What were the main action items discussed?",
  "meeting_id": "optional-specific-meeting-id",
  "max_results": 5
}
```

**Response:**
```json
{
  "query": "What were the main action items discussed?",
  "response": "Based on your meetings, the main action items were...",
  "sources": [
    {
      "meeting_id": "meeting-123",
      "content_type": "transcript",
      "score": 0.85,
      "snippet": "Action items: 1. John to review budget..."
    }
  ]
}
```

## Infrastructure Components

### OpenSearch Serverless
- **Collection Name**: `meeting-vectors`
- **Index Name**: `meetings`
- **Vector Dimension**: 1536 (Titan embeddings)
- **Search Method**: HNSW with cosine similarity

### Security
- IAM roles with least privilege access
- Data access policies for Lambda functions
- Encrypted data at rest and in transit

### Performance
- Optimized vector indexing for fast queries
- Text chunking for better context preservation
- Async processing for large datasets

## Deployment

### Prerequisites
1. AWS CDK installed and configured
2. Bedrock access enabled for:
   - Amazon Titan Embed Text v1
   - Anthropic Claude 3 Haiku

### Deploy the Enhanced Stack
```bash
# Install dependencies
pip install -r requirements.txt

# Install Lambda dependencies
cd lambda
pip install -r requirements.txt -t .
cd ..

# Deploy the stacks
cdk deploy --all
```

### Post-Deployment Setup
1. Note the API Gateway URL from the deployment output
2. Update `test_rag.py` with your API URL
3. Upload some audio files to test the complete workflow

## Usage Examples

### Basic Query
```python
import requests

response = requests.post(
    "https://your-api-url/prod/query",
    json={"query": "What decisions were made about the budget?"}
)
```

### Meeting-Specific Query
```python
response = requests.post(
    "https://your-api-url/prod/query",
    json={
        "query": "What action items were assigned to John?",
        "meeting_id": "specific-meeting-id"
    }
)
```

## Testing

Use the provided test script:
```bash
python test_rag.py
```

## Cost Considerations

### OpenSearch Serverless
- Pay-per-use pricing
- No upfront costs or minimum fees
- Scales automatically based on usage

### Bedrock Usage
- Titan Embeddings: ~$0.0001 per 1K tokens
- Claude 3 Haiku: ~$0.00025 per 1K input tokens

### Estimated Monthly Cost
For 100 meetings/month with average 30-minute duration:
- OpenSearch: ~$20-50
- Bedrock Embeddings: ~$5-10
- Bedrock LLM: ~$10-20
- **Total: ~$35-80/month**

## Monitoring and Troubleshooting

### CloudWatch Logs
- Check Lambda function logs for errors
- Monitor OpenSearch collection metrics
- Track API Gateway request/response patterns

### Common Issues
1. **Embedding Generation Fails**: Check Bedrock permissions and quotas
2. **Search Returns No Results**: Verify index creation and data ingestion
3. **Slow Query Response**: Check OpenSearch collection capacity

## Future Enhancements

1. **User Authentication**: Add user-based access controls
2. **Advanced Filtering**: Filter by date, participants, topics
3. **Conversation Memory**: Maintain context across multiple queries
4. **Real-time Updates**: Stream new embeddings as meetings are processed
5. **Analytics Dashboard**: Visualize query patterns and popular topics

## Security Best Practices

1. **API Authentication**: Implement API keys or OAuth
2. **Data Encryption**: All data encrypted in transit and at rest
3. **Access Logging**: Monitor all API access and queries
4. **Regular Updates**: Keep dependencies and models updated

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Verify Bedrock model access and quotas
3. Ensure OpenSearch collection is healthy
4. Review IAM permissions for all components
