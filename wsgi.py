"""WSGI entry point for the MOAD AI Query Application."""
import os
from dotenv import load_dotenv

# Load environment variables before creating the app
load_dotenv()

# Set environment to production by default for wsgi
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("FLASK_DEBUG", "0")

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run() 