import os
import boto3
from boto3.dynamodb.conditions import Key
import json

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["SUMMARY_TABLE"])
s3 = boto3.client('s3')

def handler(event, context):
    meeting_id = event["pathParameters"]["meeting_id"]

    try:
        response = table.get_item(Key={"meeting_id": meeting_id})
        item = response.get("Item")

        if not item:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Summary not found"})
            }
        
        # Read summary text from S3
        summary_text = ""
        if item.get("summary_url"):
            bucket, key = parse_s3_url(item["summary_url"])
            try:
                obj = s3.get_object(Bucket=bucket, Key=key)
                summary_text = obj['Body'].read().decode('utf-8')
            except Exception as e:
                print(f"Error reading S3 file: {str(e)}")

        print("Full summary text:", summary_text)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "summary_url": item.get("summary_url"),
                "audio_url": item.get("audio_url"),
                "summary_text": summary_text
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def parse_s3_url(url):
    """Extract bucket and key from S3 URL"""
    if url.startswith('s3://'):
        parts = url[5:].split('/', 1)
        return parts[0], parts[1]
    elif url.startswith('https://'):
        parts = url.split('/')
        bucket = parts[2].split('.')[0]
        key = '/'.join(parts[3:])
        return bucket, key
    return None, None
