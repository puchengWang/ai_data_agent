import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
SQL_EXECUTOR_LAMBDA_NAME = os.getenv("SQL_EXECUTOR_LAMBDA_NAME")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID")

if not SQL_EXECUTOR_LAMBDA_NAME:
    raise ValueError("Missing environment variable: SQL_EXECUTOR_LAMBDA_NAME")


if not BEDROCK_MODEL_ID:
    raise ValueError("Missing environment variable: BEDROCK_MODEL_ID")