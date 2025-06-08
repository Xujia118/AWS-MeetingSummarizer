import json
import boto3
import os
import re

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['SUMMARY_TABLE']

table = dynamodb.Table(TABLE_NAME)


def handler(event, context):

    try:
        body = json.loads(event['body'])
        meeting_id = body.get('meeting_id')
        emails = body.get('emails')

        if not meeting_id:
            return _response(400, {'error': 'Missing meeting_id'})

        if not isinstance(emails, list):
            return _response(400, {'error': 'Emails must be provided as an array'})

        invalid_emails = [email for email in emails if not validate_email(email)]
        if invalid_emails:
            return _response(400, {
                'error': 'Invalid email format',
                'invalid_emails': invalid_emails
            })

        # Update emails and status
        table.update_item(
            Key={'meeting_id': meeting_id},
            UpdateExpression="SET emails = :emails, #st = :status",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":emails": emails,
                ":status": "pending_processing"
            }
        )

        print(f"Updated meeting {meeting_id} with emails.")

        return _response(200, {
            'message': 'Emails saved successfully',
            'meeting_id': meeting_id
        })

    except Exception as e:
        print("Error:", str(e))
        return _response(500, {'error': str(e)})


def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


def _response(status_code, body_dict):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body_dict)
    }

