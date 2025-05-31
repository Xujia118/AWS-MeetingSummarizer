from aws_cdk import (
    Stack,
    Duration,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sqs as sqs,
    aws_iam as iam,
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

        # TODO: Find a better solution to solve dependency issue
        # This lambda shouldn't be here
        # Process transcript lambda does the main AI workflow
        process_transcript_lambda = lambda_.Function(
            self, "ProcessTranscript",
            function_name="ProcessTranscript",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="process_transcript.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                'SUMMARY_QUEUE_URL': self.summary_queue.queue_url
            }
        )

        process_transcript_lambda.add_event_source(
            lambda_event_sources.S3EventSource(
                self.bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="texts/")]
            )
        )

        # Permissions
        self.bucket.grant_read(process_transcript_lambda)

        process_transcript_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "comprehend:DetectSentiment",
                "comprehend:DetectEntities",
                "comprehend:DetectKeyPhrases",
                "comprehend:DetectSyntax",
                "comprehend:DetectDominantLanguage"
            ],
            resources=["*"]
        ))

        process_transcript_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*"
            ]
        ))

        self.summary_queue.grant_send_messages(process_transcript_lambda)
