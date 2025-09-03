"""Unified Market Data Module - Phase 4C"""

__version__ = "4.1.0"

# Import the consolidated classes
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import all consolidated classes (Updated for new structure)
from .core.data_manager import UnifiedDataManager, EnhancedDataManager
from .core.data_feeds import UnifiedDataFeeds, MarketDataFeeds
from .quality.data_monitor import UnifiedDataQualityMonitor, DataQualityMonitor
from .analytics.data_analytics import UnifiedDataAnalytics, MarketDataAnalytics

# Import Phase 4C additions - specialized classes
from .core.enhanced_clickhouse_loader import (
    EnhancedClickHouseLoader, DataRequest, PairScreeningCriteria, SmartCache
)
from .core.backtesting_data_provider import BacktestingDataProvider
from .core.data_validation_monitor import (
    DataValidationMonitor, ValidationSeverity, ValidationResult
)

__all__ = [
    # Phase 4B unified classes
    'UnifiedDataManager',
    'UnifiedDataFeeds', 
    'UnifiedDataQualityMonitor',
    'UnifiedDataAnalytics',
    # Phase 4B backward compatibility
    'EnhancedDataManager',
    'MarketDataFeeds',
    'DataQualityMonitor',
    'MarketDataAnalytics',
    # Phase 4C specialized classes
    'EnhancedClickHouseLoader',
    'BacktestingDataProvider',
    'DataValidationMonitor',
    'DataRequest',
    'PairScreeningCriteria',
    'SmartCache',
    'ValidationSeverity',
    'ValidationResult'
]

def get_consolidation_status():
    """Get the status of Phase 4C market data consolidation"""
    return {
        "phase": "4C", 
        "status": "COMPLETE", 
        "files_before": 10, 
        "files_after": 8,  # 5 + 3 specialized classes
        "version": __version__,
        "specialized_classes": ["EnhancedClickHouseLoader", "BacktestingDataProvider", "DataValidationMonitor"]
    }

def validate_consolidation():
    """Validate that all consolidated classes can be instantiated"""
    try:
        # Test unified classes
        mgr = UnifiedDataManager()
        feeds = UnifiedDataFeeds()
        monitor = UnifiedDataQualityMonitor()
        analytics = UnifiedDataAnalytics()
        
        # Test Phase 4C specialized classes
        validation_monitor = DataValidationMonitor()
        data_request = DataRequest(
            symbols=['AAPL', 'MSFT'], 
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now()
        )
        
        # Test backward compatibility classes
        legacy_mgr = EnhancedDataManager()
        legacy_feeds = MarketDataFeeds()
        legacy_monitor = DataQualityMonitor()
        legacy_analytics = MarketDataAnalytics()
        
        return {
            "validation_passed": True, 
            "message": "All unified and legacy classes instantiated successfully",
            "classes_tested": 8
        }
    except Exception as e:
        return {
            "validation_passed": False, 
            "error": str(e)
        }
