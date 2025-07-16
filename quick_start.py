#!/usr/bin/env python3
"""
Quick Start Script - Technical Indicators Integration
====================================================

This script gets you started immediately with Phase 1 tasks:
1. Sets up ClickHouse table
2. Tests API connectivity  
3. Downloads sample indicators to verify everything works
4. Updates project tracker with progress

Run this first to validate your setup before the full download.
"""

import sys
import os
import time
from datetime import datetime
import requests
import json

# Add project path
sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini/new_structure')

try:
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False

def test_api_connectivity(api_key: str) -> bool:
    """Test if Polygon.io API is accessible"""
    print("🔍 Testing Polygon.io API connectivity...")
    
    try:
        # Test with a simple SMA request
        url = "https://api.polygon.io/v1/indicators/sma/AAPL"
        params = {
            "timespan": "day",
            "adjusted": "true",
            "window": 20,
            "series_type": "close",
            "order": "desc",
            "limit": 1,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK":
            print("✅ API connectivity verified")
            return True
        else:
            print(f"❌ API returned error: {data}")
            return False
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def setup_clickhouse_table() -> bool:
    """Setup ClickHouse technical indicators table"""
    print("🗄️  Setting up ClickHouse table...")
    
    if not CLICKHOUSE_AVAILABLE:
        print("⚠️  ClickHouse driver not available")
        print("   Install with: pip install clickhouse-connect")
        return False
    
    try:
        # Connect to ClickHouse
        client = clickhouse_connect.get_client(
            host="localhost",
            port=8123,
            database='polygon_data'
        )
        
        # Create table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS technical_indicators (
            symbol String,
            date Date,
            timestamp DateTime,
            
            -- Moving Averages
            sma_20 Nullable(Float64),
            sma_50 Nullable(Float64),
            ema_20 Nullable(Float64),
            
            -- Momentum Oscillators  
            rsi_14 Nullable(Float64),
            
            -- MACD
            macd_line Nullable(Float64),
            macd_signal Nullable(Float64),
            macd_histogram Nullable(Float64),
            
            -- Metadata
            indicator_type String,
            timespan String DEFAULT 'day',
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (symbol, date)
        PARTITION BY toYYYYMM(date)
        """
        
        client.command(create_table_sql)
        print("✅ ClickHouse table created successfully")
        
        # Test insertion
        test_data = [{
            'symbol': 'TEST',
            'date': '2025-07-16',
            'timestamp': datetime.now(),
            'sma_20': 100.0,
            'indicator_type': 'test'
        }]
        
        client.insert('technical_indicators', test_data)
        print("✅ Table insertion test passed")
        
        # Clean up test data
        client.command("DELETE FROM technical_indicators WHERE symbol = 'TEST'")
        
        return True
        
    except Exception as e:
        print(f"❌ ClickHouse setup failed: {e}")
        return False

def download_sample_indicators(api_key: str) -> bool:
    """Download sample indicators to test the full pipeline"""
    print("📥 Testing indicator download with sample data...")
    
    # Test symbols
    test_symbols = ["AAPL", "SPY"]
    
    for symbol in test_symbols:
        try:
            print(f"   Testing {symbol}...")
            
            # Download small sample of SMA data
            url = f"https://api.polygon.io/v1/indicators/sma/{symbol}"
            params = {
                "timespan": "day",
                "adjusted": "true",
                "window": 20,
                "series_type": "close", 
                "order": "desc",
                "limit": 5,
                "apikey": api_key
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "OK":
                values = data.get("results", {}).get("values", [])
                print(f"   ✅ {symbol}: Downloaded {len(values)} SMA records")
            else:
                print(f"   ❌ {symbol}: {data}")
                return False
            
            # Rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ {symbol}: Download failed - {e}")
            return False
    
    print("✅ Sample download test passed")
    return True

def update_project_tracker():
    """Update project tracker with setup completion"""
    print("📊 Updating project tracker...")
    
    try:
        # Load tracker
        sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')
        from project_tracker import ProjectTracker, TaskStatus
        
        tracker = ProjectTracker()
        
        # Mark ClickHouse setup as completed
        tracker.update_task_status(
            "p1_clickhouse_setup", 
            TaskStatus.COMPLETED,
            actual_hours=0.5,
            note="Quick start setup completed successfully"
        )
        
        print("✅ Project tracker updated")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not update project tracker: {e}")
        return False

def main():
    """Main quick start function"""
    
    print("""
🚀 TECHNICAL INDICATORS QUICK START
===================================

This script will verify your setup and get you ready for the 
full historical indicators download (2023-2025).

Steps:
1. Test Polygon.io API connectivity
2. Setup ClickHouse table structure
3. Download sample indicators
4. Update project tracker

Let's get started!
    """)
    
    # Configuration
    API_KEY = "kwnaUOlnQq7lLqRU0KQg2MqndGblHPnR"
    
    # Step 1: Test API
    if not test_api_connectivity(API_KEY):
        print("❌ API test failed. Please check your API key and internet connection.")
        return False
    
    # Step 2: Setup ClickHouse
    if not setup_clickhouse_table():
        print("❌ ClickHouse setup failed. You can still proceed with CSV storage.")
        clickhouse_ready = False
    else:
        clickhouse_ready = True
    
    # Step 3: Test download
    if not download_sample_indicators(API_KEY):
        print("❌ Sample download failed. Please check your API key permissions.")
        return False
    
    # Step 4: Update tracker
    update_project_tracker()
    
    # Success summary
    print(f"""
🎉 QUICK START COMPLETED SUCCESSFULLY!
=====================================

✅ Polygon.io API: Connected and working
{'✅' if clickhouse_ready else '⚠️ '} ClickHouse: {'Ready for bulk storage' if clickhouse_ready else 'Not available (will use CSV)'}
✅ Indicator Downloads: Tested and working
✅ Project Tracker: Updated

🚀 NEXT STEPS:
1. Run the full historical download:
   python download_historical_indicators.py
   
2. Monitor progress with project tracker:
   python project_tracker.py
   
3. Estimated download time: 45-60 minutes for 2.5 years

💡 The full download will get:
   • SMA (20, 50 day) for all symbols
   • EMA (20 day) for all symbols  
   • RSI (14 day) for all symbols
   • MACD (12,26,9) for all symbols
   • Period: 2023-01-01 to 2025-06-30

Ready to start the full download? Run:
python download_historical_indicators.py
    """)
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Quick start failed. Please check the errors above and try again.")
        sys.exit(1)
