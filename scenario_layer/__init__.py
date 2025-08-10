"""
Scenario Layer for StatArb Trading System
========================================

This layer provides different trading scenarios on top of the unified core engine:
- Historical Backtesting: Replay historical data for strategy validation
- Real-Time Simulation: Live simulation with real market data  
- Paper Trading: Virtual trading environment with order simulation
- Scenario Orchestration: Unified management and coordination

Author: Pro Quant Desk Trader
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Import scenario engines
try:
    from .backtesting import (
        HistoricalBacktestingEngine,
        BacktestConfig,
        BacktestResult,
        BacktestMetrics
    )
    
    from .simulation import (
        RealTimeSimulationEngine,
        SimulationConfig,
        SimulationResult
    )
    
    from .paper_trading import (
        PaperTradingSimulator,
        PaperTradingConfig,
        PaperTradingResult
    )
    
    from .orchestrator import (
        ScenarioOrchestrator,
        ScenarioConfig,
        ScenarioType,
        ScenarioResult
    )
    
    logger.info("Scenario layer loaded successfully")
    
except ImportError as e:
    logger.warning(f"Some scenario components not available: {e}")
    # Graceful degradation
    HistoricalBacktestingEngine = None
    RealTimeSimulationEngine = None
    PaperTradingSimulator = None
    ScenarioOrchestrator = None

# Module exports
__all__ = [
    # Historical Backtesting
    'HistoricalBacktestingEngine',
    'BacktestConfig',
    'BacktestResult', 
    'BacktestMetrics',
    
    # Real-Time Simulation
    'RealTimeSimulationEngine',
    'SimulationConfig',
    'SimulationResult',
    
    # Paper Trading
    'PaperTradingSimulator',
    'PaperTradingConfig',
    'PaperTradingResult',
    
    # Orchestration
    'ScenarioOrchestrator',
    'ScenarioConfig',
    'ScenarioType',
    'ScenarioResult'
]
