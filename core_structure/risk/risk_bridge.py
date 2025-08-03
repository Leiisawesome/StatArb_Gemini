"""
RiskBridge: Production ↔ Backtesting Risk Management Integration

This module provides a bridge between production risk management systems and backtesting
risk requirements. It ensures risk management consistency between production and
backtesting environments.

Key Features:
- Production-to-backtesting risk management bridging
- VaR (Value at Risk) calculation and monitoring
- Position limits and concentration risk management
- Real-time risk monitoring and alerting
- Risk-adjusted performance metrics
- Integration with ExecutionBridge for risk-aware execution
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import json
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

# Core system imports
try:
    from ..infrastructure.config_manager import ConfigManager
    from ..infrastructure.message_bus import MessageBus
    from ..infrastructure.metrics_collector import MetricsCollector
except ImportError:
    ConfigManager = None
    MessageBus = None
    MetricsCollector = None

# Risk management imports
try:
    from .risk_manager import RiskManager, RiskLimits
    from .stop_loss_manager import StopLossManager
    from .var_calculator import VaRCalculator
except ImportError:
    RiskManager = None
    RiskLimits = None
    StopLossManager = None
    VaRCalculator = None

logger = logging.getLogger(__name__)

class RiskMode(Enum):
    """Risk management modes for different environments"""
    PRODUCTION = "production"
    BACKTESTING = "backtesting"
    SIMULATION = "simulation"
    PAPER_TRADING = "paper_trading"

class RiskLevel(Enum):
    """Risk levels for monitoring and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskBridgeConfig:
    """Configuration for RiskBridge"""
    
    # Risk mode
    risk_mode: RiskMode = RiskMode.BACKTESTING
    
    # VaR settings
    enable_var_calculation: bool = True
    var_confidence_level: float = 0.95  # 95% confidence
    var_time_horizon: int = 1  # 1 day horizon
    var_method: str = "historical"  # historical, parametric, monte_carlo
    
    # Position limits
    max_position_size: float = 0.1  # 10% max position size
    max_sector_exposure: float = 0.3  # 30% max sector exposure
    max_portfolio_risk: float = 0.02  # 2% max portfolio risk
    
    # Stop-loss settings
    enable_stop_loss: bool = True
    stop_loss_pct: float = 0.05  # 5% stop-loss
    take_profit_pct: float = 0.10  # 10% take-profit
    trailing_stop_pct: float = 0.03  # 3% trailing stop
    
    # Drawdown limits
    max_drawdown: float = 0.15  # 15% max drawdown
    daily_loss_limit: float = 0.05  # 5% daily loss limit
    
    # Volatility limits
    max_volatility: float = 0.25  # 25% max volatility
    
    # Performance settings
    max_concurrent_calculations: int = 10
    calculation_timeout: float = 30.0
    
    # Monitoring settings
    enable_real_time_monitoring: bool = True
    risk_check_interval: float = 1.0  # 1 second
    alert_threshold: float = 0.8  # 80% of limit triggers alert

@dataclass
class RiskMetrics:
    """Risk metrics for a position or portfolio"""
    
    symbol: str
    position_size: float
    current_price: float
    avg_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    var_1d: float
    var_1d_pct: float
    volatility: float
    beta: float
    sharpe_ratio: float
    max_drawdown: float
    risk_level: RiskLevel
    alerts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PortfolioRiskMetrics:
    """Portfolio-level risk metrics"""
    
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    portfolio_var_1d: float
    portfolio_var_1d_pct: float
    portfolio_volatility: float
    portfolio_beta: float
    portfolio_sharpe_ratio: float
    current_drawdown: float
    max_drawdown: float
    daily_pnl: float
    daily_pnl_pct: float
    risk_level: RiskLevel
    position_risks: Dict[str, RiskMetrics] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RiskAlert:
    """Risk alert structure"""
    
    alert_id: str
    alert_type: str  # 'position_limit', 'var_breach', 'drawdown', 'volatility'
    symbol: Optional[str] = None
    severity: RiskLevel = RiskLevel.MEDIUM
    message: str = ""
    current_value: float = 0.0
    limit_value: float = 0.0
    breach_pct: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class VaRResult:
    """VaR calculation result"""
    
    symbol: str
    var_1d: float
    var_1d_pct: float
    var_5d: float
    var_5d_pct: float
    cvar_1d: float
    cvar_1d_pct: float
    confidence_level: float
    method: str
    calculation_time: float
    timestamp: datetime = field(default_factory=datetime.now)

