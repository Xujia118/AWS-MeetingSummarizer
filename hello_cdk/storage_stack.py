from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
)
from constructs import Construct


class StorageStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, bucket, summary_queue, table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        '''Read from SQS -> Write summary to S3 -> Write audio and summary urls to DB'''

        store_summary_lambda = lambda_.Function(
            self, "StoreSummary",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="store_summary.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                'SUMMARY_BUCKET': bucket.bucket_name,
                'DDB_TABLE': table.table_name
            }
        )

        store_summary_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(self.summary_queue)
        )

        # Permissions
        summary_queue.grant_consume_messages(store_summary_lambda)
        bucket.grant_put(store_summary_lambda)
        table.grant_write_data(store_summary_lambda)
