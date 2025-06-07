import os
import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

# Read from environment variables set in CDK
SUMMARY_BUCKET = os.environ['SUMMARY_BUCKET']
SUMMARY_PREFIX = os.environ.get('SUMMARY_PREFIX', 'summaries/')
TABLE_NAME = os.environ['SUMMARY_TABLE']
SENDER_EMAIL = os.environ['SENDER_EMAIL']

table = dynamodb.Table(TABLE_NAME)


def handler(event, context):
    for record in event['Records']:
        # Each record is an SQS message
        body = json.loads(record['body'])

        meeting_id = body['meeting_id']
        summary = body['summary']
        bucket = body['bucket']  # original transcript bucket
        key = body['key']  # original filename


        # Load metadata (including recipient_emails) from DynamoDB
        response = table.get_item(Key={'meeting_id': meeting_id})
        item = response.get('Item', {})

        recipient_emails = item.get('emails', [])

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

        # Step 2: Update DynamoDB
        table.update_item(
            Key={'meeting_id': meeting_id},
            UpdateExpression="""
                SET audio_url = :audio,
                    summary_url = :summary,
                    #ts = :ts,
                    #st = :status
            """,
            ExpressionAttributeNames={
                "#ts": "timestamp",
                "#st": "status"
            },
            ExpressionAttributeValues={
                ":audio": audio_url,
                ":summary": summary_url,
                ":ts": datetime.now().isoformat(),
                ":status": "completed"
            }
        )

        # Step 3: Send notifications
        for email in recipient_emails:
            try:
                ses.send_email(
                    Source=SENDER_EMAIL,
                    Destination={'ToAddresses': [email]},
                    Message={
                        'Subject': {'Data': f"Meeting Summary: {meeting_id}"},
                        'Body': {
                            'Text': {'Data': f"Summary:\n{summary}\n\nDownload: s3://{SUMMARY_BUCKET}/{summary_key}"},
                            'Html': {'Data': f"""
                        <html>
                            <body>
                                <h1>Meeting Summary</h1>
                                <p>Meeting ID: {meeting_id}</p>
                                <pre>{summary}</pre>
                                <a href="https://s3.console.aws.amazon.com/s3/object/{SUMMARY_BUCKET}/{summary_key}">Download Summary</a>
                            </body>
                        </html>
                    """}
                        }
                    }
                )
                print(f"Email sent to {email}")
            except Exception as e:
                print(f"Failed to send to {email}: {str(e)}")
