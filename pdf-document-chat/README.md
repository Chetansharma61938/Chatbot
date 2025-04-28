# PDF Document Chat

A Streamlit application that allows users to upload PDF documents and chat with their contents using AI.

## Features

- PDF document upload and processing
- Semantic search using RAG
- Chat interface for document queries
- Redis vector storage
- Groq LLM integration

## Deployment on Streamlit Cloud

1. Fork this repository to your GitHub account

2. Sign up for Streamlit Cloud (https://streamlit.io/cloud)

3. Connect your GitHub repository to Streamlit Cloud

4. Configure the following secrets in Streamlit Cloud:
   - REDIS_HOST: Your Redis host
   - REDIS_PORT: Redis port (default: 6379)
   - REDIS_PASSWORD: Your Redis password
   - GROQ_API_KEY: Your Groq API key

5. Deploy the app

## Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd pdf-document-chat
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your environment variables:
```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
GROQ_API_KEY=your-groq-api-key
```

5. Run the app:
```bash
streamlit run streamlit_app.py
```

## Requirements

- Python 3.8+
- Redis server
- Groq API key
- Streamlit

## Project Structure

- `streamlit_app.py`: Main Streamlit application
- `rag_utils.py`: RAG implementation
- `requirements.txt`: Python dependencies
- `.streamlit/secrets.toml`: Streamlit Cloud secrets 