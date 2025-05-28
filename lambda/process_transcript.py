import json
import os
import boto3

s3 = boto3.client('s3')
comprehend = boto3.client('comprehend')
bedrock = boto3.client('bedrock-runtime')


def handler(event, context):
    # Step 1: Get bucket and key from input
    bucket = event.get('bucket')
    key = event.get('key')

    print("bucket:", bucket)
    print("key:", key)

    if not bucket or not key:
        raise ValueError("Missing bucket or key in event")

    # Step 2: Fetch transcript from S3
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        transcript = response['Body'].read().decode("utf-8")
        print("my transcript:", transcript)
    except Exception as e:
        raise RuntimeError(f"Error fetching from S3: {e}")


    # # Step 3: Run Comprehend Analysis
    # try:
    #     sentiment_response = comprehend.detect_sentiment(Text=transcript, LanguageCode="en")
    #     sentiment = sentiment_response["Sentiment"]
    # except Exception as e:
    #     raise RuntimeError("Error with Comprehend: {e}")
    
    # # Step 4: Generate summary with Bedrock
    # try:
    #     bedrock_prompt = f"""Human: Please summarize the following transcript in a few bullet points:\n\n{transcript}\n\nAssistant:"""
    #     bedrock_response = bedrock.invoke_model(
    #         modelId="deepseek.r1-v1:0",
    #         contentType="application/json",
    #         accept="application/json",
    #         body=json.dumps({
    #             "prompt": bedrock_prompt,
    #             "max_tokens_to_sample": 300,
    #             "temperature": 0.7,
    #             "stop_sequences": ["\n\nhuman:"]
    #         })
    #     )
    #     body = json.loads(bedrock_response['body'].read())
    #     summary = body.get("completion", "No summary returned.")
    # except Exception as e:
    #     raise RuntimeError("Error with Bedrock: {e}")

    # # Step 5: Return enriched payload
    # response = {
    #     "bucket": bucket,
    #     "key": key,
    #     "text": transcript,
    #     "sentiment": sentiment,
    #     "summary": summary
    # }

    # print("response:", response)

    # return response
