'''
The minimal setup

POST /audios → Lambda generates a pre-signed S3 PUT URL.
Frontend uses this URL to upload directly to S3 (audios/).
The S3 upload will trigger downstream processing (if configured).
'''
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_apigateway as apigw
)
from constructs import Construct


class APIStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, bucket, table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda for audio upload
        upload_audio_lambda = lambda_.Function(
            self, "GeneratedPresignedURL",
            function_name="GeneratedPresignedURL",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="upload_audio.handler",
            code=lambda_.Code.from_asset('lambda'),
            timeout=Duration.seconds(500),
            environment={
                "AUDIO_BUCKET": bucket.bucket_name,
                "AUDIO_PREFIX": "audios/"
            }
        )

        '''
        Since we are building serverless, we can't use socket
        Without socket, there is no way to send summary to frontend without user action
        For production, we can send an email link via SNS
        For demo, we just poll
        '''

        # Lambda to fetch summary data from DB
        get_summary_lambda = lambda_.Function(
            self, "GetSummary",
            function_name="GetSummary",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="get_summary.handler",
            code=lambda_.Code.from_asset('lambda'),
            timeout=Duration.seconds(30),
            environment={
                "SUMMARY_BUCKET": bucket.bucket_name,
                'SUMMARY_TABLE': table.table_name,
                "SUMMARY_PREFIX": "summaries/"
            }
        )

        # Permissions
        bucket.grant_put(upload_audio_lambda)
        table.grant_read_data(get_summary_lambda)

        # API Gateway
        api = apigw.RestApi(
            self, "AudioAPI",
            rest_api_name="Audio to Text Processing Service",
            description="API for uploading audio files and retrieving summaries",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS
            )
        )

        # Create the /audios resource and POST method
        audios = api.root.add_resource("audios")
        audios.add_method(
            "POST",
            apigw.LambdaIntegration(upload_audio_lambda),
            request_parameters={
                "method.request.header.Content-Type": True
            },
            request_models={
                "application/json": apigw.Model.EMPTY_MODEL
            }
        )

        # Create the /summaries resource and GET method
        summaries = api.root.add_resource('summaries')

        single_summary = summaries.add_resource("{meeting_id}") 
        single_summary.add_method(
            'GET',
            apigw.LambdaIntegrationOptions(),
            request_parameters={
                "method.request.path.meeting_id": True
            }
        )
        
        # Output the API endpoint URL
        self.api_url = api.url

