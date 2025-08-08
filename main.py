# main.py
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

app = FastAPI()

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load your data
try:
    df = pd.read_csv("data.csv")
    print("✅ Loaded data.csv successfully")
except FileNotFoundError:
    raise FileNotFoundError("data.csv not found! Please place it in the project root.")

# Clean text
df['Query'] = df['Query'].str.strip().str.lower()
df['Response'] = df['Response'].str.strip()

# Load model and encode queries
print("🧠 Loading SentenceTransformer model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
query_embeddings = model.encode(df['Query'].tolist())
print(f"✅ Encoded {len(query_embeddings)} query embeddings")

# Offensive patterns
offensive_patterns = [
    r'\b(fuck|shit|damn|bitch|asshole|idiot|stupid|fool|dumb|cunt|nigger|retard|bastard|whore)\w*\b',
    r'\b(hate|kill|die|fag|slut)\b'
]

def is_offensive(text):
    return any(re.search(pattern, text.lower()) for pattern in offensive_patterns)

def get_fallback_response():
    return df.iloc[df['compound'].abs().idxmin()]['Response']

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(query: str = Form(...)):
    global df, query_embeddings

    user_query = query.strip()
    if not user_query:
        return JSONResponse({'response': get_fallback_response()})

    processed = user_query.lower()

    # Block offensive input
    if is_offensive(processed):
        return JSONResponse({'response': "I can't respond to that."})

    try:
        user_embed = model.encode([processed])
        sims = cosine_similarity(user_embed, query_embeddings)[0]
        best_idx = np.argmax(sims)
        best_score = sims[best_idx]

        if best_score > 0.5:
            bot_response = df.iloc[best_idx]['Response']
        else:
            bot_response = "I'm not sure about that. Can you ask differently?"

        return JSONResponse({'response': bot_response, 'score': float(best_score)})

    except Exception as e:
        print("Error:", e)
        return JSONResponse({'response': "Oops! Something went wrong."})

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Chatbot App at http://127.0.0.1:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)