#!/usr/bin/env python3
"""
Script to preprocess the MOAD PowerPoint file and prepare cached versions.
Run this script before starting the application to improve performance.
"""

import os
import sys
import time
import argparse
from app.api.content_manager import ContentManager
from app.api.db_manager import DatabaseManager

def main():
    """Main function to prepare MOAD content."""
    parser = argparse.ArgumentParser(description="Prepare MOAD content for faster queries")
    parser.add_argument('--pptx', default='moad.pptx', help='Path to the MOAD PowerPoint file')
    parser.add_argument('--format', choices=['json', 'db', 'both'], default='both', 
                      help='Output format: json, db, or both (default)')
    parser.add_argument('--json-path', default='moad_content.json', help='Path to save JSON content')
    parser.add_argument('--db-path', default='moad_db.sqlite', help='Path to save SQLite database')
    args = parser.parse_args()
    
    if not os.path.exists(args.pptx):
        print(f"ERROR: MOAD PowerPoint file not found: {args.pptx}")
        return 1
    
    print(f"Preparing MOAD content from: {args.pptx}")
    
    # Process JSON format
    if args.format in ['json', 'both']:
        print("\n--- Preparing JSON Cache ---")
        start_time = time.time()
        
        content_manager = ContentManager(args.pptx, args.json_path)
        content = content_manager.load_content()
        
        print(f"JSON preparation completed in {time.time() - start_time:.2f} seconds")
        print(f"Extracted {len(content)} slides")
        print(f"JSON cache saved to: {args.json_path}")
    
    # Process SQLite database format
    if args.format in ['db', 'both']:
        print("\n--- Preparing SQLite Database ---")
        start_time = time.time()
        
        db_manager = DatabaseManager(args.db_path, args.pptx)
        slides_count = db_manager.import_from_pptx()
        
        print(f"Database preparation completed in {time.time() - start_time:.2f} seconds")
        print(f"Imported {slides_count} slides into the database")
        print(f"SQLite database saved to: {args.db_path}")
    
    print("\nMOAD content preparation complete!")
    print("You can now start the application for faster queries.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 