import os
import boto3
from urllib.parse import unquote_plus

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

        content_disposition = headers.get('content-disposition', '')
        filename = (extract_filename(content_disposition) or "audio_upload").lstrip('/')

        content_type = headers.get("content-type", 'application/octet-stream')

        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': AUDIO_BUCKET,
                'Key': f"{AUDIO_PREFIX}{filename}",
                "ContentType": content_type
            },
            ExpiresIn=3600
        )

        print("presigned url:", presigned_url)
        
        return {
            'statusCode': 200,
            'body': {
                'upload_url': presigned_url,
                'filename': filename,
                's3_path': f"s3://{AUDIO_BUCKET}/{AUDIO_PREFIX}{filename}"
            }
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

