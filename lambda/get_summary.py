import os
import boto3
from boto3.dynamodb.conditions import Key
import json

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["SUMMARY_TABLE"])


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

        return {
            "statusCode": 200,
            "body": json.dumps({
                "summary_url": item.get("summary_url"),
                "audio_url": item.get("audio_url")
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
