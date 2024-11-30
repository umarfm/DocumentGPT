from flask import Blueprint, request, jsonify, current_app, url_for
from app.services.document_service import DocumentService
from app.services.openai_service import OpenAIService
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from flask import render_template, flash,redirect

main = Blueprint('main', __name__)

document_service = None
openai_service = None

@main.before_app_first_request
def initialize_services():
    global document_service, openai_service
    document_service = DocumentService(current_app.config['UPLOAD_FOLDER'])
    openai_service = OpenAIService()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@main.route('/upload', methods=['POST'])
def upload_document():
    """
    Upload and process a new document.
    Returns document metadata including paragraph IDs and locations.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = Path(current_app.config['UPLOAD_FOLDER']) / filename
        file.save(filepath)
        
        # Process and index the document
        try:
            doc_metadata = document_service.process_document(str(filepath))
            return jsonify({
                'message': 'File uploaded and processed successfully',
                'metadata': doc_metadata
            }), 200
        except Exception as e:
            return jsonify({'error': f'Error processing document: {str(e)}'}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

@main.route('/ask', methods=['POST'])
def ask_question():
    """
    Answer a question based on document content.
    Returns answer with source references.
    """
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({'error': 'Question is required'}), 400
    
    question = data['question']
    
    # Get relevant document sections
    relevant_sections = document_service.find_relevant_sections(question)
    
    # Generate answer using OpenAI
    response = openai_service.generate_answer(question, relevant_sections)
    
    if response['status'] == 'success':
        # Generate URLs for source verification
        for source in response['sources']:
            source['url'] = url_for('main.view_document',
                                  filename=source['document'],
                                  start=source['char_start'],
                                  end=source['char_end'],
                                  _external=True)
    
    return jsonify(response), 200

@main.route('/document/<filename>')
def view_document(filename):
    """
    View specific part of a document with robust encoding handling.
    """
    try:
        start = int(request.args.get('start', 0))
        end = int(request.args.get('end', -1))
        
        filepath = Path(current_app.config['UPLOAD_FOLDER']) / secure_filename(filename)
        
        if not filepath.exists():
            return jsonify({'error': 'Document not found'}), 404
            
        # Try different encodings
        encodings = ['utf-8', 'utf-16', 'ascii', 'iso-8859-1', 'cp1252']
        content = None
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                    break
            except UnicodeDecodeError:
                continue
                
        if content is None:
            return jsonify({'error': 'Could not decode the document'}), 500
            
        if end > -1:
            content = content[start:end]
            
        return jsonify({'content': content}), 200
            
    except Exception as e:
        return jsonify({'error': f'Error retrieving document: {str(e)}'}), 500
    
    
@main.route('/')
def index():
    """Render the main question-asking interface."""
    return render_template('index.html')

@main.route('/documents')
def documents():
    """Render the document management interface."""
    docs = []
    if document_service:
        for filename, metadata in document_service.document_index.items():
            docs.append({
                'filename': filename,
                'last_updated': metadata['last_updated'],
                'total_paragraphs': metadata['total_paragraphs']
            })
    return render_template('documents.html', documents=docs)

@main.route('/view/<filename>')
def view_document_page(filename):
    """Render the document viewing interface."""
    try:
        filepath = Path(current_app.config['UPLOAD_FOLDER']) / secure_filename(filename)
        
        if not filepath.exists():
            flash('Document not found', 'error')
            return redirect(url_for('main.documents'))
            
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Get document metadata
        metadata = document_service.document_index.get(filename, {})
        
        return render_template('view_document.html', 
                             filename=filename,
                             content=content,
                             metadata=metadata)
                             
    except Exception as e:
        flash(f'Error viewing document: {str(e)}', 'error')
        return redirect(url_for('main.documents'))

@main.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200