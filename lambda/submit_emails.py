import json
import boto3
import os


def handler(event, context):
    # Parse the incoming request
    body = json.loads(event['body'])
    meeting_id = body['meeting_id']
    emails = body['emails']  # Expecting a list of email addresses

    # Validate emails (basic validation)
    if not isinstance(emails, list) or len(emails) == 0:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid email list provided'})
        }

    # Store emails in DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['SUMMARY_TABLE'])

    try:
        # Update the meeting record with the subscriber emails
        table.update_item(
            Key={'meeting_id': meeting_id},
            UpdateExpression='SET subscriber_emails = list_append(if_not_exists(subscriber_emails, :empty_list), :emails)',
            ExpressionAttributeValues={
                ':emails': emails,
                ':empty_list': []
            }
        )

        # If using SES, you would add code here to send confirmation emails
        # ses = boto3.client('ses', region_name=os.environ['SES_REGION'])
        # ... send emails logic ...

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Emails submitted successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
