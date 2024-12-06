import os
import boto3
import json
import openai
import pinecone
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# AWS setup
S3_BUCKET = os.getenv("S3_BUCKET")
S3_FOLDER_SRC = "regulations/"
S3_PATH_TGT_PYPDF = "parsed_pdfs/"
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# OpenAI API key for embedding generation
openai.api_key = os.getenv("OPENAI_API_KEY")


# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Optionally, create an index if it does not exist
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=1536,
        metric='cosine',
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )

# Now you can access the Pinecone index
index = pc.Index(PINECONE_INDEX_NAME)


# AWS session setup
session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name='us-east-2'
)
s3 = session.client('s3')


# Function to split text into smaller chunks to stay within the token limit
def split_text(text, max_tokens=8192):
    tokens = text.split()  # Simple split; refine if necessary
    return [tokens[i:i + max_tokens] for i in range(0, len(tokens), max_tokens)]


# Function to create embeddings from extracted text and upload to Pinecone
def create_embeddings_from_json(pdf_file, bucket_name, s3_folder):
    print(f"Processing {pdf_file}...")

    # Download the parsed JSON from S3
    try:
        json_obj = s3.get_object(Bucket=bucket_name, Key=pdf_file)
        json_content = json_obj['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading file {pdf_file}: {e}")
        return

    # Parse the JSON content to extract the text
    try:
        parsed_data = json.loads(json_content)
        extracted_text = parsed_data.get('content', "")
    except Exception as e:
        print(f"Error parsing JSON for {pdf_file}: {e}")
        return

    if not extracted_text:
        print(f"No content found in {pdf_file}")
        return

    # Truncate text to the max token limit
    extracted_text = extracted_text[:8192]  # Simple truncation (for large text)

    # Split the extracted text into smaller chunks to avoid token limits
    text_chunks = split_text(extracted_text)

    embeddings = []
    for chunk in text_chunks:
        try:
            response = openai.Embedding.create(
                model="text-embedding-ada-002",
                input=" ".join(chunk)
            )
            embeddings.append(response.data[0].embedding)  # Correctly access the embedding
        except Exception as e:
            print(f"Error creating embeddings for {pdf_file}: {e}")
            continue

    if not embeddings:
        print(f"No embeddings created for {pdf_file}")
        return

    # Flatten the embeddings (if they are nested lists)
    embeddings_flat = [item for sublist in embeddings for item in sublist]

    # Prepare metadata for Pinecone
    metadata = {
        "pdf_file": pdf_file,
        "content": extracted_text[:500]  # Store the first 500 characters as a preview
    }
    print(f"Embedding length: {len(embeddings_flat)}")  # Ensure the embeddings are flat

    # Upload embeddings to Pinecone
    try:
        # Note that we use the PDF filename as the ID
        upsert_response = index.upsert(
            vectors=[(pdf_file, embeddings_flat, metadata)] 
        )
        print(f"Uploaded embedding for {pdf_file} to Pinecone")
    except Exception as e:
        print(f"Error uploading to Pinecone for {pdf_file}: {e}")
        return

    # Optionally, save the preview of the text back to S3
    json_filename = pdf_file.split('/')[-1].replace(".pdf", ".json")
    json_content = json.dumps({"content": extracted_text})
    
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=f"{s3_folder}/{json_filename}",
            Body=json_content,
            ContentType='application/json'
        )
        print(f"Extracted text uploaded as {json_filename} to {s3_folder}")
    except Exception as e:
        print(f"Error uploading {json_filename} to S3: {e}")



# List JSON files in the S3 folder
def list_json_files_in_s3(bucket_name, folder):
    json_files = []
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.json'):
                json_files.append(obj['Key'])
    except Exception as e:
        print(f"Error listing files in S3: {e}")
    return json_files


# Main function to process JSON files, generate embeddings, and store in Pinecone
if __name__ == "__main__":
    # List all parsed JSON files in the 'parsed_pdfs/' folder
    json_files = list_json_files_in_s3(S3_BUCKET, S3_PATH_TGT_PYPDF)
    
    if not json_files:
        print(f"No JSON files found in {S3_PATH_TGT_PYPDF}")
    else:
        print(f"Found {len(json_files)} JSON files in {S3_PATH_TGT_PYPDF}")
        
        # Process each JSON file and create embeddings
        for json_file in json_files:
            create_embeddings_from_json(json_file, S3_BUCKET, S3_PATH_TGT_PYPDF)
