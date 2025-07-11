#!/usr/bin/env python3
"""
Script to delete and recreate the OpenSearch index with correct dimensions
"""

import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# Configuration
region = 'us-east-1'
opensearch_endpoint = '0kmjbt4trr6gkphym2ob.us-east-1.aoss.amazonaws.com'  # Replace with your endpoint
index_name = 'meetings'

# Set up OpenSearch client
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, region, 'aoss')

client = OpenSearch(
    hosts=[{'host': opensearch_endpoint, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=60
)

def main():
    try:
        # Delete existing index if it exists
        if client.indices.exists(index=index_name):
            print(f"Deleting existing index: {index_name}")
            client.indices.delete(index=index_name)
            print("Index deleted successfully")
        
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
                    "content_type": {"type": "keyword"},
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
        
        print(f"Creating new index: {index_name}")
        client.indices.create(index=index_name, body=index_mapping)
        print("Index created successfully with correct dimensions")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
