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
from pydantic import BaseModel

from config import fastapi_config
from utils.snowflake_client import SnowflakeClient
from utils.s3_utils import S3Client
from utils import get_news
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.chat_models import ChatOpenAI
from tavily import TavilyClient

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
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

openai.api_key = OPENAI_API_KEY

if not all([SECRET_KEY, GOOGLE_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_API_KEY]):
    raise RuntimeError("Missing required environment variables.")

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from pinecone import Pinecone, ServerlessSpec
pc = Pinecone(api_key=PINECONE_API_KEY)
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=1536,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1'),
    )
index = pc.Index(PINECONE_INDEX_NAME)

snowflake_client = SnowflakeClient()

class UserCreateRequest(BaseModel):
    username: str
    password: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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
    creds_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise creds_exception
        user = get_user_from_snowflake(username)
        if user is None:
            raise creds_exception
        return user
    except JWTError:
        raise creds_exception

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
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        if data["status"] == "OK" and len(data["results"]) > 0:
            loc = data["results"][0]["geometry"]["location"]
            return {"lat": loc["lat"], "lng": loc["lng"]}
    return None

_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")

def get_place_details(place_id: str) -> Dict[str, Any]:
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "key": GOOGLE_API_KEY,
        "fields": "website,types,geometry"
    }
    resp = requests.get(details_url, params=params)
    if resp.status_code == 200:
        d_data = resp.json()
        if d_data.get("status") == "OK":
            result = d_data.get("result", {})
            return {
                "website": result.get("website", None),
                "types": result.get("types", []),
                "lat": result.get("geometry", {}).get("location", {}).get("lat"),
                "lng": result.get("geometry", {}).get("location", {}).get("lng")
            }
    return {"website": None, "types": [], "lat": None, "lng": None}

def find_restaurants(lat: float, lng: float, radius_meters: int = 8047) -> List[Dict[str, Any]]:
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius_meters,
        "type": "restaurant",
        "key": GOOGLE_API_KEY
    }
    resp = requests.get(url, params=params)
    restaurants = []
    if resp.status_code == 200:
        data = resp.json()
        if data["status"] == "OK":
            for place in data.get("results", []):
                place_id = place.get("place_id")
                details = get_place_details(place_id)
                cuisine_types = [t for t in details["types"] if t != "restaurant"] or ["N/A"]
                restaurant_info = {
                    "name": place.get("name"),
                    "address": place.get("vicinity"),
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total"),
                    "price_level": place.get("price_level"),
                    "place_id": place_id,
                    "lat": details["lat"],
                    "lng": details["lng"],
                    "cuisine_types": cuisine_types,
                    "website": details["website"]
                }
                restaurants.append(restaurant_info)
    return restaurants

class QueryModel(BaseModel):
    question: str

@app.post("/ask")
def ask_question(query: QueryModel):
    # For direct regulation queries if needed
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
            raise HTTPException(status_code=404, detail="No relevant data found.")
        contexts = [m['metadata']['content'] for m in matches]
        combined_context = " ".join(contexts)
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """
                    You are an expert in Massachusetts food regulation laws. Respond strictly based on the provided context. Include regulation titles, codes, and user-friendly explanations.
                """},
                {"role": "user", "content": f"Context: {combined_context}\n\n{query.question}"},
            ],
        )
        answer = completion['choices'][0]['message']['content']
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

def search_regulations(query: str) -> str:
    # Used by the agent
    try:
        embedding_response = openai.Embedding.create(model="text-embedding-ada-002", input=query)
        embedding_vector = embedding_response['data'][0]['embedding']
        response = index.query(vector=embedding_vector, top_k=5, include_metadata=True)
        matches = response.get('matches', [])
        if not matches:
            return "No relevant regulations found."
        contexts = [m['metadata']['content'] for m in matches]
        return " ".join(contexts)
    except Exception:
        return "Error searching regulations."

def get_restaurants_tool(zip_code: str) -> str:
    coords = geocode_zip_code(zip_code)
    if not coords:
        return "Invalid zip code."
    restaurants = find_restaurants(coords["lat"], coords["lng"])
    if not restaurants:
        return "No restaurants found."
    result = ""
    for r in restaurants[:5]:
        result += (f"Name: {r['name']}, Address: {r['address']}, Rating: {r.get('rating','N/A')}, "
                   f"Cuisine: {', '.join(r['cuisine_types'])}, Website: {r.get('website','N/A')}\n")
    return result.strip()

def web_search_tool(query: str) -> str:
    return tavily_client.search(query)

def download_tool(url: str) -> str:
    headers = {"User-Agent": _USER_AGENT}
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            content = resp.text[:500]
            return f"Downloaded content snippet: {content}"
        else:
            return f"Failed to download content. Status code: {resp.status_code}"
    except Exception as e:
        return f"Error downloading content: {e}"

tools = [
    Tool(name="search_regulations", func=search_regulations, description="Summarize MA restaurant regulations"),
    Tool(name="get_restaurants", func=get_restaurants_tool, description="Fetch restaurant data by ZIP"),
    Tool(name="web_search", func=web_search_tool, description="Search external info"),
    Tool(name="download", func=download_tool, description="Download webpage content snippet")
]

GLOBAL_SYSTEM_PROMPT = """
You are a Massachusetts Restaurant Business Assistant:
- Always provide very detailed, multi-paragraph answers with headings and bullet points where appropriate.
- For competitive analysis, deeply analyze local restaurant data provided.
- For a business plan request, produce a comprehensive, step-by-step plan including:
  - Massachusetts regulations (in simple terms)
  - Menu suggestions
  - Local market insights from provided data
  - Step-by-step guide to setting up
- For normal queries, provide detailed and helpful responses.
- If the query is out-of-scope, politely refuse.
- Use tools if needed, never mention them to the user.
- If stuck, finalize with the best info you have.
- Always summarize the answer at put that the end.
"""

llm_for_agent = ChatOpenAI(temperature=0, openai_api_key=OPENAI_API_KEY, max_tokens=3000)

agent = initialize_agent(
    tools=tools,
    llm=llm_for_agent,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=10,
    max_execution_time=120
)

class QNRequest(BaseModel):
    question: str
    restaurants_data: List[Dict[str, Any]] = []
    zip_code: str

@app.post("/qn_agent")
def qn_agent_endpoint(request: QNRequest, current_user: dict = Depends(get_current_user)):
    # Build context
    restaurant_context = "Local Restaurants Data:\n"
    for r in request.restaurants_data[:10]:
        restaurant_context += f"- {r['name']} (Rating: {r.get('rating','N/A')}, Cuisine: {', '.join(r['cuisine_types'])}, Website: {r.get('website','N/A')})\n"
    prompt = f"{GLOBAL_SYSTEM_PROMPT}\n\nZIP Code: {request.zip_code}\n\n{restaurant_context}\nUser Query: {request.question}"

    try:
        response = agent({"input": prompt, "chat_history": []})
        # The response is a dict with 'input', 'chat_history', 'output'
        answer = response.get("output", "No final answer provided.")
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

@app.get("/get_news")
async def root():
    return get_news("Find the latest trends in small business technology.")
