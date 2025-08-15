"""
High-Performance Risk Manager
============================

Ultra-fast risk management system designed for concurrent risk validation
with 50,000+ validations/second and <2ms latency per validation.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import threading
from enum import Enum

logger = logging.getLogger(__name__)

class RiskStatus(Enum):
    """Risk validation status"""
    APPROVED = "approved"
    REJECTED = "rejected"
    WARNING = "warning"

@dataclass
class RiskManagerConfig:
    """Configuration for high-performance risk manager"""
    # Performance targets
    target_validations_per_second: int = 50000
    target_latency_ms: float = 2.0
    max_workers: int = 12
    
    # Risk limits
    max_position_size: float = 0.25
    max_portfolio_risk: float = 0.02
    max_daily_loss: float = 0.05
    max_drawdown: float = 0.15
    
    # Validation settings
    enable_parallel_validation: bool = True
    enable_real_time_monitoring: bool = True
    enable_position_limits: bool = True
    enable_portfolio_limits: bool = True

@dataclass
class RiskValidationResult:
    """Result of risk validation operation"""
    validations_performed: int
    processing_time_ms: float
    validations_per_second: float
    approved_count: int
    rejected_count: int
    warning_count: int
    optimization_techniques_used: List[str] = field(default_factory=list)

class ParallelRiskValidator:
    """Parallel risk validation engine"""
    
    def __init__(self, max_workers: int = 12):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="RiskVal")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_trades_parallel(self, trades: List[Dict[str, Any]], 
                                risk_limits: Dict[str, float]) -> List[Tuple[str, Dict[str, Any]]]:
        """Validate multiple trades in parallel"""
        if len(trades) <= 1:
            # Single trade - process directly
            if trades:
                return [self._validate_single_trade(trades[0], risk_limits)]
            return []
        
        # Multiple trades - parallel processing
        futures = []
        for i, trade in enumerate(trades):
            future = self.executor.submit(self._safe_trade_validation, i, trade, risk_limits)
            futures.append(future)
        
        # Collect results with timeout
        results = []
        for future in as_completed(futures, timeout=2.0):  # 2s timeout
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Risk validation failed: {e}")
                results.append((RiskStatus.REJECTED.value, {"error": str(e)}))
        
        return results
    
    def _safe_trade_validation(self, trade_id: int, trade: Dict[str, Any], 
                              risk_limits: Dict[str, float]) -> Tuple[str, Dict[str, Any]]:
        """Safe wrapper for trade validation"""
        try:
            return self._validate_single_trade(trade, risk_limits)
        except Exception as e:
            self.logger.error(f"Trade validation error for trade {trade_id}: {e}")
            return (RiskStatus.REJECTED.value, {"error": str(e)})
    
    def _validate_single_trade(self, trade: Dict[str, Any], 
                              risk_limits: Dict[str, float]) -> Tuple[str, Dict[str, Any]]:
        """Validate a single trade"""
        # Extract trade details
        symbol = trade.get('symbol', '')
        quantity = trade.get('quantity', 0)
        price = trade.get('price', 0)
        trade_value = abs(quantity * price)
        
        # Position size check
        max_position_value = risk_limits.get('max_position_size', 0.25) * risk_limits.get('portfolio_value', 1000000)
        if trade_value > max_position_value:
            return (RiskStatus.REJECTED.value, {"reason": "position_size_exceeded"})
        
        # Basic validation passed
        return (RiskStatus.APPROVED.value, {"trade_value": trade_value})
    
    def __del__(self):
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

class VectorizedRiskCalculator:
    """Vectorized risk calculations for portfolio metrics"""
    
    @staticmethod
    def calculate_portfolio_var(positions: np.ndarray, returns: np.ndarray, 
                               confidence_level: float = 0.05) -> float:
        """Calculate portfolio VaR using vectorized operations"""
        if len(positions) == 0 or len(returns) == 0:
            return 0.0
        
        # Portfolio value
        portfolio_value = np.sum(np.abs(positions))
        
        # Calculate historical portfolio returns
        if returns.ndim == 1:
            # Single asset
            portfolio_returns = returns
        else:
            # Multiple assets - weight by positions
            weights = positions / (portfolio_value + 1e-10)
            portfolio_returns = np.dot(returns, weights)
        
        # Calculate VaR at confidence level
        if len(portfolio_returns) > 0:
            var = np.percentile(portfolio_returns, confidence_level * 100)
            return abs(var * portfolio_value)
        
        return 0.0
    
    @staticmethod
    def calculate_max_drawdown(pnl_series: np.ndarray) -> float:
        """Calculate maximum drawdown using vectorized operations"""
        if len(pnl_series) == 0:
            return 0.0
        
        # Calculate cumulative P&L
        cumulative_pnl = np.cumsum(pnl_series)
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(cumulative_pnl)
        
        # Calculate drawdowns
        drawdowns = (cumulative_pnl - running_max) / (running_max + 1e-10)
        
        # Return maximum drawdown
        return abs(np.min(drawdowns))
    
    @staticmethod
    def calculate_position_concentration(positions: np.ndarray) -> float:
        """Calculate position concentration using Herfindahl index"""
        if len(positions) == 0:
            return 0.0
        
        # Calculate position weights
        total_value = np.sum(np.abs(positions))
        if total_value == 0:
            return 0.0
        
        weights = np.abs(positions) / total_value
        
        # Herfindahl index
        concentration = np.sum(weights ** 2)
        
        return concentration

class HighPerformanceRiskManager:
    """
    Ultra-fast risk manager designed to achieve 50,000+ validations/second
    with sub-2ms latency using parallel processing and vectorized calculations.
    """
    
    def __init__(self, config: Optional[RiskManagerConfig] = None):
        self.config = config or RiskManagerConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # High-performance components
        if self.config.enable_parallel_validation:
            self.parallel_validator = ParallelRiskValidator(self.config.max_workers)
        
        self.risk_calculator = VectorizedRiskCalculator()
        
        # Risk monitoring
        self.current_positions: Dict[str, float] = {}
        self.portfolio_pnl: List[float] = []
        self.risk_metrics: Dict[str, float] = {}
        self.positions_lock = threading.RLock()
        
        # Performance tracking
        self.validation_times: List[float] = []
        self.validation_counts: List[int] = []
        self.total_validations = 0
        
        self.logger.info(f"HighPerformanceRiskManager initialized - Target: {self.config.target_validations_per_second} validations/sec")
    
    def validate_trades(self, trades: List[Dict[str, Any]], 
                       portfolio_state: Optional[Dict[str, Any]] = None) -> RiskValidationResult:
        """
        Validate multiple trades with high-throughput processing
        """
        start_time = time.perf_counter()
        optimization_techniques = []
        
        try:
            if not trades:
                return self._create_empty_result(start_time)
            
            # Prepare risk limits
            risk_limits = self._prepare_risk_limits(portfolio_state)
            
            # Choose validation strategy
            if len(trades) > 1 and self.config.enable_parallel_validation:
                # Parallel validation for multiple trades
                validation_results = self.parallel_validator.validate_trades_parallel(trades, risk_limits)
                optimization_techniques.append("parallel_validation")
            else:
                # Sequential validation
                validation_results = []
                for trade in trades:
                    result = self._validate_single_trade_direct(trade, risk_limits)
                    validation_results.append(result)
                optimization_techniques.append("sequential_validation")
            
            # Apply vectorized portfolio risk checks
            if self.config.enable_portfolio_limits:
                self._validate_portfolio_risk_vectorized(trades, portfolio_state)
                optimization_techniques.append("vectorized_portfolio_risk")
            
            return self._create_result(start_time, validation_results, optimization_techniques)
            
        except Exception as e:
            self.logger.error(f"High-performance risk validation failed: {e}")
            return self._create_error_result(start_time, len(trades))
    
    def _prepare_risk_limits(self, portfolio_state: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Prepare risk limits for validation"""
        limits = {
            'max_position_size': self.config.max_position_size,
            'max_portfolio_risk': self.config.max_portfolio_risk,
            'max_daily_loss': self.config.max_daily_loss,
            'max_drawdown': self.config.max_drawdown
        }
        
        if portfolio_state:
            limits['portfolio_value'] = portfolio_state.get('total_value', 1000000)
            limits['current_risk'] = portfolio_state.get('current_risk', 0.0)
            limits['daily_pnl'] = portfolio_state.get('daily_pnl', 0.0)
        else:
            limits['portfolio_value'] = 1000000  # Default
            limits['current_risk'] = 0.0
            limits['daily_pnl'] = 0.0
        
        return limits
    
    def _validate_single_trade_direct(self, trade: Dict[str, Any], 
                                    risk_limits: Dict[str, float]) -> Tuple[str, Dict[str, Any]]:
        """Direct single trade validation"""
        try:
            # Extract trade details
            symbol = trade.get('symbol', '')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            trade_value = abs(quantity * price)
            
            # Position size validation
            max_position_value = risk_limits['max_position_size'] * risk_limits['portfolio_value']
            if trade_value > max_position_value:
                return (RiskStatus.REJECTED.value, {
                    "reason": "position_size_exceeded",
                    "trade_value": trade_value,
                    "max_allowed": max_position_value
                })
            
            # Portfolio risk validation
            portfolio_value = risk_limits['portfolio_value']
            risk_contribution = trade_value / portfolio_value
            
            if risk_limits['current_risk'] + risk_contribution > risk_limits['max_portfolio_risk']:
                return (RiskStatus.WARNING.value, {
                    "reason": "portfolio_risk_warning",
                    "risk_contribution": risk_contribution
                })
            
            # Daily loss validation
            if risk_limits['daily_pnl'] < -risk_limits['max_daily_loss'] * portfolio_value:
                return (RiskStatus.REJECTED.value, {
                    "reason": "daily_loss_limit_exceeded",
                    "daily_pnl": risk_limits['daily_pnl']
                })
            
            return (RiskStatus.APPROVED.value, {
                "trade_value": trade_value,
                "risk_contribution": risk_contribution
            })
            
        except Exception as e:
            return (RiskStatus.REJECTED.value, {"error": str(e)})
    
    def _validate_portfolio_risk_vectorized(self, trades: List[Dict[str, Any]], 
                                          portfolio_state: Optional[Dict[str, Any]]) -> None:
        """Validate portfolio-level risk using vectorized operations"""
        if not portfolio_state:
            return
        
        try:
            # Get current positions
            positions = np.array(list(self.current_positions.values()))
            
            if len(positions) > 0:
                # Calculate portfolio concentration
                concentration = self.risk_calculator.calculate_position_concentration(positions)
                
                # Calculate VaR if we have return data
                if 'returns' in portfolio_state:
                    returns = np.array(portfolio_state['returns'])
                    portfolio_var = self.risk_calculator.calculate_portfolio_var(positions, returns)
                    self.risk_metrics['portfolio_var'] = portfolio_var
                
                # Calculate max drawdown
                if self.portfolio_pnl:
                    pnl_array = np.array(self.portfolio_pnl)
                    max_dd = self.risk_calculator.calculate_max_drawdown(pnl_array)
                    self.risk_metrics['max_drawdown'] = max_dd
                
                self.risk_metrics['concentration'] = concentration
            
        except Exception as e:
            self.logger.warning(f"Portfolio risk validation failed: {e}")
    
    def update_positions(self, symbol: str, quantity: float, price: float) -> None:
        """Update position tracking for risk monitoring"""
        with self.positions_lock:
            position_value = quantity * price
            self.current_positions[symbol] = self.current_positions.get(symbol, 0) + position_value
    
    def update_portfolio_pnl(self, pnl: float) -> None:
        """Update portfolio P&L for drawdown calculation"""
        self.portfolio_pnl.append(pnl)
        
        # Keep only recent P&L (last 1000 points)
        if len(self.portfolio_pnl) > 1000:
            self.portfolio_pnl = self.portfolio_pnl[-1000:]
    
    def _create_result(self, start_time: float, validation_results: List[Tuple[str, Dict[str, Any]]], 
                      optimization_techniques: List[str]) -> RiskValidationResult:
        """Create risk validation result with performance metrics"""
        processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
        validations_performed = len(validation_results)
        
        # Update performance tracking
        self.validation_times.append(processing_time)
        self.validation_counts.append(validations_performed)
        self.total_validations += validations_performed
        
        # Keep only recent measurements
        if len(self.validation_times) > 1000:
            self.validation_times = self.validation_times[-1000:]
            self.validation_counts = self.validation_counts[-1000:]
        
        # Calculate validations per second
        validations_per_second = (validations_performed / (processing_time / 1000)) if processing_time > 0 else 0
        
        # Count results by status
        approved_count = sum(1 for status, _ in validation_results if status == RiskStatus.APPROVED.value)
        rejected_count = sum(1 for status, _ in validation_results if status == RiskStatus.REJECTED.value)
        warning_count = sum(1 for status, _ in validation_results if status == RiskStatus.WARNING.value)
        
        return RiskValidationResult(
            validations_performed=validations_performed,
            processing_time_ms=processing_time,
            validations_per_second=validations_per_second,
            approved_count=approved_count,
            rejected_count=rejected_count,
            warning_count=warning_count,
            optimization_techniques_used=optimization_techniques
        )
    
    def _create_empty_result(self, start_time: float) -> RiskValidationResult:
        """Create empty result for no trades"""
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return RiskValidationResult(
            validations_performed=0,
            processing_time_ms=processing_time,
            validations_per_second=0.0,
            approved_count=0,
            rejected_count=0,
            warning_count=0,
            optimization_techniques_used=["no_trades"]
        )
    
    def _create_error_result(self, start_time: float, trade_count: int) -> RiskValidationResult:
        """Create error result for failed validation"""
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return RiskValidationResult(
            validations_performed=trade_count,
            processing_time_ms=processing_time,
            validations_per_second=0.0,
            approved_count=0,
            rejected_count=trade_count,
            warning_count=0,
            optimization_techniques_used=["error_fallback"]
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        if not self.validation_times:
            return {}
        
        avg_processing_time = np.mean(self.validation_times)
        avg_validations_per_batch = np.mean(self.validation_counts)
        avg_validations_per_second = avg_validations_per_batch / (avg_processing_time / 1000) if avg_processing_time > 0 else 0
        
        return {
            'average_processing_time_ms': avg_processing_time,
            'average_validations_per_batch': avg_validations_per_batch,
            'average_validations_per_second': avg_validations_per_second,
            'total_validations_performed': self.total_validations,
            'target_validations_per_second': self.config.target_validations_per_second,
            'target_latency_ms': self.config.target_latency_ms,
            'throughput_target_achieved': avg_validations_per_second >= self.config.target_validations_per_second,
            'latency_target_achieved': avg_processing_time <= self.config.target_latency_ms,
            'current_risk_metrics': self.risk_metrics.copy()
        }
    
    def get_current_risk_status(self) -> Dict[str, Any]:
        """Get current risk status"""
        with self.positions_lock:
            total_exposure = sum(abs(pos) for pos in self.current_positions.values())
            
            return {
                'total_positions': len(self.current_positions),
                'total_exposure': total_exposure,
                'risk_metrics': self.risk_metrics.copy(),
                'positions': self.current_positions.copy()
            }
