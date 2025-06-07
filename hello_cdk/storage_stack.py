from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_ses as ses,
    aws_iam as iam
)
from constructs import Construct


class StorageStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, bucket, summary_queue, table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        '''Read from SQS -> Write summary to S3 -> Write audio and summary urls to DB -> SES'''

        # SES
        sender_email = "xujia118@hotmail.com" # to update
        ses.EmailIdentity(self, "SenderIdentity",
                          identity=ses.Identity.email(sender_email)
                          )

        store_summary_lambda = lambda_.Function(
            self, "StoreSummary",
            function_name="StoreSummary",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="store_summary.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                'SUMMARY_BUCKET': bucket.bucket_name,
                'SUMMARY_TABLE': table.table_name,
                'SUMMARY_PREFIX': 'summaries/'
            }
        )

        store_summary_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(summary_queue)
        )

        # Permissions
        summary_queue.grant_consume_messages(store_summary_lambda)
        bucket.grant_read_write(store_summary_lambda)
        table.grant_write_data(store_summary_lambda)
        store_summary_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"] 
            )
        )
