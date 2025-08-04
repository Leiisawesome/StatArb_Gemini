"""
Test environment configuration for integration tests.

This module provides configuration settings for different test environments and scenarios.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class TestEnvironmentConfig:
    """Configuration for test environment."""
    
    # Test execution settings
    test_timeout_seconds: int = 300
    max_concurrent_tests: int = 4
    retry_failed_tests: bool = True
    max_retries: int = 3
    
    # Data settings
    test_data_dir: str = "test_data"
    test_results_dir: str = "test_results"
    cleanup_test_data: bool = True
    
    # Performance settings
    performance_monitoring: bool = True
    memory_monitoring: bool = True
    cpu_monitoring: bool = True
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = "integration_tests.log"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Database settings
    test_database_url: str = "sqlite:///test_integration.db"
    cleanup_database: bool = True
    
    # Mock service settings
    mock_services_enabled: bool = True
    mock_delay_ms: int = 1
    mock_failure_rate: float = 0.0
    
    # Bridge settings
    bridge_cache_enabled: bool = True
    bridge_cache_ttl: int = 300
    bridge_performance_tracking: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    def save_to_file(self, filepath: str):
        """Save config to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'TestEnvironmentConfig':
        """Load config from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)


@dataclass
class PerformanceTargets:
    """Performance targets for integration tests."""
    
    # Latency targets (milliseconds)
    signal_generation_latency_ms: float = 100.0
    execution_latency_ms: float = 500.0
    data_processing_latency_ms: float = 50.0
    risk_validation_latency_ms: float = 200.0
    portfolio_update_latency_ms: float = 100.0
    
    # Throughput targets
    signals_per_minute: int = 1000
    executions_per_minute: int = 500
    data_points_per_second: int = 10000
    
    # Resource usage targets
    max_memory_usage_mb: float = 2048.0
    max_cpu_usage_percent: float = 80.0
    max_disk_usage_mb: float = 1024.0
    
    # Quality targets
    signal_accuracy_percent: float = 95.0
    execution_quality_percent: float = 99.0
    data_consistency_percent: float = 99.9
    error_rate_percent: float = 0.1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert targets to dictionary."""
        return asdict(self)


@dataclass
class TestScenarios:
    """Test scenarios configuration."""
    
    # Market scenarios
    normal_market: Dict[str, Any] = None
    high_volatility: Dict[str, Any] = None
    trending_market: Dict[str, Any] = None
    crisis_market: Dict[str, Any] = None
    
    # Load scenarios
    normal_load: Dict[str, Any] = None
    high_load: Dict[str, Any] = None
    stress_load: Dict[str, Any] = None
    
    # Error scenarios
    component_failure: Dict[str, Any] = None
    network_failure: Dict[str, Any] = None
    data_corruption: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.normal_market is None:
            self.normal_market = {
                'volatility': 0.15,
                'trend': 0.0,
                'correlation': 0.3,
                'volume_multiplier': 1.0
            }
        
        if self.high_volatility is None:
            self.high_volatility = {
                'volatility': 0.35,
                'trend': 0.0,
                'correlation': 0.5,
                'volume_multiplier': 1.5
            }
        
        if self.trending_market is None:
            self.trending_market = {
                'volatility': 0.20,
                'trend': 0.1,
                'correlation': 0.4,
                'volume_multiplier': 1.2
            }
        
        if self.crisis_market is None:
            self.crisis_market = {
                'volatility': 0.50,
                'trend': -0.2,
                'correlation': 0.8,
                'volume_multiplier': 2.0
            }
        
        if self.normal_load is None:
            self.normal_load = {
                'symbols': 10,
                'signals_per_minute': 100,
                'executions_per_minute': 50
            }
        
        if self.high_load is None:
            self.high_load = {
                'symbols': 50,
                'signals_per_minute': 500,
                'executions_per_minute': 250
            }
        
        if self.stress_load is None:
            self.stress_load = {
                'symbols': 100,
                'signals_per_minute': 1000,
                'executions_per_minute': 500
            }
        
        if self.component_failure is None:
            self.component_failure = {
                'failure_rate': 0.1,
                'recovery_time_seconds': 30,
                'affected_components': ['signal_generator', 'execution_engine']
            }
        
        if self.network_failure is None:
            self.network_failure = {
                'failure_rate': 0.05,
                'recovery_time_seconds': 60,
                'affected_services': ['market_data', 'order_execution']
            }
        
        if self.data_corruption is None:
            self.data_corruption = {
                'corruption_rate': 0.01,
                'affected_data_types': ['price_data', 'volume_data'],
                'detection_time_seconds': 5
            }


