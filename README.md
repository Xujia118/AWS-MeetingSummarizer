
# Meeting Summarizer - A Fully Automated Serverless System Using AWS

## Getting Started

### Prerequisites
Install AWS CLI and CDK and configure AWS credentials in terminal

Activate virtual environment

```
$ Source .venv\bin\activate
```

Ensure "boto3>=1.38" is in requirements.txt, then install the required dependencies.

```
$ pip install -r requirements.txt
```

Deploy

```
$ cdk deploy --all
```

# System Workflow

## 🗂 Step 1: Audio Upload
* Frontend calls POST /audios
* Triggers `upload_audio.py` lambda"
    * Saves metadata to DynamoDB:
```
        item = {
            'meeting_id': meeting_id,
            'filename': filename,
            's3_path': s3_path,
            'status': 'waiting_for_emails',
        }
```
* Returns:
```
        {       
            'meeting_id': meeting_id,
            'upload_url': presigned_url,
        } 
```

Sending meeting_id to frontend at this step is critical, as frontend later has to to call GET /summaries/{summary_id} to retrieve a specific summary.

## 📧 Step 2: Collect Emails
* In parallele, frontend calls POST /emails with meeting_id in payload
* Triggers `collect_emails.py` lambda. 
    * Validates and saves emails to the DynamoDB table record:
```
        {
            "emails": ["a@example.com", "b@example.com"]
        }
``` 

## 🎧 Step 3: S3 Upload & Transcripton
* Audio file is uploaded to S3 under /audios/
* S3 triggers audio_queue (SQS)
* Triggers transcribe_start.py Lambda:
    * Starts an AWS Transcribe job
    * Output saved to S3 under /texts/


✨ Step 4: Process Transcript & Generate Summary
* Upload to /texts/ triggers process_transcript.py Lambda:
    * Fetches transcript from S3
    * Analyzes with AWS Comprehend
    * Sends enriched text to Amazon Bedrock
    * Receives final summary
    * Pushes to summary_queue:
`send_summary_to_sqs(meeting_id, summary, bucket, key)`

## 💾 Step 5: Store and Email Summary
* summary_queue triggers get_summary.py Lambda:
    * Saves summary to S3
    * Updates DynamoDB with:
```
    {
        "summary_key": "<s3_key>",
        "summary_url": "<presigned_url>"
    }
```
    * Fetches recipients using meeting_id
    * Sends summary email via AWS SES


## 🖥 Step 6: Frontend Polls for Summary
* Frontend polls `GET /summaries/{meeting_id}`
* Calls get_summary.py Lambda:
    * Returns summary text when available
