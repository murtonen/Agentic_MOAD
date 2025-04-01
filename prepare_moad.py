#!/usr/bin/env python3
"""
Script to preprocess the MOAD PowerPoint file and prepare cached versions.
Run this script before starting the application to improve performance.
"""

import os
import sys
import time
import argparse
import json
from app.utils.extractors.pptx_extractor import PPTXExtractor

def extract_content_to_json(pptx_path, json_path):
    """Extract content from PowerPoint and save to JSON."""
    print(f"\n--- Preparing JSON Cache ---")
    start_time = time.time()
    
    try:
        extractor = PPTXExtractor(pptx_path)
        content = extractor.extract_all_slides()
        
        # Save to JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        print(f"JSON preparation completed in {time.time() - start_time:.2f} seconds")
        print(f"Extracted {len(content)} slides")
        print(f"JSON cache saved to: {json_path}")
        
        return content
    except Exception as e:
        print(f"ERROR: Failed to extract content: {str(e)}")
        print("Please check that the PowerPoint file is valid and accessible.")
        return None

def main():
    """Main function to prepare MOAD content."""
    parser = argparse.ArgumentParser(description="Prepare MOAD content for faster queries")
    parser.add_argument('--pptx', default='moad.pptx', help='Path to the MOAD PowerPoint file')
    parser.add_argument('--output', default='moad_content.json', help='Path to save the extracted content')
    parser.add_argument('--skip-errors', action='store_true', help='Continue processing even if errors occur')
    args = parser.parse_args()
    
    if not os.path.exists(args.pptx):
        print(f"ERROR: MOAD PowerPoint file not found: {args.pptx}")
        return 1
    
    print(f"Preparing MOAD content from: {args.pptx}")
    
    # Extract content
    content = extract_content_to_json(args.pptx, args.output)
    
    if content is None and not args.skip_errors:
        print("\nExtraction failed. Please check the errors above.")
        return 1
    elif content is None:
        print("\nExtraction had errors but --skip-errors flag was set.")
        print("Continuing with partial results.")
    
    print("\nMOAD content preparation complete!")
    print("You can now start the application for faster queries.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 