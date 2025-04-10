import os
import logging
import uuid
from flask import Flask, render_template, request, jsonify, session
import redis
from werkzeug.utils import secure_filename
from rag_utils import (
    process_pdf, 
    store_document_embeddings, 
    query_document, 
    get_redis_connection
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Check if essential libraries are available
missing_libs = []
try:
    import PyPDF2
except ImportError:
    missing_libs.append("PyPDF2")

# Initialize Redis connection
try:
    redis_client = get_redis_connection()
    redis_client.ping()  # Test connection
    logger.info("Redis connection successful")
except redis.ConnectionError as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None
except Exception as e:
    logger.error(f"Error setting up Redis: {e}")
    redis_client = None

# File upload configuration
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = '/tmp'  # Temporary storage for uploads

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Render the main page"""
    # Initialize session if not already done
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Please upload a PDF.'}), 400
    
    try:
        # Save the file temporarily
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Generate a document ID for this upload
        doc_id = f"{session['session_id']}_{filename}"
        
        # Process the PDF and store in Redis
        chunks = process_pdf(file_path)
        if not chunks:
            return jsonify({'error': 'Failed to extract text from PDF'}), 400
        
        # Store chunks and their embeddings in Redis
        store_document_embeddings(redis_client, doc_id, chunks)
        
        # Save document ID in session for later retrieval
        session['current_doc_id'] = doc_id
        
        # Clean up the temporary file
        os.remove(file_path)
        
        return jsonify({
            'success': True, 
            'message': 'Document processed successfully!',
            'doc_id': doc_id
        })
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/query', methods=['POST'])
def query():
    """Handle user query"""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    if 'current_doc_id' not in session:
        return jsonify({'error': 'No document has been uploaded yet'}), 400
    
    user_query = data['query']
    
    # Check if user wants to exit
    if user_query.lower() == 'exit':
        return jsonify({'answer': 'Chat session ended. You may upload a new document or ask new questions.'})
    
    try:
        # Get answer from RAG system
        answer = query_document(redis_client, session['current_doc_id'], user_query)
        return jsonify({'answer': answer})
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({'error': f'Error processing query: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    redis_status = "Connected" if redis_client and redis_client.ping() else "Disconnected"
    return jsonify({
        'status': 'healthy',
        'redis': redis_status
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
