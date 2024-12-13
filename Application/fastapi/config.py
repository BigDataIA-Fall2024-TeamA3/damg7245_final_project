# damg7245_final_project/Application/fastapi/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AWS_ACCESS_KEY_ID=os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY=os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION=os.getenv('AWS_REGION')
    S3_BUCKET_NAME=os.getenv('S3_BUCKET_NAME')
    NVIDIA_API_KEY=os.getenv('NVIDIA_API_KEY')
    SNOWFLAKE_ACCOUNT=os.getenv('SNOWFLAKE_ACCOUNT')
    SNOWFLAKE_USER=os.getenv('SNOWFLAKE_USER')
    SNOWFLAKE_PASSWORD=os.getenv('SNOWFLAKE_PASSWORD')
    SNOWFLAKE_WAREHOUSE=os.getenv('SNOWFLAKE_WAREHOUSE')
    SNOWFLAKE_DATABASE=os.getenv('SNOWFLAKE_DATABASE')
    SNOWFLAKE_SCHEMA=os.getenv('SNOWFLAKE_SCHEMA')
    SNOWFLAKE_ROLE=os.getenv('SNOWFLAKE_ROLE')
    FASTAPI_URL=os.getenv('FASTAPI_URL')
    DATABASE_URL=os.getenv('DATABASE_URL')
    SECRET_KEY=os.getenv('SECRET_KEY')
    TAVILY_API_KEY=os.getenv('TAVILY_API_KEY')
fastapi_config = Config()