from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import openai
import os
load_dotenv()
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

openai.api_key = os.getenv("OPENAI_API_KEY")

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


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

index = pc.Index(PINECONE_INDEX_NAME)

app = FastAPI()

class Query(BaseModel):
    question: str

@app.post("/ask")
def ask_question(query: Query):
    try:
        embedding_response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=query.question
        )
        embedding_vector = embedding_response['data'][0]['embedding']

       
        response = index.query(
            vector=embedding_vector,
            top_k=5,  
            include_metadata=True  
        )

       
        matches = response.get('matches', [])
        if not matches:
            raise HTTPException(status_code=404, detail="No relevant data found in the database.")

        contexts = [match['metadata']['content'] for match in matches]
        combined_context = " ".join(contexts) 


        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert in Massachusetts food regulation laws."},
                {"role": "user", "content": f"Answer this question based on the following context: {combined_context}\n\n{query.question}"}
            ]
        )
        
        answer = completion['choices'][0]['message']['content']
        return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))