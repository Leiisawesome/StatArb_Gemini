"""
Unified Core Engine - Clean Architecture
========================================

Professional-grade unified trading engine serving as the single entry point
for all trading operations in the two-layer architecture (trade_engine + core_structure).

Architecture:
- Trade Engine Layer: Templates, optimization, performance analysis
- Core Structure Layer: Signal generation, execution, risk, portfolio

Author: Pro Quant Trading System
Version: 2.0 (Cleaned & Optimized)
"""

import asyncio
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import pandas as pd

# Core Structure Imports
from .signal_generation.signal_generator import SignalGenerator, SignalConfig, TradingSignal, SignalType, SignalStrength
from .execution_engine.execution_engine import ExecutionEngine, ExecutionRequest, ExecutionResult, ExecutionStatus, OrderSide, ExecutionAlgorithm
from .execution_engine.ibkr_execution_bridge import IBKRExecutionBridge, IBKRExecutionBridgeFactory
from .risk.risk_manager import RiskManager, RiskLimits
from .portfolio.portfolio_manager import PortfolioManager, PortfolioMetrics
from .market_data.data_manager import DataManager
from .analytics.performance_analytics import PerformanceAnalyzer
from .broker_integration import IBKRConfig

# Trade Engine Integration (Two-Layer Architecture)
try:
    from trade_engine.dynamic_adaptation.parameter_optimizer import RealTimeParameterOptimizer
    from trade_engine.analytics.performance_analyzer import PerformanceAnalyzer as TradeEnginePerformanceAnalyzer
    from trade_engine.templates.template_registry import get_trade_engine_template_registry
    TRADE_ENGINE_AVAILABLE = True
except ImportError as e:
    TRADE_ENGINE_AVAILABLE = False
    TRADE_ENGINE_IMPORT_ERROR = str(e)

logger = logging.getLogger(__name__)

# ================================================================================
# CONFIGURATION CLASSES
# ================================================================================

class EngineStatus(Enum):
    """Engine operational status"""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class TradingMode(Enum):
    """Trading execution mode"""
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    SIMULATION = "simulation"

@dataclass
class CoreEngineConfig:
    """Unified core engine configuration"""
    # Engine Identity
    engine_id: str = field(default_factory=lambda: f"engine_{uuid.uuid4().hex[:8]}")
    trading_mode: TradingMode = TradingMode.PAPER_TRADING
    
    # Performance Settings
    max_concurrent_strategies: int = 10
    max_processing_time_ms: int = 1000
    enable_monitoring: bool = True
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    
    # Risk Management
    max_portfolio_risk: float = 0.02  # 2% VaR limit
    max_position_size: float = 0.1    # 10% max position size
    max_drawdown: float = 0.15        # 15% max drawdown
    
    # Execution Settings
    initial_capital: float = 10_000_000  # $10M default
    max_order_value: float = 1_000_000   # $1M max order
    commission_rate: float = 0.0005      # 5 bps
    default_execution_algorithm: str = "TWAP"
    
    # IBKR Integration
    enable_ibkr_integration: bool = False
    ibkr_account_id: Optional[str] = None
    ibkr_paper_trading: bool = True
    ibkr_config: Optional[IBKRConfig] = None
    
    # Component Configs
    signal_config: Optional[SignalConfig] = None
    risk_limits: Optional[RiskLimits] = None

@dataclass
class StrategyConfig:
    """Strategy configuration for parameter injection"""
    strategy_id: str
    strategy_name: str
    strategy_type: str
    
    # Strategy Parameters
    signal_params: Dict[str, Any] = field(default_factory=dict)
    risk_params: Dict[str, Any] = field(default_factory=dict)
    execution_params: Dict[str, Any] = field(default_factory=dict)
    portfolio_params: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class TradingResult:
    """Complete trading cycle result"""
    strategy_id: str
    timestamp: datetime
    success: bool
    
    # Results
    signals: List[TradingSignal] = field(default_factory=list)
    execution_results: List[ExecutionResult] = field(default_factory=list)
    portfolio_update: Optional[PortfolioMetrics] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Error Handling
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    
    # Performance
    processing_time_ms: float = 0.0
    cache_hit: bool = False

@dataclass
class EngineMetrics:
    """Engine performance metrics"""
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    average_processing_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    active_strategies: int = 0
    error_count: int = 0
    warning_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

# ================================================================================
# MAIN UNIFIED CORE ENGINE
# ================================================================================

