# """
# Streamlit UI for the LangGraph PDF chatbot.

# Run with:  streamlit run app.py

# The page is built from four small functions at the bottom of this file:
#     render_sidebar() -> render_chat_history() -> handle_user_input() -> load_selected_thread()
# """

# import uuid

# import streamlit as st
# from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# from backend.graph import chatbot, retrieve_all_threads
# from backend.rag import get_document_metadata, ingest_pdf


# # =========================== Helpers ===========================
# def new_thread_id():
#     return uuid.uuid4()


# def extract_text(content) -> str:
#     """Gemini returns a string OR a list of blocks; always give back plain text."""
#     if isinstance(content, str):
#         return content
#     if isinstance(content, list):
#         parts = []
#         for block in content:
#             if isinstance(block, str):
#                 parts.append(block)
#             elif isinstance(block, dict) and block.get("type") == "text":
#                 parts.append(block.get("text", ""))
#         return "".join(parts)
#     return ""


# def add_thread(thread_id):
#     if thread_id not in st.session_state["chat_threads"]:
#         st.session_state["chat_threads"].append(thread_id)


# def start_new_chat():
#     thread_id = new_thread_id()
#     st.session_state["thread_id"] = thread_id
#     add_thread(thread_id)
#     st.session_state["message_history"] = []


# def load_conversation(thread_id) -> list:
#     """Fetch saved messages of a thread from the database."""
#     state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
#     return state.values.get("messages", [])


# # ===================== Session state setup =====================
# def init_session_state():
#     """st.session_state survives reruns; create defaults once."""
#     st.session_state.setdefault("message_history", [])  # messages shown on screen
#     st.session_state.setdefault("thread_id", new_thread_id())  # current chat id
#     st.session_state.setdefault("ingested_docs", {})  # thread -> uploaded PDFs
#     if "chat_threads" not in st.session_state:
#         st.session_state["chat_threads"] = retrieve_all_threads()
#     add_thread(st.session_state["thread_id"])


# # =========================== Sidebar ===========================
# def render_sidebar(thread_key: str):
#     """Draw the sidebar. Returns a thread id if the user clicked a past chat."""
#     thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
#     selected_thread = None

#     st.sidebar.title("LangGraph PDF Chatbot")
#     st.sidebar.markdown(f"**Thread ID:** `{thread_key}`")

#     if st.sidebar.button("New Chat", use_container_width=True):
#         start_new_chat()
#         st.rerun()

#     # Status of the PDF attached to this chat
#     if thread_docs:
#         latest = list(thread_docs.values())[-1]
#         st.sidebar.success(
#             f"Using `{latest.get('filename')}` "
#             f"({latest.get('chunks')} chunks from {latest.get('documents')} pages)"
#         )
#     else:
#         st.sidebar.info("No PDF indexed yet.")

#     # PDF upload
#     uploaded_pdf = st.sidebar.file_uploader("Upload a PDF for this chat", type=["pdf"])
#     if uploaded_pdf:
#         if uploaded_pdf.name in thread_docs:
#             st.sidebar.info(f"`{uploaded_pdf.name}` already processed for this chat.")
#         else:
#             with st.sidebar.status("Indexing PDF…", expanded=True) as status_box:
#                 summary = ingest_pdf(
#                     uploaded_pdf.getvalue(),
#                     thread_id=thread_key,
#                     filename=uploaded_pdf.name,
#                 )
#                 thread_docs[uploaded_pdf.name] = summary
#                 status_box.update(
#                     label="✅ PDF indexed", state="complete", expanded=False
#                 )

#     # Past conversations (newest first)
#     st.sidebar.subheader("Past conversations")
#     past_threads = st.session_state["chat_threads"][::-1]
#     if not past_threads:
#         st.sidebar.write("No past conversations yet.")
#     for thread_id in past_threads:
#         if st.sidebar.button(str(thread_id), key=f"side-thread-{thread_id}"):
#             selected_thread = thread_id

#     return selected_thread


# # ========================== Chat area ==========================
# def render_chat_history():
#     for message in st.session_state["message_history"]:
#         with st.chat_message(message["role"]):
#             st.markdown(message["content"])


# def handle_user_input(thread_key: str):
#     user_input = st.chat_input("Ask about your document or use tools")
#     if not user_input:
#         return

#     # 1) Show and store the user's message
#     st.session_state["message_history"].append({"role": "user", "content": user_input})
#     with st.chat_message("user"):
#         st.markdown(user_input)

#     config = {
#         "configurable": {"thread_id": thread_key},
#         "metadata": {"thread_id": thread_key},
#         "run_name": "chat_turn",
#     }

