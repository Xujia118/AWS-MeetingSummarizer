import json
import os
import boto3
from botocore.config import Config
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import datetime

config = Config(
    retries={
        'max_attempts': 3,
        'mode': 'standard'
    }
)

bedrock = boto3.client('bedrock-runtime', config=config)
region = os.environ.get('AWS_REGION', 'us-east-1')
service = 'aoss'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

# OpenSearch client
opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
index_name = os.environ['INDEX_NAME']

client = OpenSearch(
    hosts=[{'host': opensearch_endpoint.replace('https://', ''), 'port': 443}],
    http_auth=awsauth,
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
    """Create the OpenSearch index if it doesn't exist"""
    try:
        if not client.indices.exists(index=index_name):
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
                            "dimension": 1536,  # Titan embeddings dimension
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
            print(f"Created index: {index_name}")
        else:
            print(f"Index {index_name} already exists")
            
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
        
        body = {
            "inputText": text
        }
        
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        result = json.loads(response['body'].read())
        return result['embedding']
        
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise


def store_embedding(meeting_id, content, content_type, embedding, bucket, transcript_key, chunk_index):
    """Store embedding in OpenSearch"""
    try:
        doc_id = f"{meeting_id}_{content_type}_{chunk_index}"
        
        document = {
            "meeting_id": meeting_id,
            "content_type": content_type,
            "content": content,
            "embedding": embedding,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "bucket": bucket,
            "transcript_key": transcript_key,
            "chunk_index": chunk_index
        }
        
        response = client.index(
            index=index_name,
            id=doc_id,
            body=document
        )
        
        print(f"Stored embedding for {doc_id}: {response['result']}")
        
    except Exception as e:
        print(f"Error storing embedding: {str(e)}")
        raise
