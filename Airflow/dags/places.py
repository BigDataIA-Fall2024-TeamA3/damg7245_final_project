from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import time
import boto3
import requests
import pathlib
from dotenv import load_dotenv
import pandas as pd
import re
from io import BytesIO
import snowflake.connector
import urllib.parse

# Load environment variables


env_path = pathlib.Path('/opt/airflow/.env')
load_dotenv(dotenv_path=env_path)


# Set up AWS S3 client


s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

# Environment Variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
LOCAL_REPO_DIR = os.getenv("LOCAL_REPO_DIR", "/home/airflow/tmp/stage/")
LOCAL_FILE_NAME = 'massachusetts_restaurants.csv'
LOCAL_FILE_PATH = os.path.join(LOCAL_REPO_DIR, LOCAL_FILE_NAME)
S3_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
S3_FILE_PATH = os.getenv('S3_FILE_PATH')
S3_FILE_NAME = 'data/massachusetts_restaurants.csv'
SNOWFLAKE_TABLE = 'restaurant_details'


# Define Default Arguments


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False
}


# Define Python Callable Functions


def extract_restaurant_data(**kwargs):
    """
    Extracts restaurant data from Google Places API for Massachusetts and stores it locally.
    """
    # Ensure local repository directory exists
    os.makedirs(LOCAL_REPO_DIR, exist_ok=True)
    print(f"Local repository directory ensured at: {LOCAL_REPO_DIR}")

    # Define Massachusetts boundaries
    MIN_LAT = 41.0
    MAX_LAT = 42.9
    MIN_LNG = -73.5
    MAX_LNG = -69.9
    GRID_STEP = 0.02  # Approximately 2 km

    def generate_grid(min_lat, max_lat, min_lng, max_lng, step=0.02):
        latitudes = [min_lat + x * step for x in range(int((max_lat - min_lat) / step) + 1)]
        longitudes = [min_lng + x * step for x in range(int((max_lng - min_lng) / step) + 1)]
        grid = [(lat, lng) for lat in latitudes for lng in longitudes]
        return grid

    grid_points = generate_grid(MIN_LAT, MAX_LAT, MIN_LNG, MAX_LNG, GRID_STEP)
    print(f"Generated {len(grid_points)} grid points for Massachusetts.")

    def fetch_restaurants(lat, lng, radius=1500, type='restaurant', keyword=None):
        url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
        params = {
            'key': GOOGLE_API_KEY,
            'location': f"{lat},{lng}",
            'radius': radius,
            'type': type
        }
        if keyword:
            params['keyword'] = keyword

        restaurants = []
        while True:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                print(f"Error: {response.status_code} for location ({lat}, {lng})")
                break

            data = response.json()
            if data.get('status') not in ['OK', 'ZERO_RESULTS']:
                print(f"API Error: {data.get('status')} for location ({lat}, {lng})")
                break

            restaurants.extend(data.get('results', []))

            # Check for next page
            if 'next_page_token' in data:
                next_page_token = data['next_page_token']
                time.sleep(2)  # Wait before next request
                params = {
                    'key': GOOGLE_API_KEY,
                    'pagetoken': next_page_token
                }
            else:
                break

        return restaurants

    def extract_zip_code(address):
        match = re.search(r'\b\d{5}(?:-\d{4})?\b', address)
        return match.group(0) if match else None

    # To keep track of unique restaurants
    unique_place_ids = set()
    restaurants_list = []

    for idx, (lat, lng) in enumerate(grid_points):
        print(f"Fetching restaurants for grid point {idx + 1}/{len(grid_points)}: ({lat}, {lng})")
        try:
            restaurants = fetch_restaurants(lat, lng, radius=1500)
            for place in restaurants:
                place_id = place.get('place_id')
                if place_id and place_id not in unique_place_ids:
                    unique_place_ids.add(place_id)
                    address = place.get('vicinity', '')
                    zip_code = extract_zip_code(address)
                    restaurant = {
                        'place_id': place_id,
                        'name': place.get('name'),
                        'address': address,
                        'zip_code': zip_code,
                        'latitude': place['geometry']['location']['lat'],
                        'longitude': place['geometry']['location']['lng'],
                        'rating': place.get('rating'),
                        'user_ratings_total': place.get('user_ratings_total'),
                        'business_status': place.get('business_status'),
                        'types': place.get('types')
                    }
                    restaurants_list.append(restaurant)
            # Respect API rate limits
            time.sleep(1)
        except Exception as e:
            print(f"Exception occurred: {e}")
            continue

    # Create DataFrame
    restaurants_df = pd.DataFrame(restaurants_list)
    print(f"Total unique restaurants fetched: {len(restaurants_df)}")

    # Save DataFrame to local CSV
    try:
        restaurants_df.to_csv(LOCAL_FILE_PATH, index=False)
        print(f"Successfully saved data locally at: {LOCAL_FILE_PATH}")
    except Exception as e:
        print(f"Error saving data locally: {e}")
        raise

    # Push the local file path to XCom for the next task
    kwargs['ti'].xcom_push(key='local_file_path', value=LOCAL_FILE_PATH)

