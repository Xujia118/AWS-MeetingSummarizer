#!/usr/bin/env python3
import os

import aws_cdk as cdk

from hello_cdk.shared_resources_stack import SharedResourcesStack
from hello_cdk.input_stack import InputStack
from hello_cdk.ai_stack import AIStack
from hello_cdk.storage_stack import StorageStack
from hello_cdk.api_stack import APIStack 


app = cdk.App()

shared_resources_stack = SharedResourcesStack(app, "SharedResourcesStack")

input_stack = InputStack(app, "InputStack",
                         bucket=shared_resources_stack.bucket,
                         audio_queue=shared_resources_stack.audio_queue,
                         )

ai_stack = AIStack(app, "AIStack",
                   bucket=shared_resources_stack.bucket,
                   audio_queue=shared_resources_stack.audio_queue,
                   summary_queue=shared_resources_stack.summary_queue
                   )

storage_stack = StorageStack(app, "StorageStack",
                             bucket=shared_resources_stack.bucket,
                             summary_queue=shared_resources_stack.summary_queue,
                             table=shared_resources_stack.table
                             )

api_stack = APIStack(app, "APIStack",
                     bucket=shared_resources_stack.bucket,
                     table=shared_resources_stack.table,
                     )


app.synth()

