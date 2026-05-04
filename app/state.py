import os
import pickle
import boto3
from botocore.config import Config

R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "layzur-life")
SESSION_BLOB_NAME = os.getenv("SESSION_BLOB_NAME", "insta-session.pkl")

def _get_s3_client():
    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
        raise EnvironmentError("Missing R2 credentials.")
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(region_name='auto', signature_version='s3v4'),
    )

def load_session() -> dict | None:
    try:
        s3 = _get_s3_client()
        response = s3.get_object(Bucket=R2_BUCKET_NAME, Key=SESSION_BLOB_NAME)
        return pickle.loads(response['Body'].read())
    except s3.exceptions.NoSuchKey:
        print("No existing session found in R2.")
    except Exception as e:
        print(f"Could not load session: {e}")
    return None

def save_session(session: dict):
    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=SESSION_BLOB_NAME,
            Body=pickle.dumps(session)
        )
    except Exception as e:
        print(f"Could not save session: {e}")
