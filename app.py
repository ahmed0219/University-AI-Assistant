"""
University AI Administrative Assistant
Main Streamlit Application - Q&A System
"""
import streamlit as st
import uuid

# Import components
from agents.orchestrator import create_orchestrator
from database.operations import get_db_operations
from database.faq_cache import get_faq_cache

# Initialize database
db_ops = get_db_operations()

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="University AI Assistant",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ========== SESSION STATE ==========
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "user" not in st.session_state:
    st.session_state.user = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None

# ========== AUTH FUNCTIONS ==========
def login(username: str, password: str) -> bool:
    user = db_ops.authenticate_user(username, password)
    if user:
        st.session_state.user = user
        st.session_state.orchestrator = create_orchestrator(
            session_id=st.session_state.session_id,
            user_id=username
        )
        return True
    return False

def register(username: str, password: str) -> bool:
    return db_ops.create_user(username, password, role="student")

def logout():
    st.session_state.user = None
    st.session_state.orchestrator = None
    st.session_state.chat_history = []
    st.session_state.session_id = str(uuid.uuid4())

# ========== AUTH UI ==========
if not st.session_state.user:
    st.title("🎓 University AI Assistant")
    st.markdown("Your intelligent guide to university information and policies!")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if login(username, password):
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Choose Username", key="reg_user")
            new_password = st.text_input("Choose Password", type="password", key="reg_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            submitted = st.form_submit_button("Create Account")
            
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 4:
                    st.error("Password must be at least 4 characters")
                elif register(new_username, new_password):
                    st.success("Account created! Please login.")
                else:
                    st.error("Username already exists")
    
    st.stop()

# ========== MAIN APP (LOGGED IN) ==========

# Sidebar
with st.sidebar:
    st.markdown(f"### 👋 Hello, {st.session_state.user['username']}!")
    st.caption(f"Role: {st.session_state.user['role'].title()}")
    
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
    
    st.divider()
    
    st.markdown("### 🔗 Quick Links")
    st.page_link("pages/4_email_generator.py", label="📧 Générateur d'Emails")
    
    st.divider()
    
    st.markdown("### ℹ️ About")
    st.caption("Ask questions about university policies, procedures, admissions, courses, and more. I'll find answers from official documents.")

# Main Title
st.title("🎓 University AI Assistant")
st.markdown("Ask me anything about university policies, procedures, courses, and more!")

# FAQ Cache for common questions
faq_cache = get_faq_cache()

# Display chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("sources"):
            with st.expander("📚 Sources"):
                for source in msg["sources"]:
                    st.caption(f"• {source.get('file', 'Unknown')}")

# Chat input
user_question = st.chat_input("Type your question here...")

if user_question:
    # Display user message
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.write(user_question)
    
    # Check cache first
    cached_response = faq_cache.get(user_question)
    
    if cached_response:
        response_text = cached_response
        sources = []
    else:
        # Get orchestrator response
        with st.spinner("Searching university documents..."):
            orchestrator = st.session_state.orchestrator
            if orchestrator is None:
                orchestrator = create_orchestrator(
                    session_id=st.session_state.session_id,
                    user_id=st.session_state.user['username']
                )
                st.session_state.orchestrator = orchestrator
            
            result = orchestrator.process_query(user_question)
            response_text = result.get("answer", "I couldn't find information about that.")
            sources = result.get("sources", [])
            
            # Cache the response
            faq_cache.set(user_question, response_text)
    
    # Display assistant response
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": response_text,
        "sources": sources
    })
    with st.chat_message("assistant"):
        st.write(response_text)
        if sources:
            with st.expander("📚 Sources"):
                for source in sources:
                    st.caption(f"• {source.get('file', 'Unknown')}")
    
    st.rerun()

# Clear chat button
if st.session_state.chat_history:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

# Footer
st.markdown("---")
st.caption("🎓 University AI Assistant | Powered by Gemini & RAG")
