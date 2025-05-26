import boto3
import os
import json
import time
import urllib.parse

transcribe = boto3.client('transcribe')


def handler(event, context):
    results = []

    for record in event['Records']:
        # The body contains a JSON string of the original S3 event
        s3_event = json.loads(record['body'])
        s3_record = s3_event['Records'][0]  # Expecting 1 per message
        bucket = s3_record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(s3_record['s3']['object']['key']) # decode the key exactly as S3 object
        media_uri = f"s3://{bucket}/{key}"
        job_name = f"TranscriptionJob-{int(time.time())}"
        output_bucket = os.environ['TRANSCRIBE_OUTPUT_BUCKET']

        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            # Dynamically detect format from extension
            MediaFormat=key.split('.')[-1],
            LanguageCode='en-US',
            OutputBucketName=output_bucket,
            OutputKey=f"texts/{job_name}.json"
        )

        results.append(
            {"status": "STARTED", "job_name": job_name, "file": key})

    return {"results": results}
