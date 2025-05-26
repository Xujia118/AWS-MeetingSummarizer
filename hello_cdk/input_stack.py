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

        self.bucket = s3.Bucket(
            self, "MeetingSummarizerBucket",
            bucket_name="meeting-summarizer-yanlu"
        )

        self.audio_queue = sqs.Queue(
            self, "AuioUploadQueue",
            queue_name="AudioUploadQueue-yanlu"
        )

        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(self.audio_queue),
            s3.NotificationKeyFilter(prefix="audios/")
        )

