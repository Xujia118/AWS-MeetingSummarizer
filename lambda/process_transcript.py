import json
import os
import boto3
import urllib.parse
from datetime import datetime

s3 = boto3.client('s3')
comprehend = boto3.client('comprehend')
bedrock = boto3.client('bedrock-runtime')
sqs = boto3.client('sqs')


def handler(event, context):
    try:
        # Step 1: Get bucket and key from input
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])

        # Step 2: Fetch and parse transcript
        transcript = get_transcript_from_s3(bucket, key)
        if not transcript:
            raise ValueError("Empty transcript retrieved")

        # Step 3: Analyze with Comprehend
        comprehend_results = analyze_with_comprehend(transcript)

        # Step 4: Generate summary
        summary = generate_summary_with_bedrock(transcript, comprehend_results)
        print("Final summary:", summary)

        # Step 5: Push to summary_queue 
        meeting_id = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        send_summary_to_sqs(meeting_id, summary, bucket, key)

    except Exception as e:
        print("Processing error:", str(e))
        raise


def get_transcript_from_s3(bucket, key):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        raw_content = response['Body'].read().decode("utf-8")

        # Parse JSON if transcript is in a structured format
        try:
            transcript_data = json.loads(raw_content)
            return transcript_data.get('results', {}).get('transcripts', [{}])[0].get('transcript', '')
        except json.JSONDecodeError:
            return raw_content  # Fallback to raw text

    except Exception as e:
        raise RuntimeError(f"S3 Error: {str(e)}")


def analyze_with_comprehend(text):
    """Run comprehensive NLP analysis using Comprehend"""
    try:
        # Get key phrases
        phrases = comprehend.detect_key_phrases(
            Text=text,
            LanguageCode='en'
        )['KeyPhrases']

        # Detect entities
        entities = comprehend.detect_entities(
            Text=text,
            LanguageCode='en'
        )['Entities']

        # Detect sentiment
        sentiment = comprehend.detect_sentiment(
            Text=text,
            LanguageCode='en'
        )

        return {
            'key_phrases': [{'Text': p['Text'], 'Score': p['Score']} for p in phrases],
            'entities': [{'Text': e['Text'], 'Type': e['Type'], 'Score': e['Score']} for e in entities],
            'sentiment': sentiment['Sentiment'],
            'sentiment_scores': sentiment['SentimentScore']
        }

    except Exception as e:
        raise RuntimeError(f"Comprehend Error: {str(e)}")


def generate_summary_with_bedrock(transcript, comprehend_results):
    """Generate summary using Claude 3 Haiku (on-demand)"""
    try:
        print("Using Claude 3 Haiku (on-demand)...")

        # Prepare the prompt
        participants = [e['Text'] for e in comprehend_results['entities']
                        if e['Type'] == 'PERSON' and e['Score'] > 0.9]
        top_phrases = sorted(comprehend_results['key_phrases'],
                             key=lambda x: x['Score'], reverse=True)[:3]

        prompt = f"""Create a structured meeting summary:

            Participants: {', '.join(set(participants))}
            Key Topics: {', '.join([p['Text'] for p in top_phrases])}
            Sentiment: {comprehend_results['sentiment']}

            Structure the response with:
            1. Key Decisions
            2. Action Items (with owners)
            3. Follow-up Needed

            Meeting Excerpts:
            {transcript[:2000]}"""

        # Claude 3 uses the Messages API
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
        summary = result['content'][0]['text']
        print("Generated Summary:", summary)
        return summary

    except Exception as e:
        print("Claude 3 Haiku Error:", str(e))
        raise RuntimeError(f"Summary generation failed: {str(e)}")


def send_summary_to_sqs(meeting_id, summary, bucket, key):
    try:
        queue_url = os.environ['SUMMARY_QUEUE_URL']

        message = {
            'meeting_id': meeting_id,
            'summary': summary,
            'bucket': bucket,
            'key': key
        }

        messsage_body = json.dumps(message)

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=messsage_body
        )

        print(f"Sent summary to SQS for meeting_id={meeting_id}")
    
    except Exception as e:
        raise RuntimeError(f"SQS Error: {str(e)}")

