import os
import sys
from flask import Flask, render_template, request, jsonify, Response, g
import openai
from dotenv import load_dotenv
import re
import time
import numpy as np
import threading
from collections import defaultdict
from datetime import datetime, timedelta
import ipaddress

# Add the current directory to PYTHONPATH
sys.path.insert(0, os.path.abspath("."))

from app.api.pptx_extractor import PPTXExtractor
from app.api.content_manager import ContentManager
from app.api.query_cache import QueryCache
from app.api.license_analyzer import LicenseAnalyzer

# Load environment variables
load_dotenv()

# Path to MOAD PowerPoint file
MOAD_PATH = "moad.pptx"

# Security settings
# IP-based rate limiting: tracks request counts per IP
ip_request_counts = defaultdict(lambda: {"count": 0, "reset_time": datetime.now() + timedelta(hours=1)})
ip_block_list = set()  # IPs that have been blocked due to suspicious behavior
request_limiter_lock = threading.Lock()  # Lock for thread safety

# List of suspicious patterns to block
SUSPICIOUS_PATTERNS = [
    'eval-stdin.php', '../', 'auto_prepend_file', '/bin/sh', '.env', 
    'wp-admin', 'wp-login', 'phpMyAdmin', 'setup.php', 'admin.php',
    'shell', 'cmd.exe', 'passwd', 'config', '.git', '.htaccess', 
    'SELECT', 'UNION', '<script', 'javascript:', 'onload=', 'onerror='
]

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                static_folder='app/static',
                template_folder='app/components')
    
    # Initialize content manager
    content_manager = ContentManager(pptx_path="moad.pptx")
    
    # Initialize query cache
    query_cache = QueryCache()
    
    # Initialize license analyzer
    license_analyzer = LicenseAnalyzer()
    
    # Load the MOAD content
    start_time = time.time()
    print("Loading MOAD content...")
    content_manager.load_content()
    print(f"Content loading completed in {time.time() - start_time:.2f} seconds")
    
    # Performance metrics
    app.config['performance_metrics'] = {
        'avg_query_time': 0,
        'total_queries': 0
    }
    
    # --------------------------------------------
    # Security middleware
    # --------------------------------------------
    @app.before_request
    def check_security():
        """
        Security middleware to check for various attack vectors.
        This runs before every request.
        """
        # Get client IP
        client_ip = request.remote_addr
        
        # 1. Check if IP is in blocklist
        if client_ip in ip_block_list:
            return Response("Access Denied", status=403)
            
        # 2. Check rate limiting
        with request_limiter_lock:
            ip_data = ip_request_counts[client_ip]
            current_time = datetime.now()
            
            # Reset counter if time period has elapsed
            if current_time > ip_data["reset_time"]:
                ip_data["count"] = 0
                ip_data["reset_time"] = current_time + timedelta(hours=1)
                
            # Increment request count    
            ip_data["count"] += 1
            
            # Check if over limit (200 requests per hour)
            if ip_data["count"] > 200:
                print(f"Rate limit exceeded for IP: {client_ip}. Blocking.")
                ip_block_list.add(client_ip)
                return Response("Rate limit exceeded", status=429)
        
        # 3. Check for suspicious request patterns
        request_path = request.path.lower()
        request_args = str(request.args).lower()
        request_data = str(request.form).lower() if request.form else ""
        
        for pattern in SUSPICIOUS_PATTERNS:
            if (pattern in request_path or 
                pattern in request_args or 
                pattern in request_data):
                    
                print(f"Suspicious request from {client_ip}: {pattern}")
                # Add to watchlist - block after multiple suspicious requests
                ip_data["suspicious_count"] = ip_data.get("suspicious_count", 0) + 1
                
                if ip_data["suspicious_count"] >= 3:
                    print(f"Blocking IP {client_ip} after multiple suspicious requests")
                    ip_block_list.add(client_ip)
                    
                return Response("Bad Request", status=400)
    
    # Add security headers to all responses
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' https://via.placeholder.com data:;"
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response
    
    # --------------------------------------------
    # Application routes
    # --------------------------------------------
    @app.route('/')
    def index():
        """Render the main page."""
        return render_template('index.html')
    
    @app.route('/api/query', methods=['POST'])
    def process_query():
        """
        Process a query and return a summary of relevant information.
        """
        query = request.form.get('query', '')
        force_refresh = request.form.get('force_refresh', 'false').lower() == 'true'
        print(f"Processing query: {query}")
        
        # Additional query validation
        if not query or len(query) > 500:  # Prevent excessively long queries
            return jsonify({"error": "Invalid query"}), 400
            
        # Sanitize the query for logging and processing
        query = re.sub(r'[^\w\s\-\.,\?\'\"]+', '', query)
        
        # Check cache first (unless refresh is forced)
        cached_result = query_cache.get(query, force_refresh)
        if cached_result and not force_refresh:
            print("Returning cached result")
            return jsonify(cached_result)
        
        # If not in cache, process the query
        start_time = time.time()
        
        # Detect if this is a license comparison query
        is_license_query = _is_license_comparison_query(query)
        
        # Get relevant slides from content manager
        relevant_slides = content_manager.get_relevant_slides(query, max_results=10)
        
        # If this is a license query but we didn't get enough relevant results,
        # try to recursively search for more specific information
        if is_license_query and len(relevant_slides) < 5:
            feature = _extract_feature_from_query(query)
            if feature:
                print(f"License query about {feature} detected, searching for more specific information")
                # Try more specific searches
                specific_queries = [
                    f"{feature} license comparison",
                    f"{feature} capability matrix",
                    f"{feature} in standard vs pro",
                    f"itsm {feature} license",
                    f"servicenow {feature} availability"
                ]
                
                # Gather results from specific searches
                additional_slides = []
                for specific_query in specific_queries:
                    print(f"Trying specific query: {specific_query}")
                    specific_results = content_manager.get_relevant_slides(specific_query, max_results=3)
                    for result in specific_results:
                        # Check if this slide is already in our results
                        if result["slide_id"] not in [slide["slide_id"] for slide in relevant_slides]:
                            additional_slides.append(result)
                
                # Add unique additional slides to our results
                if additional_slides:
                    print(f"Found {len(additional_slides)} additional relevant slides")
                    # Merge with original slides, keeping original ones first
                    relevant_slides.extend(additional_slides)
                    # Cap at 15 max slides to avoid token limits
                    relevant_slides = relevant_slides[:15]
        
        if not relevant_slides:
            result = {
                "summary": "No relevant information found in the MOAD for this query.",
                "verified": True,
                "source_slides": []
            }
            query_cache.set(query, result)
            return jsonify(result)
        
        # Prepare slides for summary generation
        slide_contents = [slide['content'] for slide in relevant_slides]
        
        # If this is a license query, use the license analyzer
        if is_license_query:
            summary = generate_license_summary(query, slide_contents)
        else:
            # Generate comprehensive summary for non-license queries
            summary = generate_comprehensive_summary(query, slide_contents)
        
        # Prepare source slides for response
        source_slides = [
            {
                "slide_id": slide["slide_id"],
                "content_preview": slide["content_preview"]
            }
            for slide in relevant_slides
        ]
        
        # Create result
        result = {
            "summary": summary,
            "verified": True,
            "source_slides": source_slides
        }
        
        # Cache the result
        query_cache.set(query, result)
        
        # Update performance metrics
        query_time = time.time() - start_time
        update_performance_metrics(query_time)
        
        print(f"Query processed in {query_time:.2f} seconds")
        
        return jsonify(result)
    
    @app.route('/api/clear_cache', methods=['POST'])
    def clear_cache():
        """Clear the query cache for a specific query or all queries."""
        query = request.form.get('query', None)
        query_cache.clear(query)
        return jsonify({"success": True, "message": "Cache cleared successfully"})
    
    # --------------------------------------------
    # Admin routes (with basic authentication)
    # --------------------------------------------
    @app.route('/admin/security', methods=['GET'])
    def admin_security():
        """Admin endpoint to view security information."""
        # Basic auth check - would use a proper auth system in production
        auth = request.authorization
        if not auth or auth.username != 'admin' or auth.password != os.getenv('ADMIN_PASSWORD', 'changeme'):
            return Response('Authentication required', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
                
        # Display security information
        return jsonify({
            "blocked_ips": list(ip_block_list),
            "rate_limited_ips": {
                ip: data for ip, data in ip_request_counts.items() 
                if data["count"] > 100  # Show IPs with high request counts
            }
        })
    
    def update_performance_metrics(query_time):
        """Update performance metrics for monitoring."""
        metrics = app.config['performance_metrics']
        metrics['total_queries'] += 1
        
        # Update average query time with exponential moving average
        if metrics['total_queries'] == 1:
            metrics['avg_query_time'] = query_time
        else:
            # Use alpha=0.2 for the EMA
            metrics['avg_query_time'] = 0.2 * query_time + 0.8 * metrics['avg_query_time']
    
    def generate_comprehensive_summary(query, slide_contents):
        """
        Generate a comprehensive summary based on the query and content from relevant slides.
        
        Args:
            query: The user query
            slide_contents: List of content from relevant slides
        
        Returns:
            A comprehensive summary
        """
        try:
            # Get OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "API key not found. Please set the OPENAI_API_KEY environment variable."
            
            # Combine slide contents
            combined_content = "\n\n".join(slide_contents)
            print(f"Generating summary for query: '{query}' based on {len(slide_contents)} slides")
            
            # Detect if query is asking about license differences or feature availability
            is_license_comparison = any(term in query.lower() for term in ['license', 'edition', 'version', 'tier', 'standard', 'pro', 'enterprise', 'pro+'])
            is_feature_comparison = any(term in query.lower() for term in ['difference', 'compare', 'versus', 'vs', 'feature', 'capability'])
            
            # Customize prompt for license/feature comparisons
            comparison_instructions = ""
            if is_license_comparison and is_feature_comparison:
                comparison_instructions = """
                FEATURE COMPARISON INSTRUCTIONS:
                1. Create a clear feature/license comparison table if possible
                2. Label columns with license tiers (Standard, Pro, Pro+, Enterprise) 
                3. For each feature, use ✓ (available) or ✗ (not available) 
                4. Group features by category (core features, advanced features, etc.)
                5. If information is not available, state this clearly for that specific feature
                
                For license differences, make sure to check slides containing capability matrices,
                as they often show which features are available in which license tiers.
                Look specifically for license mentions near feature names.
                """
                
            # Create prompt for the summary
            prompt = f"""
            You are a ServiceNow expert answering questions precisely and accurately.
            
            User Query: "{query}"
            
            Below is content from relevant slides. Use ONLY this information to answer the query.
            
            {combined_content}
            
            {comparison_instructions}
            
            INSTRUCTIONS:
            1. Be EXTREMELY CONCISE. No introductions, conclusions, or explanations.
            2. Start with a DIRECT ANSWER to the question.
            3. Focus on the SPECIFIC information requested - nothing more.
            4. For feature availability, start with "Yes" or "No" followed by minimal context.
            5. For comparisons, use structured formats like tables or lists.
            6. Include ONLY information explicitly stated in the slides.
            7. Limit to 3-5 bullet points whenever possible.
            8. If information is not available, DO NOT state this generally. Instead:
               - Look for indirect clues (e.g., features appearing in Pro sections but not Standard)
               - Make reasoned inferences based on typical feature hierarchy
               - State "Based on available information..." and provide your best assessment
            
            Format your response using simple HTML for clear presentation. Do not include comments or explanations in your HTML.
            """
            
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You specialize in creating extremely concise, direct answers with minimal text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0
            )
            
            summary_content = response.choices[0].message.content
            print(f"Generated summary length: {len(summary_content)} chars")
            
            # Clean up any markdown artifacts or unwanted formatting
            summary_content = re.sub(r'```html', '', summary_content)
            summary_content = re.sub(r'```', '', summary_content)
            
            # Check if content is empty after cleanup
            if not summary_content or summary_content.strip() == "":
                print("WARNING: Summary generation returned empty content")
                return "<p>Unable to generate a summary for this query. Please try with a more specific question.</p>"
            
            # Skip the formatting agent and go directly to visual design for cleaner results
            visual_summary = apply_visual_design(query, summary_content)
            
            return visual_summary
        except Exception as e:
            error_message = f"Error generating summary: {str(e)}"
            print(error_message)
            return f"""
            <div style="border: 1px solid #f44336; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3 style="color: #f44336;">Error Generating Summary</h3>
                <p>There was an error processing your query: {str(e)}</p>
                <p>Found {len(slide_contents)} relevant slides, but couldn't generate a summary.</p>
            </div>
            """
    
    def generate_license_summary(query, slide_contents):
        """
        Generate a specialized summary for license-related queries using the license analyzer.
        
        Args:
            query: The user query
            slide_contents: List of content from relevant slides
            
        Returns:
            A formatted summary of license differences
        """
        try:
            # Use the license analyzer to extract license information
            analysis_result = license_analyzer.analyze_license_differences(slide_contents, query)
            
            # Generate a formatted summary
            summary_html = license_analyzer.generate_license_summary(analysis_result, query)
            
            # Apply visual design for consistent presentation
            visual_summary = apply_visual_design(query, summary_html)
            
            return visual_summary
        except Exception as e:
            print(f"Error in license analyzer: {str(e)}")
            # Fall back to the standard summarization method
            return generate_comprehensive_summary(query, slide_contents)
    
    def _is_license_comparison_query(query: str) -> bool:
        """
        Check if query is about license comparisons.
        
        Args:
            query: The search query
            
        Returns:
            True if query is about license comparisons
        """
        query_lower = query.lower()
        
        # Check for license comparison indicators
        license_terms = ['license', 'edition', 'version', 'tier', 'standard', 'pro', 'enterprise', 'pro+']
        comparison_terms = ['compare', 'comparison', 'difference', 'vs', 'versus', 'between', 'different']
        
        has_license = any(term in query_lower for term in license_terms)
        has_comparison = any(term in query_lower for term in comparison_terms)
        
        return has_license and has_comparison
    
    def _extract_feature_from_query(query: str) -> str:
        """
        Extract the main feature from the query.
        
        Args:
            query: The query string
            
        Returns:
            The main feature mentioned in the query
        """
        query_lower = query.lower()
        
        # List of common ServiceNow features
        features = [
            'virtual agent', 'now assist', 'predictive intelligence', 
            'workflow', 'performance analytics', 'ai search', 'knowledge graph',
            'chatbot', 'automation', 'cmdb', 'service portal'
        ]
        
        # Find which feature is in the query
        for feature in features:
            if feature in query_lower:
                return feature
        
        return None

    def enhance_formatting(query, content):
        """
        Formatting agent that enhances the structure and presentation of content.
        
        Args:
            query: The original user query
            content: The raw content to format
        
        Returns:
            Formatted content with better structure and presentation
        """
        try:
            # Get OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return content  # Return original content if no API key
            
            formatting_prompt = f"""
            You are a formatting expert specializing in creating well-structured and visually appealing HTML content.
            
            CONTENT TO FORMAT:
            {content}
            
            INSTRUCTIONS:
            1. Structure the content using appropriate HTML tags:
               - Use <h1>, <h2>, <h3> for headings
               - Use <ul> and <ol> for lists
               - Use <table> for tabular data and comparisons
               - Use <p> for paragraphs
               - Use <div> with appropriate classes for sections
               
            2. Enhance the visual organization:
               - Add clear visual hierarchy
               - Create sections for different parts of the content
               - Use classes for styling important elements
            
            3. Improve readability:
               - Ensure consistent formatting throughout
               - Add appropriate whitespace
               - Highlight key information
               
            4. Use these specific classes for enhanced styling:
               - .feature-available for available features
               - .feature-unavailable for unavailable features
               - .highlight for important information
               - .comparison-table for comparison tables
               - .section-header for section headers
            
            FORMAT the content to be visually appealing and well-structured.
            Return ONLY the formatted HTML content.
            """
            
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a formatting expert specializing in creating well-structured HTML content. Return only the HTML with no explanations or code fences."},
                    {"role": "user", "content": formatting_prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            # Get and clean response
            formatted_content = response.choices[0].message.content
            
            # Remove any markdown code fences
            formatted_content = re.sub(r'```html', '', formatted_content)
            formatted_content = re.sub(r'```', '', formatted_content)
            
            return formatted_content
        except Exception as e:
            print(f"Error in formatting agent: {e}")
            return content  # Return original content if there's an error
    
    def apply_visual_design(query, content):
        """
        Visual design agent that transforms the content into a more graphical presentation.
        
        Args:
            query: The original user query
            content: The formatted content
        
        Returns:
            Visually enhanced content with icons, emojis, and better visual elements
        """
        try:
            # Check if content is empty and return a meaningful message
            if not content or content.strip() == "":
                print("WARNING: Empty content passed to visual_design agent")
                return "<p>No content was generated for this query. Please try again with a more specific question.</p>"
            
            # Get OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return content  # Return original content if no API key
            
            # Extract query type to customize design
            is_comparison = any(term in query.lower() for term in ['compare', 'comparison', 'vs', 'versus', 'difference'])
            is_availability = any(term in query.lower() for term in ['include', 'includes', 'available', 'have', 'has', 'support'])
            is_license = any(term in query.lower() for term in ['standard', 'pro', 'enterprise', 'license', 'edition'])
            
            print(f"Applying visual design to content ({len(content)} chars)")
            
            # Add example response as reference if dealing with license comparison
            example_response = ""
            if is_comparison and is_license:
                example_response = """
                REFERENCE STYLE (do not copy content, just layout style):
                
                🔹 ITSM Standard
                Virtual Agent is not included in the base ITSM Standard offering.
                
                Customers on Standard would typically rely on basic self-service portals or request forms, without conversational AI capabilities.
                
                🔹 ITSM Pro
                Virtual Agent is included and enhanced with Predictive Intelligence and NLU (Natural Language Understanding).
                
                You get:
                - Pre-built Virtual Agent topics for common ITSM use cases (incident, request, change, etc.)
                - AI Search to help guide users during conversation
                - Custom topic building using low-code/no-code tools
                - Now Assist for Virtual Agent, which augments the Virtual Agent with LLM features
                - Integration with Microsoft Teams, Slack, or other channels
                
                🔹 ITSM Pro+
                Everything from ITSM Pro, plus:
                - Access to Now Assist Skill Kit and AI Agents, including agentic workflows
                - More advanced use cases like incident categorization and review generation
                - Multi-agent collaboration, chaining skills across domains
                - Integration with Generative AI Controller for "Bring Your Own Model" support
                - Enhanced personalization and accuracy via Knowledge Graph integration
                """
            
            visual_prompt = f"""
            You are a professional UI/UX expert. Transform the content into a visually engaging, clean presentation.

            QUERY: {query}
            
            CONTENT TO TRANSFORM:
            {content}
            
            {example_response}
            
            REQUIREMENTS:
            1. Create a DASHBOARD-STYLE presentation without any HTML comments or debugging information.
            2. Start with a clear, direct title answering the main query.
            3. Use simple, card-based layout similar to modern web dashboards.
            4. Use appropriate visual elements:
               - For AVAILABILITY: Use green checkmarks (✓) for available features, red X (✗) for unavailable
               - For COMPARISONS: Use color-coded sections with clear headings like "🔹 ITSM Standard", "🔹 ITSM Pro", etc.
               - For FEATURES: Use bulleted lists with icons (✓, ✗, 🔄, etc.)
               
            5. Make the answer EXTREMELY DIRECT AND CONCISE:
               - Remove any unnecessary text, explanations, or introductions
               - Focus only on the most important information
               - Use bullet points and short phrases where possible
               
            6. Apply consistent visual styling:
               - Clean, readable typography
               - Clear visual hierarchy with blue section headings
               - Appropriate spacing between sections
               - Highlight important capabilities in each tier
               
            7. For license comparisons, organize by tiers with colored headings (like the reference style)
               - Use blue diamond emoji (🔹) before each license tier name
               - List features in bullet points under each tier
               - Clearly indicate what's included vs. not included
               
            ABSOLUTELY DO NOT:
            - Include any HTML comments or debugging info (```html, etc.)
            - Add explanatory notes about your design decisions 
            - Include any self-referential text or descriptions of what you're doing
            - Use markdown formatting symbols in the final HTML output
            
            ONLY return clean, production-ready HTML without any explanation or comments.
            """
            
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a UI/UX professional creating production-ready HTML/CSS dashboards. Your outputs contain only clean code with no debugging information or self-commentary."},
                    {"role": "user", "content": visual_prompt}
                ],
                max_tokens=1500,
                temperature=0.1
            )
            
            output = response.choices[0].message.content
            
            # Clean up any remaining HTML comments or explanatory text
            output = re.sub(r'```html.*?```', '', output, flags=re.DOTALL)
            output = re.sub(r'```.*?```', '', output, flags=re.DOTALL)
            output = re.sub(r'<\!--.*?-->', '', output, flags=re.DOTALL)
            output = re.sub(r'This HTML code creates.*', '', output, flags=re.DOTALL)
            
            # Check if output is empty after cleanup
            if not output or output.strip() == "":
                print("WARNING: Visual design agent returned empty output after cleanup")
                return content  # Return original content if output is empty
                
            print(f"Visual design completed, output length: {len(output)} chars")
            return output
        except Exception as e:
            print(f"ERROR in visual design agent: {str(e)}")
            # Return the original content with error information
            return f"""
            <div style="border: 1px solid #f44336; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3 style="color: #f44336;">Error in Visual Formatting</h3>
                <p>The original content is displayed below:</p>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">{content}</div>
            </div>
            """
    
    return app

if __name__ == "__main__":
    print("Starting optimized MOAD Query System...")
    print("Access the web interface at http://localhost:5000")
    app = create_app()
    app.run(host="0.0.0.0", debug=True) 