#!/usr/bin/env python3
"""
Critical Duplicate Consolidation Plan
====================================

Based on deep analysis, here are the most critical duplicates to consolidate:

PRIORITY 1 - ORDER TYPES (5 duplicates):
- OrderType: 5 implementations across execution and broker modules
- OrderSide: 3 implementations  
- OrderStatus: 3 implementations
- Order: 3 implementations

PRIORITY 2 - STRATEGY CONFIG (3 duplicates):
- StrategyConfig: 3 implementations across interfaces and config modules

PRIORITY 3 - MARKET REGIME (4 duplicates):
- MarketRegime: 4 implementations across data processing and signal generation

PRIORITY 4 - MONITORING CLASSES (2 duplicates each):
- DataQualityMonitor: 2 implementations
- PerformanceMetric: 2 implementations  
- AlertLevel: 2 implementations
- FeatureEngine: 2 implementations

EXECUTION PLAN:
1. Create canonical definitions in infrastructure/types/
2. Update all imports to use canonical versions
3. Remove duplicate implementations
4. Validate system still works
"""

import os
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def create_canonical_types():
    """Create canonical type definitions"""
    
    # Create types directory
    types_dir = Path("core_structure/infrastructure/types")
    types_dir.mkdir(exist_ok=True)
    
    # Create __init__.py
    init_content = '''"""
Canonical Type Definitions
=========================

Centralized location for all shared types to eliminate duplicates.
"""

from .order_types import OrderType, OrderSide, OrderStatus, Order
from .strategy_types import StrategyConfig
from .market_types import MarketRegime
from .monitoring_types import AlertLevel, PerformanceMetric

__all__ = [
    'OrderType', 'OrderSide', 'OrderStatus', 'Order',
    'StrategyConfig', 
    'MarketRegime',
    'AlertLevel', 'PerformanceMetric'
]
'''
    
    with open(types_dir / "__init__.py", "w") as f:
        f.write(init_content)
    
    # Create order_types.py
    order_types_content = '''"""
Canonical Order Type Definitions
===============================

Single source of truth for all order-related types.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

class OrderType(Enum):
    """Standard order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderSide(Enum):
    """Order side (buy/sell)"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order execution status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class Order:
    """Canonical order representation"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
'''
    
    with open(types_dir / "order_types.py", "w") as f:
        f.write(order_types_content)
    
    # Create strategy_types.py
    strategy_types_content = '''"""
Canonical Strategy Type Definitions
==================================
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class StrategyType(Enum):
    """Strategy types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"
    CUSTOM = "custom"

@dataclass
class StrategyConfig:
    """Canonical strategy configuration"""
    strategy_id: str
    strategy_type: StrategyType
    symbols: list
    parameters: Dict[str, Any]
    risk_params: Optional[Dict[str, Any]] = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.risk_params is None:
            self.risk_params = {}
'''
    
    with open(types_dir / "strategy_types.py", "w") as f:
        f.write(strategy_types_content)
    
    # Create market_types.py
    market_types_content = '''"""
Canonical Market Type Definitions
================================
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class MarketRegime(Enum):
    """Market regime types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"

@dataclass
class RegimeInfo:
    """Market regime information"""
    regime: MarketRegime
    confidence: float
    duration: Optional[int] = None
    volatility: Optional[float] = None
'''
    
    with open(types_dir / "market_types.py", "w") as f:
        f.write(market_types_content)
    
    # Create monitoring_types.py
    monitoring_types_content = '''"""
Canonical Monitoring Type Definitions
====================================
"""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class PerformanceMetric:
    """Performance metric data"""
    name: str
    value: float
    timestamp: datetime
    unit: Optional[str] = None
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
'''
    
    with open(types_dir / "monitoring_types.py", "w") as f:
        f.write(monitoring_types_content)
    
    logger.info("✅ Created canonical type definitions")

def main():
    logger.info("🔧 Creating Canonical Type Definitions")
    logger.info("=" * 50)
    
    create_canonical_types()
    
    logger.info("\n📋 NEXT STEPS:")
    logger.info("1. Update imports across codebase to use canonical types")
    logger.info("2. Remove duplicate implementations")
    logger.info("3. Test system functionality")
    logger.info("4. Validate all modules still work")

if __name__ == "__main__":
    main()
