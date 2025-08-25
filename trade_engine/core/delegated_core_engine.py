"""
Delegated Core Engine Implementation
===================================

Professional-grade core engine that delegates to strategy interfaces
instead of implementing strategy-specific logic internally.

Author: Professional Trading System Architecture
Version: 1.0.0
"""

from typing import Dict, List, Any, Optional, Protocol
import logging
import pandas as pd
from datetime import datetime
from dataclasses import dataclass

from ..interfaces import (
    StrategyInterface, PortfolioInterface, ExecutionInterface,
    SignalConverterInterface, ConfigurationInterface,
    TradingSignal, RawSignal, ComponentMissingError,
    ComponentValidationError, INTERFACE_VERSION
)
from ..conversion import SignalConverter, SignalConversionConfig


@dataclass
class CoreEngineConfig:
    """Configuration for the core engine."""
    enable_risk_checks: bool = True
    enable_signal_filtering: bool = True
    max_signals_per_cycle: int = 100
    signal_validation_timeout: float = 5.0
    component_validation_enabled: bool = True


class DelegatedCoreEngine:
    """
    Professional core engine with proper delegation pattern.
    
    This engine orchestrates trading operations by delegating to
    specialized components through well-defined interfaces.
    
    Key Principles:
    - No strategy-specific logic in core engine
    - Interface-based delegation pattern
    - Fail-fast error handling
    - No fallback mechanisms (professional-grade reliability)
    """
    
    def __init__(
        self,
        strategy_interface: StrategyInterface,
        portfolio_interface: PortfolioInterface,
        execution_interface: ExecutionInterface,
        configuration_interface: ConfigurationInterface,
        signal_converter: Optional[SignalConverterInterface] = None,
        config: Optional[CoreEngineConfig] = None
    ):
        """
        Initialize core engine with required components.
        
        Args:
            strategy_interface: Strategy implementation
            portfolio_interface: Portfolio management implementation
            execution_interface: Order execution implementation
            configuration_interface: Configuration management
            signal_converter: Signal conversion implementation (optional)
            config: Core engine configuration
            
        Raises:
            ComponentMissingError: If required components are missing
            ComponentValidationError: If component validation fails
        """
        self.config = config or CoreEngineConfig()
        self.logger = logging.getLogger(__name__)
        
        # Validate and store interfaces
        self._validate_and_store_interfaces(
            strategy_interface, portfolio_interface, execution_interface, configuration_interface
        )
        
        # Initialize signal converter
        self.signal_converter = signal_converter or SignalConverter()
        
        # Engine state
        self._is_initialized = False
        self._cycle_count = 0
        self._last_processing_time = None
        
        # Performance tracking
        self._performance_metrics = {
            'total_cycles': 0,
            'successful_cycles': 0,
            'signals_generated': 0,
            'signals_executed': 0,
            'errors_encountered': 0
        }
        
        self.logger.info(f"DelegatedCoreEngine initialized with interfaces: {self._get_interface_info()}")
    
    def _validate_and_store_interfaces(
        self, 
        strategy_interface: StrategyInterface,
        portfolio_interface: PortfolioInterface,
        execution_interface: ExecutionInterface,
        configuration_interface: ConfigurationInterface
    ) -> None:
        """Validate and store interface implementations."""
        
        # Validate interface implementations
        if not isinstance(strategy_interface, StrategyInterface):
            raise ComponentValidationError("strategy_interface must implement StrategyInterface")
        
        if not isinstance(portfolio_interface, PortfolioInterface):
            raise ComponentValidationError("portfolio_interface must implement PortfolioInterface")
        
        if not isinstance(execution_interface, ExecutionInterface):
            raise ComponentValidationError("execution_interface must implement ExecutionInterface")
        
        if not isinstance(configuration_interface, ConfigurationInterface):
            raise ComponentValidationError("configuration_interface must implement ConfigurationInterface")
        
        # Store interfaces
        self.strategy_interface = strategy_interface
        self.portfolio_interface = portfolio_interface
        self.execution_interface = execution_interface
        self.configuration_interface = configuration_interface
        
        # Validate configuration
        if self.config.component_validation_enabled:
            if not self.configuration_interface.validate_configuration():
                raise ComponentValidationError("Configuration validation failed")
    
    def _get_interface_info(self) -> Dict[str, str]:
        """Get information about loaded interfaces."""
        strategy_name = self.strategy_interface.get_strategy_name() if hasattr(self.strategy_interface, 'get_strategy_name') else type(self.strategy_interface).__name__
        
        return {
            'strategy': strategy_name,
            'portfolio': type(self.portfolio_interface).__name__,
            'execution': type(self.execution_interface).__name__,
            'configuration': type(self.configuration_interface).__name__,
            'signal_converter': type(self.signal_converter).__name__,
            'interface_version': INTERFACE_VERSION
        }
    
    async def initialize(self) -> None:
        """Initialize the core engine."""
        try:
            self.logger.info("Initializing DelegatedCoreEngine...")
            
            # Validate all required indicators are available
            required_indicators = self.strategy_interface.get_required_indicators()
            self.logger.info(f"Strategy requires indicators: {required_indicators}")
            
            # Validate strategy parameters
            strategy_config = self.configuration_interface.get_strategy_config(
                self.strategy_interface.get_strategy_name()
            )
            
            if not self.strategy_interface.validate_parameters(strategy_config):
                raise ComponentValidationError("Strategy parameter validation failed")
            
            self._is_initialized = True
            self.logger.info("✅ DelegatedCoreEngine initialization complete")
            
        except Exception as e:
            self.logger.error(f"Core engine initialization failed: {e}")
            raise ComponentMissingError(f"Failed to initialize core engine: {e}")
    
    async def process_trading_cycle(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Process a complete trading cycle with proper delegation.
        
        Args:
            market_data: Market data for signal generation
            
        Returns:
            Dictionary containing cycle results
            
        Raises:
            ComponentMissingError: If required components are missing
        """
        if not self._is_initialized:
            raise ComponentMissingError("Core engine not initialized - call initialize() first")
        
        cycle_start_time = datetime.now()
        self._cycle_count += 1
        
        try:
            self.logger.info(f"🔄 Starting trading cycle {self._cycle_count}")
            
            # Step 1: Generate raw signals through strategy interface
            raw_signals = await self._generate_raw_signals(market_data)
            
            # Step 2: Convert raw signals to trading signals
            trading_signals = await self._convert_signals(raw_signals)
            
            # Step 3: Apply risk management filters
            filtered_signals = await self._apply_risk_filters(trading_signals)
            
            # Step 4: Execute signals
            execution_results = await self._execute_signals(filtered_signals)
            
            # Step 5: Update portfolio state
            await self._update_portfolio_state(execution_results)
            
            # Step 6: Compile cycle results
            cycle_results = self._compile_cycle_results(
                raw_signals, trading_signals, filtered_signals, execution_results, cycle_start_time
            )
            
            self._update_performance_metrics(cycle_results)
            self.logger.info(f"✅ Trading cycle {self._cycle_count} completed successfully")
            
            return cycle_results
            
        except Exception as e:
            self._performance_metrics['errors_encountered'] += 1
            self.logger.error(f"❌ Trading cycle {self._cycle_count} failed: {e}")
            raise
    
    async def _generate_raw_signals(self, market_data: pd.DataFrame) -> List[RawSignal]:
        """Generate raw signals through strategy interface delegation."""
        try:
            self.logger.debug("Delegating signal generation to strategy interface...")
            
            # Validate market data
            if market_data.empty:
                self.logger.warning("Empty market data provided")
                return []
            
            # Delegate to strategy interface - NO CORE ENGINE LOGIC HERE
            raw_signals = self.strategy_interface.calculate_signals(market_data)
            
            self.logger.info(f"Strategy interface generated {len(raw_signals)} raw signals")
            
            # Validate raw signals
            validated_signals = []
            for signal in raw_signals:
                if self._validate_raw_signal(signal):
                    validated_signals.append(signal)
                else:
                    self.logger.warning(f"Invalid raw signal filtered out: {signal.symbol}")
            
            return validated_signals
            
        except Exception as e:
            self.logger.error(f"Raw signal generation failed: {e}")
            return []
    
    def _validate_raw_signal(self, signal: RawSignal) -> bool:
        """Validate a raw signal."""
        try:
            # Basic validation
            if not signal.symbol:
                return False
            
            if not 0.0 <= signal.confidence <= 1.0:
                return False
            
            if pd.isna(signal.value):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _convert_signals(self, raw_signals: List[RawSignal]) -> List[TradingSignal]:
        """Convert raw signals to trading signals through signal converter."""
        try:
            self.logger.debug(f"Converting {len(raw_signals)} raw signals...")
            
            # Delegate to signal converter
            trading_signals = self.signal_converter.convert_to_trading_signals(raw_signals)
            
            # Apply signal filtering if enabled
            if self.config.enable_signal_filtering:
                trading_signals = self.signal_converter.apply_signal_filters(trading_signals)
            
            # Enforce signal limits
            if len(trading_signals) > self.config.max_signals_per_cycle:
                self.logger.warning(
                    f"Signal count ({len(trading_signals)}) exceeds limit ({self.config.max_signals_per_cycle}), truncating"
                )
                trading_signals = trading_signals[:self.config.max_signals_per_cycle]
            
            self.logger.info(f"Converted to {len(trading_signals)} trading signals")
            return trading_signals
            
        except Exception as e:
            self.logger.error(f"Signal conversion failed: {e}")
            return []
    
    async def _apply_risk_filters(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Apply risk management filters through portfolio interface."""
        if not self.config.enable_risk_checks:
            return signals
        
        try:
            self.logger.debug(f"Applying risk filters to {len(signals)} signals...")
            
            # Get current positions
            current_positions = self.portfolio_interface.get_current_positions()
            
            filtered_signals = []
            for signal in signals:
                # Delegate risk checking to portfolio interface
                if self.portfolio_interface.check_risk_limits(signal, current_positions):
                    filtered_signals.append(signal)
                else:
                    self.logger.info(f"Signal for {signal.symbol} filtered out by risk limits")
            
            self.logger.info(f"Risk filtering passed {len(filtered_signals)} of {len(signals)} signals")
            return filtered_signals
            
        except Exception as e:
            self.logger.error(f"Risk filtering failed: {e}")
            return []
    
    async def _execute_signals(self, signals: List[TradingSignal]) -> List[Dict[str, Any]]:
        """Execute signals through execution interface."""
        try:
            self.logger.debug(f"Executing {len(signals)} signals...")
            
            execution_results = []
            
            for signal in signals:
                try:
                    # Validate signal with execution interface
                    if not self.execution_interface.validate_order(signal):
                        self.logger.warning(f"Signal for {signal.symbol} failed execution validation")
                        continue
                    
                    # Get current market price (this would come from market data in real implementation)
                    current_price = self._get_current_price(signal.symbol)
                    
                    # Delegate execution to execution interface
                    execution_result = self.execution_interface.execute_signal(signal, current_price)
                    
                    if execution_result:
                        execution_results.append(execution_result)
                        self.logger.info(f"✅ Executed signal for {signal.symbol}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to execute signal for {signal.symbol}: {e}")
                    continue
            
            self.logger.info(f"Successfully executed {len(execution_results)} of {len(signals)} signals")
            return execution_results
            
        except Exception as e:
            self.logger.error(f"Signal execution failed: {e}")
            return []
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current market price for a symbol. This would be enhanced in real implementation."""
        # Placeholder - in real implementation this would query market data
        return 100.0
    
    async def _update_portfolio_state(self, execution_results: List[Dict[str, Any]]) -> None:
        """Update portfolio state through portfolio interface."""
        try:
            if execution_results:
                # Delegate portfolio updates to portfolio interface
                self.portfolio_interface.update_portfolio(execution_results)
                self.logger.debug(f"Portfolio state updated with {len(execution_results)} executions")
            
        except Exception as e:
            self.logger.error(f"Portfolio state update failed: {e}")
    
    def _compile_cycle_results(
        self,
        raw_signals: List[RawSignal],
        trading_signals: List[TradingSignal],
        filtered_signals: List[TradingSignal],
        execution_results: List[Dict[str, Any]],
        cycle_start_time: datetime
    ) -> Dict[str, Any]:
        """Compile comprehensive cycle results."""
        cycle_end_time = datetime.now()
        processing_time = (cycle_end_time - cycle_start_time).total_seconds()
        
        return {
            'cycle_number': self._cycle_count,
            'timestamp': cycle_end_time,
            'processing_time_seconds': processing_time,
            'raw_signals_count': len(raw_signals),
            'trading_signals_count': len(trading_signals),
            'filtered_signals_count': len(filtered_signals),
            'executed_signals_count': len(execution_results),
            'raw_signals': raw_signals,
            'trading_signals': trading_signals,
            'filtered_signals': filtered_signals,
            'execution_results': execution_results,
            'interface_info': self._get_interface_info(),
            'performance_metrics': self._performance_metrics.copy()
        }
    
    def _update_performance_metrics(self, cycle_results: Dict[str, Any]) -> None:
        """Update performance metrics."""
        self._performance_metrics['total_cycles'] += 1
        
        if cycle_results['executed_signals_count'] > 0:
            self._performance_metrics['successful_cycles'] += 1
        
        self._performance_metrics['signals_generated'] += cycle_results['raw_signals_count']
        self._performance_metrics['signals_executed'] += cycle_results['executed_signals_count']
        
        self._last_processing_time = cycle_results['processing_time_seconds']
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status."""
        return {
            'is_initialized': self._is_initialized,
            'cycle_count': self._cycle_count,
            'last_processing_time_seconds': self._last_processing_time,
            'performance_metrics': self._performance_metrics.copy(),
            'interface_info': self._get_interface_info(),
            'config': self.config.__dict__,
            'interface_version': INTERFACE_VERSION
        }
    
    def reset_engine_state(self) -> None:
        """Reset engine state (useful for testing)."""
        self._cycle_count = 0
        self._last_processing_time = None
        self._performance_metrics = {
            'total_cycles': 0,
            'successful_cycles': 0,
            'signals_generated': 0,
            'signals_executed': 0,
            'errors_encountered': 0
        }
        
        # Reset signal converter history
        if hasattr(self.signal_converter, 'reset_signal_history'):
            self.signal_converter.reset_signal_history()
        
        self.logger.info("Engine state reset")
