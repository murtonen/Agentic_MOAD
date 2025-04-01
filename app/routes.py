import time
from flask import Blueprint, request, jsonify, render_template
from app.services.query_service import QueryService
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize query service
query_service = QueryService()

@main_bp.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@api_bp.route('/query', methods=['GET'])
def query():
    """
    Process a query about ServiceNow MOAD
    
    Query parameters:
    - query: The question to ask about ServiceNow
    - bypass_cache: Whether to bypass the cache (optional, default=False)
    
    Returns:
    - JSON with query results including summary and sources
    """
    start_time = time.time()
    
    # Get query parameters
    query = request.args.get('query')
    bypass_cache = request.args.get('bypass_cache', 'false').lower() == 'true'
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        # Process the query
        logger.info(f"Processing query: {query} (bypass_cache={bypass_cache})")
        result, cached = query_service.process_query(query, bypass_cache)
        
        # Build response
        processing_time = time.time() - start_time
        response = {
            'summary': result.get('summary', 'No information found'),
            'sources': result.get('sources', []),
            'processing_time': round(processing_time, 2),
            'cached': cached
        }
        
        logger.info(f"Query processed in {processing_time:.2f}s (cached={cached})")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return jsonify({
            'error': f"Failed to process query: {str(e)}",
            'processing_time': time.time() - start_time
        }), 500

def init_app(app):
    """Register blueprints with the Flask app"""
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp) 