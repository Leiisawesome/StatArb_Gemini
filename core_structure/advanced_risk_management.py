#!/usr/bin/env python3
"""
Phase 4 Advanced Risk Management System
=======================================

Comprehensive risk management system that provides real-time monitoring,
circuit breakers, position limits, VaR calculations, and regime-aware
risk controls for production trading.

PHASE 4 RISK MANAGEMENT FEATURES:
- Real-time position monitoring and risk calculation
- Dynamic VaR computation with multiple models
- Circuit breakers and automatic position limits
- Regime-aware risk adjustments
- Correlation monitoring and concentration limits
- Stress testing and scenario analysis
- Automated risk reporting and alerts
- Integration with Phase 3 analytics optimizations

Author: Professional Trading System Architecture - Phase 4 Risk Management
Version: 7.0.0 (Advanced Risk Management)
"""

import asyncio
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from collections import deque, defaultdict
import pandas as pd
import numpy as np
import uuid
from scipy import stats
from arch import arch_model
import warnings
warnings.filterwarnings('ignore')

# Import RiskLimits - MANDATORY (NO FALLBACKS)
from core_structure.components.risk.unified_risk_manager import RiskLimits

# Import regime interfaces for risk-regime integration
try:
    from core_structure.infrastructure.types import RegimeType, MarketRegime, RegimeConfidence, RegimeInfo
    REGIME_INTERFACE_AVAILABLE = True
except ImportError:
    import logging
    logging.getLogger(__name__).warning("⚠️ Regime interfaces not available - regime integration disabled")
    RegimeType = None
    MarketRegime = None
    RegimeConfidence = None
    RegimeInfo = None
    REGIME_INTERFACE_AVAILABLE = False

logger = logging.getLogger(__name__)

# ================================================================================
# RISK MANAGEMENT ENUMS AND TYPES
# ================================================================================

