"""
Tools the chatbot can call. The LLM decides when to use them based on each
function's docstring, so keep docstrings clear.

To add a new tool: write a @tool function and add it to the `tools` list.
"""
from typing import Optional

import requests
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

from backend.config import ALPHAVANTAGE_API_KEY
from backend.rag import get_retriever, get_source_filename

# Web search (ready-made tool)
search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage.
    """
    if not ALPHAVANTAGE_API_KEY:
        return {"error": "ALPHAVANTAGE_API_KEY is not set in the .env file"}

    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHAVANTAGE_API_KEY,
        },
        timeout=15,
    )
    return response.json()


@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.
    Always include the thread_id when calling this tool.
    """
    retriever = get_retriever(thread_id)
    if retriever is None:
        return {
            "error": "No document indexed for this chat. Upload a PDF first.",
            "query": query,
        }

    results = retriever.invoke(query)
    return {
        "query": query,
        "context": [doc.page_content for doc in results],
        "metadata": [doc.metadata for doc in results],
        "source_file": get_source_filename(thread_id),
    }


# Every tool the LLM is allowed to use
tools = [search_tool, get_stock_price, calculator, rag_tool]
