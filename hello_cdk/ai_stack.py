from aws_cdk import (
    Duration,
    Stack,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)

from constructs import Construct

'''
sequenceDiagram
    participant S3 as S3 (Audio + Transcript + Summary)
    participant Transcribe
    participant Lambda
    participant Comprehend
    participant Bedrock
    participant DB as DynamoDB / RDS

    Note over S3, Transcribe: Step 1: Transcribe starts using audio in S3
    Transcribe->>S3: Save transcript JSON
    S3->>Lambda: Trigger Lambda on new transcript file
    Lambda->>S3: Fetch transcript text
    Lambda->>Comprehend: Analyze text (real-time)
    Lambda->>Bedrock: Summarize (real-time)
    Lambda->>S3: Save summary
    Lambda->>DB: Save metadata and pointers
'''


class AIStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, bucket, audio_queue, summary_queue, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        '''
        Lambda for Transcribe. 
        Transcribe is an independent step. When SQS has a new message, a lambda worker is notified.
        It fetches audio path in S3 and sends to Transcribe.
        Transcribe goes to find the audio file and transcribes, and stores text back to S3.
        '''

        # Transcribe lambda retrieves messages from SQS and triggers Transcribe
        transcribe_lambda = lambda_.Function(
            self, "StartTranscribeLambda",
            function_name="StartTranscriptionJob",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="transcribe_start.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "TRANSCRIBE_OUTPUT_BUCKET": bucket.bucket_name,
                "TRANSCRIBE_OUTPUT_PREFIX": "texts/",
                "SUMMARY_QUEUE_URL": summary_queue.queue_url,
            },
            timeout=Duration.seconds(30),
        )

        transcribe_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(audio_queue)
        )

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
                'SUMMARY_QUEUE_URL': summary_queue.url
            }
        )

        process_transcript_lambda.add_event_source(
            lambda_event_sources.S3EventSource(
                bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="texts/")]
            )
        )

        # Grant permissions
        audio_queue.grant_consume_messages(transcribe_lambda)
        bucket.grant_read_write(transcribe_lambda)
        transcribe_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["transcribe:StartTranscriptionJob"],
            resources=["*"]
        ))

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

        summary_queue.grant_send_messages(process_transcript_lambda)

