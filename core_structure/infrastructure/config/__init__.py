"""Unified Configuration Management System"""

from .unified_config_manager import (
    UnifiedConfigManager,
    UnifiedConfig,
    StrategyConfig,
    TrainingConfig,
    TradingConfig,
    DatabaseConfig,
    PortfolioRiskConfig,
    LoggingConfig,
    Environment
)

# Legacy exports for backward compatibility
from .risk_config import RiskConfig as EnterpriseRiskConfig
# Note: RiskConfig renamed to PortfolioRiskConfig in unified_config_manager
RiskConfig = PortfolioRiskConfig  # Backward compatibility alias
# ConfigManager and EnhancedConfigManager have been consolidated into UnifiedConfigManager

__all__ = [
    'UnifiedConfigManager',
    'UnifiedConfig', 
    'StrategyConfig',
    'TrainingConfig',
    'TradingConfig',
    'DatabaseConfig',
    'RiskConfig',
    'LoggingConfig',
    'Environment'
] 