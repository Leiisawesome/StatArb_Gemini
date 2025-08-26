"""
Two-Layer Architecture Integration Adapter
==========================================

This adapter seamlessly integrates the optimized core engine with the existing
trade_engine + core_structure architecture while maintaining backwards compatibility
and providing performance improvements.

Key Features:
- Transparent integration with existing interfaces
- Progressive migration support  
- Performance monitoring and comparison
- Fallback to original implementation
- A/B testing capabilities

Author: Pro Quant Desk Trader
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Import optimized components
from .optimized_core_engine import OptimizedCoreEngine, create_optimized_engine
from .hot_path_optimizer import get_hot_path_optimizer
from .object_pooling import get_pool_manager
from .optimized_interfaces import get_interface_coordinator

# Import existing core components
from ...core_structure.unified_core_engine import UnifiedCoreEngine, StrategyConfig, TradingResult
from ..interfaces import StrategyInterface, PortfolioInterface, ExecutionInterface

logger = logging.getLogger(__name__)

class IntegrationMode(Enum):
    """Integration modes for progressive migration"""
    LEGACY_ONLY = "legacy_only"           # Use only legacy engine
    OPTIMIZED_ONLY = "optimized_only"     # Use only optimized engine
    A_B_TESTING = "a_b_testing"           # Split traffic between engines
    HYBRID = "hybrid"                     # Use optimized for simple, legacy for complex
    PERFORMANCE_COMPARISON = "perf_compare"  # Run both engines and compare

@dataclass
class IntegrationConfig:
    """Configuration for integration adapter"""
    mode: IntegrationMode = IntegrationMode.HYBRID
    optimized_engine_percentage: float = 50.0  # For A/B testing
    performance_threshold_ms: float = 1.0      # Switch threshold for hybrid mode
    enable_performance_logging: bool = True
    enable_result_validation: bool = True
    fallback_on_error: bool = True
    max_complexity_for_optimized: int = 10     # Complexity threshold for hybrid mode

@dataclass
class IntegrationMetrics:
    """Metrics for integration performance comparison"""
    legacy_cycles: int = 0
    optimized_cycles: int = 0
    legacy_avg_time_ms: float = 0.0
    optimized_avg_time_ms: float = 0.0
    performance_improvement_ratio: float = 0.0
    error_rate_legacy: float = 0.0
    error_rate_optimized: float = 0.0
    result_validation_failures: int = 0

class TwoLayerIntegrationAdapter:
    """
    Integration adapter that seamlessly connects optimized and legacy engines
    within the existing two-layer architecture.
    """
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
        
        # Engine instances
        self.legacy_engine: Optional[UnifiedCoreEngine] = None
        self.optimized_engine: Optional[OptimizedCoreEngine] = None
        
        # Performance tracking
        self.metrics = IntegrationMetrics()
        self.legacy_times: List[float] = []
        self.optimized_times: List[float] = []
        
        # State management
        self.is_initialized = False
        self.current_cycle = 0
        
        logger.info(f"TwoLayerIntegrationAdapter initialized with mode: {self.config.mode}")
    
    async def initialize(self, strategy_config: StrategyConfig) -> bool:
        """Initialize both engines based on integration mode"""
        try:
            # Always initialize legacy engine for fallback
            self.legacy_engine = UnifiedCoreEngine(strategy_config)
            await self.legacy_engine.initialize()
            
            # Initialize optimized engine if needed
            if self.config.mode in [
                IntegrationMode.OPTIMIZED_ONLY,
                IntegrationMode.A_B_TESTING,
                IntegrationMode.HYBRID,
                IntegrationMode.PERFORMANCE_COMPARISON
            ]:
                self.optimized_engine = await create_optimized_engine(strategy_config)
            
            self.is_initialized = True
            logger.info("TwoLayerIntegrationAdapter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TwoLayerIntegrationAdapter: {e}")
            return False
    
    def _calculate_strategy_complexity(self, strategy_config: StrategyConfig) -> int:
        """Calculate strategy complexity score for hybrid mode decisions"""
        complexity = 0
        
        # Add complexity based on strategy features
        if hasattr(strategy_config, 'multi_asset') and strategy_config.multi_asset:
            complexity += 3
        
        if hasattr(strategy_config, 'use_options') and strategy_config.use_options:
            complexity += 5
        
        if hasattr(strategy_config, 'dynamic_hedging') and strategy_config.dynamic_hedging:
            complexity += 4
        
        if hasattr(strategy_config, 'ml_models') and strategy_config.ml_models:
            complexity += 3
        
        if hasattr(strategy_config, 'alternative_data') and strategy_config.alternative_data:
            complexity += 2
        
        return complexity
    
    def _should_use_optimized_engine(
        self, 
        strategy_config: StrategyConfig, 
        market_data: Dict[str, Any]
    ) -> bool:
        """Decide which engine to use based on integration mode and conditions"""
        
        if self.config.mode == IntegrationMode.LEGACY_ONLY:
            return False
        
        if self.config.mode == IntegrationMode.OPTIMIZED_ONLY:
            return True
        
        if self.config.mode == IntegrationMode.A_B_TESTING:
            # Use cycle number to determine A/B split
            return (self.current_cycle % 100) < self.config.optimized_engine_percentage
        
        if self.config.mode == IntegrationMode.HYBRID:
            # Use optimized engine for simple strategies only
            complexity = self._calculate_strategy_complexity(strategy_config)
            return complexity <= self.config.max_complexity_for_optimized
        
        if self.config.mode == IntegrationMode.PERFORMANCE_COMPARISON:
            # Always use optimized engine, but also run legacy for comparison
            return True
        
        return False
    
    async def execute_trading_cycle(
        self, 
        market_data: Dict[str, Any], 
        strategy_config: StrategyConfig
    ) -> TradingResult:
        """Execute trading cycle using appropriate engine(s)"""
        
        if not self.is_initialized:
            raise RuntimeError("Adapter not initialized")
        
        self.current_cycle += 1
        use_optimized = self._should_use_optimized_engine(strategy_config, market_data)
        
        if self.config.mode == IntegrationMode.PERFORMANCE_COMPARISON:
            # Run both engines and compare results
            return await self._execute_performance_comparison(market_data, strategy_config)
        
        elif use_optimized and self.optimized_engine:
            try:
                # Use optimized engine
                start_time = time.perf_counter()
                result = await self.optimized_engine.execute_optimized_trading_cycle(
                    market_data, strategy_config
                )
                execution_time = (time.perf_counter() - start_time) * 1000
                
                self._update_optimized_metrics(execution_time, True)
                
                # Validate result if enabled
                if self.config.enable_result_validation:
                    is_valid = await self._validate_result(result, strategy_config)
                    if not is_valid and self.config.fallback_on_error:
                        logger.warning("Optimized result validation failed, falling back to legacy")
                        return await self._execute_legacy_engine(market_data, strategy_config)
                
                return result
                
            except Exception as e:
                logger.error(f"Error in optimized engine: {e}")
                self._update_optimized_metrics(0, False)
                
                if self.config.fallback_on_error:
                    logger.info("Falling back to legacy engine")
                    return await self._execute_legacy_engine(market_data, strategy_config)
                else:
                    raise
        
        else:
            # Use legacy engine
            return await self._execute_legacy_engine(market_data, strategy_config)
    
    async def _execute_legacy_engine(
        self, 
        market_data: Dict[str, Any], 
        strategy_config: StrategyConfig
    ) -> TradingResult:
        """Execute using legacy engine"""
        start_time = time.perf_counter()
        
        try:
            # Convert to legacy engine format if needed
            result = await self.legacy_engine.execute_trading_cycle(market_data, strategy_config)
            execution_time = (time.perf_counter() - start_time) * 1000
            
            self._update_legacy_metrics(execution_time, True)
            return result
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            self._update_legacy_metrics(execution_time, False)
            raise
    
    async def _execute_performance_comparison(
        self, 
        market_data: Dict[str, Any], 
        strategy_config: StrategyConfig
    ) -> TradingResult:
        """Execute both engines and compare performance"""
        
        # Execute both engines in parallel
        legacy_task = asyncio.create_task(
            self._execute_legacy_engine(market_data, strategy_config)
        )
        
        optimized_start = time.perf_counter()
        optimized_result = await self.optimized_engine.execute_optimized_trading_cycle(
            market_data, strategy_config
        )
        optimized_time = (time.perf_counter() - optimized_start) * 1000
        
        # Wait for legacy result
        legacy_result = await legacy_task
        
        # Compare results
        await self._compare_results(legacy_result, optimized_result)
        
        # Log performance comparison
        if self.config.enable_performance_logging:
            improvement = ((legacy_result.processing_time_ms - optimized_time) / 
                          legacy_result.processing_time_ms * 100)
            
            logger.info(
                f"Performance comparison - Legacy: {legacy_result.processing_time_ms:.2f}ms, "
                f"Optimized: {optimized_time:.2f}ms, Improvement: {improvement:.1f}%"
            )
        
        # Return optimized result (assuming it's primary)
        return optimized_result
    
    async def _validate_result(self, result: TradingResult, strategy_config: StrategyConfig) -> bool:
        """Validate trading result for correctness"""
        try:
            # Basic validation checks
            if not result.success:
                return False
            
            # Check for reasonable values
            if hasattr(result, 'signals') and result.signals:
                for signal in result.signals:
                    if hasattr(signal, 'strength') and abs(signal.strength) > 10:  # Reasonable signal strength
                        return False
            
            # Check processing time is reasonable
            if result.processing_time_ms > 10000:  # 10 seconds max
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating result: {e}")
            return False
    
    async def _compare_results(self, legacy_result: TradingResult, optimized_result: TradingResult):
        """Compare results from both engines for validation"""
        try:
            # Compare signal counts
            legacy_signal_count = len(legacy_result.signals) if legacy_result.signals else 0
            optimized_signal_count = len(optimized_result.signals) if optimized_result.signals else 0
            
            if abs(legacy_signal_count - optimized_signal_count) > 1:
                logger.warning(
                    f"Signal count difference: Legacy={legacy_signal_count}, "
                    f"Optimized={optimized_signal_count}"
                )
                self.metrics.result_validation_failures += 1
            
            # Compare performance metrics
            if (hasattr(legacy_result, 'performance_metrics') and 
                hasattr(optimized_result, 'performance_metrics')):
                # Add specific metric comparisons here
                pass
            
        except Exception as e:
            logger.error(f"Error comparing results: {e}")
    
    def _update_legacy_metrics(self, execution_time_ms: float, success: bool):
        """Update legacy engine metrics"""
        self.metrics.legacy_cycles += 1
        self.legacy_times.append(execution_time_ms)
        
        if len(self.legacy_times) > 1000:
            self.legacy_times = self.legacy_times[-1000:]
        
        self.metrics.legacy_avg_time_ms = sum(self.legacy_times) / len(self.legacy_times)
        
        if not success:
            self.metrics.error_rate_legacy = (
                (self.metrics.error_rate_legacy * (self.metrics.legacy_cycles - 1) + 1) / 
                self.metrics.legacy_cycles
            )
    
    def _update_optimized_metrics(self, execution_time_ms: float, success: bool):
        """Update optimized engine metrics"""
        self.metrics.optimized_cycles += 1
        self.optimized_times.append(execution_time_ms)
        
        if len(self.optimized_times) > 1000:
            self.optimized_times = self.optimized_times[-1000:]
        
        self.metrics.optimized_avg_time_ms = sum(self.optimized_times) / len(self.optimized_times)
        
        if not success:
            self.metrics.error_rate_optimized = (
                (self.metrics.error_rate_optimized * (self.metrics.optimized_cycles - 1) + 1) / 
                self.metrics.optimized_cycles
            )
        
        # Update performance improvement ratio
        if self.metrics.legacy_avg_time_ms > 0:
            self.metrics.performance_improvement_ratio = (
                self.metrics.legacy_avg_time_ms / self.metrics.optimized_avg_time_ms
            )
    
    def get_integration_metrics(self) -> IntegrationMetrics:
        """Get comprehensive integration metrics"""
        return self.metrics
    
    def get_performance_report(self) -> str:
        """Generate comprehensive performance comparison report"""
        report = []
        report.append("=" * 80)
        report.append("TWO-LAYER ARCHITECTURE INTEGRATION REPORT")
        report.append("=" * 80)
        
        # Configuration
        report.append("INTEGRATION CONFIGURATION")
        report.append("-" * 40)
        report.append(f"Mode: {self.config.mode.value}")
        report.append(f"Optimized Engine %: {self.config.optimized_engine_percentage}")
        report.append(f"Performance Threshold: {self.config.performance_threshold_ms}ms")
        report.append(f"Max Complexity for Optimized: {self.config.max_complexity_for_optimized}")
        report.append("")
        
        # Performance comparison
        report.append("PERFORMANCE COMPARISON")
        report.append("-" * 40)
        report.append(f"Legacy Engine Cycles: {self.metrics.legacy_cycles}")
        report.append(f"Legacy Avg Time: {self.metrics.legacy_avg_time_ms:.2f}ms")
        report.append(f"Legacy Error Rate: {self.metrics.error_rate_legacy:.2%}")
        report.append("")
        
        report.append(f"Optimized Engine Cycles: {self.metrics.optimized_cycles}")
        report.append(f"Optimized Avg Time: {self.metrics.optimized_avg_time_ms:.2f}ms")
        report.append(f"Optimized Error Rate: {self.metrics.error_rate_optimized:.2%}")
        report.append("")
        
        if self.metrics.performance_improvement_ratio > 0:
            improvement = (self.metrics.performance_improvement_ratio - 1) * 100
            report.append(f"Performance Improvement: {improvement:.1f}%")
            report.append(f"Speed Multiplier: {self.metrics.performance_improvement_ratio:.2f}x")
        
        report.append(f"Result Validation Failures: {self.metrics.result_validation_failures}")
        report.append("")
        
        # Engine-specific reports
        if self.optimized_engine:
            report.append("OPTIMIZED ENGINE DETAILED REPORT")
            report.append("-" * 40)
            optimized_report = self.optimized_engine.get_comprehensive_performance_report()
            report.append(optimized_report)
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    async def switch_integration_mode(self, new_mode: IntegrationMode):
        """Dynamically switch integration mode"""
        logger.info(f"Switching integration mode from {self.config.mode} to {new_mode}")
        
        old_mode = self.config.mode
        self.config.mode = new_mode
        
        # Initialize optimized engine if switching to mode that requires it
        if (new_mode in [IntegrationMode.OPTIMIZED_ONLY, IntegrationMode.A_B_TESTING, 
                        IntegrationMode.HYBRID, IntegrationMode.PERFORMANCE_COMPARISON] and 
            not self.optimized_engine):
            
            # Need to recreate with proper strategy config
            logger.warning("Optimized engine not available for new mode - may need reinitialization")
    
    async def shutdown(self):
        """Shutdown both engines"""
        logger.info("Shutting down TwoLayerIntegrationAdapter")
        
        try:
            if self.legacy_engine:
                await self.legacy_engine.shutdown()
            
            if self.optimized_engine:
                await self.optimized_engine.shutdown()
            
            logger.info("TwoLayerIntegrationAdapter shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during adapter shutdown: {e}")

# Factory functions
async def create_integration_adapter(
    strategy_config: StrategyConfig,
    integration_config: IntegrationConfig = None
) -> TwoLayerIntegrationAdapter:
    """Create and initialize integration adapter"""
    adapter = TwoLayerIntegrationAdapter(integration_config)
    
    if await adapter.initialize(strategy_config):
        logger.info("Integration adapter created successfully")
        return adapter
    else:
        raise RuntimeError("Failed to initialize integration adapter")

# Convenience wrapper for existing code
class OptimizedTradingEngine:
    """
    Drop-in replacement for existing trading engine that provides optimizations
    while maintaining full backwards compatibility.
    """
    
    def __init__(self, strategy_config: StrategyConfig, integration_config: IntegrationConfig = None):
        self.strategy_config = strategy_config
        self.integration_config = integration_config or IntegrationConfig(mode=IntegrationMode.HYBRID)
        self.adapter: Optional[TwoLayerIntegrationAdapter] = None
    
    async def initialize(self):
        """Initialize the optimized trading engine"""
        self.adapter = await create_integration_adapter(
            self.strategy_config, 
            self.integration_config
        )
    
    async def execute_trading_cycle(self, market_data: Dict[str, Any]) -> TradingResult:
        """Execute trading cycle with optimizations"""
        if not self.adapter:
            raise RuntimeError("Engine not initialized")
        
        return await self.adapter.execute_trading_cycle(market_data, self.strategy_config)
    
    def get_performance_report(self) -> str:
        """Get performance report"""
        if not self.adapter:
            return "Engine not initialized"
        
        return self.adapter.get_performance_report()
    
    async def shutdown(self):
        """Shutdown the engine"""
        if self.adapter:
            await self.adapter.shutdown()
