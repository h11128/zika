#!/usr/bin/env python3
"""
Extract and process CC-CEDICT data
"""

import gzip
import os

def extract_cedict():
    """Extract the gzipped CEDICT file."""
    input_file = "data/cedict_ts.u8"
    output_file = "data/cedict_ts.txt"
    
    print(f"Extracting {input_file}...")
    
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"Error: {input_file} not found!")
            return False
        
        # Extract gzip file
        with gzip.open(input_file, 'rt', encoding='utf-8') as f_in:
            with open(output_file, 'w', encoding='utf-8') as f_out:
                f_out.write(f_in.read())
        
        print(f"Successfully extracted to {output_file}")
        
        # Show file size
        size = os.path.getsize(output_file)
        print(f"Extracted file size: {size:,} bytes")
        
        return True
        
    except Exception as e:
        print(f"Error extracting file: {e}")
        return False

if __name__ == "__main__":
    extract_cedict()
