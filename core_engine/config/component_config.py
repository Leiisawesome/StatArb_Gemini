"""
Component-specific configurations
"""
from dataclasses import dataclass
from typing import List

@dataclass
class DataConfig:
    """Data management configuration"""
    symbols: List[str] = None
    target_date: str = "2024-12-20"
    enable_caching: bool = True
    cache_ttl: int = 3600

@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_position_size: float = 0.10
    max_daily_var: float = 0.05
    auto_approval_threshold: float = 0.01
    elevated_review_threshold: float = 0.05

@dataclass
class ProcessingConfig:
    """Processing pipeline configuration"""
    signal_threshold: float = 0.6
    feature_normalization: str = "robust"
    enable_cross_sectional: bool = True
