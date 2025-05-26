from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
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
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        '''Transcribe is an independent step'''
        # Poll SQS with EventBridge
        # Transcribe starts transcription job and saves text to S3
        # Code still missing...


        # Lambda: Fetch transcript text from S3
        fetch_transcript_lambda = lambda_.Function(
            self, "FetchTranscriptLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="fetch_transcript.handler",
            code=lambda_.Code.from_asset("lambda/fetch_transcript"),
            timeout=Duration.seconds(30),
        )

        # Call Comprehend on transcription text
        comprehend_lambda = lambda_.Function(
            self, "ComprehendLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="comprehend_handler.handler",
            code=lambda_.Code.from_asset("lambda/comprehend_handler"),
            timeout=Duration.seconds(30),
        )

        # Lambda: Call Bedrock to summarize text
        bedrock_lambda = lambda_.Function(
            self, "BedrockLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="bedrock_handler.handler",
            code=lambda_.Code.from_asset("lambda/bedrock_handler"),
            timeout=Duration.seconds(30),
        )

        # Lambda: Save summary to S3
        save_summary_lambda = lambda_.Function(
            self, "SaveSummaryLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="save_summary.handler",
            code=lambda_.Code.from_asset("lambda/save_summary"),
            timeout=Duration.seconds(30),
        )

        # Lambda: Save metadata to DynamoDB
        save_metadata_lambda = lambda_.Function(
            self, "SaveMetadataLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="save_metadata.handler",
            code=lambda_.Code.from_asset("lambda/save_metadata"),
            timeout=Duration.seconds(30),
        )

        # Grant necessary permissions


        '''Step Functions start'''
        # Lambda fetches text from S3 and sends to Comprehend
        fetch_task = tasks.LambdaInvoke(
            self, "Fetch Transcript",
            lambda_function=fetch_transcript_lambda,
            output_path="$.Payload",
        )

        # Lambda gets enriched text from Comprehend and sends to Bedrock
        comprehend_task = tasks.LambdaInvoke(
            self, "Comprehend Text",
            lambda_function=comprehend_lambda,
            output_path="$.Payload",
        )

        # Bedrock summarizes the text 
        bedrock_task = tasks.LambdaInvoke(
            self, "Summarize with Bedrock",
            lambda_function=bedrock_lambda,
            output_path="$.Payload",
        )

        # Lambda gets the summary and sends to S3
        save_summary_task = tasks.LambdaInvoke(
            self, "Save Summary to S3",
            lambda_function=save_summary_lambda,
            output_path="$.Payload",
        )

        # Lambda sends all the metadata to DynamoDB
        save_metadata_task = tasks.LambdaInvoke(
            self, "Save Metadata to DynamoDB",
            lambda_function=save_metadata_lambda,
            output_path="$.Payload",
        )
        
        # Chain tasks in order
        definition = fetch_task.next(
            comprehend_task
        ).next(
            bedrock_task
        ).next(
            save_summary_task
        ).next(
            save_metadata_task
        )

        # Create the state machine
        sm = sfn.StateMachine(
            self, "AIProcessingStateMachine",
            definition=definition,
            timeout=Duration.minutes(5)
        )

