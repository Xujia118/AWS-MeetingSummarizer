import os
import json
import boto3
from urllib.parse import unquote_plus
from datetime import datetime

s3 = boto3.client('s3')

AUDIO_BUCKET = os.environ['AUDIO_BUCKET']
AUDIO_PREFIX = os.environ.get('AUDIO_PREFIX', 'audios/')


def handler(event, context):
    try:
        if 'body' not in event:
            return {
                'statusCode': 400,
                'body': 'No file content provided'
            }

        headers = event.get('headers', {})

        # We need to send meeting id to frontend now, because all sequent steps are within backend
        meeting_id = datetime.now().strftime('%Y%m%dT%H%M%SZ')

        filename = f"{meeting_id}.mp3"

        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': AUDIO_BUCKET,
                'Key': f"{AUDIO_PREFIX}{filename}",
                "ContentType": 'application/octet-stream'
            },
            ExpiresIn=3600
        )

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
                'filename': filename,
                's3_path': f"s3://{AUDIO_BUCKET}/{AUDIO_PREFIX}{filename}"
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
