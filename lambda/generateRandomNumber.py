import json
import random


def handler(event, context):
    random_number = random.random()

    return {
        "statusCode": 200,
        "randomNumber": random_number,
    }
