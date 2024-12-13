import os
import json
import io
import time
import requests
import pathlib
import boto3
import PyPDF2
import openai
import pinecone
import pdfkit

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# Load environment variables

env_path = pathlib.Path('/opt/airflow/.env')
load_dotenv(dotenv_path=env_path)

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
bucket_name = os.getenv('bucket_name')
s3_folder = os.getenv('s3_folder', 'regulations/')
S3_BUCKET = os.getenv("S3_BUCKET", bucket_name)
S3_FOLDER_SRC = s3_folder
S3_PATH_TGT_PYPDF = "parsed_pdfs/"
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", AWS_ACCESS_KEY_ID)
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", AWS_SECRET_ACCESS_KEY)
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "my-index")

openai.api_key = os.getenv("OPENAI_API_KEY")


# Initialize AWS clients

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name='us-east-2'
)
s3 = session.client('s3')


# Functions


def upload_file_to_s3(file_obj, file_name):
    s3.upload_fileobj(file_obj, S3_BUCKET, f"{S3_FOLDER_SRC}{file_name}")
    print(f"Uploaded to s3://{S3_BUCKET}/{S3_FOLDER_SRC}{file_name}")

def html_to_pdf_and_upload(html_content, file_name):
    pdf_buffer = io.BytesIO()
    temp_pdf_file = "/tmp/temp.pdf"
    pdfkit.from_string(html_content, temp_pdf_file)
    with open(temp_pdf_file, 'rb') as temp_file:
        pdf_buffer.write(temp_file.read())
    pdf_buffer.seek(0)
    upload_file_to_s3(pdf_buffer, file_name)

def scrape_upload_pdfs():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    base_url = "https://search.mass.gov/laws-regulations?page={}&q=Food%20Establishments"
    total_pages = 10
    page_increment = 10

    for page_number in range(1, total_pages * page_increment + 1, page_increment):
        url = base_url.format(page_number)
        print(f"Processing page {page_number}: {url}")
        driver.get(url)
        time.sleep(3)

        regulation_links = driver.find_elements(By.CSS_SELECTOR, "a[data-result-type='result']")
        print(f"Found {len(regulation_links)} regulations on page {page_number}.")

        for index in range(len(regulation_links)):
            try:
                regulation_links = driver.find_elements(By.CSS_SELECTOR, "a[data-result-type='result']")
                link = regulation_links[index]
                title = link.find_element(By.XPATH, ".//span").text.strip()
                regulation_url = link.get_attribute("href")

                print(f"Processing regulation: {title}")
                driver.get(regulation_url)
                time.sleep(2)

                # Check for PDF download link
                try:
                    pdf_link = driver.find_element(By.CSS_SELECTOR, "a.ma__download-link__file-link").get_attribute("href")
                    response = requests.get(pdf_link, stream=True)
                    if response.status_code == 200:
                        pdf_buffer = io.BytesIO(response.content)
                        upload_file_to_s3(pdf_buffer, f"{title.replace(' ', '_')}.pdf")
                except:
                    # Handle printable page
                    print(f"No downloadable PDF found for {title}, attempting to save the page as PDF.")
                    page_html = driver.page_source
                    html_to_pdf_and_upload(page_html, f"{title.replace(' ', '_')}_print.pdf")
                    print(f"Saved and uploaded printable page for {title}")

                driver.back()
                time.sleep(3)

            except Exception as e:
                print(f"Error processing regulation: {e}")

    driver.quit()
    print("Scraping completed.")

def list_pdfs_in_s3(bucket_name, folder):
    pdf_files = []
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
    for obj in response.get('Contents', []):
        if obj['Key'].endswith('.pdf'):
            pdf_files.append(obj['Key'])
    return pdf_files

def extract_text_from_pdf_pypdf(pdf_file, bucket_name, s3_folder):
    print(f"Processing {pdf_file}...")
    pdf_obj = s3.get_object(Bucket=bucket_name, Key=pdf_file)
    pdf_content = pdf_obj['Body'].read()

    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
    extracted_text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        extracted_text += page.extract_text()

    pdf_filename = pdf_file.split('/')[-1]
    json_filename = pdf_filename.replace(".pdf", ".json")
    json_content = json.dumps({"content": extracted_text})

    s3.put_object(
        Bucket=bucket_name,
        Key=f"{s3_folder}{json_filename}",
        Body=json_content,
        ContentType='application/json'
    )
    print(f"Extracted text uploaded as {json_filename} to {s3_folder}")