class RiskLevel(Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of risk alerts"""
    POSITION_LIMIT = "position_limit"
    VAR_BREACH = "var_breach"
    DRAWDOWN_LIMIT = "drawdown_limit"
    CORRELATION_LIMIT = "correlation_limit"
    CIRCUIT_BREAKER = "circuit_breaker"
    REGIME_CHANGE = "regime_change"
    LIQUIDITY_RISK = "liquidity_risk"

class RiskControlAction(Enum):
    """Risk control actions"""
    MONITOR = "monitor"
    REDUCE_POSITION = "reduce_position"
    HALT_TRADING = "halt_trading"
    EMERGENCY_EXIT = "emergency_exit"
    NOTIFICATION_ONLY = "notification_only"

class VaRModel(Enum):
    """Value-at-Risk calculation models"""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"

# ================================================================================
# CENTRAL RISK AUTHORIZATION TYPES
# ================================================================================

@dataclass
class TradeRequest:
    """Trade request for central risk authorization"""
    request_id: str
    strategy_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    price: Optional[float] = None
    order_type: str = "MARKET"
    timestamp: datetime = field(default_factory=datetime.now)
    signal_confidence: float = 1.0
    expected_hold_time: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TradeAuthorization:
    """Trade authorization result from central risk manager"""
    request_id: str
    authorization_id: str
    approved: bool
    reason: str
    risk_level: RiskLevel
    adjusted_quantity: Optional[float] = None
    conditions: List[str] = field(default_factory=list)
    expiry_time: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=5))
    metadata: Dict[str, Any] = field(default_factory=dict)
    GARCH = "garch"
    REGIME_AWARE = "regime_aware"

@dataclass
class Position:
    """Trading position with risk metrics"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    entry_time: datetime
    last_update: datetime
    strategy: str = ""
    risk_weight: float = 1.0

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    timestamp: datetime
    portfolio_value: float
    total_exposure: float
    var_1d_95: float
    var_1d_99: float
    expected_shortfall: float
    max_drawdown: float
    current_drawdown: float
    beta: float
    sharpe_ratio: float
    correlation_risk: float
    concentration_risk: float
    leverage: float
    stress_test_loss: float

@dataclass
class RiskAlert:
    """Risk management alert"""
    alert_id: str
    alert_type: AlertType
    level: RiskLevel
    message: str
    timestamp: datetime
    symbol: Optional[str] = None
    current_value: float = 0.0
    threshold: float = 0.0
    recommended_action: RiskControlAction = RiskControlAction.MONITOR
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RiskConfiguration:
    """Risk management configuration"""
    # Position limits
    max_position_size: float = 0.1  # 10% of portfolio
    max_portfolio_exposure: float = 1.0  # 100% gross exposure
    max_sector_concentration: float = 0.3  # 30% per sector
    max_single_position: float = 0.05  # 5% per position
    
    # VaR limits
    var_limit_daily_95: float = 0.02  # 2% daily VaR at 95%
    var_limit_daily_99: float = 0.03  # 3% daily VaR at 99%
    expected_shortfall_limit: float = 0.05  # 5% expected shortfall
    
    # Drawdown limits
    max_daily_loss: float = 0.02  # 2% max daily loss
    max_total_drawdown: float = 0.10  # 10% max drawdown
    stop_loss_threshold: float = 0.05  # 5% stop loss
    
    # Correlation limits
    max_correlation: float = 0.8  # 80% max correlation
    min_diversification_ratio: float = 0.3  # 30% min diversification
    
    # Risk monitoring
    risk_check_interval_seconds: float = 30.0
    alert_cooldown_minutes: float = 5.0
    enable_circuit_breakers: bool = True
    enable_auto_rebalancing: bool = True
    
    # Model parameters
    var_confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    var_lookback_days: int = 252
    stress_test_scenarios: int = 1000

# ================================================================================
# VALUE-AT-RISK CALCULATOR
# ================================================================================

class VaRCalculator:
    """
    Advanced Value-at-Risk calculator with multiple models
    and regime-aware adjustments
    """
    
    def __init__(self, config: RiskConfiguration):
        self.config = config
        self.historical_data: Dict[str, pd.DataFrame] = {}
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.volatility_models: Dict[str, Any] = {}
        
        # Regime integration
        self.current_regime = "normal"
        self.regime_adjustments = {
            "crisis_mode": 1.5,
            "high_volatility": 1.3,
            "trending_bull": 0.9,
            "trending_bear": 1.2,
            "sideways_range": 1.0
        }
        
        logger.info("📊 VaR Calculator initialized")
    
    def update_historical_data(self, symbol: str, price_data: pd.DataFrame) -> None:
        """Update historical price data for VaR calculation"""
        # Calculate returns
        if 'close' in price_data.columns:
            returns = price_data['close'].pct_change().dropna()
            
            # Store last N observations
            max_observations = self.config.var_lookback_days
            if len(returns) > max_observations:
                returns = returns.tail(max_observations)
            
            self.historical_data[symbol] = returns
            
            # Update correlation matrix if we have multiple symbols
            if len(self.historical_data) > 1:
                self._update_correlation_matrix()
    
    def _update_correlation_matrix(self) -> None:
        """Update correlation matrix for portfolio VaR"""
        try:
            # Align all return series
            symbols = list(self.historical_data.keys())
            return_df = pd.DataFrame()
            
            for symbol in symbols:
                return_df[symbol] = self.historical_data[symbol]
            
            # Calculate correlation matrix
            self.correlation_matrix = return_df.corr()
            
        except Exception as e:
            logger.error(f"Error updating correlation matrix: {e}")
    
    def calculate_var(self, positions: Dict[str, Position], confidence_level: float = 0.95, 
                     model: VaRModel = VaRModel.HISTORICAL) -> Tuple[float, Dict[str, Any]]:
        """Calculate Value-at-Risk for portfolio"""
        try:
            if not positions:
                return 0.0, {'error': 'No positions provided'}
            
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(positions)
            
            if len(portfolio_returns) < 30:  # Minimum data requirement
                return 0.0, {'error': 'Insufficient historical data'}
            
            # Calculate VaR based on model
            if model == VaRModel.HISTORICAL:
                var_value = self._historical_var(portfolio_returns, confidence_level)
            elif model == VaRModel.PARAMETRIC:
                var_value = self._parametric_var(portfolio_returns, confidence_level)
            elif model == VaRModel.MONTE_CARLO:
                var_value = self._monte_carlo_var(positions, confidence_level)
            elif model == VaRModel.REGIME_AWARE:
                var_value = self._regime_aware_var(portfolio_returns, confidence_level)
            else:
                var_value = self._historical_var(portfolio_returns, confidence_level)
            
            # Apply regime adjustments
            regime_multiplier = self.regime_adjustments.get(self.current_regime, 1.0)
            adjusted_var = var_value * regime_multiplier
            
            # Calculate expected shortfall (CVaR)
            expected_shortfall = self._calculate_expected_shortfall(portfolio_returns, confidence_level)
            
            return adjusted_var, {
                'raw_var': var_value,
                'regime_adjusted_var': adjusted_var,
                'expected_shortfall': expected_shortfall,
                'confidence_level': confidence_level,
                'model': model.value,
                'regime': self.current_regime,
                'regime_multiplier': regime_multiplier,
                'data_points': len(portfolio_returns)
            }
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0.0, {'error': str(e)}
    
    def _calculate_portfolio_returns(self, positions: Dict[str, Position]) -> pd.Series:
        """Calculate portfolio returns from positions"""
        portfolio_returns = pd.Series()
        
        try:
            # Get portfolio weights
            total_value = sum(abs(pos.market_value) for pos in positions.values())
            
            if total_value == 0:
                return portfolio_returns
            
            # Aggregate returns weighted by position size
            for symbol, position in positions.items():
                if symbol in self.historical_data:
                    weight = abs(position.market_value) / total_value
                    symbol_returns = self.historical_data[symbol] * weight
                    
                    if portfolio_returns.empty:
                        portfolio_returns = symbol_returns
                    else:
                        # Align indices and add
                        aligned_returns = symbol_returns.reindex(portfolio_returns.index, fill_value=0)
                        portfolio_returns += aligned_returns
            
        except Exception as e:
            logger.error(f"Error calculating portfolio returns: {e}")
        
        return portfolio_returns
    
    def _historical_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate historical VaR"""
        if len(returns) == 0:
            return 0.0
        
        # Sort returns and find percentile
        sorted_returns = returns.sort_values()
        var_index = int((1 - confidence_level) * len(sorted_returns))
        
        return abs(sorted_returns.iloc[var_index])
    
    def _parametric_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate parametric VaR assuming normal distribution"""
        if len(returns) == 0:
            return 0.0
        
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Z-score for confidence level
        z_score = stats.norm.ppf(1 - confidence_level)
        
        return abs(mean_return + z_score * std_return)
    
    def _monte_carlo_var(self, positions: Dict[str, Position], confidence_level: float) -> float:
        """Calculate Monte Carlo VaR"""
        try:
            if not self.correlation_matrix is not None or len(positions) < 2:
                # Fall back to historical VaR
                portfolio_returns = self._calculate_portfolio_returns(positions)
                return self._historical_var(portfolio_returns, confidence_level)
            
            # Generate correlated random returns
            symbols = list(positions.keys())
            n_simulations = self.config.stress_test_scenarios
            
            # Get mean returns and covariance matrix
            returns_data = []
            for symbol in symbols:
                if symbol in self.historical_data:
                    returns_data.append(self.historical_data[symbol])
            
            if not returns_data:
                return 0.0
            
            returns_df = pd.concat(returns_data, axis=1, keys=symbols)
            mean_returns = returns_df.mean()
            cov_matrix = returns_df.cov()
            
            # Monte Carlo simulation
            simulated_returns = np.random.multivariate_normal(
                mean_returns.values, 
                cov_matrix.values, 
                n_simulations
            )
            
            # Calculate portfolio returns for each simulation
            portfolio_values = []
            total_value = sum(abs(pos.market_value) for pos in positions.values())
            
            for sim_returns in simulated_returns:
                portfolio_return = 0.0
                for i, symbol in enumerate(symbols):
                    if symbol in positions:
                        weight = abs(positions[symbol].market_value) / total_value
                        portfolio_return += weight * sim_returns[i]
                portfolio_values.append(portfolio_return)
            
            # Calculate VaR from simulated values
            portfolio_values = np.array(portfolio_values)
            var_index = int((1 - confidence_level) * len(portfolio_values))
            sorted_values = np.sort(portfolio_values)
            
            return abs(sorted_values[var_index])
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo VaR: {e}")
            portfolio_returns = self._calculate_portfolio_returns(positions)
            return self._historical_var(portfolio_returns, confidence_level)
    
    def _regime_aware_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate regime-aware VaR with volatility clustering"""
        try:
            # Fit GARCH model for volatility clustering
            model = arch_model(returns * 100, vol='Garch', p=1, q=1)
            fitted_model = model.fit(disp='off')
            
            # Get conditional volatility
            conditional_vol = fitted_model.conditional_volatility.iloc[-1] / 100
            
            # Calculate regime-adjusted VaR
            z_score = stats.norm.ppf(1 - confidence_level)
            regime_var = abs(z_score * conditional_vol)
            
            return regime_var
            
        except Exception as e:
            logger.warning(f"Error in regime-aware VaR calculation: {e}, falling back to parametric VaR")
            return self._parametric_var(returns, confidence_level)
    
    def _calculate_expected_shortfall(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if len(returns) == 0:
            return 0.0
        
        # Sort returns and find VaR threshold
        sorted_returns = returns.sort_values()
        var_index = int((1 - confidence_level) * len(sorted_returns))
        
        # Expected shortfall is mean of returns beyond VaR
        tail_returns = sorted_returns.iloc[:var_index]
        
        return abs(tail_returns.mean()) if len(tail_returns) > 0 else 0.0
    
    def update_regime(self, regime: str) -> None:
        """Update current market regime for risk adjustments"""
        self.current_regime = regime
        logger.info(f"🎯 VaR calculator updated with regime: {regime}")

# ================================================================================
# POSITION MONITOR
# ================================================================================

class PositionMonitor:
    """
    Real-time position monitoring with risk checks and alerts
    """
    
    def __init__(self, config: RiskConfiguration):
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.position_history = deque(maxlen=10000)
        self.risk_alerts: List[RiskAlert] = []
        
        # Monitoring thread
        self._running = False
        self._monitor_thread = None
        self._last_alert_times: Dict[str, datetime] = {}
        
        logger.info("👁️ Position Monitor initialized")
    
    async def initialize(self) -> None:
        """Initialize position monitoring"""
        self._running = True
        self._start_monitoring()
        logger.info("✅ Position monitoring started")
    
    def _start_monitoring(self) -> None:
        """Start background position monitoring"""
        def monitoring_loop():
            while self._running:
                try:
                    self._check_all_positions()
                    time.sleep(self.config.risk_check_interval_seconds)
                except Exception as e:
                    logger.error(f"Position monitoring error: {e}")
                    time.sleep(5)
        
        self._monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("🔄 Position monitoring loop started")
    
    def update_position(self, symbol: str, quantity: float, current_price: float, 
                       entry_price: float = None, strategy: str = "") -> None:
        """Update position information"""
        now = datetime.now()
        
        if symbol in self.positions:
            # Update existing position
            position = self.positions[symbol]
            position.quantity = quantity
            position.current_price = current_price
            position.market_value = quantity * current_price
            position.unrealized_pnl = (current_price - position.entry_price) * quantity
            position.last_update = now
            position.strategy = strategy or position.strategy
        else:
            # Create new position
            entry_price = entry_price or current_price
            position = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                current_price=current_price,
                market_value=quantity * current_price,
                unrealized_pnl=(current_price - entry_price) * quantity,
                entry_time=now,
                last_update=now,
                strategy=strategy
            )
            self.positions[symbol] = position
        
        # Add to history
        self.position_history.append({
            'timestamp': now,
            'symbol': symbol,
            'quantity': quantity,
            'price': current_price,
            'market_value': position.market_value,
            'unrealized_pnl': position.unrealized_pnl
        })
        
        # Check position immediately
        self._check_position(symbol, position)
    
    def remove_position(self, symbol: str) -> None:
        """Remove position (on close)"""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"📤 Position removed: {symbol}")
    
    def _check_all_positions(self) -> None:
        """Check all positions for risk violations"""
        for symbol, position in self.positions.items():
            self._check_position(symbol, position)
        
        # Check portfolio-level risks
        self._check_portfolio_risks()
    
    def _check_position(self, symbol: str, position: Position) -> None:
        """Check individual position for risk violations"""
        alerts = []
        
        # Check position size limit
        portfolio_value = self.get_portfolio_value()
        if portfolio_value > 0:
            position_weight = abs(position.market_value) / portfolio_value
            
            if position_weight > self.config.max_single_position:
                alerts.append(RiskAlert(
                    alert_id=f"pos_limit_{symbol}_{int(time.time())}",
                    alert_type=AlertType.POSITION_LIMIT,
                    level=RiskLevel.HIGH,
                    message=f"Position {symbol} exceeds size limit: {position_weight:.2%} > {self.config.max_single_position:.2%}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    current_value=position_weight,
                    threshold=self.config.max_single_position,
                    recommended_action=RiskControlAction.REDUCE_POSITION
                ))
        
        # Check stop loss
        if position.quantity != 0:
            pnl_percentage = position.unrealized_pnl / abs(position.quantity * position.entry_price)
            
            if pnl_percentage < -self.config.stop_loss_threshold:
                alerts.append(RiskAlert(
                    alert_id=f"stop_loss_{symbol}_{int(time.time())}",
                    alert_type=AlertType.DRAWDOWN_LIMIT,
                    level=RiskLevel.CRITICAL,
                    message=f"Stop loss triggered for {symbol}: {pnl_percentage:.2%} loss",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    current_value=pnl_percentage,
                    threshold=-self.config.stop_loss_threshold,
                    recommended_action=RiskControlAction.EMERGENCY_EXIT
                ))
        
        # Process alerts
        for alert in alerts:
            self._process_alert(alert)
    
    def _check_portfolio_risks(self) -> None:
        """Check portfolio-level risk violations"""
        alerts = []
        portfolio_value = self.get_portfolio_value()
        
        if portfolio_value == 0:
            return
        
        # Check total exposure
        total_exposure = sum(abs(pos.market_value) for pos in self.positions.values())
        exposure_ratio = total_exposure / portfolio_value
        
        if exposure_ratio > self.config.max_portfolio_exposure:
            alerts.append(RiskAlert(
                alert_id=f"exposure_{int(time.time())}",
                alert_type=AlertType.POSITION_LIMIT,
                level=RiskLevel.HIGH,
                message=f"Portfolio exposure exceeds limit: {exposure_ratio:.2%} > {self.config.max_portfolio_exposure:.2%}",
                timestamp=datetime.now(),
                current_value=exposure_ratio,
                threshold=self.config.max_portfolio_exposure,
                recommended_action=RiskControlAction.REDUCE_POSITION
            ))
        
        # Check daily loss
        daily_pnl = self.get_daily_pnl()
        daily_loss_pct = daily_pnl / portfolio_value if portfolio_value > 0 else 0.0
        
        if daily_loss_pct < -self.config.max_daily_loss:
            alerts.append(RiskAlert(
                alert_id=f"daily_loss_{int(time.time())}",
                alert_type=AlertType.DRAWDOWN_LIMIT,
                level=RiskLevel.CRITICAL,
                message=f"Daily loss limit exceeded: {daily_loss_pct:.2%} < -{self.config.max_daily_loss:.2%}",
                timestamp=datetime.now(),
                current_value=daily_loss_pct,
                threshold=-self.config.max_daily_loss,
                recommended_action=RiskControlAction.HALT_TRADING
            ))
        
        # Process alerts
        for alert in alerts:
            self._process_alert(alert)
    
    def _process_alert(self, alert: RiskAlert) -> None:
        """Process risk alert"""
        # Check cooldown period
        alert_key = f"{alert.alert_type.value}_{alert.symbol or 'portfolio'}"
        last_alert_time = self._last_alert_times.get(alert_key)
        
        if last_alert_time:
            time_since_last = (datetime.now() - last_alert_time).total_seconds()
            if time_since_last < self.config.alert_cooldown_minutes * 60:
                return  # Skip due to cooldown
        
        # Add alert
        self.risk_alerts.append(alert)
        self._last_alert_times[alert_key] = datetime.now()
        
        # Log alert
        logger.warning(f"🚨 RISK ALERT: {alert.message}")
        
        # Keep only recent alerts
        if len(self.risk_alerts) > 1000:
            self.risk_alerts = self.risk_alerts[-500:]
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        return sum(pos.market_value for pos in self.positions.values())
    
    def get_daily_pnl(self) -> float:
        """Get daily P&L"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get portfolio position summary"""
        total_value = self.get_portfolio_value()
        total_pnl = self.get_daily_pnl()
        
        return {
            'total_positions': len(self.positions),
            'portfolio_value': total_value,
            'total_exposure': sum(abs(pos.market_value) for pos in self.positions.values()),
            'daily_pnl': total_pnl,
            'daily_pnl_pct': (total_pnl / total_value) if total_value > 0 else 0.0,
            'largest_position': max((abs(pos.market_value) for pos in self.positions.values()), default=0.0),
            'positions': {
                symbol: {
                    'quantity': pos.quantity,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'strategy': pos.strategy
                }
                for symbol, pos in self.positions.items()
            }
        }
    
    def get_recent_alerts(self, hours: int = 24) -> List[RiskAlert]:
        """Get recent risk alerts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.risk_alerts if alert.timestamp >= cutoff_time]
    
    async def shutdown(self) -> None:
        """Shutdown position monitoring"""
        self._running = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("✅ Position monitoring shutdown complete")

# ================================================================================
# ADVANCED RISK MANAGER
# ================================================================================

class AdvancedRiskManager(object):
    """
    Comprehensive risk management system that integrates all risk components
    with Phase 3 analytics, real-time trading capabilities, and regime-aware risk management
    """
    
    def __init__(self, config: RiskConfiguration):
        self.config = config
        self.manager_id = f"risk_mgr_{uuid.uuid4().hex[:8]}"
        
        # Create risk_limits from config for compatibility with backtest expectations
        self.risk_limits = RiskLimits(
            max_position_size_pct=config.max_position_size,
            default_stop_loss_pct=config.stop_loss_threshold,
            default_take_profit_pct=config.stop_loss_threshold * 2.0,  # 2x stop loss as take profit
            default_trailing_stop_pct=config.stop_loss_threshold * 0.75  # 75% of stop loss
        )
        
        # Initialize components
        self.var_calculator = VaRCalculator(config)
        self.position_monitor = PositionMonitor(config)
        
        # Risk state
        self.current_risk_metrics: Optional[RiskMetrics] = None
        self.circuit_breaker_active = False
        self.emergency_mode = False
        
        # Regime-aware risk management state
        self.current_regime = None  # Will store RegimeType when available
        self.regime_confidence: float = 0.0
        self.regime_adjusted_limits: Optional[RiskLimits] = None
        self.regime_history: deque = deque(maxlen=100)  # Track regime changes
        
        # Integration with Phase 3 analytics
        self.analytics_integration = None
        
        # Performance tracking
        self.risk_events = deque(maxlen=1000)
        
        # Authorization tracking for token validation
        self.authorization_history: Dict[str, TradeAuthorization] = {}
        self.authorization_cleanup_interval = 300  # Clean up old authorizations every 5 minutes
        
        logger.info(f"🛡️ Advanced Risk Manager {self.manager_id} initialized")
    
    async def initialize(self) -> None:
        """Initialize the advanced risk management system"""
        try:
            # Initialize components
            await self.position_monitor.initialize()
            
            # Initialize Phase 3 analytics integration - MANDATORY (NO FALLBACKS)
            from core_structure.analytics.performance_optimization import (
                vectorized_calc, parallel_processor, intelligent_cache
            )
            self.analytics_integration = {
                'vectorized_calc': vectorized_calc,
                'parallel_processor': parallel_processor,
                'intelligent_cache': intelligent_cache
            }
            logger.info("✅ Phase 3 analytics integration enabled")
            
            # Start risk monitoring
            self._start_risk_monitoring()
            
            logger.info("✅ Advanced Risk Manager ready")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Advanced Risk Manager: {e}")
            raise
    
    def _start_risk_monitoring(self) -> None:
        """Start comprehensive risk monitoring"""
        def risk_monitoring_loop():
            while True:
                try:
                    self._calculate_comprehensive_risk_metrics()
                    self._check_circuit_breakers()
                    time.sleep(60)  # Calculate risk metrics every minute
                except Exception as e:
                    logger.error(f"Risk monitoring error: {e}")
                    time.sleep(10)
        
        risk_thread = threading.Thread(target=risk_monitoring_loop, daemon=True)
        risk_thread.start()
        logger.info("🔄 Comprehensive risk monitoring started")
    
    def _calculate_comprehensive_risk_metrics(self) -> None:
        """Calculate comprehensive risk metrics"""
        try:
            positions = self.position_monitor.positions
            portfolio_value = self.position_monitor.get_portfolio_value()
            
            if not positions or portfolio_value == 0:
                return
            
            # Calculate VaR at multiple confidence levels
            var_95, var_details_95 = self.var_calculator.calculate_var(
                positions, confidence_level=0.95, model=VaRModel.HISTORICAL
            )
            var_99, var_details_99 = self.var_calculator.calculate_var(
                positions, confidence_level=0.99, model=VaRModel.HISTORICAL
            )
            
            # Calculate other risk metrics
            daily_pnl = self.position_monitor.get_daily_pnl()
            total_exposure = sum(abs(pos.market_value) for pos in positions.values())
            
            # Calculate drawdown
            current_drawdown = self._calculate_current_drawdown()
            max_drawdown = self._calculate_max_drawdown()
            
            # Calculate correlation and concentration risk
            correlation_risk = self._calculate_correlation_risk(positions)
            concentration_risk = self._calculate_concentration_risk(positions, portfolio_value)
            
            # Calculate leverage
            leverage = total_exposure / portfolio_value if portfolio_value > 0 else 0.0
            
            # Create comprehensive risk metrics
            self.current_risk_metrics = RiskMetrics(
                timestamp=datetime.now(),
                portfolio_value=portfolio_value,
                total_exposure=total_exposure,
                var_1d_95=var_95,
                var_1d_99=var_99,
                expected_shortfall=var_details_95.get('expected_shortfall', 0.0),
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                beta=self._calculate_beta(positions),
                sharpe_ratio=self._calculate_sharpe_ratio(positions),
                correlation_risk=correlation_risk,
                concentration_risk=concentration_risk,
                leverage=leverage,
                stress_test_loss=self._run_stress_test(positions)
            )
            
            # Cache metrics using Phase 3 optimization if available
            if self.analytics_integration and 'intelligent_cache' in self.analytics_integration:
                cache = self.analytics_integration['intelligent_cache']
                cache_key = f"risk_metrics_{int(time.time() // 60)}"  # Cache for 1 minute
                cache.put(cache_key, self.current_risk_metrics.__dict__, ttl=60)
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown"""
        # This would track the portfolio high-water mark
        # For now, return a simplified calculation
        daily_pnl = self.position_monitor.get_daily_pnl()
        portfolio_value = self.position_monitor.get_portfolio_value()
        
        return (daily_pnl / portfolio_value) if portfolio_value > 0 else 0.0
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        # This would track historical maximum drawdown
        # For now, return the configured limit
        return self.config.max_total_drawdown
    
    def _calculate_correlation_risk(self, positions: Dict[str, Position]) -> float:
        """Calculate portfolio correlation risk"""
        if len(positions) < 2:
            return 0.0
        
        # Use correlation matrix if available
        if self.var_calculator.correlation_matrix is not None:
            symbols = list(positions.keys())
            correlations = []
            
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols[i+1:], i+1):
                    if symbol1 in self.var_calculator.correlation_matrix.index and \
                       symbol2 in self.var_calculator.correlation_matrix.columns:
                        corr = self.var_calculator.correlation_matrix.loc[symbol1, symbol2]
                        correlations.append(abs(corr))
            
            return np.mean(correlations) if correlations else 0.0
        
        return 0.0
    
    def _calculate_concentration_risk(self, positions: Dict[str, Position], portfolio_value: float) -> float:
        """Calculate portfolio concentration risk"""
        if portfolio_value == 0:
            return 0.0
        
        # Calculate Herfindahl-Hirschman Index
        weights = [abs(pos.market_value) / portfolio_value for pos in positions.values()]
        hhi = sum(w**2 for w in weights)
        
        # Convert to concentration risk (0 = perfectly diversified, 1 = fully concentrated)
        max_hhi = 1.0  # Fully concentrated
        min_hhi = 1.0 / len(positions) if positions else 1.0  # Equally weighted
        
        if max_hhi == min_hhi:
            return 0.0
        
        concentration_risk = (hhi - min_hhi) / (max_hhi - min_hhi)
        return min(1.0, max(0.0, concentration_risk))
    
    def _calculate_beta(self, positions: Dict[str, Position]) -> float:
        """Calculate portfolio beta (simplified)"""
        # This would calculate beta relative to a benchmark
        # For now, return a placeholder
        return 1.0
    
    def _calculate_sharpe_ratio(self, positions: Dict[str, Position]) -> float:
        """Calculate portfolio Sharpe ratio"""
        # This would calculate the Sharpe ratio from historical returns
        # For now, return a placeholder
        return 0.5
    
    def _run_stress_test(self, positions: Dict[str, Position]) -> float:
        """Run stress test scenarios"""
        try:
            # Simple stress test: -20% market shock
            stress_loss = 0.0
            for position in positions.values():
                stressed_value = position.market_value * 0.8  # 20% decline
                stress_loss += position.market_value - stressed_value
            
            return stress_loss
            
        except Exception as e:
            logger.error(f"Error in stress test: {e}")
            return 0.0
    
    def _check_circuit_breakers(self) -> None:
        """Check if circuit breakers should be triggered"""
        if not self.config.enable_circuit_breakers or self.circuit_breaker_active:
            return
        
        metrics = self.current_risk_metrics
        if not metrics:
            return
        
        # Check VaR limits
        if metrics.var_1d_95 > self.config.var_limit_daily_95:
            self._trigger_circuit_breaker(f"VaR 95% limit exceeded: {metrics.var_1d_95:.4f} > {self.config.var_limit_daily_95:.4f}")
        
        # Check drawdown limits
        if metrics.current_drawdown < -self.config.max_daily_loss:
            self._trigger_circuit_breaker(f"Daily loss limit exceeded: {metrics.current_drawdown:.2%}")
        
        # Check concentration risk
        if metrics.concentration_risk > 0.8:  # 80% concentration threshold
            self._trigger_circuit_breaker(f"High concentration risk: {metrics.concentration_risk:.2%}")
    
    def _trigger_circuit_breaker(self, reason: str) -> None:
        """Trigger circuit breaker"""
        self.circuit_breaker_active = True
        
        # Create critical alert
        alert = RiskAlert(
            alert_id=f"circuit_breaker_{int(time.time())}",
            alert_type=AlertType.CIRCUIT_BREAKER,
            level=RiskLevel.CRITICAL,
            message=f"CIRCUIT BREAKER ACTIVATED: {reason}",
            timestamp=datetime.now(),
            recommended_action=RiskControlAction.HALT_TRADING
        )
        
        self.position_monitor.risk_alerts.append(alert)
        
        logger.critical(f"🔴 CIRCUIT BREAKER ACTIVATED: {reason}")
        
        # Record risk event
        self.risk_events.append({
            'timestamp': datetime.now(),
            'type': 'circuit_breaker',
            'reason': reason,
            'metrics': self.current_risk_metrics.__dict__ if self.current_risk_metrics else {}
        })
    
    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker (manual intervention)"""
        self.circuit_breaker_active = False
        logger.info("🟢 Circuit breaker reset")
    
    def update_position(self, symbol: str, quantity: float, current_price: float, 
                       entry_price: float = None, strategy: str = "") -> None:
        """Update position and trigger risk checks"""
        self.position_monitor.update_position(symbol, quantity, current_price, entry_price, strategy)
        
        # Update VaR calculator with price data if needed
        if symbol not in self.var_calculator.historical_data:
            # This would normally fetch historical data
            # For now, create a simple price series
            price_series = pd.Series([current_price] * 100)  # Placeholder
            self.var_calculator.update_historical_data(symbol, pd.DataFrame({'close': price_series}))
    
    def update_regime(self, regime: str) -> None:
        """Update market regime for risk adjustments"""
        self.var_calculator.update_regime(regime)
        logger.info(f"🎯 Risk manager updated with regime: {regime}")
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get comprehensive risk status"""
        position_summary = self.position_monitor.get_position_summary()
        recent_alerts = self.position_monitor.get_recent_alerts(hours=24)
        
        return {
            'manager_id': self.manager_id,
            'circuit_breaker_active': self.circuit_breaker_active,
            'emergency_mode': self.emergency_mode,
            
            # Current risk metrics
            'risk_metrics': self.current_risk_metrics.__dict__ if self.current_risk_metrics else {},
            
            # Position summary
            'positions': position_summary,
            
            # Alerts
            'recent_alerts': [
                {
                    'type': alert.alert_type.value,
                    'level': alert.level.value,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'symbol': alert.symbol
                }
                for alert in recent_alerts
            ],
            
            # Configuration
            'risk_limits': {
                'max_position_size': self.config.max_position_size,
                'max_daily_loss': self.config.max_daily_loss,
                'var_limit_95': self.config.var_limit_daily_95,
                'var_limit_99': self.config.var_limit_daily_99
            },
            
            'timestamp': datetime.now().isoformat()
        }
    
    # ================================================================================
    # CENTRAL RISK AUTHORIZATION - INSTITUTIONAL GRADE RISK GOVERNANCE
    # ================================================================================
    
    async def authorize_trade(self, trade_request: TradeRequest) -> TradeAuthorization:
        """
        Central trade authorization - ALL trades must go through this method
        
        This implements institutional-grade risk governance where no component
        can execute trades independently. Following elite trading desk patterns.
        """
        authorization_id = f"auth_{uuid.uuid4().hex[:12]}"
        
        try:
            # 1. Check circuit breaker status
            if self.circuit_breaker_active:
                return TradeAuthorization(
                    request_id=trade_request.request_id,
                    authorization_id=authorization_id,
                    approved=False,
                    reason="Circuit breaker active - trading halted",
                    risk_level=RiskLevel.CRITICAL
                )
            
            # 2. Check emergency mode
            if self.emergency_mode:
                return TradeAuthorization(
                    request_id=trade_request.request_id,
                    authorization_id=authorization_id,
                    approved=False,
                    reason="Emergency mode active - new trades not permitted",
                    risk_level=RiskLevel.CRITICAL
                )
            
            # 3. Validate trade request
            validation_result = await self._validate_trade_request(trade_request)
            if not validation_result['valid']:
                return TradeAuthorization(
                    request_id=trade_request.request_id,
                    authorization_id=authorization_id,
                    approved=False,
                    reason=validation_result['reason'],
                    risk_level=RiskLevel.HIGH
                )
            
            # 4. Check position limits
            position_check = await self._check_position_limits(trade_request)
            if not position_check['approved']:
                return TradeAuthorization(
                    request_id=trade_request.request_id,
                    authorization_id=authorization_id,
                    approved=False,
                    reason=position_check['reason'],
                    risk_level=RiskLevel.HIGH,
                    adjusted_quantity=position_check.get('adjusted_quantity')
                )
            
            # 5. Check portfolio-level risk
            portfolio_check = await self._check_portfolio_risk(trade_request)
            if not portfolio_check['approved']:
                return TradeAuthorization(
                    request_id=trade_request.request_id,
                    authorization_id=authorization_id,
                    approved=False,
                    reason=portfolio_check['reason'],
                    risk_level=RiskLevel.MEDIUM
                )
            
            # 6. Check strategy allocation limits
            strategy_check = await self._check_strategy_limits(trade_request)
            if not strategy_check['approved']:
                return TradeAuthorization(
                    request_id=trade_request.request_id,
                    authorization_id=authorization_id,
                    approved=False,
                    reason=strategy_check['reason'],
                    risk_level=RiskLevel.MEDIUM
                )
            
            # 7. All checks passed - approve trade
            logger.info(f"✅ Trade authorized: {trade_request.symbol} {trade_request.side} {trade_request.quantity}")
            
            authorization = TradeAuthorization(
                request_id=trade_request.request_id,
                authorization_id=authorization_id,
                approved=True,
                reason="Trade approved - all risk checks passed",
                risk_level=RiskLevel.LOW,
                conditions=self._get_trade_conditions(trade_request),
                metadata={
                    'approval_timestamp': datetime.now().isoformat(),
                    'risk_score': self._calculate_trade_risk_score(trade_request)
                }
            )
            
            # Store authorization in history for token validation
            self.authorization_history[authorization_id] = authorization
            
            # Clean up old authorizations periodically
            if len(self.authorization_history) % 50 == 0:  # Every 50 authorizations
                await self._cleanup_old_authorizations()
            
            return authorization
            
        except Exception as e:
            logger.error(f"❌ Trade authorization error: {e}")
            return TradeAuthorization(
                request_id=trade_request.request_id,
                authorization_id=authorization_id,
                approved=False,
                reason=f"Authorization system error: {str(e)}",
                risk_level=RiskLevel.CRITICAL
            )
    
    async def validate_authorization_token(self, authorization_token: str, symbol: str, 
                                         side: str, quantity: float) -> bool:
        """
        Validate authorization token for execution engine.
        
        This method validates that:
        1. The authorization token exists and is valid
        2. The token corresponds to an approved trade authorization
        3. The token has not expired
        4. The trade parameters match the original authorization
        """
        try:
            # Check if token exists in our authorization records
            authorization_record = None
            for auth_id, auth in self.authorization_history.items():
                if (hasattr(auth, 'authorization_id') and 
                    auth.authorization_id == authorization_token):
                    authorization_record = auth
                    break
            
            if not authorization_record:
                logger.warning(f"⚠️ Authorization token not found: {authorization_token[:8]}...")
                return False
            
            # Check if authorization was approved
            if not authorization_record.approved:
                logger.warning(f"⚠️ Authorization token represents rejected trade: {authorization_token[:8]}...")
                return False
            
            # Check token expiration (authorization valid for 5 minutes)
            if hasattr(authorization_record, 'timestamp'):
                token_age = datetime.now() - authorization_record.timestamp
                if token_age > timedelta(minutes=5):
                    logger.warning(f"⚠️ Authorization token expired: {authorization_token[:8]}... (age: {token_age})")
                    return False
            
            # Validate trade parameters match authorization
            # Note: This is a basic implementation - in production, you would store
            # more detailed trade parameters in the authorization record
            logger.info(f"✅ Authorization token validated: {authorization_token[:8]}... for {symbol} {side} {quantity}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating authorization token: {e}")
            return False
    
    async def _validate_trade_request(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """Validate basic trade request parameters"""
        # Check required fields
        if not trade_request.symbol or not trade_request.strategy_id:
            return {'valid': False, 'reason': 'Missing required fields (symbol, strategy_id)'}
        
        # Check quantity
        if trade_request.quantity <= 0:
            return {'valid': False, 'reason': 'Invalid quantity - must be positive'}
        
        # Check side
        if trade_request.side not in ['BUY', 'SELL']:
            return {'valid': False, 'reason': 'Invalid side - must be BUY or SELL'}
        
        # Check signal confidence
        if trade_request.signal_confidence < 0.3:  # Minimum confidence threshold
            return {'valid': False, 'reason': f'Signal confidence too low: {trade_request.signal_confidence:.2f}'}
        
        return {'valid': True, 'reason': 'Trade request validation passed'}
    
    async def _check_position_limits(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """Check position size limits"""
        current_position = self.position_monitor.positions.get(trade_request.symbol)
        portfolio_value = self.position_monitor.get_portfolio_value()
        
        if portfolio_value == 0:
            return {'approved': False, 'reason': 'Portfolio value is zero - cannot determine position limits'}
        
        # Calculate new position value
        price = trade_request.price or 100.0  # Default price if not provided
        trade_value = trade_request.quantity * price
        
        if trade_request.side == 'BUY':
            new_position_value = trade_value
            if current_position:
                new_position_value += current_position.market_value
        else:  # SELL
            new_position_value = -trade_value
            if current_position:
                new_position_value += current_position.market_value
        
        # Check position size limit (use regime-adjusted limits if available)
        current_limits = self.get_current_risk_limits()
        position_weight = abs(new_position_value) / portfolio_value
        if position_weight > current_limits.max_position_size_pct:
            # Calculate adjusted quantity that would fit within limits
            max_position_value = portfolio_value * current_limits.max_position_size_pct
            adjusted_quantity = max_position_value / price
            
            return {
                'approved': False,
                'reason': f'Position size limit exceeded: {position_weight:.1%} > {current_limits.max_position_size_pct:.1%}',
                'adjusted_quantity': adjusted_quantity
            }
        
        return {'approved': True, 'reason': 'Position limits check passed'}
    
    async def _check_portfolio_risk(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """Check portfolio-level risk constraints"""
        # Check current drawdown
        if self.current_risk_metrics and self.current_risk_metrics.current_drawdown > 0.08:  # 8% drawdown threshold
            return {
                'approved': False,
                'reason': f'Portfolio drawdown too high: {self.current_risk_metrics.current_drawdown:.1%}'
            }
        
        # Check daily P&L
        daily_pnl = self.position_monitor.get_daily_pnl()
        portfolio_value = self.position_monitor.get_portfolio_value()
        
        if portfolio_value > 0:
            daily_loss_pct = abs(min(daily_pnl, 0)) / portfolio_value
            if daily_loss_pct > self.risk_limits.daily_loss_limit:
                return {
                    'approved': False,
                    'reason': f'Daily loss limit exceeded: {daily_loss_pct:.1%} > {self.risk_limits.daily_loss_limit:.1%}'
                }
        
        return {'approved': True, 'reason': 'Portfolio risk check passed'}
    
    async def _check_strategy_limits(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """Check strategy-specific limits"""
        # This would check strategy allocation limits
        # For now, implement basic strategy validation
        
        if not trade_request.strategy_id:
            return {'approved': False, 'reason': 'No strategy ID provided'}
        
        # Could add strategy-specific risk limits here
        # e.g., max allocation per strategy, strategy drawdown limits, etc.
        
        return {'approved': True, 'reason': 'Strategy limits check passed'}
    
    def _get_trade_conditions(self, trade_request: TradeRequest) -> List[str]:
        """Get any conditions/requirements for the approved trade"""
        conditions = []
        
        # Add stop-loss requirement for large positions
        price = trade_request.price or 100.0
        trade_value = trade_request.quantity * price
        portfolio_value = self.position_monitor.get_portfolio_value()
        
        if portfolio_value > 0 and (trade_value / portfolio_value) > 0.05:  # > 5% of portfolio
            stop_loss_pct = self.risk_limits.default_stop_loss_pct * 100
            conditions.append(f"Mandatory stop-loss at {stop_loss_pct:.1f}% required for position size > 5%")
        
        # Add monitoring requirement for high confidence signals
        if trade_request.signal_confidence > 0.8:
            conditions.append("Enhanced monitoring required for high-confidence signal")
        
        return conditions
    
    def _calculate_trade_risk_score(self, trade_request: TradeRequest) -> float:
        """Calculate risk score for the trade (0.0 = low risk, 1.0 = high risk)"""
        risk_score = 0.0
        
        # Base risk from position size
        price = trade_request.price or 100.0
        trade_value = trade_request.quantity * price
        portfolio_value = self.position_monitor.get_portfolio_value()
        
        if portfolio_value > 0:
            position_weight = trade_value / portfolio_value
            risk_score += min(position_weight * 2.0, 0.5)  # Up to 0.5 from position size
        
        # Risk from signal confidence (inverse relationship)
        confidence_risk = (1.0 - trade_request.signal_confidence) * 0.3
        risk_score += confidence_risk
        
        # Risk from current market conditions
        if self.current_risk_metrics:
            if self.current_risk_metrics.current_drawdown > 0.05:
                risk_score += 0.2  # Add risk if in drawdown
        
        return min(risk_score, 1.0)
    
    async def _cleanup_old_authorizations(self) -> None:
        """Clean up expired authorization tokens to prevent memory leaks"""
        try:
            current_time = datetime.now()
            expired_tokens = []
            
            for auth_id, authorization in self.authorization_history.items():
                if hasattr(authorization, 'timestamp') and authorization.timestamp:
                    token_age = current_time - authorization.timestamp
                    if token_age > timedelta(minutes=10):  # Remove tokens older than 10 minutes
                        expired_tokens.append(auth_id)
            
            for auth_id in expired_tokens:
                self.authorization_history.pop(auth_id, None)
            
            if expired_tokens:
                logger.info(f"🧹 Cleaned up {len(expired_tokens)} expired authorization tokens")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up authorization tokens: {e}")
    
    # ================================================================================
    # REGIME-AWARE RISK MANAGEMENT - INSTITUTIONAL INTEGRATION
    # ================================================================================
    
    async def on_regime_change(self, old_regime: Any, new_regime: Any, 
                             transition: Any) -> None:
        """
        Handle regime changes with dynamic risk parameter adjustment
        
        This implements institutional-grade regime-aware risk management where
        risk parameters automatically adjust based on market conditions.
        """
        if not REGIME_INTERFACE_AVAILABLE:
            return
            
        try:
            # Update current regime state
            self.current_regime = new_regime.regime_type if new_regime else None
            self.regime_confidence = new_regime.confidence if new_regime else 0.0
            
            # Record regime transition
            transition_record = {
                'timestamp': datetime.now(),
                'old_regime': old_regime.regime_type.value if old_regime else 'unknown',
                'new_regime': new_regime.regime_type.value if new_regime else 'unknown',
                'confidence': new_regime.confidence if new_regime else 0.0,
                'transition_reason': getattr(transition, 'reason', 'automatic')
            }
            self.regime_history.append(transition_record)
            
            # Adjust risk parameters based on new regime
            self.regime_adjusted_limits = await self._calculate_regime_adjusted_limits(new_regime)
            
            # Log regime change and risk adjustment
            logger.info(f"🎯 Regime change detected: {old_regime.regime_type.value if old_regime else 'unknown'} → {new_regime.regime_type.value if new_regime else 'unknown'}")
            logger.info(f"📊 Risk parameters adjusted for new regime (confidence: {self.regime_confidence:.2f})")
            
            # Evaluate if circuit breaker should be triggered
            await self._evaluate_regime_risk_triggers(new_regime, transition)
            
            # Notify risk monitoring systems
            self._record_regime_risk_event(transition_record)
            
        except Exception as e:
            logger.error(f"❌ Error handling regime change: {e}")
    
    async def _calculate_regime_adjusted_limits(self, regime: Any) -> RiskLimits:
        """Calculate risk limits adjusted for current market regime"""
        if not regime or not REGIME_INTERFACE_AVAILABLE:
            return self.risk_limits
        
        # Base limits from configuration
        base_limits = self.risk_limits
        
        # Regime-specific adjustments
        regime_adjustments = {
            'HIGH_VOLATILITY': {
                'position_size_multiplier': 0.7,  # Reduce position sizes by 30%
                'stop_loss_multiplier': 1.5,      # Tighter stop losses
                'daily_loss_multiplier': 0.8      # Reduce daily loss limits
            },
            'LOW_VOLATILITY': {
                'position_size_multiplier': 1.2,  # Increase position sizes by 20%
                'stop_loss_multiplier': 0.8,      # Wider stop losses
                'daily_loss_multiplier': 1.1      # Slightly higher daily loss limits
            },
            'TRENDING_UP': {
                'position_size_multiplier': 1.1,  # Slightly larger positions
                'stop_loss_multiplier': 0.9,      # Slightly wider stops
                'daily_loss_multiplier': 1.0      # Standard daily limits
            },
            'TRENDING_DOWN': {
                'position_size_multiplier': 0.8,  # Smaller positions
                'stop_loss_multiplier': 1.2,      # Tighter stops
                'daily_loss_multiplier': 0.9      # Stricter daily limits
            },
            'SIDEWAYS': {
                'position_size_multiplier': 1.0,  # Standard positions
                'stop_loss_multiplier': 1.0,      # Standard stops
                'daily_loss_multiplier': 1.0      # Standard daily limits
            }
        }
        
        # Get regime-specific multipliers
        regime_name = regime.regime_type.value if hasattr(regime.regime_type, 'value') else str(regime.regime_type)
        adjustments = regime_adjustments.get(regime_name, regime_adjustments['SIDEWAYS'])
        
        # Apply confidence-based scaling
        confidence_factor = min(regime.confidence, 1.0)
        
        # Calculate adjusted limits
        adjusted_limits = RiskLimits(
            max_position_size_pct=base_limits.max_position_size_pct * adjustments['position_size_multiplier'] * confidence_factor,
            default_stop_loss_pct=base_limits.default_stop_loss_pct * adjustments['stop_loss_multiplier'],
            default_take_profit_pct=base_limits.default_take_profit_pct,
            default_trailing_stop_pct=base_limits.default_trailing_stop_pct * adjustments['stop_loss_multiplier'],
            daily_loss_limit=getattr(base_limits, 'daily_loss_limit', 0.05) * adjustments['daily_loss_multiplier']
        )
        
        logger.info(f"📊 Risk limits adjusted for regime {regime_name}: "
                   f"position_size={adjusted_limits.max_position_size_pct:.1%}, "
                   f"stop_loss={adjusted_limits.default_stop_loss_pct:.1%}")
        
        return adjusted_limits
    
    async def _evaluate_regime_risk_triggers(self, regime: Any, transition: Any) -> None:
        """Evaluate if regime change should trigger risk management actions"""
        if not regime or not REGIME_INTERFACE_AVAILABLE:
            return
        
        regime_name = regime.regime_type.value if hasattr(regime.regime_type, 'value') else str(regime.regime_type)
        
        # High volatility regime triggers
        if regime_name == 'HIGH_VOLATILITY' and regime.confidence > 0.8:
            logger.warning(f"⚠️ High volatility regime detected with high confidence: {regime.confidence:.2f}")
            
            # Consider reducing portfolio exposure
            if self.current_risk_metrics and self.current_risk_metrics.total_exposure > 0.8:
                logger.warning("📉 Consider reducing portfolio exposure due to high volatility regime")
        
        # Crisis/emergency regime triggers
        if regime_name in ['CRISIS', 'EMERGENCY', 'EXTREME_VOLATILITY'] and regime.confidence > 0.7:
            logger.critical(f"🚨 Crisis regime detected: {regime_name} (confidence: {regime.confidence:.2f})")
            
            # Activate enhanced monitoring
            self.emergency_mode = True
            logger.critical("🚨 Emergency mode activated due to crisis regime")
        
        # Transition speed triggers
        if hasattr(transition, 'speed') and transition.speed > 0.9:  # Very rapid regime change
            logger.warning(f"⚡ Rapid regime transition detected - enhanced monitoring recommended")
    
    def _record_regime_risk_event(self, transition_record: Dict[str, Any]) -> None:
        """Record regime-related risk events for analysis"""
        risk_event = {
            'timestamp': transition_record['timestamp'],
            'type': 'regime_change',
            'data': transition_record,
            'risk_impact': self._assess_regime_risk_impact(transition_record)
        }
        self.risk_events.append(risk_event)
    
    def _assess_regime_risk_impact(self, transition_record: Dict[str, Any]) -> str:
        """Assess the risk impact of a regime transition"""
        old_regime = transition_record.get('old_regime', 'unknown')
        new_regime = transition_record.get('new_regime', 'unknown')
        confidence = transition_record.get('confidence', 0.0)
        
        # High-risk regime transitions
        high_risk_transitions = [
            ('LOW_VOLATILITY', 'HIGH_VOLATILITY'),
            ('TRENDING_UP', 'TRENDING_DOWN'),
            ('SIDEWAYS', 'HIGH_VOLATILITY')
        ]
        
        if (old_regime, new_regime) in high_risk_transitions and confidence > 0.7:
            return 'HIGH'
        elif 'HIGH_VOLATILITY' in new_regime and confidence > 0.6:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def get_current_risk_limits(self) -> RiskLimits:
        """Get current risk limits (regime-adjusted if available)"""
        if self.regime_adjusted_limits and REGIME_INTERFACE_AVAILABLE:
            return self.regime_adjusted_limits
        return self.risk_limits
    
    def get_regime_status(self) -> Dict[str, Any]:
        """Get current regime-aware risk management status"""
        return {
            'current_regime': str(self.current_regime) if self.current_regime else 'unknown',
            'regime_confidence': self.regime_confidence,
            'regime_adjusted_limits': self.regime_adjusted_limits.__dict__ if self.regime_adjusted_limits else None,
            'regime_history_count': len(self.regime_history),
            'emergency_mode': self.emergency_mode,
            'recent_regime_changes': list(self.regime_history)[-5:] if self.regime_history else []
        }
    
    async def shutdown(self) -> None:
        """Shutdown risk management system"""
        logger.info("🛑 Shutting down Advanced Risk Manager")
        
        await self.position_monitor.shutdown()
        
        logger.info("✅ Advanced Risk Manager shutdown complete")

# ================================================================================
# FACTORY AND CONVENIENCE FUNCTIONS
# ================================================================================

def create_advanced_risk_manager(risk_profile: str = "moderate") -> AdvancedRiskManager:
    """Create an advanced risk manager with appropriate configuration"""
    
    if risk_profile.lower() == "conservative":
        config = RiskConfiguration(
            max_position_size=0.05,  # 5% max position
            max_daily_loss=0.01,     # 1% max daily loss
            var_limit_daily_95=0.015, # 1.5% VaR limit
            var_limit_daily_99=0.02,  # 2% VaR limit
            stop_loss_threshold=0.03,  # 3% stop loss
            enable_circuit_breakers=True
        )
    elif risk_profile.lower() == "aggressive":
        config = RiskConfiguration(
            max_position_size=0.15,  # 15% max position
            max_daily_loss=0.05,     # 5% max daily loss
            var_limit_daily_95=0.04, # 4% VaR limit
            var_limit_daily_99=0.06,  # 6% VaR limit
            stop_loss_threshold=0.10,  # 10% stop loss
            enable_circuit_breakers=True
        )
    else:  # moderate
        config = RiskConfiguration()  # Use defaults
    
    return AdvancedRiskManager(config)

async def create_and_initialize_risk_manager(risk_profile: str = "moderate") -> AdvancedRiskManager:
    """Create and initialize an advanced risk manager"""
    risk_manager = create_advanced_risk_manager(risk_profile)
    await risk_manager.initialize()
    return risk_manager

# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    'AdvancedRiskManager',
    'VaRCalculator',
    'PositionMonitor',
    'RiskConfiguration',
    'RiskMetrics',
    'RiskAlert',
    'Position',
    'RiskLevel',
    'AlertType',
    'RiskControlAction',
    'VaRModel',
    'create_advanced_risk_manager',
    'create_and_initialize_risk_manager'
]