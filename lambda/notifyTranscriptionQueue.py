import os
import json
import boto3

sqs = boto3.client('sqs')


def handler(event, context):
    queue_url = os.environ['QUEUE_URL']

    for record in event['Records']:
        # Extract relevant information from S3 event
        s3_info = {
            'bucket': record['s3']['bucket']['name'],
            'key': record['s3']['object']['key'],
            'eventTime': record['eventTime']
        }

        # Send message to SQS
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(s3_info)
        )

        print(f"Message sent to SQS: {response['MessageId']}")

    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete')
    }
