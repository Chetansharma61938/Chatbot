document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const uploadForm = document.getElementById('upload-form');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');
    const loadingIndicator = document.getElementById('loading-indicator');
    const uploadSection = document.getElementById('upload-section');
    const chatSection = document.getElementById('chat-section');
    const chatHistory = document.getElementById('chat-history');
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const newDocumentBtn = document.getElementById('new-document-btn');
    const pdfFileInput = document.getElementById('pdf-file');

    // Handle file upload
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const fileInput = document.getElementById('pdf-file');
        const file = fileInput.files[0];
        
        if (!file) {
            showUploadStatus('Please select a PDF file.', 'danger');
            return;
        }
        
        if (file.size > 16 * 1024 * 1024) {
            showUploadStatus('File is too large. Maximum size is 16MB.', 'danger');
            return;
        }
        
        // Show loading indicator
        uploadBtn.disabled = true;
        loadingIndicator.classList.remove('d-none');
        uploadStatus.classList.add('d-none');
        
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        
        // Send upload request
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingIndicator.classList.add('d-none');
            uploadBtn.disabled = false;
            
            if (data.error) {
                showUploadStatus(data.error, 'danger');
            } else {
                showUploadStatus(data.message, 'success');
                
                // Show chat section after successful upload
                setTimeout(() => {
                    uploadSection.classList.add('d-none');
                    chatSection.classList.remove('d-none');
                    
                    // Add system message to chat history
                    addMessageToChatHistory('system', 'Document processed successfully. You can now ask questions about the content.');
                    
                    // Focus on query input
                    queryInput.focus();
                }, 1500);
            }
        })
        .catch(error => {
            loadingIndicator.classList.add('d-none');
            uploadBtn.disabled = false;
            showUploadStatus('Error uploading file: ' + error.message, 'danger');
        });
    });

    // Handle query submission
    queryForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const query = queryInput.value.trim();
        if (!query) return;
        
        // Add user message to chat history
        addMessageToChatHistory('user', query);
        
        // Clear input
        queryInput.value = '';
        
        // If user wants to exit
        if (query.toLowerCase() === 'exit') {
            addMessageToChatHistory('system', 'Chat session ended. You may upload a new document or ask new questions.');
            return;
        }
        
        // Add loading message
        const loadingMsgId = 'loading-' + Date.now();
        addLoadingMessage(loadingMsgId);
        
        // Send query to backend
        fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query
            })
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            removeLoadingMessage(loadingMsgId);
            
            if (data.error) {
                addMessageToChatHistory('error', data.error);
            } else {
                addMessageToChatHistory('assistant', data.answer);
            }
            
            // Scroll to bottom of chat history
            scrollChatToBottom();
        })
        .catch(error => {
            // Remove loading message
            removeLoadingMessage(loadingMsgId);
            
            addMessageToChatHistory('error', 'Error: ' + error.message);
            scrollChatToBottom();
        });
    });

    // Handle new document button
    newDocumentBtn.addEventListener('click', function() {
        // Clear file input
        pdfFileInput.value = '';
        
        // Clear chat history
        chatHistory.innerHTML = '';
        
        // Switch back to upload section
        chatSection.classList.add('d-none');
        uploadSection.classList.remove('d-none');
        uploadStatus.classList.add('d-none');
    });

    // Helper functions
    function showUploadStatus(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.className = `alert mt-3 alert-${type}`;
        uploadStatus.classList.remove('d-none');
    }

    function addMessageToChatHistory(sender, message) {
        const messageDiv = document.createElement('div');
        
        switch(sender) {
            case 'user':
                messageDiv.className = 'user-message';
                messageDiv.innerHTML = `
                    <div class="message-content">${formatMessage(message)}</div>
                `;
                break;
                
            case 'assistant':
                messageDiv.className = 'assistant-message';
                messageDiv.innerHTML = `
                    <div class="message-content">${formatMessage(message)}</div>
                `;
                break;
                
            case 'system':
                messageDiv.className = 'system-message';
                messageDiv.innerHTML = `
                    <i class="fas fa-info-circle me-2"></i>
                    <span>${formatMessage(message)}</span>
                `;
                break;
                
            case 'error':
                messageDiv.className = 'error-message';
                messageDiv.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <span>${formatMessage(message)}</span>
                `;
                break;
                
            default:
                messageDiv.className = 'mb-3 p-2 rounded bg-secondary';
                messageDiv.innerHTML = `
                    <div class="message-content">${formatMessage(message)}</div>
                `;
        }
        
        chatHistory.appendChild(messageDiv);
        scrollChatToBottom();
    }

    function addLoadingMessage(id) {
        const loadingDiv = document.createElement('div');
        loadingDiv.id = id;
        loadingDiv.className = 'assistant-message';
        loadingDiv.innerHTML = `
            <div class="message-content">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm text-light me-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span>Thinking...</span>
                </div>
            </div>
        `;
        
        chatHistory.appendChild(loadingDiv);
        scrollChatToBottom();
    }

    function removeLoadingMessage(id) {
        const loadingMsg = document.getElementById(id);
        if (loadingMsg) {
            loadingMsg.remove();
        }
    }

    function formatMessage(message) {
        // Convert line breaks to <br> tags
        return message.replace(/\n/g, '<br>');
    }

    function scrollChatToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
});
