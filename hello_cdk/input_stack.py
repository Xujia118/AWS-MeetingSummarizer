from aws_cdk import (
    Stack,
    Duration,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
)
from constructs import Construct


class InputStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        '''Upload audio file to S3 -> S3 event -> SQS'''

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

        '''Fetch transcript from S3'''      
        # This lambda has to be created here or we will have cyclic dependency issue
        
        self.process_transcript_lambda = lambda_.Function(
            self, "ProcessTranscript",
            function_name="ProcessTranscript",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="process_transcript.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=512
        )

        self.process_transcript_lambda.add_event_source(
            lambda_event_sources.S3EventSource(
                self.bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="texts/")]
            )
        )

        # Grant permissions
        self.bucket.grant_read(self.process_transcript_lambda)
        self.bucket.grant_put(self.process_transcript_lambda)
