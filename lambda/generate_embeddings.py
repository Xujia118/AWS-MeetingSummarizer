import json
import os
import boto3
from botocore.config import Config
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import datetime

config = Config(
    retries={
        'max_attempts': 3,
        'mode': 'standard'
    }
)

bedrock = boto3.client('bedrock-runtime', config=config)
region = os.environ.get('AWS_REGION', 'us-east-1')

# OpenSearch client setup
opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
index_name = os.environ['INDEX_NAME']

# Use AWSV4SignerAuth for OpenSearch Serverless
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, region, 'aoss')

client = OpenSearch(
    hosts=[{'host': opensearch_endpoint.replace('https://', ''), 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=60
)


def handler(event, context):
    """Process SQS messages and generate embeddings for meeting data"""
    try:
        # Ensure index exists
        ensure_index_exists()
        
        for record in event['Records']:
            message_body = json.loads(record['body'])
            process_meeting_data(message_body)
            
    except Exception as e:
        print(f"Error processing embeddings: {str(e)}")
        raise


def ensure_index_exists():
    """Create the OpenSearch index if it doesn't exist, or recreate if dimensions are wrong"""
    try:
        # Check if index exists
        if client.indices.exists(index=index_name):
            # Get current mapping to check dimensions
            try:
                mapping = client.indices.get_mapping(index=index_name)
                current_dimension = mapping[index_name]['mappings']['properties']['embedding']['dimension']
                
                if current_dimension != 1024:
                    print(f"Index exists but has wrong dimension ({current_dimension}). Recreating...")
                    client.indices.delete(index=index_name)
                    print("Old index deleted")
                else:
                    print(f"Index {index_name} already exists with correct dimensions")
                    return
            except Exception as e:
                print(f"Error checking index mapping: {str(e)}. Recreating index...")
                client.indices.delete(index=index_name)
                print("Old index deleted")
        
        # Create new index with correct mapping
        index_mapping = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            },
            "mappings": {
                "properties": {
                    "meeting_id": {"type": "keyword"},
                    "content_type": {"type": "keyword"},  # 'transcript' or 'summary'
                    "content": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,  # Titan v2 embeddings dimension
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "timestamp": {"type": "date"},
                    "bucket": {"type": "keyword"},
                    "transcript_key": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "doc_id": {"type": "keyword"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "participants": {"type": "keyword"},
                            "key_phrases": {"type": "keyword"},
                            "sentiment": {"type": "keyword"}
                        }
                    }
                }
            }
        }
        
        client.indices.create(index=index_name, body=index_mapping)
        print(f"Created index: {index_name} with correct dimensions (1024)")
            
    except Exception as e:
        print(f"Error creating index: {str(e)}")
        raise


def process_meeting_data(message_data):
    """Process meeting data and generate embeddings"""
    try:
        meeting_id = message_data['meeting_id']
        transcript = message_data['transcript']
        summary = message_data['summary']
        bucket = message_data['bucket']
        transcript_key = message_data['transcript_key']
        
        print(f"Processing embeddings for meeting_id: {meeting_id}")
        
        # Generate embeddings for transcript chunks
        transcript_chunks = chunk_text(transcript, max_length=8000)
        for i, chunk in enumerate(transcript_chunks):
            if chunk.strip():  # Skip empty chunks
                embedding = generate_embedding(chunk)
                store_embedding(
                    meeting_id=meeting_id,
                    content=chunk,
                    content_type='transcript',
                    embedding=embedding,
                    bucket=bucket,
                    transcript_key=transcript_key,
                    chunk_index=i
                )
        
        # Generate embedding for summary
        if summary.strip():
            summary_embedding = generate_embedding(summary)
            store_embedding(
                meeting_id=meeting_id,
                content=summary,
                content_type='summary',
                embedding=summary_embedding,
                bucket=bucket,
                transcript_key=transcript_key,
                chunk_index=0
            )
        
        print(f"Successfully processed embeddings for meeting_id: {meeting_id}")
        
    except Exception as e:
        print(f"Error processing meeting data: {str(e)}")
        raise


def chunk_text(text, max_length=8000, overlap=200):
    """Split text into overlapping chunks for better context preservation"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_length
        
        # Try to break at sentence boundaries
        if end < len(text):
            # Look for sentence endings within the last 500 characters
            last_period = text.rfind('.', start + max_length - 500, end)
            last_exclamation = text.rfind('!', start + max_length - 500, end)
            last_question = text.rfind('?', start + max_length - 500, end)
            
            sentence_end = max(last_period, last_exclamation, last_question)
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


def generate_embedding(text):
    """Generate embedding using Amazon Titan"""
    try:
        # Truncate text if too long for Titan
        if len(text) > 25000:
            text = text[:25000]
        
        print(f"Generating embedding for text: {text[:100]}...")
        
        body = {
            "inputText": text
        }
        
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        result = json.loads(response['body'].read())
        embedding = result.get('embedding')
        
        if embedding is None:
            print(f"Warning: No embedding returned from Bedrock. Response: {result}")
            raise ValueError("No embedding returned from Bedrock")
        
        print(f"Successfully generated embedding with dimension: {len(embedding)}")
        return embedding
        
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise


def store_embedding(meeting_id, content, content_type, embedding, bucket, transcript_key, chunk_index):
    """Store embedding in OpenSearch"""
    try:
        print(f"About to store embedding - type: {type(embedding)}, length: {len(embedding) if embedding else 'None'}")
        
        if embedding is None:
            raise ValueError("Embedding is None - cannot store")
        
        document = {
            "meeting_id": meeting_id,
            "content_type": content_type,
            "content": content,
            "embedding": embedding,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "bucket": bucket,
            "transcript_key": transcript_key,
            "chunk_index": chunk_index,
            "doc_id": f"{meeting_id}_{content_type}_{chunk_index}"  # Include as field instead of ID
        }
        
        print(f"Document prepared, embedding field type: {type(document['embedding'])}")
        
        response = client.index(
            index=index_name,
            body=document
        )
        
        print(f"Stored embedding for {meeting_id}_{content_type}_{chunk_index}: {response['result']}")
        
    except Exception as e:
        print(f"Error storing embedding: {str(e)}")
        raise
