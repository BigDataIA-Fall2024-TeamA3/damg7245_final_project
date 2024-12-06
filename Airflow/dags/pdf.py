import io
import boto3
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pdfkit
import time
from dotenv import load_dotenv
import pathlib
import os

env_path = pathlib.Path('/opt/airflow/.env')
load_dotenv(dotenv_path=env_path)

# Set up your S3 credentials and bucket
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)
bucket_name = os.getenv('bucket_name')
s3_folder = os.getenv('s3_folder')

# Step 1: Set up Selenium WebDriver
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Base URL with a placeholder for page number
base_url = "https://search.mass.gov/laws-regulations?page={}&q=Food%20Establishments"
total_pages = 10
page_increment = 10

def upload_file_to_s3(file_obj, file_name):
    try:
        s3.upload_fileobj(file_obj, bucket_name, f"{s3_folder}{file_name}")
        print(f"Uploaded to s3://{bucket_name}/{s3_folder}{file_name}")
    except Exception as e:
        print(f"Failed to upload to S3: {e}")

def html_to_pdf_and_upload(html_content, file_name):
    try:
        pdf_buffer = io.BytesIO()
        # Create a temporary local PDF file, then read it into the buffer
        temp_pdf_file = "/tmp/temp.pdf"
        pdfkit.from_string(html_content, temp_pdf_file)
        with open(temp_pdf_file, 'rb') as temp_file:
            pdf_buffer.write(temp_file.read())
        pdf_buffer.seek(0)  # Reset buffer position
        upload_file_to_s3(pdf_buffer, file_name)
    except Exception as e:
        print(f"Failed to convert HTML to PDF for {file_name}: {e}")

# Loop through pages and process regulations
for page_number in range(1, total_pages * page_increment + 1, page_increment):
    try:
        url = base_url.format(page_number)
        print(f"Processing page {page_number}: {url}")
        driver.get(url)
        time.sleep(3)

        # Fetch regulation links
        regulation_links = driver.find_elements(By.CSS_SELECTOR, "a[data-result-type='result']")
        print(f"Found {len(regulation_links)} regulations on page {page_number}.")

        # Loop through regulation links using their index
        for index in range(len(regulation_links)):
            try:
                # Refetch the element by its index
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
                    try:
                        print(f"No downloadable PDF found for {title}, attempting to save the page as PDF.")
                        # Get the current page's HTML
                        page_html = driver.page_source
                        html_to_pdf_and_upload(page_html, f"{title.replace(' ', '_')}_print.pdf")
                        print(f"Saved and uploaded printable page for {title}")
                    except Exception as e:
                        print(f"Failed to save printable page for {title}: {e}")

                # Go back to the main page
                driver.back()
                time.sleep(3)

            except Exception as e:
                print(f"Error processing regulation: {e}")

    except Exception as e:
        print(f"Error processing page {page_number}: {e}")

# Close the browser
driver.quit()
print("Scraping completed.")