def extract_text_from_pdfs():
    pdf_files = list_pdfs_in_s3(S3_BUCKET, S3_FOLDER_SRC)
    if not pdf_files:
        print(f"No PDFs found in {S3_FOLDER_SRC}")
    else:
        print(f"Found {len(pdf_files)} PDFs in {S3_FOLDER_SRC}")
        for pdf_file in pdf_files:
            extract_text_from_pdf_pypdf(pdf_file, S3_BUCKET, S3_PATH_TGT_PYPDF)

def list_json_files_in_s3(bucket_name, folder):
    json_files = []
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
    for obj in response.get('Contents', []):
        if obj['Key'].endswith('.json'):
            json_files.append(obj['Key'])
    return json_files

def split_text(text, max_tokens=8192):
    tokens = text.split()
    return [tokens[i:i + max_tokens] for i in range(0, len(tokens), max_tokens)]

def create_embeddings_from_json(pdf_file, bucket_name, s3_folder, index):
    print(f"Processing {pdf_file}...")
    # Download JSON
    json_obj = s3.get_object(Bucket=bucket_name, Key=pdf_file)
    json_content = json_obj['Body'].read().decode('utf-8')

    parsed_data = json.loads(json_content)
    extracted_text = parsed_data.get('content', "")

    if not extracted_text:
        print(f"No content found in {pdf_file}")
        return

    # Truncate text
    extracted_text = extracted_text[:8192]
    text_chunks = split_text(extracted_text)

    embeddings = []
    for chunk in text_chunks:
        try:
            response = openai.Embedding.create(
                model="text-embedding-ada-002",
                input=" ".join(chunk)
            )
            embeddings.append(response.data[0].embedding)
        except Exception as e:
            print(f"Error creating embeddings for {pdf_file}: {e}")
            continue

    if not embeddings:
        print(f"No embeddings created for {pdf_file}")
        return

    # Flatten embeddings
    # Note: `response.data[0].embedding` is already a single vector, we concatenated multiple chunks.
    # Pinecone expects one vector per ID. If we want multiple vectors per file, we must store multiple IDs.
    # For simplicity, we'll just take the first embedding or average them.
    # Here let's average all embeddings (if multiple chunks):
    import numpy as np
    all_embeddings = np.array(embeddings)
    final_embedding = np.mean(all_embeddings, axis=0).tolist()

    metadata = {
        "pdf_file": pdf_file,
        "content": extracted_text[:500]
    }

    # Upsert to pinecone
    index.upsert(vectors=[(pdf_file, final_embedding, metadata)])
    print(f"Uploaded embedding for {pdf_file} to Pinecone")

def create_embeddings():
    # Initialize Pinecone
    pinecone.init(api_key=os.getenv("PINECONE_API_KEY"), environment="us-east-1-aws")
    # Create index if not exists
    if PINECONE_INDEX_NAME not in pinecone.list_indexes():
        pinecone.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=1536,
            metric='cosine'
        )
    index = pinecone.Index(PINECONE_INDEX_NAME)

    json_files = list_json_files_in_s3(S3_BUCKET, S3_PATH_TGT_PYPDF)
    if not json_files:
        print(f"No JSON files found in {S3_PATH_TGT_PYPDF}")
    else:
        print(f"Found {len(json_files)} JSON files in {S3_PATH_TGT_PYPDF}")
        for json_file in json_files:
            create_embeddings_from_json(json_file, S3_BUCKET, S3_PATH_TGT_PYPDF, index)


# Define the DAG and Tasks

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 0
}

with DAG(
    dag_id='scrape_extract_embeddings_pipeline',
    default_args=default_args,
    schedule=None,
    catchup=False
) as dag:

    t1 = PythonOperator(
        task_id='scrape_upload_pdfs',
        python_callable=scrape_upload_pdfs
    )

    t2 = PythonOperator(
        task_id='extract_text_from_pdfs',
        python_callable=extract_text_from_pdfs
    )

    t3 = PythonOperator(
        task_id='create_embeddings',
        python_callable=create_embeddings
    )

    t1 >> t2 >> t3
