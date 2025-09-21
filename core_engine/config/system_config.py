"""
System-wide configuration for core_engine
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class SystemConfig:
    """System-wide configuration"""
    # System settings
    max_components: int = 100
    health_check_interval: int = 30
    initialization_timeout: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Performance
    max_concurrent_operations: int = 50
    operation_timeout: int = 300
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SystemConfig':
        """Create config from dictionary"""
        return cls(**config_dict)