class TestEnvironmentManager:
    """Manages test environment configuration and setup."""
    
    def __init__(self, config: TestEnvironmentConfig):
        self.config = config
        self.performance_targets = PerformanceTargets()
        self.test_scenarios = TestScenarios()
        self._setup_directories()
    
    def _setup_directories(self):
        """Create necessary directories for testing."""
        directories = [
            self.config.test_data_dir,
            self.config.test_results_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_test_data_path(self, filename: str) -> str:
        """Get full path for test data file."""
        return os.path.join(self.config.test_data_dir, filename)
    
    def get_test_results_path(self, filename: str) -> str:
        """Get full path for test results file."""
        return os.path.join(self.config.test_results_dir, filename)
    
    def cleanup_test_artifacts(self):
        """Clean up test artifacts if enabled."""
        if not self.config.cleanup_test_data:
            return
        
        import shutil
        
        # Clean up test data directory
        if os.path.exists(self.config.test_data_dir):
            shutil.rmtree(self.config.test_data_dir)
        
        # Clean up test results directory
        if os.path.exists(self.config.test_results_dir):
            shutil.rmtree(self.config.test_results_dir)
        
        # Clean up database
        if self.config.cleanup_database and self.config.test_database_url.startswith('sqlite:///'):
            db_path = self.config.test_database_url.replace('sqlite:///', '')
            if os.path.exists(db_path):
                os.remove(db_path)
    
    def save_test_results(self, test_name: str, results: Dict[str, Any]):
        """Save test results to file."""
        results_file = self.get_test_results_path(f"{test_name}_results.json")
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    def load_test_results(self, test_name: str) -> Dict[str, Any]:
        """Load test results from file."""
        results_file = self.get_test_results_path(f"{test_name}_results.json")
        
        if not os.path.exists(results_file):
            return {}
        
        with open(results_file, 'r') as f:
            return json.load(f)
    
    def validate_performance_targets(self, metrics: Dict[str, float]) -> Dict[str, bool]:
        """Validate performance metrics against targets."""
        targets = self.performance_targets.to_dict()
        validation_results = {}
        
        for metric, target in targets.items():
            if metric in metrics:
                actual = metrics[metric]
                validation_results[metric] = actual <= target
            else:
                validation_results[metric] = False
        
        return validation_results


# Default configurations
DEFAULT_TEST_CONFIG = TestEnvironmentConfig()
DEFAULT_PERFORMANCE_TARGETS = PerformanceTargets()
DEFAULT_TEST_SCENARIOS = TestScenarios()


def get_test_environment_config(config_file: Optional[str] = None) -> TestEnvironmentManager:
    """Get test environment configuration."""
    if config_file and os.path.exists(config_file):
        config = TestEnvironmentConfig.load_from_file(config_file)
    else:
        config = DEFAULT_TEST_CONFIG
    
    return TestEnvironmentManager(config)


def create_test_config_file(filepath: str, config: TestEnvironmentConfig = None):
    """Create a test configuration file."""
    if config is None:
        config = DEFAULT_TEST_CONFIG
    
    config.save_to_file(filepath)
    print(f"Test configuration saved to: {filepath}")


if __name__ == "__main__":
    # Create default test configuration file
    create_test_config_file("test_environment_config.json")
    print("Default test environment configuration created.") 