#     # 2) Stream the assistant's reply
#     with st.chat_message("assistant"):
#         tool_status = {"box": None}  # shows "Using <tool>..." while a tool runs

#         def stream_ai_reply():
#             for chunk, _ in chatbot.stream(
#                 {"messages": [HumanMessage(content=user_input)]},
#                 config=config,
#                 stream_mode="messages",
#             ):
#                 if isinstance(chunk, ToolMessage):
#                     label = f"🔧 Using `{getattr(chunk, 'name', 'tool')}` …"
#                     if tool_status["box"] is None:
#                         tool_status["box"] = st.status(label, expanded=True)
#                     else:
#                         tool_status["box"].update(
#                             label=label, state="running", expanded=True
#                         )

#                 if isinstance(chunk, AIMessage):
#                     text = extract_text(chunk.content)
#                     if text:
#                         yield text

#         ai_message = st.write_stream(stream_ai_reply())

#         if tool_status["box"] is not None:
#             tool_status["box"].update(
#                 label="✅ Tool finished", state="complete", expanded=False
#             )

#     # 3) Store the assistant's reply
#     st.session_state["message_history"].append(
#         {"role": "assistant", "content": ai_message}
#     )

#     doc_meta = get_document_metadata(thread_key)
#     if doc_meta:
#         st.caption(
#             f"Document indexed: {doc_meta.get('filename')} "
#             f"(chunks: {doc_meta.get('chunks')}, pages: {doc_meta.get('documents')})"
#         )


# def load_selected_thread(selected_thread):
#     """Switch to a past chat and rebuild its messages on screen."""
#     st.session_state["thread_id"] = selected_thread

#     history = []
#     for msg in load_conversation(selected_thread):
#         if isinstance(msg, ToolMessage):
#             continue  # hide raw tool output
#         text = extract_text(msg.content)
#         if not text:
#             continue  # hide AI messages that only contain tool calls
#         role = "user" if isinstance(msg, HumanMessage) else "assistant"
#         history.append({"role": role, "content": text})

#     st.session_state["message_history"] = history
#     st.session_state["ingested_docs"].setdefault(str(selected_thread), {})
#     st.rerun()


# # ============================ Page ============================
# init_session_state()
# thread_key = str(st.session_state["thread_id"])

# selected_thread = render_sidebar(thread_key)

# st.title("Multi Utility Chatbot")
# render_chat_history()
# handle_user_input(thread_key)
# st.divider()

# if selected_thread:
#     load_selected_thread(selected_thread)
"""
Streamlit UI for the LangGraph PDF chatbot.

Run with:  streamlit run app.py

The page is built from four small functions at the bottom of this file:
    render_sidebar() -> render_chat_history() -> handle_user_input() -> load_selected_thread()
"""

import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.graph import chatbot, retrieve_all_threads
from backend.rag import get_document_metadata, ingest_pdf

# ======================= Page look & feel =======================
st.set_page_config(
    page_title="Multi Utility Chatbot", page_icon="🤖", layout="centered"
)

USER_AVATAR = "🧑"
BOT_AVATAR = "🤖"

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem;}
    [data-testid="stChatMessage"] {border-radius: 14px; padding: 0.75rem 1rem;}
    [data-testid="stSidebar"] .stButton button {text-align: left; border-radius: 10px;}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================== Helpers ===========================
def new_thread_id():
    return uuid.uuid4()


