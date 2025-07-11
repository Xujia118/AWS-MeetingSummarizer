import json
import os
import boto3
from botocore.config import Config
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

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
    """Handle RAG queries from API Gateway"""
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Parse the request
        body = None
        if 'body' in event and event['body'] is not None:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = event
        
        # Ensure body is not None
        if body is None:
            body = {}
        
        query = body.get('query', '')
        meeting_id = body.get('meeting_id')  # Optional: filter by specific meeting
        max_results = body.get('max_results', 5)
        
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({'error': 'Query parameter is required'})
            }
        
        # Generate embedding for the query
        query_embedding = generate_embedding(query)
        
        # Search for relevant context
        search_results = search_similar_content(query_embedding, meeting_id, max_results)
        
        # Generate response using RAG
        response = generate_rag_response(query, search_results)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'query': query,
                'response': response,
                'sources': [
                    {
                        'meeting_id': hit['_source']['meeting_id'],
                        'content_type': hit['_source']['content_type'],
                        'score': hit['_score'],
                        'snippet': hit['_source']['content'][:200] + '...' if len(hit['_source']['content']) > 200 else hit['_source']['content']
                    }
                    for hit in search_results['hits']['hits']
                ]
            })
        }
        
    except Exception as e:
        print(f"Error processing RAG query: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


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
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        result = json.loads(response['body'].read())
        return result['embedding']
        
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise


def search_similar_content(query_embedding, meeting_id=None, max_results=5):
    """Search for similar content in OpenSearch"""
    try:
        # Build the search query
        search_body = {
            "size": max_results,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_embedding,
                                    "k": max_results * 2  # Get more candidates for better filtering
                                }
                            }
                        }
                    ]
                }
            },
            "_source": ["meeting_id", "content_type", "content", "timestamp", "chunk_index"]
        }
        
        # Add meeting_id filter if specified
        if meeting_id:
            search_body["query"]["bool"]["filter"] = [
                {"term": {"meeting_id": meeting_id}}
            ]
        
        response = client.search(
            index=index_name,
            body=search_body
        )
        
        return response
        
    except Exception as e:
        print(f"Error searching content: {str(e)}")
        raise


def generate_rag_response(query, search_results):
    """Generate response using retrieved context and Claude"""
    try:
        # Extract relevant context from search results
        contexts = []
        for hit in search_results['hits']['hits']:
            source = hit['_source']
            context = f"Meeting {source['meeting_id']} ({source['content_type']}): {source['content']}"
            contexts.append(context)
        
        if not contexts:
            return "I couldn't find any relevant information in your meetings to answer that question."
        
        # Prepare the prompt for Claude
        context_text = "\n\n".join(contexts[:3])  # Use top 3 most relevant contexts
        
        prompt = f"""You are an AI assistant helping users understand their meeting content. Based on the following meeting excerpts, please answer the user's question accurately and concisely.

Meeting Context:
{context_text}

User Question: {query}

Please provide a helpful answer based on the meeting content above. If the context doesn't contain enough information to fully answer the question, please say so and provide what information you can find. Always cite which meeting(s) your answer comes from.

Answer:"""

        # Generate response using Claude
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": prompt
                }]
            }],
            "max_tokens": 1024,
            "temperature": 0.3
        }

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )

        result = json.loads(response['body'].read())
        return result['content'][0]['text']
        
    except Exception as e:
        print(f"Error generating RAG response: {str(e)}")
        return f"I encountered an error while processing your question: {str(e)}"


def handle_options(event, context):
    """Handle CORS preflight requests"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': ''
    }
