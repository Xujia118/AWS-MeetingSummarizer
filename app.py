#!/usr/bin/env python3
import os

import aws_cdk as cdk

from hello_cdk.input_stack import InputStack
from hello_cdk.learn_stack import LearnStack


app = cdk.App()
InputStack(app, "InputStack")
# LearnStack(app, "LearnStack")


app.synth()
