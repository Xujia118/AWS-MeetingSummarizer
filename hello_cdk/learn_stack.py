from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class LearnStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define lambda function that generates a random number
        random_number_lambda = lambda_.Function(
            self, "RandomNumberGenerator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset("lambda"),
            handler="generateRandomNumber.handler",
        )

        # Define Step Functions states

        # Task state to invoke the lambda function
        generate_number_task = tasks.LambdaInvoke(
            self, "GenerateRandomNumber",
            lambda_function=random_number_lambda,
            output_path="$.Payload"
        )

        # Choice state to check if number is less than 0.5
        choice = sfn.Choice(self, "NumberLessThan0.5?")

        # Condition for the choice
        less_than_condition = sfn.Condition.number_less_than(
            "$.randomNumber", 0.5)

        # Wait state (optional, to add delay between retries)
        wait = sfn.Wait(
            self, "WaitBeforeRetry",
            time=sfn.WaitTime.duration(Duration.seconds(1))
        )

        # Success State
        success = sfn.Succeed(self, "Success")

        # Failure State
        failure = sfn.Fail(self, "Failure")

        # Define the workflow
        chain = (
            generate_number_task
            .next(choice
                  .when(less_than_condition, wait.next(generate_number_task))
                  .otherwise(success)
                  )
        )

        state_machine = sfn.StateMachine(
            self, "RandomNumberStateMAchine",
            definition=chain,
            timeout=Duration.minutes(5)
        )
