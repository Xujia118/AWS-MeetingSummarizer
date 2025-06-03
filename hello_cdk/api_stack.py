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

    def __init__(self, scope: Construct, construct_id: str, bucket, **kwargs) -> None:
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

        # Permissions
        bucket.grant_put(upload_audio_lambda)

        # API Gateway
        api = apigw.RestApi(
            self, "AudioAPI",
            rest_api_name="Audio Processing Service",
            description="API for uploading audio files",
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

        # Output the API endpoint URL
        self.api_url = api.url

