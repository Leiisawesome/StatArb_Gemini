"""
Market Data Test Configuration
=============================

Configuration file for market data module tests including:
- Test database settings
- Mock API configurations
- Test data parameters
- Performance test thresholds
"""

import os
from pathlib import Path

# Test Database Configuration
TEST_DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 9000,
    'database': 'test_trading_data',
    'user': 'default',
    'password': '',
    'settings': {
        'max_execution_time': 60,
        'max_memory_usage': 1000000000
    }
}

# Mock API Configurations
MOCK_POLYGON_CONFIG = {
    'api_key': 'test_polygon_key_12345',
    'base_url': 'https://api.polygon.io',
    'timeout': 30,
    'max_retries': 3,
    'rate_limit': 5  # calls per minute for free tier
}

MOCK_ALPHAVANTAGE_CONFIG = {
    'api_key': 'test_alphavantage_key_abcdef',
    'base_url': 'https://www.alphavantage.co',
    'timeout': 30,
    'max_retries': 3,
    'rate_limit': 5  # calls per minute for free tier
}

# Test Data Configuration
TEST_DATA_CONFIG = {
    'sample_symbols': ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN'],
    'test_date_range': {
        'start': '2025-01-01',
        'end': '2025-01-31'
    },
    'sample_size': 1000,
    'price_range': {'min': 10.0, 'max': 3000.0},
    'volume_range': {'min': 100, 'max': 10000000}
}

# Market Data Manager Test Configuration
DATA_MANAGER_TEST_CONFIG = {
    'cache_ttl_seconds': 60,  # Shorter TTL for testing
    'real_time_enabled': True,
    'max_symbols_per_query': 10,  # Smaller batch for testing
    'default_lookback_days': 30,
    'enable_regime_detection': True,
    'enable_liquidity_analysis': True
}

# Feed Manager Test Configuration
FEED_MANAGER_TEST_CONFIG = {
    'max_feeds': 5,
    'default_timeout': 10,  # Shorter timeout for tests
    'enable_monitoring': True,
    'heartbeat_interval': 5,
    'reconnect_delay': 1,  # Quick reconnect for tests
    'max_reconnect_attempts': 3
}

# Performance Test Thresholds
PERFORMANCE_THRESHOLDS = {
    'max_query_time_seconds': 5.0,
    'max_data_processing_time_seconds': 2.0,
    'max_feed_latency_ms': 100.0,
    'min_throughput_ticks_per_second': 1000,
    'max_memory_usage_mb': 500
}

# Test File Paths
TEST_PATHS = {
    'test_data_dir': Path(__file__).parent / 'test_data',
    'sample_csv': Path(__file__).parent / 'test_data' / 'sample_market_data.csv',
    'sample_json': Path(__file__).parent / 'test_data' / 'sample_ticks.json',
    'config_templates': Path(__file__).parent / 'config_templates'
}

# Mock Data Templates
MOCK_POLYGON_TICK_RESPONSE = {
    "status": "OK",
    "request_id": "test_request_123",
    "results": [
        {
            "T": "AAPL",
            "v": 1000,
            "av": 1500,
            "t": 1640995200000,
            "n": 1,
            "c": [],
            "h": 150.5,
            "l": 149.5,
            "o": 150.0,
            "vw": 150.25
        }
    ]
}

MOCK_ALPHAVANTAGE_QUOTE_RESPONSE = {
    "Global Quote": {
        "01. symbol": "AAPL",
        "02. open": "150.00",
        "03. high": "151.00",
        "04. low": "149.00",
        "05. price": "150.50",
        "06. volume": "1000000",
        "07. latest trading day": "2025-01-01",
        "08. previous close": "149.50",
        "09. change": "1.00",
        "10. change percent": "0.67%"
    }
}

MOCK_HISTORICAL_DATA_RESPONSE = {
    "symbol": "AAPL",
    "data": [
        {
            "timestamp": "2025-01-01T09:30:00Z",
            "open": 150.0,
            "high": 151.0,
            "low": 149.5,
            "close": 150.5,
            "volume": 1000000
        },
        {
            "timestamp": "2025-01-01T09:31:00Z",
            "open": 150.5,
            "high": 151.5,
            "low": 150.0,
            "close": 151.0,
            "volume": 1200000
        }
    ]
}

# Error Response Templates
MOCK_ERROR_RESPONSES = {
    'unauthorized': {
        'status_code': 401,
        'response': {"error": "Unauthorized", "message": "Invalid API key"}
    },
    'rate_limit': {
        'status_code': 429,
        'response': {"error": "Rate limit exceeded", "message": "Too many requests"}
    },
    'server_error': {
        'status_code': 500,
        'response': {"error": "Internal server error"}
    },
    'not_found': {
        'status_code': 404,
        'response': {"error": "Not found", "message": "Symbol not found"}
    }
}

# Test Environment Settings
TEST_ENVIRONMENT = {
    'log_level': 'DEBUG',
    'enable_debug_logging': True,
    'capture_network_calls': True,
    'mock_external_apis': True,
    'use_test_database': True,
    'cleanup_after_tests': True
}

# Integration Test Configuration
INTEGRATION_TEST_CONFIG = {
    'real_api_tests': {
        'enabled': False,  # Set to True for real API testing
        'polygon_api_key': os.getenv('POLYGON_API_KEY'),
        'alphavantage_api_key': os.getenv('ALPHAVANTAGE_API_KEY')
    },
    'database_tests': {
        'enabled': True,
        'create_test_tables': True,
        'cleanup_tables': True
    },
    'performance_tests': {
        'enabled': True,
        'large_dataset_size': 100000,
        'concurrent_connections': 5
    }
}

# Fixtures Configuration
FIXTURE_CONFIG = {
    'sample_data_size': 100,
    'date_range_days': 30,
    'symbols_count': 5,
    'ticks_per_symbol': 1000,
    'randomize_data': True,
    'seed': 42  # For reproducible random data
}
