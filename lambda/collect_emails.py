import json
import boto3
import os
import re

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['SUMMARY_TABLE']

table = dynamodb.Table(TABLE_NAME)


def handler(event, context):

    print("collecting emails...")

    try:
        body = json.loads(event['body'])

        print('body:', body)

        emails = body.pop('emails', [])  # Remove emails from the body dict

        if not isinstance(emails, list):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Emails must be provided as an array'})
            }

        invalid_emails = [
            email for email in emails if not validate_email(email)]
        if invalid_emails:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid email format',
                    'invalid_emails': invalid_emails
                })
            }

        # Create complete item by merging all original fields + emails
        item = {
            **body,  # Unpacks all original metadata fields
            'emails': emails,
            'status': 'pending_processing',
        }

        # Store meetin id, metadata and emails in DynamoDB (First write)
        table.put_item(Item=item)

        print("put item in db:", item)

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',  # Or specific origin
                'Access-Control-Allow-Credentials': True,
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Meeting record created with emails',
                'meeting_id': body['meeting_id']
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e)})
        }


def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)