def upload_to_s3(**kwargs):
    """
    Loads the extracted data from the local repository to AWS S3.
    """
    # Retrieve the local file path from XCom
    ti = kwargs['ti']
    local_file_path = ti.xcom_pull(key='local_file_path', task_ids='extract_restaurant_data_task')

    if not local_file_path:
        raise ValueError("No local file path found in XCom. Extraction might have failed.")

    # Upload the local file to S3
    try:
        with open(local_file_path, 'rb') as f:
            s3.upload_fileobj(f, S3_BUCKET_NAME, S3_FILE_NAME)
        print(f"Successfully uploaded {local_file_path} to s3://{S3_BUCKET_NAME}/{S3_FILE_NAME}")
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        raise

def insert_into_snowflake(**kwargs):
    """
    Loads the data from S3 into Snowflake's restaurant_details table and adds an insert_date audit field.
    """
    # Retrieve the S3 file path from environment variables
    s3_path = f"s3://{S3_BUCKET_NAME}/{S3_FILE_PATH}/{S3_FILE_NAME}"

    # Download the file from S3
    try:
        obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=S3_FILE_NAME)
        data = obj['Body'].read()
        restaurants_df = pd.read_csv(BytesIO(data))
        print(f"Successfully downloaded data from s3://{S3_BUCKET_NAME}/{S3_FILE_PATH}/{S3_FILE_NAME}")
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        raise

    # Add insert_date column
    restaurants_df['insert_date'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Connect to Snowflake
    try:
        conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA'),
            role=os.getenv('SNOWFLAKE_ROLE')
        )
        cursor = conn.cursor()
        print("Connected to Snowflake successfully.")
    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        raise

    # Create table if not exists with insert_date
    try:
        create_table_query = f"""
            CREATE OR REPLACE TABLE {SNOWFLAKE_TABLE} (
                place_id STRING,
                name STRING,
                address STRING,
                zip_code STRING,
                latitude FLOAT,
                longitude FLOAT,
                rating FLOAT,
                user_ratings_total INT,
                business_status STRING,
                types ARRAY,
                insert_date TIMESTAMP
            );
        """
        cursor.execute(create_table_query)
        print(f"Table {SNOWFLAKE_TABLE} created/replaced successfully.")
    except Exception as e:
        print(f"Error creating table in Snowflake: {e}")
        cursor.close()
        conn.close()
        raise

    # Insert data into Snowflake
    try:
        # Prepare the data for insertion
        for index, row in restaurants_df.iterrows():
            insert_query = f"""
                INSERT INTO {SNOWFLAKE_TABLE} (
                    place_id, name, address, zip_code, latitude, longitude, rating,
                    user_ratings_total, business_status, types, insert_date
                ) VALUES (
                    %(place_id)s, %(name)s, %(address)s, %(zip_code)s, %(latitude)s,
                    %(longitude)s, %(rating)s, %(user_ratings_total)s, %(business_status)s,
                    %(types)s, %(insert_date)s
                )
            """
            cursor.execute(insert_query, row.to_dict())
        print(f"Data inserted into {SNOWFLAKE_TABLE} successfully.")
    except Exception as e:
        print(f"Error inserting data into Snowflake: {e}")
        cursor.close()
        conn.close()
        raise

    # Close the Snowflake connection
    try:
        cursor.close()
        conn.close()
        print("Snowflake connection closed successfully.")
    except Exception as e:
        print(f"Error closing Snowflake connection: {e}")

    # Optionally, delete the local file after successful upload
    try:
        os.remove(local_file_path)
        print(f"Successfully deleted local file: {local_file_path}")
    except Exception as e:
        print(f"Error deleting local file: {e}")


# Define the DAG


with DAG(
    'massachusetts_restaurant_pipeline',
    default_args=default_args,
    description='Extracts restaurant data from Google Places API, loads to S3, and inserts into Snowflake',
    schedule_interval=timedelta(days=1),
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'restaurants', 'massachusetts'],
) as dag:
    # Task 1: Extract Data and Store Locally
    extract_restaurant_data_task = PythonOperator(
        task_id='extract_restaurant_data_task',
        python_callable=extract_restaurant_data,
        provide_context=True,
    )

    # Task 2: Load Data from Local to S3
    upload_to_s3_task = PythonOperator(
        task_id='upload_to_s3_task',
        python_callable=upload_to_s3,
        provide_context=True,
    )

    # Task 3: Insert Data into Snowflake
    insert_into_snowflake_task = PythonOperator(
        task_id='insert_into_snowflake_task',
        python_callable=insert_into_snowflake,
        provide_context=True,
    )

    # Define task dependencies
    extract_restaurant_data_task >> upload_to_s3_task >> insert_into_snowflake_task