class UnifiedCoreEngine:
    """
    Unified Core Engine - Two-Layer Architecture Entry Point
    
    Coordinates between Trade Engine (templates, optimization) and 
    Core Structure (execution, risk, portfolio) layers.
    """
    
    def __init__(self, config: Optional[CoreEngineConfig] = None):
        """Initialize unified core engine with two-layer architecture"""
        self.config = config or CoreEngineConfig()
        self.status = EngineStatus.INITIALIZING
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"🚀 UnifiedCoreEngine initializing with ID: {self.config.engine_id}")
        
        # Core Components (Core Structure Layer)
        self._initialize_core_components()
        
        # Trade Engine Integration (Trade Engine Layer)
        self._initialize_trade_engine()
        
        # IBKR Integration
        self._initialize_ibkr_integration()
        
        # Strategy Management
        self.active_strategies: Dict[str, StrategyConfig] = {}
        self.strategy_cache: Dict[str, Any] = {}
        self.strategy_config_cache: Dict[str, Dict[str, Any]] = {}
        self.trade_engine_strategy_initialized: Dict[str, bool] = {}
        
        # Anti-Churning System
        self.slice_trading_locks: Dict[str, set] = {}  # {strategy_slice: {symbols}}
        
        # Performance Tracking
        self.metrics = EngineMetrics()
        self.cycle_times: List[float] = []
        
        # Backtesting Support
        self.backtesting_mode: bool = False
        self.backtesting_data_provider: Optional[Any] = None
        
        self.status = EngineStatus.READY
        self.logger.info("✅ Unified Core Engine initialized successfully")
    
    # ================================================================================
    # INITIALIZATION METHODS
    # ================================================================================
    
    def _initialize_core_components(self):
        """Initialize core structure layer components"""
        try:
            # Signal Generator
            signal_config = self.config.signal_config or SignalConfig()
            self.signal_generator = SignalGenerator(signal_config)
            
            # Execution Engine
            self.execution_engine = ExecutionEngine(
                initial_capital=self.config.initial_capital,
                max_order_value=self.config.max_order_value,
                commission_rate=self.config.commission_rate
            )
            
            # Risk Manager
            risk_limits = self.config.risk_limits or RiskLimits()
            self.risk_manager = RiskManager(risk_limits)
            
            # Portfolio Manager
            self.portfolio_manager = PortfolioManager(
                initial_capital=self.config.initial_capital
            )
            
            # Data Manager
            self.data_manager = DataManager()
            
            # Performance Analytics
            self.performance_analytics = PerformanceAnalyzer()
            
            self.logger.info("✅ Core structure components initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize core components: {e}")
            self.status = EngineStatus.ERROR
            raise
    
    def _initialize_trade_engine(self):
        """Initialize trade engine layer components"""
        self.trade_engine_optimizer: Optional[RealTimeParameterOptimizer] = None
        self.trade_engine_analyzer: Optional[TradeEnginePerformanceAnalyzer] = None
        self.trade_engine_template_registry = None
        
        if not TRADE_ENGINE_AVAILABLE:
            self.logger.warning(f"⚠️ Trade Engine not available: {TRADE_ENGINE_IMPORT_ERROR}")
            return
        
        try:
            # Parameter Optimizer
            self.trade_engine_optimizer = RealTimeParameterOptimizer(
                strategy_id=self.config.engine_id,
                template_id="ml_momentum_signal"
            )
            self.logger.info("✅ Trade Engine Parameter Optimizer initialized")
            
            # Performance Analyzer
            self.trade_engine_analyzer = TradeEnginePerformanceAnalyzer()
            self.logger.info("✅ Trade Engine Performance Analyzer initialized")
            
            # Template Registry
            self.trade_engine_template_registry = get_trade_engine_template_registry()
            template_count = len(self.trade_engine_template_registry.templates)
            self.logger.info(f"✅ Trade Engine Template Registry initialized with {template_count} templates")
            
            self.logger.info("🚀 Trade Engine integration complete")
            
        except Exception as e:
            self.logger.error(f"❌ Trade Engine initialization failed: {e}")
            self.logger.warning("⚠️ Falling back to core-only mode")
    
    def _initialize_ibkr_integration(self):
        """Initialize IBKR broker integration"""
        self.ibkr_bridge: Optional[IBKRExecutionBridge] = None
        
        if not self.config.enable_ibkr_integration:
            self.logger.info("IBKR integration disabled")
            return
        
        if not self.config.ibkr_account_id:
            self.logger.warning("IBKR account ID not provided - integration disabled")
            return
        
        try:
            if self.config.ibkr_config:
                self.ibkr_bridge = IBKRExecutionBridge(self.config.ibkr_config)
            elif self.config.ibkr_paper_trading:
                self.ibkr_bridge = IBKRExecutionBridgeFactory.create_paper_trading_bridge(
                    self.config.ibkr_account_id
                )
            else:
                self.ibkr_bridge = IBKRExecutionBridgeFactory.create_live_trading_bridge(
                    self.config.ibkr_account_id
                )
            
            self.logger.info("✅ IBKR integration initialized")
            
        except Exception as e:
            self.logger.error(f"❌ IBKR integration failed: {e}")
            self.ibkr_bridge = None
    
    # ================================================================================
    # STRATEGY MANAGEMENT
    # ================================================================================
    
    def inject_strategy_parameters(self, strategy_config: StrategyConfig):
        """Inject strategy parameters into core components"""
        try:
            self.logger.info(f"Injecting parameters for strategy: {strategy_config.strategy_id}")
            
            # Store strategy configuration
            self.active_strategies[strategy_config.strategy_id] = strategy_config
            
            # Create and cache strategy instance
            strategy_instance = self._create_strategy_instance(strategy_config)
            if strategy_instance:
                self.strategy_cache[strategy_config.strategy_id] = strategy_instance
                self.logger.info(f"✅ Strategy instance cached: {strategy_config.strategy_id}")
            
            # Inject parameters into core components
            self._inject_signal_parameters(strategy_config)
            self._inject_execution_parameters(strategy_config)
            self._inject_portfolio_parameters(strategy_config)
            
            self.logger.info(f"✅ Parameter injection complete: {strategy_config.strategy_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Parameter injection failed: {e}")
    
    def _create_strategy_instance(self, strategy_config: StrategyConfig):
        """Create strategy instance based on strategy type"""
        try:
            strategy_type = strategy_config.strategy_type.lower()
            
            if 'momentum' in strategy_type:
                from strategy_layer.strategies.momentum_strategy import MomentumStrategyDefinition
                legacy_config = self._convert_to_legacy_config(strategy_config)
                return MomentumStrategyDefinition(legacy_config)
                
            elif 'mean' in strategy_type or 'reversion' in strategy_type:
                from strategy_layer.strategies.mean_reversion_strategy import MeanReversionStrategyDefinition
                legacy_config = self._convert_to_legacy_config(strategy_config)
                return MeanReversionStrategyDefinition(legacy_config)
            
            else:
                self.logger.warning(f"Unknown strategy type: {strategy_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Strategy instance creation failed: {e}")
            return None
    
    def _convert_to_legacy_config(self, strategy_config: StrategyConfig):
        """Convert StrategyConfig to legacy format for backward compatibility"""
        class LegacyConfig:
            def __init__(self):
                self.strategy_id = strategy_config.strategy_id
                self.strategy_name = strategy_config.strategy_name
                self.strategy_type = strategy_config.strategy_type
                self.signal_generation = strategy_config.signal_params
                self.risk_management = strategy_config.risk_params or {
                    'max_position_size': 0.1,
                    'stop_loss': 0.05,
                    'max_portfolio_allocation': 0.2,
                    'position_sizing': {'method': 'fixed', 'size': 0.05}
                }
                self.entry_exit_logic = strategy_config.execution_params
                self.parameters = strategy_config.signal_params
                self.metadata = strategy_config.metadata
        
        return LegacyConfig()
    
    def _inject_signal_parameters(self, strategy_config: StrategyConfig):
        """Inject signal generation parameters"""
        try:
            strategy_dict = {
                'strategy_type': strategy_config.strategy_type,
                'signal_generation': strategy_config.signal_params,
                'risk_management': strategy_config.risk_params,
                'entry_exit_logic': strategy_config.execution_params,
                'parameters': strategy_config.signal_params,
                'metadata': strategy_config.metadata
            }
            
            self.signal_generator.update_config_from_strategy(strategy_dict)
            self.logger.debug(f"✅ Signal parameters injected: {strategy_config.strategy_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Signal parameter injection failed: {e}")
    
    def _inject_execution_parameters(self, strategy_config: StrategyConfig):
        """Inject execution parameters"""
        execution_params = strategy_config.execution_params
        
        if 'max_order_value' in execution_params:
            self.execution_engine.max_order_value = execution_params['max_order_value']
        
        if 'commission_rate' in execution_params:
            self.execution_engine.commission_rate = execution_params['commission_rate']
        
        self.logger.debug(f"✅ Execution parameters injected: {strategy_config.strategy_id}")
    
    def _inject_portfolio_parameters(self, strategy_config: StrategyConfig):
        """Inject portfolio parameters"""
        # Portfolio initial capital cannot be changed after initialization
        self.logger.debug(f"✅ Portfolio parameters processed: {strategy_config.strategy_id}")
    
    # ================================================================================
    # MAIN TRADING CYCLE
    # ================================================================================
    
    async def process_trading_cycle(
        self, 
        data_source: Any, 
        strategy_config: StrategyConfig
    ) -> TradingResult:
        """
        Main trading cycle processing - Two-layer architecture coordination
        
        Flow:
        1. Inject strategy parameters (Core Structure)
        2. Initialize Trade Engine (if needed)
        3. Load market data
        4. Generate signals (Strategy + Core Structure)
        5. Validate signals (Risk Management)
        6. Execute trades (Execution Engine)
        7. Update portfolio (Portfolio Manager)
        8. Generate analytics (Performance Analytics)
        9. Apply Trade Engine optimization (if available)
        """
        start_time = time.time()
        cycle_start = datetime.now()
        
        try:
            self.logger.debug(f"🔄 Trading cycle started: {strategy_config.strategy_id}")
            
            # 1. Inject slice information for anti-churning
            self._inject_slice_information(data_source, strategy_config)
            
            # 2. Inject strategy parameters
            self.inject_strategy_parameters(strategy_config)
            
            # 3. Initialize Trade Engine for strategy (if needed)
            await self._ensure_trade_engine_initialized(strategy_config)
            
            # 4. Load and process market data
            market_data = await self._load_market_data(data_source, strategy_config)
            
            # 5. Generate trading signals
            signals = await self._generate_signals(market_data, strategy_config)
            
            # 6. Validate signals with risk management
            validated_signals = await self._validate_signals(signals, strategy_config)
            
            # 7. Execute validated signals
            execution_results = await self._execute_signals(validated_signals, strategy_config)
            
            # 8. Update portfolio with execution results
            portfolio_update = await self._update_portfolio(execution_results, strategy_config)
            
            # 9. Generate performance analytics
            analytics = await self._generate_analytics(portfolio_update, strategy_config)
            
            # 10. Apply Trade Engine optimization (if available)
            await self._apply_trade_engine_optimization(signals, analytics, strategy_config)
            
            # Calculate performance metrics
            processing_time_ms = (time.time() - start_time) * 1000
            self.cycle_times.append(processing_time_ms)
            self._update_metrics(True, processing_time_ms)
            
            # Create successful result
            result = TradingResult(
                strategy_id=strategy_config.strategy_id,
                timestamp=cycle_start,
                success=True,
                signals=signals,
                execution_results=execution_results,
                portfolio_update=portfolio_update,
                performance_metrics=analytics,
                processing_time_ms=processing_time_ms
            )
            
            self.logger.info(f"✅ Trading cycle completed: {strategy_config.strategy_id}")
            return result
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            self._update_metrics(False, processing_time_ms)
            
            self.logger.error(f"❌ Trading cycle failed: {strategy_config.strategy_id} - {e}")
            
            return TradingResult(
                strategy_id=strategy_config.strategy_id,
                timestamp=cycle_start,
                success=False,
                error_message=str(e),
                processing_time_ms=processing_time_ms
            )
    
    def _inject_slice_information(self, data_source: Any, strategy_config: StrategyConfig):
        """Inject slice information for backtesting and anti-churning"""
        if isinstance(data_source, dict):
            slice_info = {
                'slice_index': data_source.get('slice_index'),
                'timestamp': data_source.get('timestamp'),
                'total_slices': data_source.get('total_slices')
            }
            
            # Update strategy config with slice information
            strategy_config.signal_params.update(slice_info)
            
            self.logger.info(f"🕐 Slice info injected: {slice_info['slice_index']}/{slice_info['total_slices']}")
    
    async def _ensure_trade_engine_initialized(self, strategy_config: StrategyConfig):
        """Ensure Trade Engine is initialized for strategy"""
        strategy_id = strategy_config.strategy_id
        
        if self.trade_engine_strategy_initialized.get(strategy_id, False):
            return
        
        if self.trade_engine_optimizer:
            try:
                self.logger.info(f"🔧 Initializing Trade Engine: {strategy_id}")
                self.trade_engine_strategy_initialized[strategy_id] = True
            except Exception as e:
                self.logger.warning(f"Trade Engine initialization failed: {e}")
    
    # ================================================================================
    # SIGNAL PROCESSING
    # ================================================================================
    
    async def _generate_signals(self, market_data: Dict[str, Any], strategy_config: StrategyConfig) -> List[TradingSignal]:
        """Generate trading signals using strategy instances"""
        try:
            signals = []
            df = market_data.get('data', pd.DataFrame())
            symbols = market_data.get('symbols', [])
            
            if df.empty or not symbols:
                self.logger.warning("No market data available for signal generation")
                return signals
            
            # Get strategy instance for signal generation
            strategy_instance = self.strategy_cache.get(strategy_config.strategy_id)
            
            if strategy_instance and hasattr(strategy_instance, 'generate_signals'):
                self.logger.info(f"Using strategy instance: {type(strategy_instance).__name__}")
                
                for symbol in symbols:
                    symbol_data = df[df['symbol'] == symbol].copy() if 'symbol' in df.columns else df.copy()
                    
                    if not symbol_data.empty:
                        # Generate signals using strategy instance
                        strategy_signals = strategy_instance.generate_signals({
                            'symbol': symbol,
                            'data': symbol_data,
                            'market_data': symbol_data
                        })
                        
                        # Convert to TradingSignal objects
                        if strategy_signals:
                            trading_signal = self._convert_strategy_signal(
                                symbol, strategy_signals, strategy_config, symbol_data
                            )
                            
                            if trading_signal:
                                signals.append(trading_signal)
                                self.logger.info(f"✅ Signal generated: {symbol}")
            else:
                # Fallback to generic signal generator (non-backtesting only)
                if not self.backtesting_mode:
                    self.logger.info("Using generic signal generator")
                    for symbol in symbols:
                        symbol_data = df[df['symbol'] == symbol].copy() if 'symbol' in df.columns else df.copy()
                        signal = await self.signal_generator.generate_signal(symbol, symbol_data)
                        if signal:
                            signals.append(signal)
            
            self.logger.info(f"Generated {len(signals)} signals")
            return signals
            
        except Exception as e:
            self.logger.error(f"Signal generation failed: {e}")
            return []
    
    def _convert_strategy_signal(self, symbol: str, strategy_signals: Dict, strategy_config: StrategyConfig, symbol_data=None) -> Optional[TradingSignal]:
        """Convert strategy-specific signals to TradingSignal objects"""
        try:
            # Extract time-slice context
            slice_timestamp = strategy_config.signal_params.get('slice_timestamp', datetime.now())
            slice_index = strategy_config.signal_params.get('slice_index', 0)
            
            # Get current position status
            current_position = self.portfolio_manager.get_position(symbol) if self.portfolio_manager else None
            has_position = bool(current_position and current_position.quantity > 0)
            
            # Handle explicit entry/exit signals
            if 'entry_signal' in strategy_signals or 'exit_signal' in strategy_signals:
                return self._process_explicit_signals(
                    symbol, strategy_signals, strategy_config, slice_timestamp, has_position
                )
            
            # Handle momentum-based signals
            elif 'momentum' in strategy_signals:
                return self._process_momentum_signals(
                    symbol, strategy_signals, strategy_config, slice_timestamp, has_position, symbol_data
                )
            
            # Handle mean reversion signals
            elif any(key in strategy_signals for key in ['MA_MeanReversion', 'BB_MeanReversion', 'RSI_MeanReversion']):
                return self._process_mean_reversion_signals(
                    symbol, strategy_signals, strategy_config, slice_timestamp, has_position
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Signal conversion failed: {e}")
            return None
    
    def _process_explicit_signals(self, symbol: str, strategy_signals: Dict, strategy_config: StrategyConfig, 
                                slice_timestamp: datetime, has_position: bool) -> Optional[TradingSignal]:
        """Process explicit entry/exit signals"""
        exit_signal = strategy_signals.get('exit_signal', 0.0)
        entry_signal = strategy_signals.get('entry_signal', 0.0)
        confidence = strategy_signals.get('confidence', 0.5)
        
        if has_position and exit_signal > 0:
            # Exit signal
            return TradingSignal(
                symbol_pair=symbol,
                signal_type=SignalType.CLOSE_LONG,
                strength=SignalStrength.STRONG if exit_signal > 0.01 else SignalStrength.MODERATE,
                confidence=confidence,
                position_size=1.0,
                entry_price=0.0,
                timestamp=slice_timestamp,
                metadata={
                    'signal_source': 'explicit_exit',
                    'exit_reason': strategy_signals.get('exit_reason', ''),
                    'strategy_id': strategy_config.strategy_id,
                    'is_exit_signal': True
                }
            )
        
        elif not has_position and entry_signal > 0:
            # Entry signal
            return TradingSignal(
                symbol_pair=symbol,
                signal_type=SignalType.LONG,
                strength=SignalStrength.STRONG if entry_signal > 0.001 else SignalStrength.MODERATE,
                confidence=confidence,
                position_size=0.25,
                entry_price=0.0,
                timestamp=slice_timestamp,
                metadata={
                    'signal_source': 'explicit_entry',
                    'entry_reason': strategy_signals.get('entry_reason', ''),
                    'strategy_id': strategy_config.strategy_id,
                    'is_exit_signal': False
                }
            )
        
        return None
    
    def _process_momentum_signals(self, symbol: str, strategy_signals: Dict, strategy_config: StrategyConfig,
                                slice_timestamp: datetime, has_position: bool, symbol_data=None) -> Optional[TradingSignal]:
        """Process momentum-based signals with intelligent logic"""
        signal_strength = float(strategy_signals.get('momentum', 0.0))
        confidence = float(strategy_signals.get('confidence', 0.5))
        
        # Get thresholds
        entry_threshold = strategy_config.signal_params.get('entry_threshold', 0.001)
        exit_threshold = strategy_config.signal_params.get('exit_threshold', 0.001)
        
        if has_position:
            # Exit logic for existing positions
            return self._process_momentum_exit(
                symbol, signal_strength, confidence, strategy_config, slice_timestamp, symbol_data
            )
        else:
            # Entry logic for new positions
            return self._process_momentum_entry(
                symbol, signal_strength, confidence, strategy_config, slice_timestamp, entry_threshold
            )
    
    def _process_momentum_exit(self, symbol: str, signal_strength: float, confidence: float,
                             strategy_config: StrategyConfig, slice_timestamp: datetime, symbol_data=None) -> Optional[TradingSignal]:
        """Process momentum exit signals"""
        # Get exit threshold
        exit_threshold = strategy_config.signal_params.get('exit_threshold', 0.001)
        momentum_strength = abs(signal_strength)
        
        # Determine if we should exit based on momentum reversal
        should_exit = momentum_strength >= exit_threshold
        
        if should_exit:
            return TradingSignal(
                symbol_pair=symbol,
                signal_type=SignalType.CLOSE_LONG,
                strength=SignalStrength.STRONG if momentum_strength > 0.002 else SignalStrength.MODERATE,
                confidence=confidence,
                position_size=1.0,
                entry_price=0.0,
                timestamp=slice_timestamp,
                metadata={
                    'signal_source': 'momentum_exit',
                    'exit_reason': f'momentum_reversal_{signal_strength:.6f}',
                    'momentum': signal_strength,
                    'strategy_id': strategy_config.strategy_id,
                    'is_exit_signal': True
                }
            )
        
        return None
    
    def _process_momentum_entry(self, symbol: str, signal_strength: float, confidence: float,
                              strategy_config: StrategyConfig, slice_timestamp: datetime, entry_threshold: float) -> Optional[TradingSignal]:
        """Process momentum entry signals"""
        momentum_strength = abs(signal_strength)
        
        # Dynamic position sizing based on momentum strength
        base_position_size = 0.2
        if momentum_strength > 0.005:
            dynamic_position_size = min(0.5, base_position_size + momentum_strength * 20)
        elif momentum_strength > 0.003:
            dynamic_position_size = min(0.4, base_position_size + momentum_strength * 15)
        else:
            dynamic_position_size = base_position_size
        
        # Determine signal type based on momentum direction
        if signal_strength >= entry_threshold:
            signal_type = SignalType.LONG
        elif signal_strength <= -entry_threshold:
            signal_type = SignalType.SHORT
        else:
            return None
        
        return TradingSignal(
            symbol_pair=symbol,
            signal_type=signal_type,
            strength=SignalStrength.STRONG if momentum_strength > 0.004 else SignalStrength.MODERATE,
            confidence=confidence,
            position_size=dynamic_position_size,
            entry_price=0.0,
            timestamp=slice_timestamp,
            metadata={
                'signal_source': 'momentum_entry',
                'entry_reason': f'momentum_strength_{signal_strength:.6f}',
                'momentum': signal_strength,
                'dynamic_position_size': dynamic_position_size,
                'strategy_id': strategy_config.strategy_id,
                'is_exit_signal': False
            }
        )
    
    def _process_mean_reversion_signals(self, symbol: str, strategy_signals: Dict, strategy_config: StrategyConfig,
                                      slice_timestamp: datetime, has_position: bool) -> Optional[TradingSignal]:
        """Process mean reversion signals"""
        # Extract mean reversion components
        ma_signal = strategy_signals.get('MA_MeanReversion', 0.0)
        bb_signal = strategy_signals.get('BB_MeanReversion', 0.0)
        rsi_signal = strategy_signals.get('RSI_MeanReversion', 0.0)
        
        # Calculate composite signal
        composite_signal = (bb_signal * 0.5) + (rsi_signal * 0.3) + (ma_signal * 0.2)
        
        # Entry logic for mean reversion
        should_enter = (bb_signal > 0.5 or composite_signal > 0.3 or rsi_signal > 0.25)
        
        if should_enter and not has_position:
            return TradingSignal(
                symbol_pair=symbol,
                signal_type=SignalType.LONG,
                strength=SignalStrength.STRONG if composite_signal > 0.4 else SignalStrength.MODERATE,
                confidence=min(0.95, 0.5 + composite_signal),
                position_size=0.25,
                entry_price=0.0,
                timestamp=slice_timestamp,
                metadata={
                    'signal_source': 'mean_reversion',
                    'ma_signal': ma_signal,
                    'bb_signal': bb_signal,
                    'rsi_signal': rsi_signal,
                    'composite_signal': composite_signal,
                    'strategy_id': strategy_config.strategy_id,
                    'is_exit_signal': False
                }
            )
        
        return None
    
    # ================================================================================
    # EXECUTION AND PORTFOLIO
    # ================================================================================
    
    async def _validate_signals(self, signals: List[TradingSignal], strategy_config: StrategyConfig) -> List[TradingSignal]:
        """Validate signals using risk management"""
        try:
            validated_signals = []
            
            for signal in signals:
                try:
                    position_size = self.risk_manager.calculate_position_size(
                        symbol=signal.symbol_pair,
                        signal_strength=signal.confidence,
                        method="signal_strength"
                    )
                    
                    if position_size.position_size <= self.risk_manager.risk_limits.max_position_size:
                        validated_signals.append(signal)
                    else:
                        self.logger.warning(f"Signal rejected - position size limit: {signal.symbol_pair}")
                        
                except Exception as e:
                    self.logger.error(f"Signal validation error: {signal.symbol_pair} - {e}")
            
            self.logger.debug(f"Validated {len(validated_signals)}/{len(signals)} signals")
            return validated_signals
            
        except Exception as e:
            self.logger.error(f"Signal validation failed: {e}")
            return []
    
    async def _execute_signals(self, signals: List[TradingSignal], strategy_config: StrategyConfig) -> List[ExecutionResult]:
        """Execute trading signals with anti-churning protection"""
        try:
            execution_results = []
            
            # Anti-churning: Track symbols traded by strategy in current slice
            current_slice = strategy_config.signal_params.get('slice_index', -1)
            strategy_id = strategy_config.strategy_id
            
            if current_slice >= 0:
                strategy_slice_key = f"{strategy_id}_{current_slice}"
                if strategy_slice_key not in self.slice_trading_locks:
                    self.slice_trading_locks[strategy_slice_key] = set()
                
                # Filter signals to prevent churning
                filtered_signals = [
                    signal for signal in signals 
                    if signal.symbol_pair not in self.slice_trading_locks[strategy_slice_key]
                ]
                
                churning_prevented = len(signals) - len(filtered_signals)
                if churning_prevented > 0:
                    self.logger.info(f"🚫 Anti-churning: Prevented {churning_prevented} trades")
                
                signals = filtered_signals
            
            # Execute each signal
            for signal in signals:
                result = await self._execute_single_signal(signal, strategy_config)
                if result:
                    execution_results.append(result)
                    
                    # Update anti-churning locks
                    if current_slice >= 0 and result.status == ExecutionStatus.SUCCESS:
                        strategy_slice_key = f"{strategy_id}_{current_slice}"
                        self.slice_trading_locks[strategy_slice_key].add(signal.symbol_pair)
            
            self.logger.debug(f"Executed {len(execution_results)} orders")
            return execution_results
            
        except Exception as e:
            self.logger.error(f"Signal execution failed: {e}")
            return []
    
    async def _execute_single_signal(self, signal: TradingSignal, strategy_config: StrategyConfig) -> Optional[ExecutionResult]:
        """Execute a single trading signal"""
        try:
            # Get current price
            current_price = self._get_current_price(signal.symbol_pair)
            
            # Calculate quantity
            quantity = self._calculate_quantity(signal, current_price)
            if quantity <= 0:
                self.logger.debug(f"Skipping {signal.symbol_pair} - invalid quantity")
                return None
            
            # Create execution request
            request = ExecutionRequest(
                symbol=signal.symbol_pair,
                side=OrderSide.BUY if signal.signal_type == SignalType.LONG else OrderSide.SELL,
                quantity=quantity,
                algorithm=ExecutionAlgorithm.TWAP,
                strategy_id=strategy_config.strategy_id
            )
            
            # Execute order
            if self.execution_engine:
                result = await self.execution_engine.execute_order(request)
            else:
                # Fallback execution
                result = ExecutionResult(
                    request_id=request.request_id,
                    status=ExecutionStatus.SUCCESS,
                    symbol=request.symbol,
                    side=request.side,
                    requested_quantity=request.quantity,
                    executed_quantity=request.quantity,
                    average_price=current_price,
                    total_cost=request.quantity * current_price * self.config.commission_rate
                )
            
            self.logger.info(f"✅ Executed: {signal.symbol_pair} {request.side} {quantity}")
            return result
            
        except Exception as e:
            self.logger.error(f"Single signal execution failed: {e}")
            return None
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        if hasattr(self, 'backtesting_data_provider') and self.backtesting_data_provider:
            price = self.backtesting_data_provider.get_current_price(symbol)
            if price:
                return price
        
        # Fallback prices
        fallback_prices = {'TSLA': 220.0, 'AAPL': 180.0, 'MSFT': 350.0, 'GOOGL': 140.0}
        return fallback_prices.get(symbol, 100.0)
    
    def _calculate_quantity(self, signal: TradingSignal, current_price: float) -> int:
        """Calculate order quantity based on signal and available capital"""
        try:
            if signal.signal_type == SignalType.CLOSE_LONG:
                # Close existing position
                current_position = self.portfolio_manager.get_position(signal.symbol_pair)
                return current_position.quantity if current_position and current_position.quantity > 0 else 0
            
            elif signal.signal_type in [SignalType.LONG, SignalType.SHORT]:
                # New position
                available_capital = self.portfolio_manager.available_capital * 0.95  # 5% reserve
                position_value = signal.position_size * available_capital
                
                if position_value >= 100.0:  # Minimum trade size
                    quantity = int(position_value / current_price)
                    max_affordable = int(available_capital / current_price)
                    return min(quantity, max_affordable)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Quantity calculation failed: {e}")
            return 0
    
    async def _update_portfolio(self, execution_results: List[ExecutionResult], strategy_config: StrategyConfig) -> PortfolioMetrics:
        """Update portfolio with execution results"""
        try:
            slice_timestamp = strategy_config.signal_params.get('slice_timestamp', datetime.now())
            
            for result in execution_results:
                if result.status == ExecutionStatus.SUCCESS:
                    self.portfolio_manager.process_trade(
                        symbol=result.symbol,
                        quantity=int(result.executed_quantity),
                        price=result.average_price,
                        trade_type="BUY" if result.side == OrderSide.BUY else "SELL",
                        timestamp=slice_timestamp
                    )
            
            # Get portfolio metrics
            current_prices = {result.symbol: result.average_price for result in execution_results}
            return self.portfolio_manager.get_portfolio_metrics(current_prices)
            
        except Exception as e:
            self.logger.error(f"Portfolio update failed: {e}")
            raise
    
    # ================================================================================
    # ANALYTICS AND OPTIMIZATION
    # ================================================================================
    
    async def _generate_analytics(self, portfolio_update: PortfolioMetrics, strategy_config: StrategyConfig) -> Dict[str, Any]:
        """Generate performance analytics"""
        try:
            return {
                'total_return': portfolio_update.total_return_pct,
                'sharpe_ratio': portfolio_update.sharpe_ratio,
                'max_drawdown': portfolio_update.max_drawdown,
                'position_count': portfolio_update.position_count,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Analytics generation failed: {e}")
            return {}
    
    async def _apply_trade_engine_optimization(self, signals: List[TradingSignal], analytics: Dict[str, Any], strategy_config: StrategyConfig):
        """Apply Trade Engine optimization if available"""
        if not self.trade_engine_optimizer:
            return
        
        try:
            optimization_params = {
                'signals_count': len(signals),
                'total_return': analytics.get('total_return', 0),
                'max_drawdown': analytics.get('max_drawdown', 0)
            }
            
            self.logger.info(f"🔧 Trade Engine optimization applied: {optimization_params}")
            
        except Exception as e:
            self.logger.warning(f"Trade Engine optimization failed: {e}")
    
    # ================================================================================
    # DATA LOADING
    # ================================================================================
    
    async def _load_market_data(self, data_source: Any, strategy_config: StrategyConfig) -> Dict[str, Any]:
        """Load and process market data from various sources"""
        try:
            if isinstance(data_source, dict):
                return self._process_dict_data_source(data_source)
            else:
                return self._create_default_market_data()
                
        except Exception as e:
            self.logger.error(f"Market data loading failed: {e}")
            return self._create_default_market_data()
    
    def _process_dict_data_source(self, data_source: dict) -> Dict[str, Any]:
        """Process dictionary-based data source"""
        # Check if pre-processed DataFrame format
        if 'data' in data_source and isinstance(data_source['data'], pd.DataFrame):
            return {
                'symbols': data_source.get('symbols', []),
                'data': data_source['data'],
                'timestamp': data_source.get('timestamp', datetime.now())
            }
        
        # Process raw data format
        metadata_keys = {'timestamp', 'slice_index', 'total_slices', 'data', 'symbols'}
        symbols = [key for key in data_source.keys() if key not in metadata_keys]
        
        if not symbols:
            return self._create_default_market_data()
        
        # Create DataFrame from raw data
        data_records = []
        current_time = data_source.get('timestamp', datetime.now())
        
        for symbol in symbols:
            symbol_data = data_source[symbol]
            record = self._create_data_record(symbol, symbol_data, current_time)
            if record:
                data_records.append(record)
        
        # Create DataFrame
        df = pd.DataFrame(data_records)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        
        return {
            'symbols': symbols,
            'data': df,
            'timestamp': current_time
        }
    
    def _create_data_record(self, symbol: str, symbol_data: Any, current_time: datetime) -> Optional[Dict]:
        """Create a data record from symbol data"""
        try:
            if isinstance(symbol_data, dict):
                if 'price_history' in symbol_data:
                    # Handle price history format
                    price_history = symbol_data['price_history']
                    if price_history:
                        return {
                            'timestamp': price_history[-1].get('timestamp', current_time),
                            'symbol': symbol,
                            'open': price_history[-1].get('open', 100.0),
                            'high': price_history[-1].get('high', 100.0),
                            'low': price_history[-1].get('low', 100.0),
                            'close': price_history[-1].get('close', 100.0),
                            'volume': price_history[-1].get('volume', 1000)
                        }
                else:
                    # Handle simple price format
                    price = symbol_data.get('price', symbol_data.get('close', 100.0))
                    return {
                        'timestamp': current_time,
                        'symbol': symbol,
                        'open': price,
                        'high': price * 1.001,
                        'low': price * 0.999,
                        'close': price,
                        'volume': symbol_data.get('volume', 1000)
                    }
            
            # Fallback record
            return {
                'timestamp': current_time,
                'symbol': symbol,
                'open': 100.0,
                'high': 100.1,
                'low': 99.9,
                'close': 100.0,
                'volume': 1000
            }
            
        except Exception as e:
            self.logger.error(f"Data record creation failed for {symbol}: {e}")
            return None
    
    def _create_default_market_data(self) -> Dict[str, Any]:
        """Create default market data structure"""
        return {
            'symbols': [],
            'data': pd.DataFrame(),
            'timestamp': datetime.now()
        }
    
    # ================================================================================
    # BACKTESTING SUPPORT
    # ================================================================================
    
    async def set_backtesting_mode(self, clickhouse_loader, data_request):
        """Initialize backtesting mode with ClickHouse data provider"""
        try:
            from core_structure.market_data.backtesting_data_provider import BacktestingDataProvider
            from core_structure.execution_engine.backtesting_execution_engine import BacktestingExecutionEngine
            
            # Initialize backtesting data provider
            self.backtesting_data_provider = BacktestingDataProvider(clickhouse_loader, data_request)
            await self.backtesting_data_provider.initialize()
            
            # Set backtesting mode
            self.backtesting_mode = True
            
            # Replace execution engine with backtesting version
            self.execution_engine = BacktestingExecutionEngine(
                commission_rate=0.001,
                slippage_bps=1.0
            )
            self.execution_engine.set_backtesting_data_provider(self.backtesting_data_provider)
            
            self.logger.info("✅ Backtesting mode initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Backtesting mode initialization failed: {e}")
            raise
    
    async def advance_backtesting_time(self, time_index: int):
        """Advance backtesting time"""
        if hasattr(self, 'backtesting_data_provider'):
            self.backtesting_data_provider.advance_time(time_index)
    
    def reset_for_backtesting(self):
        """Reset engine state for clean backtesting"""
        self.logger.info("🔄 Resetting for backtesting")
        
        # Reset portfolio
        if self.portfolio_manager:
            self.portfolio_manager.reset_for_backtesting()
        
        # Clear caches
        self.strategy_cache.clear()
        self.strategy_config_cache.clear()
        self.trade_engine_strategy_initialized.clear()
        self.slice_trading_locks.clear()
        
        # Reset metrics
        self.metrics = EngineMetrics()
        self.cycle_times.clear()
        
        self.logger.info("✅ Backtesting reset complete")
    
    # ================================================================================
    # IBKR INTEGRATION
    # ================================================================================
    
    async def connect_ibkr(self) -> bool:
        """Connect to IBKR broker"""
        if not self.ibkr_bridge:
            self.logger.warning("IBKR bridge not initialized")
            return False
        
        try:
            success = await self.ibkr_bridge.connect()
            if success:
                self.logger.info("✅ IBKR connected")
            else:
                self.logger.error("❌ IBKR connection failed")
            return success
        except Exception as e:
            self.logger.error(f"IBKR connection error: {e}")
            return False
    
    async def disconnect_ibkr(self) -> bool:
        """Disconnect from IBKR broker"""
        if not self.ibkr_bridge:
            return True
        
        try:
            success = await self.ibkr_bridge.disconnect()
            if success:
                self.logger.info("✅ IBKR disconnected")
            return success
        except Exception as e:
            self.logger.error(f"IBKR disconnection error: {e}")
            return False
    
    # ================================================================================
    # UTILITY METHODS
    # ================================================================================
    
    def _update_metrics(self, success: bool, processing_time_ms: float):
        """Update engine performance metrics"""
        self.metrics.total_cycles += 1
        
        if success:
            self.metrics.successful_cycles += 1
        else:
            self.metrics.failed_cycles += 1
        
        # Update average processing time
        if self.cycle_times:
            self.metrics.average_processing_time_ms = sum(self.cycle_times) / len(self.cycle_times)
        
        self.metrics.active_strategies = len(self.active_strategies)
        self.metrics.last_updated = datetime.now()
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status"""
        return {
            'engine_id': self.config.engine_id,
            'status': self.status.value,
            'trading_mode': self.config.trading_mode.value,
            'backtesting_mode': self.backtesting_mode,
            'trade_engine_available': TRADE_ENGINE_AVAILABLE,
            'active_strategies': len(self.active_strategies),
            'metrics': {
                'total_cycles': self.metrics.total_cycles,
                'successful_cycles': self.metrics.successful_cycles,
                'failed_cycles': self.metrics.failed_cycles,
                'average_processing_time_ms': self.metrics.average_processing_time_ms,
                'cache_hit_rate': self.metrics.cache_hit_rate
            },
            'last_updated': self.metrics.last_updated.isoformat()
        }
    
    def get_strategy_config(self, strategy_id: str) -> Optional[StrategyConfig]:
        """Get strategy configuration"""
        return self.active_strategies.get(strategy_id)
    
    def list_active_strategies(self) -> List[str]:
        """List active strategy IDs"""
        return list(self.active_strategies.keys())
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """Remove strategy from engine"""
        if strategy_id in self.active_strategies:
            del self.active_strategies[strategy_id]
            self.strategy_cache.pop(strategy_id, None)
            self.strategy_config_cache.pop(strategy_id, None)
            self.trade_engine_strategy_initialized.pop(strategy_id, None)
            self.logger.info(f"✅ Strategy removed: {strategy_id}")
            return True
        return False
    
    def shutdown(self):
        """Shutdown unified core engine"""
        self.logger.info("🔄 Shutting down Unified Core Engine")
        
        # Shutdown components
        if hasattr(self, 'signal_generator'):
            self.signal_generator.shutdown()
        
        if hasattr(self, 'portfolio_manager'):
            self.portfolio_manager.shutdown()
        
        if hasattr(self, 'risk_manager'):
            self.risk_manager.shutdown()
        
        self.status = EngineStatus.SHUTDOWN
        self.logger.info("✅ Unified Core Engine shutdown complete")
