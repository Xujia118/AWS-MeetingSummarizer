from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb
)
from constructs import Construct


class SharedResourcesStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        self.bucket = s3.Bucket(
            self, "MeetingSummarizerBucket",
            bucket_name="meeting-summarizer-yanlu"
        )

        self.audio_queue = sqs.Queue(
            self, "AudioUploadQueue",
            queue_name="AudioUploadQueue-yanlu"
        )

        self.summary_queue = sqs.Queue(
            self, 'SummaryQueue',
            queue_name='SummaryQueue-yanlu'
        )

        self.table = dynamodb.Table(
            self, "MeetingSummarizerTable",
            table_name="MeetingSummarizerTable-yanlu",
            partition_key=dynamodb.Attribute(
                name="meeting_id",
                type=dynamodb.AttributeType.STRING
            ),
        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )
