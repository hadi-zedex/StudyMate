import os
import streamlit as st
import requests

# Works locally (env var) and on Streamlit Cloud (st.secrets)
try:
    API = st.secrets["STUDYMATE_API_URL"]
except (KeyError, FileNotFoundError):
    API = os.getenv("STUDYMATE_API_URL", "http://localhost:8000")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyMate",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal style tweaks ───────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide top header, fork button, and toolbar */
    header[data-testid="stHeader"], #MainMenu, .stAppDeployButton {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Hide bottom Streamlit Cloud 'Hosted with Streamlit' & 'Created by' badges */
    footer,
    [data-testid="stStatusWidget"],
    div[class*="viewerBadge"],
    div[class*="manageApp"],
    div[class*="Profile"],
    div[class*="styles_viewerBadge"] {
        display: none !important;
        visibility: hidden !important;
    }

    [data-testid="stSidebar"] { background-color: #171717; }
    .stChatMessage { background: transparent !important; }
    div[data-testid="stFileUploader"] label { color: #8e8ea0; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "username" not in st.session_state:
    st.session_state.username = None
if "subject" not in st.session_state:
    st.session_state.subject = None
if "messages" not in st.session_state:
    st.session_state.messages = {}   # {subject: [{role, content}]}

# ── Helpers ────────────────────────────────────────────────────────────────────
def get_subjects(username: str):
    """Return only subjects belonging to this user (prefixed with username__)."""
    try:
        all_subjects = requests.get(f"{API}/api/subjects").json().get("subjects", [])
        prefix = f"{username}__"
        return [s[len(prefix):] for s in all_subjects if s.startswith(prefix)]
    except Exception:
        st.error("❌ Cannot connect to backend API.")
        return []

def full_subject_name(username: str, subject: str) -> str:
    """Qdrant collection name = username__subject"""
    return f"{username}__{subject}"

def create_subject(username: str, name: str):
    full = full_subject_name(username, name)
    r = requests.post(f"{API}/api/subjects", json={"name": full})
    return r.ok

def upload_pdf(subject: str, file_bytes: bytes, filename: str):
    r = requests.post(
        f"{API}/api/subjects/{subject}/upload",
        files={"file": (filename, file_bytes, "application/pdf")},
        timeout=120,
    )
    if r.ok:
        return r.json()
    st.error(f"Upload error ({r.status_code}): {r.text[:300]}")
    return None

def query_subject(subject: str, question: str):
    r = requests.post(
        f"{API}/api/subjects/{subject}/query",
        json={"question": question, "top_k": 5},
        timeout=60,
    )
    return r.json() if r.ok else None

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# StudyMate")
    st.markdown("*AI learning assistant*")
    st.divider()

    # Username prompt — gates everything else
    if not st.session_state.username:
        uname = st.text_input("Enter your name to get started", key="uname_input")
        if st.button("Start", key="uname_btn"):
            slug = uname.strip().lower().replace(" ", "-")
            if slug:
                st.session_state.username = slug
                st.rerun()
        st.stop()

    username = st.session_state.username
    st.caption(f"👤 Logged in as **{username}**")
    if st.button("Switch user", key="switch_btn"):
        st.session_state.username = None
        st.session_state.subject = None
        st.rerun()
    st.divider()

    # Create new subject
    with st.expander("➕ New Subject"):
        new_name = st.text_input("Subject name", placeholder="e.g. Maths", key="new_subj_input")
        if st.button("Create", key="create_btn"):
            slug = new_name.strip().lower().replace(" ", "-")
            if slug:
                if create_subject(username, slug):
                    st.success(f"✅ Created **{slug}**")
                    st.session_state.subject = full_subject_name(username, slug)
                    st.rerun()
                else:
                    st.error("Failed to create subject")

    st.divider()

    # Subject list — only user's own subjects
    subjects = get_subjects(username)
    if subjects:
        st.markdown("**Your Subjects**")
        for s in subjects:
            full = full_subject_name(username, s)
            is_active = full == st.session_state.subject
            label = f"📗 **{s}**" if is_active else f"📗 {s}"
            if st.button(label, key=f"subj_{s}", use_container_width=True):
                st.session_state.subject = full
                st.rerun()
    else:
        st.caption("No subjects yet. Create one above.")

    st.divider()

    # PDF upload (only when subject is selected)
    if st.session_state.subject:
        # Show short display name (strip username__ prefix)
        display_subj = st.session_state.subject.split("__", 1)[-1]
        st.markdown(f"**Upload to:** `{display_subj}`")
        uploaded = st.file_uploader("Choose a PDF", type=["pdf"], key="pdf_uploader")
        if uploaded:
            with st.spinner(f"Ingesting {uploaded.name}…"):
                result = upload_pdf(
                    st.session_state.subject,
                    uploaded.getvalue(),
                    uploaded.name
                )
            if result:
                st.success(f"✅ {result['ingested']} chunks ingested!")
                # Add a system message to chat
                subj = st.session_state.subject
                if subj not in st.session_state.messages:
                    st.session_state.messages[subj] = []
                st.session_state.messages[subj].append({
                    "role": "assistant",
                    "content": f"📄 Ingested **{uploaded.name}** — {result['ingested']} chunks added. You can now ask questions about this material!"
                })
                st.rerun()
            else:
                st.error("Upload failed. Please try again.")
    else:
        st.caption("Select a subject to upload materials.")

# ── Main chat area ─────────────────────────────────────────────────────────────
subject = st.session_state.subject

if not subject:
    # Welcome screen
    st.markdown("## Welcome to StudyMate, what do you want to learn today?")
    st.markdown("""
    Your AI learning assistant that answers questions **based on your class materials**.
    
    **Get started:**
    1. Click **➕ New Subject** in the sidebar (e.g. `operating-systems`)
    2. Upload your lecture slides, textbook chapters, or notes as **PDF**
    3. Ask any question and start learning with answers based on the study materials
    """)
else:
    display_name = subject.split("__", 1)[-1]
    st.markdown(f"##  {display_name}")

    # Init message history for this subject
    if subject not in st.session_state.messages:
        st.session_state.messages[subject] = [
            {"role": "assistant", "content": f"Hi! I'm your study assistant for **{display_name}**. Upload your class materials using the sidebar, then ask me anything!"}
        ]

    # Render chat history
    for msg in st.session_state.messages[subject]:
        with st.chat_message(msg["role"], avatar="📚" if msg["role"] == "assistant" else "🧑‍🎓"):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input(f"Ask a question about {subject}…"):
        # Show user message
        st.session_state.messages[subject].append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(prompt)

        # Get answer
        with st.chat_message("assistant", avatar="📚"):
            with st.spinner("Thinking…"):
                result = query_subject(subject, prompt)

            if result:
                answer = result["answer"]
                sources = result.get("sources", [])
                st.markdown(answer)
                if sources:
                    filenames = [s.replace("\\", "/").split("/")[-1] for s in sources]
                    st.caption(f"📄 Sources: {', '.join(filenames)}")
                st.session_state.messages[subject].append({
                    "role": "assistant",
                    "content": answer
                })
            else:
                err = "Sorry, something went wrong. Please check that FastAPI is running."
                st.error(err)
                st.session_state.messages[subject].append({"role": "assistant", "content": err})
