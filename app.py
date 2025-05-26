#!/usr/bin/env python3
import os

import aws_cdk as cdk

from hello_cdk.input_stack import InputStack
from hello_cdk.ai_stack import AIStack


app = cdk.App()
input_stack = InputStack(app, "InputStack")
ai_stack = AIStack(app, "AIStack", input_stack=input_stack)

app.synth()
