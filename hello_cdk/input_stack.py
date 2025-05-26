from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_sqs as sqs,
)
from constructs import Construct

'''
Upload audio file to S3 -> S3 event -> SQS
'''

class InputStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Resources, minimal versions for now
        bucket = s3.Bucket(self, "meetingSummarizer")

        queue = sqs.Queue(self, "transcriptionQueue")

        # S3 directly notifies SQS
        notification = s3n.SqsDestination(queue)
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            notification
        )

