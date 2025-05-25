from aws_cdk import (
    Duration,
    Stack,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources, 
    aws_sqs as sqs,
)
from constructs import Construct

'''
Upload audio file to S3 -> Lambda function -> SQS
'''

class InputStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Resources, minimal versions for now
        bucket = s3.Bucket(self, "meetingSummarizer")

        queue = sqs.Queue(self, "transcriptionQueue")

        function = lambda_.Function(
            self, "notifyTranscriptionQueue",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("lambda"),
            handler="notifyTranscriptionQueue.handler",
            environment={
                "QUEUE_URL": queue.queue_url
            }
        )

        # Grant permisions
        bucket.grant_read(function)
        queue.grant_send_messages(function)

        # Add event trigger
        function.add_event_source(
            lambda_event_sources.S3EventSource(
                bucket,
                events=[s3.EventType.OBJECT_CREATED]
            )
        )