class RiskBridge:
    """Bridge between production and backtesting risk management systems"""
    
    def __init__(self, config: Optional[RiskBridgeConfig] = None):
        """Initialize RiskBridge"""
        self.config = config or RiskBridgeConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Performance tracking
        self._performance_stats = {
            'total_risk_checks': 0,
            'total_alerts': 0,
            'total_var_calculations': 0,
            'total_calculation_time': 0.0,
            'avg_calculation_time': 0.0,
            'risk_checks_per_second': 0.0
        }
        
        # Risk tracking
        self._risk_alerts = []
        self._position_risks = {}
        self._portfolio_risks = {}
        self._var_results = {}
        
        # Initialize components
        self._initialize_components()
        
        # Thread pool for concurrent calculations
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_calculations)
        
        self.logger.info(f"RiskBridge initialized in {self.config.risk_mode.value} mode")
    
    def _initialize_components(self):
        """Initialize risk management components"""
        try:
            # Risk manager
            if RiskManager and RiskLimits:
                risk_limits = RiskLimits()
                risk_limits.max_position_size = self.config.max_position_size
                risk_limits.max_sector_exposure = self.config.max_sector_exposure
                risk_limits.max_portfolio_risk = self.config.max_portfolio_risk
                risk_limits.stop_loss_pct = self.config.stop_loss_pct
                risk_limits.take_profit_pct = self.config.take_profit_pct
                risk_limits.trailing_stop_pct = self.config.trailing_stop_pct
                risk_limits.max_drawdown = self.config.max_drawdown
                risk_limits.daily_loss_limit = self.config.daily_loss_limit
                risk_limits.max_volatility = self.config.max_volatility
                risk_limits.var_confidence = self.config.var_confidence_level
                
                self.risk_manager = RiskManager(risk_limits)
                self.logger.info("RiskManager initialized")
            else:
                self.risk_manager = None
                self.logger.warning("RiskManager not available")
            
            # Stop-loss manager
            if StopLossManager:
                self.stop_loss_manager = StopLossManager()
                self.logger.info("StopLossManager initialized")
            else:
                self.stop_loss_manager = None
                self.logger.warning("StopLossManager not available")
            
            # VaR calculator
            if VaRCalculator:
                self.var_calculator = VaRCalculator()
                self.logger.info("VaRCalculator initialized")
            else:
                self.var_calculator = None
                self.logger.warning("VaRCalculator not available")
            
        except Exception as e:
            self.logger.error(f"Error initializing risk components: {e}")
            raise
    
    def calculate_position_risk(
        self,
        symbol: str,
        position_size: float,
        current_price: float,
        avg_price: float,
        market_data: Optional[pd.DataFrame] = None,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> RiskMetrics:
        """Calculate risk metrics for a position"""
        start_time = time.time()
        
        try:
            # Calculate basic metrics
            unrealized_pnl = (current_price - avg_price) * position_size
            unrealized_pnl_pct = (current_price - avg_price) / avg_price if avg_price > 0 else 0.0
            
            # Calculate VaR if enabled and data available
            var_1d = 0.0
            var_1d_pct = 0.0
            volatility = 0.0
            beta = 1.0
            sharpe_ratio = 0.0
            
            if self.config.enable_var_calculation and market_data is not None:
                var_result = self._calculate_var(symbol, market_data, position_size, current_price)
                var_1d = var_result.var_1d
                var_1d_pct = var_result.var_1d_pct
                volatility = self._calculate_volatility(market_data)
                beta = self._calculate_beta(market_data, portfolio_state)
                sharpe_ratio = self._calculate_sharpe_ratio(unrealized_pnl_pct, volatility)
            
            # Determine risk level
            risk_level = self._determine_risk_level(
                unrealized_pnl_pct, var_1d_pct, volatility, position_size
            )
            
            # Generate alerts
            alerts = self._generate_position_alerts(
                symbol, position_size, unrealized_pnl_pct, var_1d_pct, volatility
            )
            
            # Create risk metrics
            risk_metrics = RiskMetrics(
                symbol=symbol,
                position_size=position_size,
                current_price=current_price,
                avg_price=avg_price,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                var_1d=var_1d,
                var_1d_pct=var_1d_pct,
                volatility=volatility,
                beta=beta,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=0.0,  # Will be calculated at portfolio level
                risk_level=risk_level,
                alerts=alerts
            )
            
            # Store position risk
            self._position_risks[symbol] = risk_metrics
            
            # Update performance stats
            calculation_time = time.time() - start_time
            self._update_performance_stats(calculation_time)
            
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating position risk for {symbol}: {e}")
            return self._create_error_risk_metrics(symbol, str(e), time.time() - start_time)
    
    def calculate_portfolio_risk(
        self,
        positions: Dict[str, Dict[str, Any]],
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> PortfolioRiskMetrics:
        """Calculate portfolio-level risk metrics"""
        start_time = time.time()
        
        try:
            # Calculate position risks
            position_risks = {}
            total_value = 0.0
            total_pnl = 0.0
            
            for symbol, position in positions.items():
                position_size = position.get('quantity', 0)
                current_price = position.get('current_price', 0.0)
                avg_price = position.get('avg_price', 0.0)
                
                if position_size != 0 and current_price > 0:
                    symbol_market_data = market_data.get(symbol) if market_data else None
                    risk_metrics = self.calculate_position_risk(
                        symbol, position_size, current_price, avg_price, 
                        symbol_market_data, portfolio_state
                    )
                    position_risks[symbol] = risk_metrics
                    
                    position_value = position_size * current_price
                    total_value += position_value
                    total_pnl += risk_metrics.unrealized_pnl
            
            # Calculate portfolio-level metrics
            total_pnl_pct = total_pnl / total_value if total_value > 0 else 0.0
            
            # Portfolio VaR
            portfolio_var_1d = 0.0
            portfolio_var_1d_pct = 0.0
            if self.config.enable_var_calculation and market_data:
                portfolio_var_1d = self._calculate_portfolio_var(position_risks, market_data)
                portfolio_var_1d_pct = portfolio_var_1d / total_value if total_value > 0 else 0.0
            
            # Portfolio volatility and beta
            portfolio_volatility = self._calculate_portfolio_volatility(position_risks)
            portfolio_beta = self._calculate_portfolio_beta(position_risks, portfolio_state)
            portfolio_sharpe_ratio = self._calculate_portfolio_sharpe_ratio(total_pnl_pct, portfolio_volatility)
            
            # Drawdown calculation
            current_drawdown = self._calculate_current_drawdown(total_value, portfolio_state)
            max_drawdown = self._calculate_max_drawdown(total_value, portfolio_state)
            
            # Daily PnL
            daily_pnl = portfolio_state.get('daily_pnl', 0.0) if portfolio_state else 0.0
            daily_pnl_pct = daily_pnl / total_value if total_value > 0 else 0.0
            
            # Determine portfolio risk level
            portfolio_risk_level = self._determine_portfolio_risk_level(
                total_pnl_pct, portfolio_var_1d_pct, portfolio_volatility, current_drawdown
            )
            
            # Generate portfolio alerts
            portfolio_alerts = self._generate_portfolio_alerts(
                total_pnl_pct, portfolio_var_1d_pct, portfolio_volatility, current_drawdown
            )
            
            # Create portfolio risk metrics
            portfolio_metrics = PortfolioRiskMetrics(
                total_value=total_value,
                total_pnl=total_pnl,
                total_pnl_pct=total_pnl_pct,
                portfolio_var_1d=portfolio_var_1d,
                portfolio_var_1d_pct=portfolio_var_1d_pct,
                portfolio_volatility=portfolio_volatility,
                portfolio_beta=portfolio_beta,
                portfolio_sharpe_ratio=portfolio_sharpe_ratio,
                current_drawdown=current_drawdown,
                max_drawdown=max_drawdown,
                daily_pnl=daily_pnl,
                daily_pnl_pct=daily_pnl_pct,
                risk_level=portfolio_risk_level,
                position_risks=position_risks,
                alerts=portfolio_alerts
            )
            
            # Store portfolio risk
            self._portfolio_risks = portfolio_metrics
            
            # Update performance stats
            calculation_time = time.time() - start_time
            self._update_performance_stats(calculation_time)
            
            return portfolio_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio risk: {e}")
            return self._create_error_portfolio_metrics(str(e), time.time() - start_time)
    
    def check_risk_limits(
        self,
        order: Any,  # ExecutionOrder from ExecutionBridge
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """Check if an order violates risk limits"""
        try:
            violations = []
            
            # Check position size limit
            if portfolio_state:
                portfolio_value = portfolio_state.get('total_value', 0)
                order_value = order.quantity * (order.price or 100)
                position_pct = order_value / portfolio_value if portfolio_value > 0 else 0.0
                
                if position_pct > self.config.max_position_size:
                    violations.append(f"Position size {position_pct:.2%} exceeds limit {self.config.max_position_size:.2%}")
            
            # Check sector exposure (if sector info available)
            if hasattr(order, 'sector') and order.sector:
                sector_exposure = self._calculate_sector_exposure(order.sector, portfolio_state)
                if sector_exposure > self.config.max_sector_exposure:
                    violations.append(f"Sector exposure {sector_exposure:.2%} exceeds limit {self.config.max_sector_exposure:.2%}")
            
            # Check portfolio risk limit
            if portfolio_state:
                current_risk = portfolio_state.get('current_risk', 0.0)
                if current_risk > self.config.max_portfolio_risk:
                    violations.append(f"Portfolio risk {current_risk:.2%} exceeds limit {self.config.max_portfolio_risk:.2%}")
            
            return len(violations) == 0, violations
            
        except Exception as e:
            self.logger.error(f"Error checking risk limits: {e}")
            return False, [f"Risk limit check error: {e}"]
    
    def create_stop_loss(
        self,
        symbol: str,
        quantity: int,
        avg_price: float,
        stop_loss_pct: Optional[float] = None
    ) -> Optional[Any]:
        """Create stop-loss order"""
        if not self.stop_loss_manager or not self.config.enable_stop_loss:
            return None
        
        try:
            stop_pct = stop_loss_pct or self.config.stop_loss_pct
            return self.stop_loss_manager.create_stop_loss(symbol, quantity, avg_price, stop_pct)
        except Exception as e:
            self.logger.error(f"Error creating stop-loss for {symbol}: {e}")
            return None
    
    def create_take_profit(
        self,
        symbol: str,
        quantity: int,
        avg_price: float,
        take_profit_pct: Optional[float] = None
    ) -> Optional[Any]:
        """Create take-profit order"""
        if not self.stop_loss_manager:
            return None
        
        try:
            profit_pct = take_profit_pct or self.config.take_profit_pct
            return self.stop_loss_manager.create_take_profit(symbol, quantity, avg_price, profit_pct)
        except Exception as e:
            self.logger.error(f"Error creating take-profit for {symbol}: {e}")
            return None
    
    def _calculate_var(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        position_size: float,
        current_price: float
    ) -> VaRResult:
        """Calculate VaR for a position"""
        start_time = time.time()
        
        try:
            if self.var_calculator:
                # Use VaR calculator if available
                var_1d = self.var_calculator.calculate_var(
                    market_data, 
                    confidence_level=self.config.var_confidence_level,
                    time_horizon=1
                )
            else:
                # Simple historical VaR calculation
                returns = market_data['close'].pct_change().dropna()
                var_1d = np.percentile(returns, (1 - self.config.var_confidence_level) * 100)
            
            # Convert to dollar amount
            var_1d_dollar = abs(var_1d) * position_size * current_price
            var_1d_pct = abs(var_1d)
            
            # Calculate 5-day VaR (simple scaling)
            var_5d = var_1d * np.sqrt(5)
            var_5d_pct = var_1d_pct * np.sqrt(5)
            
            # Calculate CVaR (Conditional VaR)
            if self.var_calculator:
                cvar_1d = self.var_calculator.calculate_cvar(
                    market_data,
                    confidence_level=self.config.var_confidence_level,
                    time_horizon=1
                )
            else:
                # Simple CVaR calculation
                returns = market_data['close'].pct_change().dropna()
                var_threshold = np.percentile(returns, (1 - self.config.var_confidence_level) * 100)
                tail_returns = returns[returns <= var_threshold]
                cvar_1d = tail_returns.mean() if len(tail_returns) > 0 else var_1d
            
            cvar_1d_dollar = abs(cvar_1d) * position_size * current_price
            cvar_1d_pct = abs(cvar_1d)
            
            calculation_time = time.time() - start_time
            
            return VaRResult(
                symbol=symbol,
                var_1d=var_1d_dollar,
                var_1d_pct=var_1d_pct,
                var_5d=var_5d * position_size * current_price,
                var_5d_pct=var_5d_pct,
                cvar_1d=cvar_1d_dollar,
                cvar_1d_pct=cvar_1d_pct,
                confidence_level=self.config.var_confidence_level,
                method=self.config.var_method,
                calculation_time=calculation_time
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating VaR for {symbol}: {e}")
            return VaRResult(
                symbol=symbol,
                var_1d=0.0,
                var_1d_pct=0.0,
                var_5d=0.0,
                var_5d_pct=0.0,
                cvar_1d=0.0,
                cvar_1d_pct=0.0,
                confidence_level=self.config.var_confidence_level,
                method="error",
                calculation_time=time.time() - start_time
            )
    
    def _calculate_volatility(self, market_data: pd.DataFrame) -> float:
        """Calculate volatility from market data"""
        try:
            returns = market_data['close'].pct_change().dropna()
            return returns.std() * np.sqrt(252)  # Annualized volatility
        except Exception as e:
            self.logger.error(f"Error calculating volatility: {e}")
            return 0.0
    
    def _calculate_beta(
        self,
        market_data: pd.DataFrame,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate beta relative to market"""
        try:
            # Simple beta calculation (would need market data in real implementation)
            return 1.0  # Default to market beta
        except Exception as e:
            self.logger.error(f"Error calculating beta: {e}")
            return 1.0
    
    def _calculate_sharpe_ratio(self, return_pct: float, volatility: float) -> float:
        """Calculate Sharpe ratio"""
        try:
            if volatility > 0:
                return return_pct / volatility
            return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def _calculate_portfolio_var(
        self,
        position_risks: Dict[str, RiskMetrics],
        market_data: Dict[str, pd.DataFrame]
    ) -> float:
        """Calculate portfolio VaR"""
        try:
            # Simple portfolio VaR (sum of individual VaRs)
            # In practice, would need correlation matrix for proper calculation
            total_var = sum(risk.var_1d for risk in position_risks.values())
            return total_var
        except Exception as e:
            self.logger.error(f"Error calculating portfolio VaR: {e}")
            return 0.0
    
    def _calculate_portfolio_volatility(self, position_risks: Dict[str, RiskMetrics]) -> float:
        """Calculate portfolio volatility"""
        try:
            # Simple weighted average volatility
            total_value = sum(risk.position_size * risk.current_price for risk in position_risks.values())
            if total_value > 0:
                weighted_vol = sum(
                    (risk.position_size * risk.current_price / total_value) * risk.volatility
                    for risk in position_risks.values()
                )
                return weighted_vol
            return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating portfolio volatility: {e}")
            return 0.0
    
    def _calculate_portfolio_beta(
        self,
        position_risks: Dict[str, RiskMetrics],
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate portfolio beta"""
        try:
            # Simple weighted average beta
            total_value = sum(risk.position_size * risk.current_price for risk in position_risks.values())
            if total_value > 0:
                weighted_beta = sum(
                    (risk.position_size * risk.current_price / total_value) * risk.beta
                    for risk in position_risks.values()
                )
                return weighted_beta
            return 1.0
        except Exception as e:
            self.logger.error(f"Error calculating portfolio beta: {e}")
            return 1.0
    
    def _calculate_portfolio_sharpe_ratio(self, return_pct: float, volatility: float) -> float:
        """Calculate portfolio Sharpe ratio"""
        return self._calculate_sharpe_ratio(return_pct, volatility)
    
    def _calculate_current_drawdown(
        self,
        current_value: float,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate current drawdown"""
        try:
            if portfolio_state:
                peak_value = portfolio_state.get('peak_value', current_value)
                if peak_value > 0:
                    return (peak_value - current_value) / peak_value
            return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating current drawdown: {e}")
            return 0.0
    
    def _calculate_max_drawdown(
        self,
        current_value: float,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate maximum drawdown"""
        try:
            if portfolio_state:
                return portfolio_state.get('max_drawdown', 0.0)
            return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    def _calculate_sector_exposure(
        self,
        sector: str,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate sector exposure"""
        try:
            # Simple sector exposure calculation
            # In practice, would need sector information for all positions
            return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating sector exposure: {e}")
            return 0.0
    
    def _determine_risk_level(
        self,
        pnl_pct: float,
        var_pct: float,
        volatility: float,
        position_size: float
    ) -> RiskLevel:
        """Determine risk level for a position"""
        try:
            # Check for critical risk
            if (pnl_pct <= -self.config.stop_loss_pct or 
                var_pct >= self.config.max_portfolio_risk or
                volatility >= self.config.max_volatility):
                return RiskLevel.CRITICAL
            
            # Check for high risk
            if (pnl_pct <= -self.config.stop_loss_pct * 0.8 or
                var_pct >= self.config.max_portfolio_risk * 0.8 or
                volatility >= self.config.max_volatility * 0.8):
                return RiskLevel.HIGH
            
            # Check for medium risk
            if (pnl_pct <= -self.config.stop_loss_pct * 0.6 or
                var_pct >= self.config.max_portfolio_risk * 0.6 or
                volatility >= self.config.max_volatility * 0.6):
                return RiskLevel.MEDIUM
            
            return RiskLevel.LOW
            
        except Exception as e:
            self.logger.error(f"Error determining risk level: {e}")
            return RiskLevel.MEDIUM
    
    def _determine_portfolio_risk_level(
        self,
        pnl_pct: float,
        var_pct: float,
        volatility: float,
        drawdown: float
    ) -> RiskLevel:
        """Determine risk level for portfolio"""
        try:
            # Check for critical risk
            if (drawdown >= self.config.max_drawdown or
                pnl_pct <= -self.config.daily_loss_limit or
                var_pct >= self.config.max_portfolio_risk):
                return RiskLevel.CRITICAL
            
            # Check for high risk
            if (drawdown >= self.config.max_drawdown * 0.8 or
                pnl_pct <= -self.config.daily_loss_limit * 0.8 or
                var_pct >= self.config.max_portfolio_risk * 0.8):
                return RiskLevel.HIGH
            
            # Check for medium risk
            if (drawdown >= self.config.max_drawdown * 0.6 or
                pnl_pct <= -self.config.daily_loss_limit * 0.6 or
                var_pct >= self.config.max_portfolio_risk * 0.6):
                return RiskLevel.MEDIUM
            
            return RiskLevel.LOW
            
        except Exception as e:
            self.logger.error(f"Error determining portfolio risk level: {e}")
            return RiskLevel.MEDIUM
    
    def _generate_position_alerts(
        self,
        symbol: str,
        position_size: float,
        pnl_pct: float,
        var_pct: float,
        volatility: float
    ) -> List[str]:
        """Generate alerts for position"""
        alerts = []
        
        # Position size alerts
        if position_size > self.config.max_position_size:
            alerts.append(f"Position size {position_size:.2%} exceeds limit {self.config.max_position_size:.2%}")
        
        # PnL alerts
        if pnl_pct <= -self.config.stop_loss_pct:
            alerts.append(f"Stop-loss triggered: {pnl_pct:.2%}")
        elif pnl_pct >= self.config.take_profit_pct:
            alerts.append(f"Take-profit triggered: {pnl_pct:.2%}")
        
        # VaR alerts
        if var_pct >= self.config.max_portfolio_risk:
            alerts.append(f"VaR {var_pct:.2%} exceeds limit {self.config.max_portfolio_risk:.2%}")
        
        # Volatility alerts
        if volatility >= self.config.max_volatility:
            alerts.append(f"Volatility {volatility:.2%} exceeds limit {self.config.max_volatility:.2%}")
        
        return alerts
    
    def _generate_portfolio_alerts(
        self,
        pnl_pct: float,
        var_pct: float,
        volatility: float,
        drawdown: float
    ) -> List[str]:
        """Generate alerts for portfolio"""
        alerts = []
        
        # Drawdown alerts
        if drawdown >= self.config.max_drawdown:
            alerts.append(f"Drawdown {drawdown:.2%} exceeds limit {self.config.max_drawdown:.2%}")
        
        # Daily loss alerts
        if pnl_pct <= -self.config.daily_loss_limit:
            alerts.append(f"Daily loss {pnl_pct:.2%} exceeds limit {self.config.daily_loss_limit:.2%}")
        
        # Portfolio VaR alerts
        if var_pct >= self.config.max_portfolio_risk:
            alerts.append(f"Portfolio VaR {var_pct:.2%} exceeds limit {self.config.max_portfolio_risk:.2%}")
        
        # Portfolio volatility alerts
        if volatility >= self.config.max_volatility:
            alerts.append(f"Portfolio volatility {volatility:.2%} exceeds limit {self.config.max_volatility:.2%}")
        
        return alerts
    
    def _create_error_risk_metrics(self, symbol: str, error_message: str, calculation_time: float) -> RiskMetrics:
        """Create error risk metrics for failed calculations"""
        return RiskMetrics(
            symbol=symbol,
            position_size=0.0,
            current_price=0.0,
            avg_price=0.0,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            var_1d=0.0,
            var_1d_pct=0.0,
            volatility=0.0,
            beta=1.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            risk_level=RiskLevel.HIGH,
            alerts=[f"Calculation error: {error_message}"]
        )
    
    def _create_error_portfolio_metrics(self, error_message: str, calculation_time: float) -> PortfolioRiskMetrics:
        """Create error portfolio metrics for failed calculations"""
        return PortfolioRiskMetrics(
            total_value=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            portfolio_var_1d=0.0,
            portfolio_var_1d_pct=0.0,
            portfolio_volatility=0.0,
            portfolio_beta=1.0,
            portfolio_sharpe_ratio=0.0,
            current_drawdown=0.0,
            max_drawdown=0.0,
            daily_pnl=0.0,
            daily_pnl_pct=0.0,
            risk_level=RiskLevel.HIGH,
            alerts=[f"Calculation error: {error_message}"]
        )
    
    def _update_performance_stats(self, calculation_time: float):
        """Update performance statistics"""
        self._performance_stats['total_risk_checks'] += 1
        self._performance_stats['total_calculation_time'] += calculation_time
        
        # Update average calculation time
        self._performance_stats['avg_calculation_time'] = (
            self._performance_stats['total_calculation_time'] / self._performance_stats['total_risk_checks']
        )
        
        # Update checks per second
        if self._performance_stats['total_calculation_time'] > 0:
            self._performance_stats['risk_checks_per_second'] = (
                self._performance_stats['total_risk_checks'] / self._performance_stats['total_calculation_time']
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._performance_stats.copy()
    
    def get_risk_alerts(self) -> List[RiskAlert]:
        """Get current risk alerts"""
        return self._risk_alerts.copy()
    
    def get_position_risks(self) -> Dict[str, RiskMetrics]:
        """Get current position risks"""
        return self._position_risks.copy()
    
    def get_portfolio_risks(self) -> Optional[PortfolioRiskMetrics]:
        """Get current portfolio risks"""
        return self._portfolio_risks
    
    def reset_performance_stats(self):
        """Reset performance statistics"""
        self._performance_stats = {
            'total_risk_checks': 0,
            'total_alerts': 0,
            'total_var_calculations': 0,
            'total_calculation_time': 0.0,
            'avg_calculation_time': 0.0,
            'risk_checks_per_second': 0.0
        }
    
    def shutdown(self):
        """Shutdown the risk bridge"""
        if self._executor:
            self._executor.shutdown(wait=True)
        self.logger.info("RiskBridge shutdown complete")

def create_risk_bridge(config: Optional[RiskBridgeConfig] = None) -> RiskBridge:
    """Create a RiskBridge instance"""
    return RiskBridge(config)

def calculate_risk_for_backtesting(
    positions: Dict[str, Dict[str, Any]],
    market_data: Optional[Dict[str, pd.DataFrame]] = None,
    portfolio_state: Optional[Dict[str, Any]] = None,
    bridge: Optional[RiskBridge] = None
) -> PortfolioRiskMetrics:
    """Convenience function for backtesting risk calculation"""
    if bridge is None:
        config = RiskBridgeConfig(risk_mode=RiskMode.BACKTESTING)
        bridge = RiskBridge(config)
    
    return bridge.calculate_portfolio_risk(positions, market_data, portfolio_state) 