def extract_text(content) -> str:
    """Gemini returns a string OR a list of blocks; always give back plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)


def start_new_chat():
    thread_id = new_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id)
    st.session_state["message_history"] = []


def load_conversation(thread_id) -> list:
    """Fetch saved messages of a thread from the database."""
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    return state.values.get("messages", [])


def thread_label(thread_id) -> str:
    """Short label for a past chat: the first 30 characters of your first message."""
    for msg in load_conversation(thread_id):
        if isinstance(msg, HumanMessage):
            text = extract_text(msg.content).strip().replace("\n", " ")
            return text[:30] + ("…" if len(text) > 30 else "")
    return "New chat"


# ===================== Session state setup =====================
def init_session_state():
    """st.session_state survives reruns; create defaults once."""
    st.session_state.setdefault("message_history", [])  # messages shown on screen
    st.session_state.setdefault("thread_id", new_thread_id())  # current chat id
    st.session_state.setdefault("ingested_docs", {})  # thread -> uploaded PDFs
    if "chat_threads" not in st.session_state:
        st.session_state["chat_threads"] = retrieve_all_threads()
    add_thread(st.session_state["thread_id"])


# =========================== Sidebar ===========================
def render_sidebar(thread_key: str):
    """Draw the sidebar. Returns a thread id if the user clicked a past chat."""
    thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
    selected_thread = None

    st.sidebar.title("🤖 PDF Chatbot")
    st.sidebar.caption(f"Chat ID: {thread_key[:8]}")

    if st.sidebar.button("New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    # Status of the PDF attached to this chat
    if thread_docs:
        latest = list(thread_docs.values())[-1]
        st.sidebar.success(
            f"Using `{latest.get('filename')}` "
            f"({latest.get('chunks')} chunks from {latest.get('documents')} pages)"
        )
    else:
        st.sidebar.info("No PDF indexed yet.")

    # PDF upload
    uploaded_pdf = st.sidebar.file_uploader("Upload a PDF for this chat", type=["pdf"])
    if uploaded_pdf:
        if uploaded_pdf.name in thread_docs:
            st.sidebar.info(f"`{uploaded_pdf.name}` already processed for this chat.")
        else:
            with st.sidebar.status("Indexing PDF…", expanded=True) as status_box:
                summary = ingest_pdf(
                    uploaded_pdf.getvalue(),
                    thread_id=thread_key,
                    filename=uploaded_pdf.name,
                )
                thread_docs[uploaded_pdf.name] = summary
                status_box.update(
                    label="✅ PDF indexed", state="complete", expanded=False
                )

    # Past conversations (newest first)
    st.sidebar.subheader("Past conversations")
    past_threads = st.session_state["chat_threads"][::-1]
    if not past_threads:
        st.sidebar.write("No past conversations yet.")
    for thread_id in past_threads[:15]:  # show the 15 most recent chats
        is_current = str(thread_id) == thread_key
        if st.sidebar.button(
            thread_label(thread_id),
            key=f"side-thread-{thread_id}",
            use_container_width=True,
            type="primary" if is_current else "secondary",
        ):
            selected_thread = thread_id

    return selected_thread


# ========================== Chat area ==========================
def render_chat_history():
    if not st.session_state["message_history"]:
        st.markdown("#### 👋 Hi! What can I help you with?")
        st.caption(
            "Upload a PDF in the sidebar and ask about it, search the web, "
            "check a stock price, or do a quick calculation."
        )
    for message in st.session_state["message_history"]:
        avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])


def handle_user_input(thread_key: str):
    user_input = st.chat_input("Ask about your document or use tools")
    if not user_input:
        return

    # 1) Show and store the user's message
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_input)

    config = {
        "configurable": {"thread_id": thread_key},
        "metadata": {"thread_id": thread_key},
        "run_name": "chat_turn",
    }

    # 2) Stream the assistant's reply
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        tool_status = {"box": None}  # shows "Using <tool>..." while a tool runs

        def stream_ai_reply():
            for chunk, _ in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
                stream_mode="messages",
            ):
                if isinstance(chunk, ToolMessage):
                    label = f"🔧 Using `{getattr(chunk, 'name', 'tool')}` …"
                    if tool_status["box"] is None:
                        tool_status["box"] = st.status(label, expanded=True)
                    else:
                        tool_status["box"].update(
                            label=label, state="running", expanded=True
                        )

                if isinstance(chunk, AIMessage):
                    text = extract_text(chunk.content)
                    if text:
                        yield text

        ai_message = st.write_stream(stream_ai_reply())

        if tool_status["box"] is not None:
            tool_status["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )

    # 3) Store the assistant's reply
    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )

    doc_meta = get_document_metadata(thread_key)
    if doc_meta:
        st.caption(
            f"Document indexed: {doc_meta.get('filename')} "
            f"(chunks: {doc_meta.get('chunks')}, pages: {doc_meta.get('documents')})"
        )


def load_selected_thread(selected_thread):
    """Switch to a past chat and rebuild its messages on screen."""
    st.session_state["thread_id"] = selected_thread

    history = []
    for msg in load_conversation(selected_thread):
        if isinstance(msg, ToolMessage):
            continue  # hide raw tool output
        text = extract_text(msg.content)
        if not text:
            continue  # hide AI messages that only contain tool calls
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        history.append({"role": role, "content": text})

    st.session_state["message_history"] = history
    st.session_state["ingested_docs"].setdefault(str(selected_thread), {})
    st.rerun()


# ============================ Page ============================
init_session_state()
thread_key = str(st.session_state["thread_id"])

selected_thread = render_sidebar(thread_key)

st.title("🤖 Multi Utility Chatbot")
render_chat_history()
handle_user_input(thread_key)
st.divider()

if selected_thread:
    load_selected_thread(selected_thread)
