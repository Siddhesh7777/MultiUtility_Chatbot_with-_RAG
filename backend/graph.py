"""
The chatbot "brain", built with LangGraph.

Flow:
    START -> chat_node (LLM)
                |-- needs a tool? -> tools node -> back to chat_node
                '-- no            -> END (final answer)

Chat history is saved in SQLite, keyed by thread_id, so old chats can be reopened.
"""

import sqlite3
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from backend.config import DB_PATH, llm
from backend.tools import tools

llm_with_tools = llm.bind_tools(tools)


# ---------- State: what the graph remembers ----------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # new messages get appended


# ---------- Nodes ----------
def chat_node(state: ChatState, config=None):
    """Ask the LLM to answer, or to request a tool call."""
    thread_id = (config or {}).get("configurable", {}).get("thread_id")

    system_message = SystemMessage(
        content=(
            "You are a helpful assistant. For questions about the uploaded PDF, call "
            f"the `rag_tool` and include the thread_id `{thread_id}`. "
            "You can also use the web search, stock price, and calculator tools "
            "when helpful. If no document is available, ask the user to upload a PDF."
        )
    )

    response = llm_with_tools.invoke(
        [system_message, *state["messages"]], config=config
    )
    return {"messages": [response]}


tool_node = ToolNode(tools)  # runs whichever tool the LLM asked for

# ---------- Memory (chat history) ----------
conn = sqlite3.connect(database=DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# ---------- Build the graph ----------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges(
    "chat_node", tools_condition
)  # tool call? -> "tools", else END
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)


# ---------- Helpers used by the UI ----------
def retrieve_all_threads() -> list:
    """List every thread_id that has saved history."""
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)
