# LangGraph PDF Chatbot

A Streamlit chatbot built with LangGraph and Gemini. It can answer questions about an
uploaded PDF (RAG), search the web, fetch stock prices, and do arithmetic.
Chats are saved in SQLite so you can reopen them later.

## Project structure

```
.
├── app.py              # Streamlit UI (sidebar, chat area, streaming)
├── backend/
│   ├── config.py       # API keys, LLM, embeddings, tuning constants
│   ├── rag.py          # PDF -> chunks -> FAISS index (one per chat thread)
│   ├── tools.py        # calculator, stock price, web search, rag_tool
│   └── graph.py        # LangGraph flow + SQLite chat memory
├── requirements.txt
├── .env.example        # copy to .env and add your keys
└── README.md
```

## How it works

```
Streamlit UI (app.py)
      |
      v
LangGraph (graph.py):  chat_node <----> tools node
      |                    |                |-- rag_tool    -> FAISS (rag.py)
      v                    |                |-- web search
 SQLite history            v                |-- stock price
                       Gemini LLM           '-- calculator
```

1. You type a message in the UI.
2. `chat_node` sends it to Gemini. If Gemini needs a tool, it asks for one.
3. The `tools` node runs the tool and returns the result to `chat_node`.
4. Gemini writes the final answer, which is streamed to the UI.
5. Every step is saved in SQLite under the chat's `thread_id`.

## Run it

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then edit .env with your keys
streamlit run app.py
```

## Common changes

| I want to...                  | Change this                                      |
|-------------------------------|--------------------------------------------------|
| Use a different LLM           | `LLM_MODEL` / `llm` in `backend/config.py`       |
| Add a new tool                | Write a `@tool` in `tools.py`, add to `tools`    |
| Change the assistant's rules  | `SystemMessage` in `chat_node` (`graph.py`)      |
| Tune PDF chunking / retrieval | `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K` in config |
| Change the look of the page   | `app.py`                                         |

## Known limitation

PDF indexes live in memory, so after restarting the app you need to re-upload the PDF
(chat history itself is kept). Saving the FAISS index to disk would fix this.
