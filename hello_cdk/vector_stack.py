from aws_cdk import (
    Stack,
    Duration,
    aws_opensearchserverless as opensearch,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct
import json


class VectorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, bucket, embedding_queue, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # OpenSearch Serverless Collection
        self.collection = opensearch.CfnCollection(
            self, "MeetingVectorCollection",
            name="meeting-vectors",
            description="Vector collection for meeting transcripts and summaries",
            type="VECTORSEARCH"
        )

        # Security policy for the collection
        security_policy = opensearch.CfnSecurityPolicy(
            self, "VectorCollectionSecurityPolicy",
            name="meeting-vectors-access",
            type="encryption",
            policy=json.dumps({
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/meeting-vectors"]
                    }
                ],
                "AWSOwnedKey": True
            })
        )

        # Network policy for the collection
        network_policy = opensearch.CfnSecurityPolicy(
            self, "VectorCollectionNetworkPolicy",
            name="meeting-vectors-network-policy",
            type="network",
            policy=json.dumps([
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/meeting-vectors"]
                        },
                        {
                            "ResourceType": "dashboard",
                            "Resource": [f"collection/meeting-vectors"]
                        }
                    ],
                    "AllowFromPublic": True
                }
            ])
        )

        # Lambda execution role for OpenSearch access
        opensearch_lambda_role = iam.Role(
            self, "OpenSearchLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add OpenSearch Serverless permissions to the role
        opensearch_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "aoss:APIAccessAll"
            ],
            resources=[f"arn:aws:aoss:{self.region}:{self.account}:collection/*"]
        ))

        # Data access policy for Lambda functions - created after Lambda role
        data_access_policy = opensearch.CfnAccessPolicy(
            self, "VectorCollectionDataPolicy",
            name="meeting-vectors-data-policy",
            type="data",
            policy=json.dumps([
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/meeting-vectors"],
                            "Permission": [
                                "aoss:CreateCollectionItems",
                                "aoss:DeleteCollectionItems",
                                "aoss:UpdateCollectionItems",
                                "aoss:DescribeCollectionItems"
                            ]
                        },
                        {
                            "ResourceType": "index",
                            "Resource": [f"index/meeting-vectors/*"],
                            "Permission": [
                                "aoss:CreateIndex",
                                "aoss:DeleteIndex",
                                "aoss:UpdateIndex",
                                "aoss:DescribeIndex",
                                "aoss:ReadDocument",
                                "aoss:WriteDocument"
                            ]
                        }
                    ],
                    "Principal": [opensearch_lambda_role.role_arn]
                }
            ])
        )

        # Create Lambda layer with dependencies
        dependencies_layer = lambda_.LayerVersion(
            self, "DependenciesLayer",
            code=lambda_.Code.from_asset("lambda-layer", bundling={
                "image": lambda_.Runtime.PYTHON_3_12.bundling_image,
                "command": [
                    "bash", "-c",
                    "pip install -r requirements.txt -t /asset-output/python"
                ]
            }),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Dependencies for meeting summarizer Lambda functions"
        )

        # Lambda function to generate embeddings
        self.generate_embeddings_lambda = lambda_.Function(
            self, "GenerateEmbeddingsLambda",
            function_name="GenerateEmbeddings",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="generate_embeddings.handler",
            code=lambda_.Code.from_asset("lambda"),
            layers=[dependencies_layer],
            timeout=Duration.seconds(300),
            memory_size=1024,
            role=opensearch_lambda_role,
            environment={
                "OPENSEARCH_ENDPOINT": self.collection.attr_collection_endpoint,
                "COLLECTION_NAME": "meeting-vectors",
                "INDEX_NAME": "meetings"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Add event source for embedding queue
        self.generate_embeddings_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(embedding_queue)
        )

        # Grant permissions for Bedrock (for embeddings)
        self.generate_embeddings_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1",
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"
            ]
        ))

        # Grant S3 read permissions
        bucket.grant_read(self.generate_embeddings_lambda)
        
        # Grant SQS permissions
        embedding_queue.grant_consume_messages(self.generate_embeddings_lambda)

        # Lambda function for RAG queries
        self.rag_query_lambda = lambda_.Function(
            self, "RAGQueryLambda",
            function_name="RAGQuery",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="rag_query.handler",
            code=lambda_.Code.from_asset("lambda"),
            layers=[dependencies_layer],
            timeout=Duration.seconds(60),
            memory_size=1024,
            role=opensearch_lambda_role,
            environment={
                "OPENSEARCH_ENDPOINT": self.collection.attr_collection_endpoint,
                "COLLECTION_NAME": "meeting-vectors",
                "INDEX_NAME": "meetings"
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant permissions for Bedrock (for embeddings and LLM)
        self.rag_query_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1",
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-*"
            ]
        ))

        # Dependencies
        self.collection.add_dependency(security_policy)
        self.collection.add_dependency(network_policy)
        data_access_policy.add_dependency(self.collection)
        self.generate_embeddings_lambda.node.add_dependency(data_access_policy)
        self.rag_query_lambda.node.add_dependency(data_access_policy)

        # Outputs
        self.collection_endpoint = self.collection.attr_collection_endpoint
        self.collection_arn = self.collection.attr_arn
