import os
import json
import boto3
from urllib.parse import unquote_plus
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

AUDIO_BUCKET = os.environ['AUDIO_BUCKET']
AUDIO_PREFIX = os.environ.get('AUDIO_PREFIX', 'audios/')
SUMMARY_TABLE = os.environ['SUMMARY_TABLE']

table = dynamodb.Table(SUMMARY_TABLE)


def handler(event, context):
    try:
        if 'body' not in event:
            return {
                'statusCode': 400,
                'body': 'No file content provided'
            }

        # We need to send meeting id to frontend now, because all sequent steps are within backend
        meeting_id = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        filename = f"{meeting_id}.mp3"
        s3_key = f"{AUDIO_PREFIX}{filename}"
        s3_path = f"s3://{AUDIO_BUCKET}/{s3_key}"

        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': AUDIO_BUCKET,
                'Key': f"{AUDIO_PREFIX}{filename}",
                "ContentType": 'application/octet-stream'
            },
            ExpiresIn=3600
        )

        item = {
            'meeting_id': meeting_id,
            'filename': filename,
            's3_path': s3_path,
            'status': 'waiting_for_emails',
        }

        table.put_item(Item=item)

        print("Saved initial record to DynamoDB:", item)

        # API Gateway expects response body to be a string
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/octet-stream',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'meeting_id': meeting_id,
                'upload_url': presigned_url,
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Error generating upload URL: {str(e)}"
        }


def extract_filename(content_disposition):
    """Extracts filename from Content-Disposition header"""
    if not content_disposition:
        return None

    parts = content_disposition.split(';')
    for part in parts:
        if 'filename=' in part:
            filename = part.split('=')[1].strip('"\' ')
            return unquote_plus(filename)  # Decode URL-encoded characters
    return None
