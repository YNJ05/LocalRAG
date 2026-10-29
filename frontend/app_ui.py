import json
import os
import uuid

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration & Endpoints
# ---------------------------------------------------------------------------
PDF_SERVICE_URL = os.getenv("PDF_SERVICE_URL", "http://localhost:8001").rstrip("/")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8002").rstrip("/")
CHAT_SERVICE_URL = os.getenv("CHAT_SERVICE_URL", "http://localhost:8003").rstrip("/")

st.set_page_config(
    page_title="LocalRAG",
    page_icon="⚪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Apple + Jenkins Inspired Theme (Ubuntu Sans, Black, Blue, White)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Ubuntu+Sans:ital,wght@0,100..800;1,100..800&family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap');

    /* Global Typography & Palette */
    html, body, [class*="css"], .stApp {
        font-family: 'Ubuntu Sans', 'Ubuntu', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #000000 !important;
        color: #f4f4f5 !important;
    }

    /* Streamlit Main Container */
    .stApp > header {
        background: transparent !important;
    }

    /* Apple-style Translucent Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(10, 10, 12, 0.85) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Ubuntu Sans', 'Ubuntu', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #ffffff !important;
    }

    /* Jenkins / Apple Title */
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.03em;
        margin-bottom: 0.15rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }

    .brand-accent {
        color: #0071e3;
    }

    .brand-subtitle {
        font-size: 0.9rem;
        color: #a1a1aa;
        margin-bottom: 1.8rem;
        font-weight: 400;
    }

    .scope-pill {
        display: inline-block;
        background: rgba(0, 113, 227, 0.12);
        color: #0071e3;
        border: 1px solid rgba(0, 113, 227, 0.35);
        padding: 0.15rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Services Status Cards */
    .status-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .status-card {
        background: #09090b;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 0.5rem 0.4rem;
        text-align: center;
        transition: border 0.2s ease;
    }

    .status-card:hover {
        border-color: rgba(0, 113, 227, 0.5);
    }

    .status-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #a1a1aa;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.2rem;
    }

    .status-indicator {
        font-size: 0.78rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }

    .indicator-online {
        color: #0071e3;
    }

    .indicator-offline {
        color: #71717a;
    }

    /* Apple-styled Action Buttons */
    div.stButton > button {
        background-color: #0071e3 !important;
        color: #ffffff !important;
        border: 1px solid #0071e3 !important;
        border-radius: 10px !important;
        font-family: 'Ubuntu Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.45rem 1rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.15s ease-in-out !important;
    }

    div.stButton > button:hover {
        background-color: #0077ed !important;
        border-color: #0077ed !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 113, 227, 0.35) !important;
    }

    div.stButton > button:active {
        transform: translateY(0px) !important;
    }

    /* Secondary / Delete / Muted Buttons */
    div[data-testid="stSidebar"] div.stButton > button {
        border-radius: 8px !important;
    }

    /* Session Code Block */
    .stCodeBlock, div[data-testid="stCode"] {
        background-color: #09090b !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }

    code {
        color: #0071e3 !important;
        font-family: 'Ubuntu Sans', monospace !important;
    }

    /* File Uploader Container */
    div[data-testid="stFileUploader"] {
        background: #09090b !important;
        border: 1px dashed rgba(255, 255, 255, 0.18) !important;
        border-radius: 10px !important;
        padding: 0.8rem !important;
        transition: border-color 0.2s ease !important;
    }

    div[data-testid="stFileUploader"]:hover {
        border-color: #0071e3 !important;
    }

    /* Radio Scope Selection */
    div[data-testid="stRadio"] > div {
        background: #09090b;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 0.5rem;
    }

    /* Chat Messages: Apple Minimalism */
    div[data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 1rem 0 !important;
    }

    /* Assistant Chat Bubble */
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
        background: rgba(18, 18, 22, 0.85) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 1.2rem 1.4rem !important;
        margin-bottom: 0.8rem !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
    }

    /* User Chat Bubble */
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        background: #0071e3 !important;
        color: #ffffff !important;
        border-radius: 14px !important;
        padding: 0.9rem 1.3rem !important;
        margin-bottom: 0.8rem !important;
        box-shadow: 0 4px 16px rgba(0, 113, 227, 0.25) !important;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) p {
        color: #ffffff !important;
        font-weight: 500 !important;
    }

    /* Avatar Icon Styling (Monochrome Black & White) */
    div[data-testid="chatAvatarIcon-assistant"],
    div[data-testid="chatAvatarIcon-user"] {
        background-color: #000000 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }

    /* Expanders & Accordions */
    details {
        background: #09090b !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        padding: 0.5rem !important;
        margin-top: 0.5rem !important;
    }

    summary {
        font-weight: 600 !important;
        color: #0071e3 !important;
        cursor: pointer !important;
    }

    /* Source Citation Card */
    .source-card {
        background: #0c0c0e;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 3px solid #0071e3;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-top: 0.6rem;
        font-size: 0.86rem;
    }

    .source-tag {
        display: inline-block;
        background: #0071e3;
        color: #ffffff;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        margin-right: 0.4rem;
    }

    .source-meta {
        font-weight: 600;
        color: #ffffff;
    }

    .source-text {
        margin-top: 0.4rem;
        color: #a1a1aa;
        line-height: 1.45;
    }

    /* Bottom Chat Input */
    div[data-testid="stChatInput"] {
        background-color: transparent !important;
    }

    div[data-testid="stChatInput"] > div {
        background: rgba(14, 14, 18, 0.8) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.6) !important;
    }

    div[data-testid="stChatInput"] textarea {
        color: #ffffff !important;
        font-family: 'Ubuntu Sans', sans-serif !important;
        font-size: 0.95rem !important;
    }

    div[data-testid="stChatInput"] textarea::placeholder {
        color: #71717a !important;
    }

    div[data-testid="stChatInput"] button {
        background: #0071e3 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: none !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #000000;
    }
    ::-webkit-scrollbar-thumb {
        background: #27272a;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #0071e3;
    }

    /* Divider */
    hr {
        border-color: rgba(255, 255, 255, 0.08) !important;
        margin: 1.2rem 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "session_id" not in st.session_state:
    try:
        res = requests.post(f"{CHAT_SERVICE_URL}/api/v1/session", timeout=3)
        if res.status_code in (200, 201):
            st.session_state["session_id"] = res.json()["session_id"]
        else:
            st.session_state["session_id"] = f"sess_{uuid.uuid4().hex[:12]}"
    except (requests.RequestException, KeyError):
        st.session_state["session_id"] = f"sess_{uuid.uuid4().hex[:12]}"

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "selected_doc_id" not in st.session_state:
    st.session_state["selected_doc_id"] = None


# Health Check Helper
def check_health(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health/live", timeout=1.5)
        return r.status_code == 200
    except requests.RequestException:
        return False


pdf_healthy = check_health(PDF_SERVICE_URL)
rag_healthy = check_health(RAG_SERVICE_URL)
chat_healthy = check_health(CHAT_SERVICE_URL)


# Fetch Documents Helper
def fetch_documents():
    try:
        headers = {"X-Session-Id": st.session_state["session_id"]}
        r = requests.get(f"{PDF_SERVICE_URL}/api/v1/documents", headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json()
    except (requests.RequestException, ValueError):
        return []
    return []


# ---------------------------------------------------------------------------
# Sidebar (Apple Monochrome + Blue Accent)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### SYSTEM STATUS")
    st.markdown(
        f"""
        <div class="status-container">
            <div class="status-card">
                <div class="status-label">PDF</div>
                <div class="status-indicator {'indicator-online' if pdf_healthy else 'indicator-offline'}">
                    {'● ACTIVE' if pdf_healthy else '○ DOWN'}
                </div>
            </div>
            <div class="status-card">
                <div class="status-label">RAG</div>
                <div class="status-indicator {'indicator-online' if rag_healthy else 'indicator-offline'}">
                    {'● ACTIVE' if rag_healthy else '○ DOWN'}
                </div>
            </div>
            <div class="status-card">
                <div class="status-label">CHAT</div>
                <div class="status-indicator {'indicator-online' if chat_healthy else 'indicator-offline'}">
                    {'● ACTIVE' if chat_healthy else '○ DOWN'}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### SESSION IDENTIFIER")
    st.code(st.session_state["session_id"], language="text")

    if st.button("Reset Session", use_container_width=True):
        st.session_state["session_id"] = f"sess_{uuid.uuid4().hex[:12]}"
        st.session_state["messages"] = []
        st.session_state["selected_doc_id"] = None
        st.rerun()

    st.markdown("---")
    st.markdown("### INGEST DOCUMENT")
    uploaded_file = st.file_uploader("Upload PDF file", type=["pdf"], key="pdf_uploader", label_visibility="collapsed")

    if uploaded_file is not None and st.button("Process & Index Document", use_container_width=True):
        with st.spinner("Extracting text and generating embeddings..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                headers = {"X-Session-Id": st.session_state["session_id"]}
                res = requests.post(f"{PDF_SERVICE_URL}/api/v1/documents", files=files, headers=headers, timeout=120)
                if res.status_code in (200, 201):
                    data = res.json()
                    st.success(f"Indexed: {data['filename']} ({data['page_count']} p, {data['chunk_count']} chunks)")
                    st.rerun()
                else:
                    st.error(f"Upload failed: {res.text}")
            except requests.RequestException as e:
                st.error(f"PDF service communication error: {e}")

    documents = fetch_documents()
    st.markdown("---")
    st.markdown(f"### KNOWLEDGE BASE ({len(documents)})")

    if documents:
        doc_options = {"All Documents": None}
        for d in documents:
            label = f"{d['filename']} ({d['chunk_count']} chunks)"
            doc_options[label] = d["id"]

        selected_label = st.radio(
            "Query Filter:",
            list(doc_options.keys()),
            index=0,
            key="doc_scope_select",
            label_visibility="collapsed",
        )
        st.session_state["selected_doc_id"] = doc_options[selected_label]

        with st.expander("Document Library"):
            for d in documents:
                col_name, col_del = st.columns([4, 1])
                with col_name:
                    st.caption(f"{d['filename']}")
                with col_del:
                    if st.button("✕", key=f"del_{d['id']}"):
                        headers = {"X-Session-Id": st.session_state["session_id"]}
                        requests.delete(f"{PDF_SERVICE_URL}/api/v1/documents/{d['id']}", headers=headers)
                        st.rerun()
    else:
        st.caption("No documents in session. Upload a PDF above.")

    st.markdown("---")
    st.caption("MODELS: `nomic-embed-text:latest` / `qwen2.5:0.5b`")


# ---------------------------------------------------------------------------
# Main View (Apple Minimalist + Jenkins Blue Accent)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="brand-title">
        <span>LocalRAG</span><span class="brand-accent">•</span><span>Microservices</span>
    </div>
    """,
    unsafe_allow_html=True,
)

active_scope = "All Documents"
if st.session_state["selected_doc_id"]:
    matched = [d["filename"] for d in documents if d["id"] == st.session_state["selected_doc_id"]]
    if matched:
        active_scope = matched[0]

st.markdown(
    f"""
    <div class="brand-subtitle">
        Private local intelligence <span style="margin: 0 0.4rem;">|</span>
        Scope: <span class="scope-pill">{active_scope}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Render Chat History
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Referenced Sources"):
                for s in msg["sources"]:
                    st.markdown(
                        f"""
                        <div class="source-card">
                            <span class="source-tag">[{s.get('source_id', 'Ref')}]</span>
                            <span class="source-meta">{s.get('filename', 'Unknown')} (Page {s.get('page_number', 1)}) — Score: {s.get('score', 0)}</span>
                            <div class="source-text">{s.get('excerpt', '')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

# Chat Input & Streaming
if prompt := st.chat_input("Enter your question regarding the uploaded documents..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        captured_sources = []

        headers = {
            "Content-Type": "application/json",
            "X-Session-Id": st.session_state["session_id"],
        }
        body = {
            "question": prompt,
            "document_id": st.session_state["selected_doc_id"],
            "stream": True,
        }

        try:
            with requests.post(
                f"{CHAT_SERVICE_URL}/api/v1/chat",
                headers=headers,
                json=body,
                stream=True,
                timeout=120,
            ) as response:
                if response.status_code == 200:
                    current_event = ""
                    for line in response.iter_lines():
                        if not line:
                            continue
                        decoded_line = line.decode("utf-8")
                        if decoded_line.startswith("event: "):
                            current_event = decoded_line.replace("event: ", "").strip()
                        elif decoded_line.startswith("data: "):
                            data_content = decoded_line.replace("data: ", "", 1)
                            if current_event == "sources":
                                try:
                                    captured_sources = json.loads(data_content)
                                except (json.JSONDecodeError, ValueError):
                                    captured_sources = []
                            elif current_event == "token":
                                full_response += data_content
                                message_placeholder.markdown(full_response + "▌")
                            elif current_event == "error":
                                full_response += f"\n\n*(Error: {data_content})*"
                                message_placeholder.markdown(full_response)
                            elif current_event == "done":
                                message_placeholder.markdown(full_response)
                                break
                    message_placeholder.markdown(full_response)
                else:
                    full_response = f"Chat service error ({response.status_code}): {response.text}"
                    message_placeholder.markdown(full_response)

        except requests.exceptions.RequestException as e:
            full_response = f"Could not connect to Chat Microservice: {e}"
            message_placeholder.markdown(full_response)

        if captured_sources:
            with st.expander("Referenced Sources"):
                for s in captured_sources:
                    st.markdown(
                        f"""
                        <div class="source-card">
                            <span class="source-tag">[{s.get('source_id', 'Ref')}]</span>
                            <span class="source-meta">{s.get('filename', 'Unknown')} (Page {s.get('page_number', 1)}) — Score: {s.get('score', 0)}</span>
                            <div class="source-text">{s.get('excerpt', '')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": full_response,
                "sources": captured_sources,
            }
        )
