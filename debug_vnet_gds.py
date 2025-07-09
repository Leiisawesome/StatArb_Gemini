#!/usr/bin/env python3
"""
Debug script for VNET/GDS data loading issues.
"""

import os
import pandas as pd
import gzip
from pathlib import Path
from datetime import datetime
import yaml

def load_config():
    """Load configuration from multiple sources."""
    data_dir = os.getenv('POLYGON_DATA_DIR')
    
    if not data_dir:
        config_path = Path('stat_arb_project/config/production_config.yaml')
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                data_dir = config.get('data', {}).get('polygon_data_dir')
    
    if not data_dir:
        data_dir = '/Users/lei/Documents/data/polygon'
    
    return data_dir

def debug_data_loading():
    """Debug the data loading process."""
    data_dir = load_config()
    print(f"Data directory: {data_dir}")
    
    data_path = Path(data_dir)
    csv_files = list(data_path.glob('*.csv.gz'))
    print(f"Total files found: {len(csv_files)}")
    
    # Check date range of available files
    dates = []
    for file_path in csv_files:
        try:
            file_date = datetime.strptime(file_path.stem, '%Y-%m-%d')
            dates.append(file_date)
        except:
            continue
    
    if dates:
        dates.sort()
        print(f"Date range: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
    
    # Test with a broader date range
    start_dt = datetime.strptime('2023-01-01', '%Y-%m-%d')
    end_dt = datetime.strptime('2023-12-31', '%Y-%m-%d')
    
    relevant_files = []
    for file_path in csv_files:
        try:
            file_date = datetime.strptime(file_path.stem, '%Y-%m-%d')
            if start_dt <= file_date <= end_dt:
                relevant_files.append(file_path)
        except:
            continue
    
    print(f"Files in 2023: {len(relevant_files)}")
    
    if relevant_files:
        print("First 5 relevant files:")
        for file_path in relevant_files[:5]:
            print(f"  {file_path.name}")
        
        # Test loading VNET and GDS from first file
        test_file = relevant_files[0]
        print(f"\nTesting data loading from {test_file.name}...")
        
        try:
            with gzip.open(test_file, 'rt') as f:
                df = pd.read_csv(f)
                print(f"Total records: {len(df)}")
                print(f"Columns: {list(df.columns)}")
                
                # Check for VNET and GDS
                vnet_data = df[df['ticker'] == 'VNET']
                gds_data = df[df['ticker'] == 'GDS']
                
                print(f"VNET records: {len(vnet_data)}")
                print(f"GDS records: {len(gds_data)}")
                
                if len(vnet_data) > 0:
                    print("Sample VNET data:")
                    print(vnet_data.head(3))
                
                if len(gds_data) > 0:
                    print("Sample GDS data:")
                    print(gds_data.head(3))
                    
        except Exception as e:
            print(f"Error reading file: {e}")

if __name__ == "__main__":
    debug_data_loading() 