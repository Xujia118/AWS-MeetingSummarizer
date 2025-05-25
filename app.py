#!/usr/bin/env python3
import os

import aws_cdk as cdk

from hello_cdk.input_stack import InputStack


app = cdk.App()
InputStack(app, "InputStack")



app.synth()
