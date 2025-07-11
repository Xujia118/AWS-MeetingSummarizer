#!/usr/bin/env python3
"""
Test script for RAG functionality
This script demonstrates how to query the RAG endpoint after deployment
"""

import json
import requests

# Replace with your actual API Gateway URL after deployment
API_BASE_URL = "https://your-api-id.execute-api.us-east-1.amazonaws.com/prod"

def test_rag_query(query, meeting_id=None):
    """Test the RAG query endpoint"""
    url = f"{API_BASE_URL}/query"
    
    payload = {
        "query": query,
        "max_results": 5
    }
    
    if meeting_id:
        payload["meeting_id"] = meeting_id
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"Query: {query}")
        print(f"Response: {result['response']}")
        print("\nSources:")
        for source in result['sources']:
            print(f"- Meeting {source['meeting_id']} ({source['content_type']}) - Score: {source['score']:.3f}")
            print(f"  Snippet: {source['snippet']}")
        print("-" * 80)
        
    except requests.exceptions.RequestException as e:
        print(f"Error querying RAG endpoint: {e}")

def main():
    """Run example queries"""
    print("Testing RAG Functionality")
    print("=" * 80)
    
    # Example queries
    test_queries = [
        "What were the main action items discussed?",
        "Who were the participants in the meetings?",
        "What decisions were made about the budget?",
        "What follow-up tasks were assigned?",
        "What was the overall sentiment of the meetings?"
    ]
    
    for query in test_queries:
        test_rag_query(query)

if __name__ == "__main__":
    print("Note: Update API_BASE_URL with your actual API Gateway URL after deployment")
    print("You can find this URL in the CDK deployment output or AWS Console")
    print()
    main()
