"""
Central settings: API keys, the LLM, the embedding model, and tuning constants.
Change the model or chunking behaviour here, nowhere else.
"""
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()  # reads keys from the .env file

# ---- Constants you may want to tweak ----
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DB_PATH = "chatbot.db"          # SQLite file that stores chat history
CHUNK_SIZE = 1000               # characters per PDF chunk
CHUNK_OVERLAP = 200             # overlap between chunks
TOP_K = 4                       # chunks retrieved per question
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

# ---- Shared model objects ----
llm = ChatGoogleGenerativeAI(model=LLM_MODEL)
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
