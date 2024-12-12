# damg7245_final_project/Application/fastapi/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import requests
import os
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import openai
from pinecone import Pinecone, ServerlessSpec
from pydantic import BaseModel

from config import fastapi_config
from utils.snowflake_client import SnowflakeClient
from utils.s3_utils import S3Client
from utils import get_news

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = fastapi_config.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
openai.api_key = OPENAI_API_KEY

pc = Pinecone(api_key=PINECONE_API_KEY)
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=1536,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1'),
    )
index = pc.Index(PINECONE_INDEX_NAME)

if not all([SECRET_KEY, GOOGLE_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_API_KEY]):
    raise RuntimeError("Missing required environment variables.")

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

snowflake_client = SnowflakeClient()


class UserCreateRequest(BaseModel):
    username: str
    password: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_from_snowflake(username: str) -> Optional[dict]:
    return snowflake_client.get_user(username)

def authenticate_user(username: str, password: str):
    user = get_user_from_snowflake(username)
    if not user:
        return False
    if not pwd_context.verify(password, user['hashed_password']):
        return False
    return user

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = get_user_from_snowflake(username)
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception

@app.post("/register")
def register(user: UserCreateRequest):
    existing_user = get_user_from_snowflake(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_password = pwd_context.hash(user.password)
    snowflake_client.create_user(user.username, hashed_password)
    return {"username": user.username, "message": "User registered successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user["username"]}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/protected-endpoint")
def protected_endpoint(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello, {current_user['username']}. You are authenticated!"}

def geocode_zip_code(zip_code: str) -> Optional[Dict[str, float]]:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={zip_code}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK" and len(data["results"]) > 0:
            location = data["results"][0]["geometry"]["location"]
            return {"lat": location["lat"], "lng": location["lng"]}
    return None

def find_restaurants(lat: float, lng: float, radius_meters: int = 8047) -> List[Dict[str, Any]]:
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius_meters,
        "type": "restaurant",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK":
            restaurants = []
            for place in data.get("results", []):
                restaurant_info = {
                    "name": place.get("name"),
                    "address": place.get("vicinity"),
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total"),
                    "price_level": place.get("price_level"),
                    "place_id": place.get("place_id")
                }
                restaurants.append(restaurant_info)
            return restaurants
    return []

class Query(BaseModel):
    question: str

@app.post("/ask")
def ask_question(query: Query):
    try:
        embedding_response = openai.Embedding.create(
            model="text-embedding-ada-002", input=query.question
        )
        embedding_vector = embedding_response['data'][0]['embedding']

        response = index.query(
            vector=embedding_vector,
            top_k=5,
            include_metadata=True,
        )

        matches = response.get('matches', [])
        if not matches:
            raise HTTPException(status_code=404, detail="No relevant data found in the database.")

        contexts = [match['metadata']['content'] for match in matches]
        combined_context = " ".join(contexts)

        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """
                    You are an expert in Massachusetts food regulation laws. Your responses should strictly
                    be based on the provided context. When answering, refer to all relevant regulations
                    related to the user's query. Include regulation titles, codes, and explanations.
                """},
                {"role": "user", "content": f"Context: {combined_context}\n\n{query.question}"},
            ],
        )

        answer = completion['choices'][0]['message']['content']
        return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/restaurants")
def get_restaurants(zip_code: str, current_user: dict = Depends(get_current_user)):
    coords = geocode_zip_code(zip_code)
    if not coords:
        raise HTTPException(status_code=404, detail="Could not geocode the provided zip code.")
    restaurants = find_restaurants(coords["lat"], coords["lng"])
    return {"restaurants": restaurants}

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get('/get_news')
async def root():
    return get_news("Find the latest trends in small business technology.")
