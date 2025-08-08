# main.py - Fixed FastAPI Chatbot (Always Responds)
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

app = FastAPI()

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ==================== Load Data ====================
df = pd.read_csv("data.csv")
df['Query'] = df['Query'].str.strip().str.lower()
df['Response'] = df['Response'].str.strip()

# Load model
print("🧠 Loading Sentence-BERT model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
query_embeddings = model.encode(df['Query'].tolist())
print(f"✅ Encoded {len(query_embeddings)} queries")

# ==================== Fallback Response ====================
def get_neutral_response():
    """Return safest response from dataset"""
    idx = df['compound'].abs().idxmin()
    return df.iloc[idx]['Response']

# ==================== Routes ====================
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(query: str = Form(...)):
    global df, query_embeddings

    # Clean input
    if not query or not query.strip():
        return JSONResponse({'response': get_neutral_response()})

    processed = query.lower().strip()

    try:
        # Encode user input
        user_embedding = model.encode([processed])
        similarities = cosine_similarity(user_embedding, query_embeddings)[0]
        best_idx = np.argmax(similarities)
        max_sim = similarities[best_idx]

        # Confidence threshold
        if max_sim > 0.5:
            # Use existing response
            response = df.iloc[best_idx]['Response']
            return JSONResponse({'response': response})
        else:
            # No good match → ask to teach in frontend
            return JSONResponse({'waiting_for_teaching': True})

    except Exception as e:
        print("Error:", e)
        # Always have a fallback
        return JSONResponse({'response': get_neutral_response()})

@app.post("/teach")
async def teach(query: str = Form(...), response: str = Form(...)):
    global df, query_embeddings

    if not response.strip():
        return JSONResponse({'response': get_neutral_response()})

    # Add new Q&A with default sentiment
    new_entry = {
        'Query': query.strip(),
        'Response': response.strip(),
        'neg': 0.0,
        'neu': 0.8,
        'pos': 0.2,
        'compound': 0.4
    }

    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv("data.csv", index=False)
    query_embeddings = model.encode(df['Query'].tolist())  # re-encode

    return JSONResponse({'response': response})

@app.get("/skip")
async def skip():
    # Return a safe neutral response
    neutral = df['Response'][df['compound'].abs().idxmin()]
    return JSONResponse({'response': neutral})