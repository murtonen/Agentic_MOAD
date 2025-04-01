# MOAD AI Query Application

A powerful AI-powered application for querying ServiceNow product, license, and feature information based on the MOAD (Mother of All Demos) content.

## Features

- **AI-Powered Queries**: Ask natural language questions about ServiceNow products, licenses, and features
- **Smart Caching**: Responses are cached to improve performance
- **Source References**: Answers include references to the source slides
- **Modern UI**: Clean, responsive interface built with Bootstrap

## Requirements

- Python 3.8+
- Flask
- OpenAI API key
- ServiceNow MOAD content (extracted via the prepare_moad.py script)

## Installation

1. Clone the repository:

```
git clone https://github.com/yourusername/moad-ai-query.git
cd moad-ai-query
```

2. Install the required packages:

```
pip install -r requirements.txt
```

3. Set up your environment variables:

Create a `.env` file in the root directory with the following content:

```
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_APP=app
FLASK_ENV=development
FLASK_DEBUG=True

# Cache Configuration
CACHE_MAX_AGE_HOURS=24

# Server Configuration
FLASK_PORT=5000
FLASK_HOST=127.0.0.1
```

4. Prepare the MOAD content:

```
python prepare_moad.py path/to/your/moad/presentation.pptx
```

## Running the Application

Start the application with:

```
python run.py
```

Then open your browser to http://127.0.0.1:5000

## Usage

1. Enter your question about ServiceNow in the search box
2. Click "Submit Query" or press Enter
3. View the results with source references
4. Click on any of the example queries to try them out

## Folder Structure

```
moad-ai-query/
├── app/
│   ├── models/         # Data models for the application
│   ├── services/       # Business logic services
│   ├── static/         # Static assets (CSS, JS, images)
│   ├── templates/      # HTML templates
│   └── utils/          # Utility functions and classes
├── data/               # Data files (MOAD content, embeddings)
├── .env                # Environment variables
├── .env.example        # Example environment variables
├── prepare_moad.py     # Script to prepare MOAD content
├── requirements.txt    # Python dependencies
├── run.py              # Application entry point
└── README.md           # Project documentation
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- ServiceNow MOAD (Mother of All Demos) for content
- OpenAI for providing the AI backend 