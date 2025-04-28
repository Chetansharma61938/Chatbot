import os
import logging
import re
import io
import redis
from typing import List, Dict, Any, Union
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Redis as RedisVectorStore
from langchain_groq import ChatGroq
from langchain_community.embeddings.fake import FakeEmbeddings
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate

# Handle different LangChain versions
try:
    # For newer versions of LangChain
    from langchain.chains.combine_documents import create_stuff_documents_chain
except ImportError:
    # For older versions of LangChain
    try:
        from langchain.chains import create_stuff_documents_chain
    except ImportError:
        # If still not found, implement our own version
        def create_stuff_documents_chain(llm, prompt):
            def chain(inputs):
                # Get the context and question from the inputs
                context = inputs.get("context", [])
                question = inputs.get("question", "")
                
                # Join the document texts with newlines
                context_text = "\n\n".join([doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in context])
                
                # Format the prompt template
                formatted_prompt = prompt.format(context=context_text, question=question)
                
                # Call the LLM
                response = llm.invoke(formatted_prompt)
                
                # Return the response
                return response
                
            return chain

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
# Use local Redis as default
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
EMBEDDINGS_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"

# Initialize embedding model
def get_embeddings_model():
    """Get the embeddings model"""
    try:
        # Using FakeEmbeddings as a fallback since sentence-transformers is not available
        # In production, this should be replaced with proper embeddings
        return FakeEmbeddings(size=1536)  # Using 1536 dimensions which is common
    except Exception as e:
        logger.error(f"Error initializing embeddings model: {e}")
        raise

# Initialize LLM
def get_llm():
    """Get the Groq LLM model"""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set. Please set it in your .env file.")
    
    try:
        return ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name=LLM_MODEL
        )
    except Exception as e:
        logger.error(f"Error initializing Groq LLM: {e}")
        raise

# Redis connection
def get_redis_connection():
    """Get Redis connection"""
    try:
        return redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            decode_responses=False  # Keep binary data as is
        )
    except Exception as e:
        logger.error(f"Error connecting to Redis: {e}")
        raise

# Process PDF and extract text
def process_pdf(file_path: str) -> List[str]:
    """
    Extract text from PDF and split into chunks
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        List of text chunks
    """
    try:
        # Extract text from PDF
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            logger.warning(f"No text extracted from {file_path}")
            return []
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )
        
        chunks = text_splitter.split_text(text)
        logger.info(f"Extracted {len(chunks)} chunks from PDF")
        
        return chunks
    
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return []

# Store document embeddings in Redis
def store_document_embeddings(redis_client, doc_id: str, chunks: List[str]) -> bool:
    """
    Generate embeddings for document chunks and store in Redis
    
    Args:
        redis_client: Redis client
        doc_id: Document ID
        chunks: List of text chunks
        
    Returns:
        Success status
    """
    try:
        embeddings = get_embeddings_model()
        
        # Create a vector store with the chunks
        vector_store = RedisVectorStore.from_texts(
            texts=chunks,
            embedding=embeddings,
            redis_url=f"redis://{':' + REDIS_PASSWORD + '@' if REDIS_PASSWORD else ''}{REDIS_HOST}:{REDIS_PORT}",
            index_name=doc_id
        )
        
        logger.info(f"Stored {len(chunks)} chunks with embeddings for document {doc_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error storing document embeddings: {e}")
        return False

# Query document using RAG
def query_document(redis_client, doc_id: str, query: str) -> str:
    """
    Query the document using RAG
    """
    try:
        # Initialize models
        embeddings = get_embeddings_model()
        llm = get_llm()
        
        # Create vector store
        vector_store = RedisVectorStore(
            redis_url=f"redis://{':' + REDIS_PASSWORD + '@' if REDIS_PASSWORD else ''}{REDIS_HOST}:{REDIS_PORT}",
            index_name=doc_id,
            embedding=embeddings
        )
        
        # Create retriever
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}  # Retrieve top 5 most relevant chunks
        )
        
        # Create more flexible prompt
        prompt_template = """You are a helpful assistant that answers questions based on the provided document sections and related information.

Context information is below.
---------------------
{context}
---------------------

Given the context information, provide a helpful and informative answer to the query. 
If the exact answer is not in the provided context, you can:
1. Provide related information from the context
2. Make reasonable inferences based on the context
3. Explain concepts that are related to the query
4. If completely unrelated, say "This question doesn't seem to be directly related to the document content."

Try to be helpful while staying within the general scope of the document's subject matter.

Query: {question}

Answer: """

        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Create document chain
        document_chain = create_stuff_documents_chain(llm, prompt)
        
        # Create RAG chain
        try:
            # Modern LangChain syntax
            rag_chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | document_chain
            )
        except (TypeError, ValueError):
            # Fallback for older LangChain versions
            def rag_chain(query):
                # Get documents from retriever
                docs = retriever.get_relevant_documents(query)
                # Pass to document chain
                return document_chain({"context": docs, "question": query})
        
        # Get response
        try:
            # For newer versions of LangChain
            response = rag_chain.invoke(query)
        except AttributeError:
            # For older versions or our fallback implementation
            response = rag_chain(query)
        
        # Handle both string and object responses
        if hasattr(response, 'content'):
            return response.content
        return str(response)
    
    except Exception as e:
        logger.error(f"Error in query processing: {e}")
        return "I encountered an error while processing your query. Please try again."
