#!/usr/bin/env python3
"""
Simple test to debug file filtering.
"""

from pathlib import Path
from datetime import datetime

data_dir = '/Users/lei/Documents/data/polygon'
data_path = Path(data_dir)
csv_files = list(data_path.glob('*.csv.gz'))

print(f"Total files: {len(csv_files)}")

# Test first few files
for i, file_path in enumerate(csv_files[:5]):
    print(f"File {i+1}: {file_path.name}")
    print(f"  Stem: {file_path.stem}")
    try:
        file_date = datetime.strptime(file_path.stem, '%Y-%m-%d')
        print(f"  Parsed date: {file_date}")
        
        # Check if it's in 2023
        start_dt = datetime.strptime('2023-01-01', '%Y-%m-%d')
        end_dt = datetime.strptime('2023-12-31', '%Y-%m-%d')
        
        in_range = start_dt <= file_date <= end_dt
        print(f"  In 2023 range: {in_range}")
        
    except Exception as e:
        print(f"  Error: {e}")
    print() 