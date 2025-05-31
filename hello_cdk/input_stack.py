from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_notifications as s3n
)
from constructs import Construct


class InputStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, bucket, audio_queue, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        '''Upload audio file to S3 -> S3 event -> SQS'''

        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(audio_queue),
            s3.NotificationKeyFilter(prefix="audios/")
        )

