import streamlit as st
import os
from rag_utils import process_pdf, store_document_embeddings, query_document, get_redis_connection
import tempfile

# Set page config
st.set_page_config(
    page_title="PDF Document Chat",
    page_icon="📚",
    layout="wide"
)

# Initialize session state
if 'current_doc_id' not in st.session_state:
    st.session_state.current_doc_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Title and description
st.title("📚 PDF Document Chat")
st.markdown("""
Upload a PDF document and chat with its contents using AI. The system will process your document 
and allow you to ask questions about its content.
""")

# File upload section
uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])

if uploaded_file is not None:
    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        # Process the PDF
        with st.spinner('Processing your document...'):
            # Extract text and create chunks
            chunks = process_pdf(tmp_path)
            if not chunks:
                st.error("Failed to extract text from the PDF. Please try another file.")
            else:
                # Store in Redis
                redis_client = get_redis_connection()
                doc_id = f"doc_{uploaded_file.name}"
                store_document_embeddings(redis_client, doc_id, chunks)
                st.session_state.current_doc_id = doc_id
                st.success("Document processed successfully! You can now ask questions about it.")
    except Exception as e:
        st.error(f"Error processing document: {str(e)}")
    finally:
        # Clean up temporary file
        os.unlink(tmp_path)

# Chat interface
if st.session_state.current_doc_id:
    st.markdown("---")
    st.subheader("Chat with your Document")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your document..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        try:
            # Get answer from RAG system
            with st.spinner('Thinking...'):
                redis_client = get_redis_connection()
                answer = query_document(redis_client, st.session_state.current_doc_id, prompt)
            
            # Add assistant message to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.write(answer)
        except Exception as e:
            st.error(f"Error processing your question: {str(e)}")
    
    # Add a button to clear chat history
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
else:
    st.info("Please upload a PDF document to start chatting.")

# Add some styling
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .stChatMessage[data-role="user"] {
        background-color: #e3f2fd;
    }
    .stChatMessage[data-role="assistant"] {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True) 