import os
import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Read from environment variables set in CDK
SUMMARY_BUCKET = os.environ['SUMMARY_BUCKET']
SUMMARY_PREFIX = os.environ.get('SUMMARY_PREFIX', 'summaries/')
TABLE_NAME = os.environ['SUMMARY_TABLE']

table = dynamodb.Table(TABLE_NAME)


def handler(event, context):
    for record in event['Records']:
        # Each record is an SQS message
        body = json.loads(record['body'])

        meeting_id = body['meeting_id']
        summary = body['summary']
        bucket = body['bucket']  # original transcript bucket
        # original transcript key (audio or transcript file key)
        key = body['key']

        # Compose S3 key for storing summary
        summary_key = f"{SUMMARY_PREFIX}{meeting_id}.txt"

        # Step 1: Save summary to S3
        s3.put_object(
            Bucket=SUMMARY_BUCKET,
            Key=summary_key,
            Body=summary.encode('utf-8'),
            ContentType='text/plain'
        )

        # Compose audio and summary URLs (assuming public or presigned URLs later)
        audio_url = f"s3://{bucket}/{key}"
        summary_url = f"s3://{SUMMARY_BUCKET}/{summary_key}"

        # Step 2: Save metadata to DynamoDB
        item = {
            'meeting_id': meeting_id,
            'audio_url': audio_url,
            'summary_url': summary_url,
            'timestamp': datetime.now().isoformat()
        }

        table.put_item(Item=item)

