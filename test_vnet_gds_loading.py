#!/usr/bin/env python3
"""
Test VNET and GDS data loading.
"""

import pandas as pd
import gzip
from pathlib import Path
from datetime import datetime

def test_data_loading():
    """Test loading VNET and GDS data."""
    data_dir = '/Users/lei/Documents/data/polygon'
    data_path = Path(data_dir)
    csv_files = list(data_path.glob('*.csv.gz'))
    
    # Filter for 2023 files
    start_dt = datetime.strptime('2023-01-01', '%Y-%m-%d')
    end_dt = datetime.strptime('2023-12-31', '%Y-%m-%d')
    
    relevant_files = []
    for file_path in csv_files:
        try:
            date_str = file_path.stem.replace('.csv', '')
            file_date = datetime.strptime(date_str, '%Y-%m-%d')
            if start_dt <= file_date <= end_dt:
                relevant_files.append(file_path)
        except:
            continue
    
    print(f"Found {len(relevant_files)} relevant files")
    
    # Test loading from first few files
    vnet_data = []
    gds_data = []
    
    for i, file_path in enumerate(relevant_files[:5]):
        print(f"\nProcessing {file_path.name}...")
        
        try:
            with gzip.open(file_path, 'rt') as f:
                df = pd.read_csv(f)
                
                # Check for VNET and GDS
                vnet_records = df[df['ticker'] == 'VNET']
                gds_records = df[df['ticker'] == 'GDS']
                
                print(f"  VNET records: {len(vnet_records)}")
                print(f"  GDS records: {len(gds_records)}")
                
                if len(vnet_records) > 0:
                    vnet_records['date'] = pd.to_datetime(file_path.stem.replace('.csv', ''))
                    vnet_data.append(vnet_records)
                
                if len(gds_records) > 0:
                    gds_records['date'] = pd.to_datetime(file_path.stem.replace('.csv', ''))
                    gds_data.append(gds_records)
                    
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f"\nTotal VNET data chunks: {len(vnet_data)}")
    print(f"Total GDS data chunks: {len(gds_data)}")
    
    if vnet_data:
        vnet_combined = pd.concat(vnet_data, ignore_index=True)
        print(f"Combined VNET records: {len(vnet_combined)}")
        print("VNET sample:")
        print(vnet_combined.head(3))
    
    if gds_data:
        gds_combined = pd.concat(gds_data, ignore_index=True)
        print(f"Combined GDS records: {len(gds_combined)}")
        print("GDS sample:")
        print(gds_combined.head(3))

if __name__ == "__main__":
    test_data_loading() 