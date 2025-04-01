# MOAD AI Query Application

An advanced multi-agent system for querying ServiceNow's Mother of All Decks (MOAD), providing intelligent, formatted answers with a focus on license and feature comparison capabilities.

## Features

- **Intelligent Query Processing**: Extract meaningful information from ServiceNow's MOAD
- **Semantic & Keyword Search**: Find relevant slides using combined search strategies
- **Specialized License Analysis**: Enhanced capability to understand license differences across ServiceNow tiers
- **Recursive Information Gathering**: Automatically search for additional context when needed
- **Smart Visual Formatting**: Present information in a clean, structured dashboard-style format
- **Query Caching**: Speed up repeated queries with intelligent caching (with bypass option)
- **Performance Monitoring**: Track query processing times and system performance

## Architecture

This application uses a sophisticated multi-agent architecture:

1. **Content Manager**
   - Extracts and indexes content from the MOAD PowerPoint
   - Provides both semantic and keyword search capabilities
   - Preserves structural information like tables and sections

2. **License Analyzer**
   - Specialized for understanding ServiceNow license differences
   - Contains domain knowledge about feature availability across tiers
   - Can analyze tables and capability matrices

3. **Summary Generation Agents**
   - Comprehensive Summary Agent: Creates detailed summaries for general queries
   - License Summary Agent: Specialized for license/feature comparisons

4. **Visual Design Agent**
   - Transforms technical content into dashboard-style visual presentations
   - Adapts layout based on query type (comparison, availability, etc.)
   - Uses appropriate visual elements (checkmarks, color-coding, etc.)

5. **Query Cache**
   - Stores and retrieves previous query results
   - Applies expiration policies to ensure freshness
   - Provides bypass option for force-refreshing content

## Setup

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `.\venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and add your OpenAI API key
6. Prepare the MOAD content (optional but recommended):
   ```
   python prepare_moad.py --pptx_path=moad.pptx --output_format=json
   ```
7. Run the application: `python test_app.py`

## Usage

1. Access the web interface at `http://localhost:5000`
2. Enter your query about ServiceNow in the search box
3. For queries requiring fresh data, enable "Bypass Cache" option
4. Submit your query and view the formatted results
5. View source slides to see where information was derived from

## Query Examples

- "What differences does virtual agent have in ITSM licenses? Like standard vs. pro vs. pro+?"
- "Compare ITSM Standard, Pro and Enterprise"
- "What features are in Workplace Service Delivery?"
- "Does Standard license include Predictive Intelligence?"
- "What is the pricing structure for CSM?"

## Technical Details

### Content Extraction
The system extracts content from the MOAD PowerPoint, preserving structural elements like tables, lists, and sections. Content is cached to improve performance.

### Search Methods
- **Semantic Search**: Uses embeddings to find conceptually similar content (when available)
- **Enhanced Keyword Search**: Weighted search with special handling for product names and features
- **Specialized License Search**: Targeted searches for capability matrices and license information

### Summary Generation
The system uses OpenAI's GPT-4 to generate comprehensive summaries based on the retrieved content. For license queries, it employs specialized analysis to extract and infer differences between license tiers.

### Visual Presentation
Information is formatted into a clean, dashboard-style presentation with appropriate visual elements:
- Color-coded license tier headings
- Checkmarks and X marks for feature availability
- Structured lists and tables for comparisons
- Visual highlighting for important information

## License
This project is for demonstration purposes only. ServiceNow and MOAD are trademarks of ServiceNow, Inc. 