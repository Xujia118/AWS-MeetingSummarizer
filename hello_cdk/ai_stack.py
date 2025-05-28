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
    def __init__(self, scope: Construct, construct_id: str, input_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        '''
        Lambda for Transcribe. 
        Transcribe is an independent step. When SQS has a new message, a lambda worker is notified.
        It fetches audio path in S3 and sends to Transcribe.
        Transcribe goes to find the audio file and transcribes, and stores text back to S3.
        '''

        # Lambda retrieves audio path in S3 for Transcribe
        # Transcribe starts transcription job and saves text to S3
        transcribe_lambda = lambda_.Function(
            self, "StartTranscribeLambda",
            function_name="StartTranscriptionJob",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="transcribe_start.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "TRANSCRIBE_OUTPUT_BUCKET": input_stack.bucket.bucket_name,
                "TRANSCRIBE_OUTPUT_PREFIX": "texts/"
            },
            timeout=Duration.seconds(30),
        )

        transcribe_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(input_stack.audio_queue)
        )

        # Grant permissions
        input_stack.audio_queue.grant_consume_messages(transcribe_lambda)
        input_stack.bucket.grant_read(transcribe_lambda)
        input_stack.bucket.grant_put(transcribe_lambda)
        transcribe_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["transcribe:StartTranscriptionJob"],
            resources=["*"]
        ))

        input_stack.process_transcript_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "comprehend:DetectSentiment",
                "comprehend:DetectEntities",
                "comprehend:DetectKeyPhrases",
                "comprehend:DetectSyntax",
                "comprehend:DetectDominantLanguage"
            ],
            resources=["*"]
        ))

        input_stack.process_transcript_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*"
            ]
        ))

        input_stack.bucket.grant_read_write(input_stack.process_transcript_lambda)


        # # Lambda: Save summary to S3
        # save_summary_lambda = lambda_.Function(
        #     self, "SaveSummaryLambda",
        #     runtime=lambda_.Runtime.PYTHON_3_12,
        #     handler="save_summary.handler",
        #     code=lambda_.Code.from_asset("lambda/save_summary"),
        #     timeout=Duration.seconds(30),
        # )

        # # # Lambda: Save metadata to DynamoDB
        # save_metadata_lambda = lambda_.Function(
        #     self, "SaveMetadataLambda",
        #     runtime=lambda_.Runtime.PYTHON_3_12,
        #     handler="save_metadata.handler",
        #     code=lambda_.Code.from_asset("lambda/save_metadata"),
        #     timeout=Duration.seconds(30),
        # )

        # Grant necessary permissions



        # # Create the state machine
        # sm = sfn.StateMachine(
        #     self, "AIProcessingStateMachine",
        #     definition=definition,
        #     timeout=Duration.minutes(5)
        # )
