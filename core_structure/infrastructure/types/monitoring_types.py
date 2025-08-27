"""
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
    EMERGENCY = "emergency"  # Highest alert level from real_time_monitor

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
