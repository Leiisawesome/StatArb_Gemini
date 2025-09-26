#!/usr/bin/env python3
"""
TSLA Institutional Backtest Implementation - Real Core Engine Version
====================================================================

Following institutional-backtest-workflow.mdc instruction map
Implements advanced mean reversion and momentum strategies for TSLA
Period: 2024-02-01 to 2024-02-29 (1 month)
Uses ACTUAL core_engine components with correct column names

Author: StatArb_Gemini (Institutional Patterns)
Version: 2.0.0 (Real Core Engine)
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import warnings
import sys
import os
warnings.filterwarnings('ignore')

# Add parent directory to path for core_engine imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Core engine imports - using actual components
from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators

# Configure logging following development best practices
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TSLABacktest")

@dataclass
class BacktestResult:
    """Backtest execution result"""
    timestamp: datetime
    symbol: str
    strategy: str
    signal_type: str
    quantity: float
    price: float
    pnl: float = 0.0
    status: str = "filled"
    confidence: float = 0.0
    regime: str = "unknown"

class AdvancedMeanReversionStrategy:
    """
    Professional-grade mean reversion strategy using REAL core engine indicators
    
    Uses actual column names from core engine:
    - rsi (not rsi_14)
    - bb_upper, bb_lower, bb_position (not bb_upper_20_20, etc.)
    - volume_ratio (not volume_ratio_20)
    - atr (not atr_14)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strategy_id = "advanced_mean_reversion"
        self.logger = logging.getLogger("AdvancedMeanReversion")
        
        # Enhanced parameters
        self.rsi_oversold = config.get('rsi_oversold', 25)
        self.rsi_overbought = config.get('rsi_overbought', 75)
        self.volume_threshold = config.get('volume_threshold', 1.3)
        self.min_confidence = config.get('min_confidence', 0.65)
        
    def generate_signals(self, indicators_df: pd.DataFrame) -> List[Dict]:
        """Generate mean reversion signals using real core engine indicators"""
        
        signals = []
        
        if len(indicators_df) < 50:  # Need sufficient history
            return signals
        
        latest = indicators_df.iloc[-1]
        recent = indicators_df.iloc[-10:]  # Last 10 periods for context
        
        # === REAL CORE ENGINE INDICATORS ===
        rsi = latest.get('rsi', 50)                           # Real column name
        bb_position = latest.get('bb_position', 0.5)          # Real column name
        bb_upper = latest.get('bb_upper', 0)                  # Real column name
        bb_lower = latest.get('bb_lower', 0)                  # Real column name
        current_price = latest.get('close', 0)
        volume_ratio = latest.get('volume_ratio', 1.0)        # Real column name
        price_position = latest.get('price_position', 0.5)    # Real column name
        volatility_20 = latest.get('volatility_20', 0.02)     # Real column name
        
        # === OVERSOLD CONDITIONS (BUY SIGNALS) ===
        oversold_conditions = [
            rsi < self.rsi_oversold,                    # RSI oversold
            bb_position < 0.15,                         # Near lower Bollinger Band
            price_position < 0.25,                      # Near recent lows
            volume_ratio > self.volume_threshold,       # Volume confirmation
            current_price < bb_lower * 1.01            # Below or near lower BB
        ]
        
        oversold_score = sum(oversold_conditions) / len(oversold_conditions)
        
        # === OVERBOUGHT CONDITIONS (SELL SIGNALS) ===
        overbought_conditions = [
            rsi > self.rsi_overbought,                  # RSI overbought
            bb_position > 0.85,                         # Near upper Bollinger Band
            price_position > 0.75,                      # Near recent highs
            volume_ratio > self.volume_threshold,       # Volume confirmation
            current_price > bb_upper * 0.99            # Above or near upper BB
        ]
        
        overbought_score = sum(overbought_conditions) / len(overbought_conditions)
        
        # === SIGNAL GENERATION ===
        if oversold_score >= 0.6:  # At least 60% of conditions met
            confidence = self._calculate_confidence(
                oversold_score, volatility_20, recent, 'buy'
            )
            
            if confidence >= self.min_confidence:
                signals.append({
                    'symbol': 'TSLA',
                    'signal_type': 'buy',
                    'quantity': self._calculate_position_size(confidence, volatility_20),
                    'confidence': confidence,
                    'strategy': self.strategy_id,
                    'price': current_price,
                    'metadata': {
                        'rsi': rsi,
                        'bb_position': bb_position,
                        'oversold_score': oversold_score,
                        'volume_ratio': volume_ratio,
                        'volatility_20': volatility_20
                    }
                })
        
        elif overbought_score >= 0.6:  # At least 60% of conditions met
            confidence = self._calculate_confidence(
                overbought_score, volatility_20, recent, 'sell'
            )
            
            if confidence >= self.min_confidence:
                signals.append({
                    'symbol': 'TSLA',
                    'signal_type': 'sell',
                    'quantity': self._calculate_position_size(confidence, volatility_20),
                    'confidence': confidence,
                    'strategy': self.strategy_id,
                    'price': current_price,
                    'metadata': {
                        'rsi': rsi,
                        'bb_position': bb_position,
                        'overbought_score': overbought_score,
                        'volume_ratio': volume_ratio,
                        'volatility_20': volatility_20
                    }
                })
        
        return signals
    
    def _calculate_confidence(self, condition_score: float, volatility: float, 
                            recent_data: pd.DataFrame, signal_type: str) -> float:
        """Calculate confidence score"""
        
        # Base confidence from condition score
        base_confidence = condition_score
        
        # Volatility adjustment (higher vol = lower confidence for mean reversion)
        vol_adjustment = max(0.7, 1.0 - (volatility - 0.02) * 5)  # Reduce confidence in high vol
        
        # Recent price consistency
        if len(recent_data) > 3:
            recent_returns = recent_data['close'].pct_change().dropna()
            if len(recent_returns) > 0:
                if signal_type == 'buy':
                    # For buy signals, prefer recent downward pressure
                    recent_bias = max(0, -recent_returns.tail(3).mean() * 10)
                else:
                    # For sell signals, prefer recent upward pressure
                    recent_bias = max(0, recent_returns.tail(3).mean() * 10)
                
                consistency_factor = 1.0 + min(recent_bias, 0.15)
            else:
                consistency_factor = 1.0
        else:
            consistency_factor = 1.0
        
        # Combine factors
        final_confidence = base_confidence * vol_adjustment * consistency_factor
        
        return min(final_confidence, 1.0)
    
    def _calculate_position_size(self, confidence: float, volatility: float) -> int:
        """Calculate position size based on confidence and volatility"""
        
        base_size = 100
        
        # Scale by confidence
        confidence_multiplier = 0.5 + (confidence * 1.0)  # 0.5x to 1.5x
        
        # Reduce size in high volatility
        vol_multiplier = max(0.5, 1.2 - (volatility - 0.02) * 10)  # Reduce in high vol
        
        final_size = base_size * confidence_multiplier * vol_multiplier
        
        return max(int(final_size), 25)  # Minimum 25 shares

class AdvancedMomentumStrategy:
    """
    Professional-grade momentum strategy using REAL core engine indicators
    
    Uses actual column names from core engine:
    - macd, macd_signal, macd_histogram
    - sma_20, sma_50, ema_21
    - roc_10 (rate of change)
    - stoch_k, stoch_d
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strategy_id = "advanced_momentum"
        self.logger = logging.getLogger("AdvancedMomentum")
        
        # Enhanced parameters
        self.momentum_threshold = config.get('momentum_threshold', 0.015)  # 1.5%
        self.volume_threshold = config.get('volume_threshold', 1.2)
        self.min_confidence = config.get('min_confidence', 0.65)
        
    def generate_signals(self, indicators_df: pd.DataFrame) -> List[Dict]:
        """Generate momentum signals using real core engine indicators"""
        
        signals = []
        
        if len(indicators_df) < 50:
            return signals
        
        latest = indicators_df.iloc[-1]
        recent = indicators_df.iloc[-10:]
        
        # === REAL CORE ENGINE INDICATORS ===
        macd = latest.get('macd', 0)                          # Real column name
        macd_signal = latest.get('macd_signal', 0)            # Real column name
        macd_histogram = latest.get('macd_histogram', 0)      # Real column name
        roc_10 = latest.get('roc_10', 0)                      # Real column name (10-period ROC)
        current_price = latest.get('close', 0)
        volume_ratio = latest.get('volume_ratio', 1.0)        # Real column name
        
        # Trend indicators
        sma_20 = latest.get('sma_20', current_price)          # Real column name
        sma_50 = latest.get('sma_50', current_price)          # Real column name
        ema_21 = latest.get('ema_21', current_price)          # Real column name
        price_position = latest.get('price_position', 0.5)    # Real column name
        
        # Oscillators
        stoch_k = latest.get('stoch_k', 50)                   # Real column name
        stoch_d = latest.get('stoch_d', 50)                   # Real column name
        
        # === BULLISH MOMENTUM CONDITIONS ===
        bullish_conditions = [
            macd > macd_signal,                            # MACD bullish crossover
            macd_histogram > 0,                            # MACD histogram positive
            roc_10 > self.momentum_threshold * 100,       # Strong positive momentum (ROC in %)
            current_price > sma_20,                        # Above short-term trend
            sma_20 > sma_50,                              # Trend alignment
            current_price > ema_21,                        # Above EMA
            price_position > 0.6,                          # Upper part of range
            stoch_k > 50 and stoch_k > stoch_d,           # Stochastic bullish
            volume_ratio > self.volume_threshold           # Volume confirmation
        ]
        
        bullish_score = sum(bullish_conditions) / len(bullish_conditions)
        
        # === BEARISH MOMENTUM CONDITIONS ===
        bearish_conditions = [
            macd < macd_signal,                            # MACD bearish crossover
            macd_histogram < 0,                            # MACD histogram negative
            roc_10 < -self.momentum_threshold * 100,      # Strong negative momentum
            current_price < sma_20,                        # Below short-term trend
            sma_20 < sma_50,                              # Trend alignment
            current_price < ema_21,                        # Below EMA
            price_position < 0.4,                          # Lower part of range
            stoch_k < 50 and stoch_k < stoch_d,           # Stochastic bearish
            volume_ratio > self.volume_threshold           # Volume confirmation
        ]
        
        bearish_score = sum(bearish_conditions) / len(bearish_conditions)
        
        # === SIGNAL GENERATION ===
        if bullish_score >= 0.6:  # At least 60% of conditions met
            confidence = self._calculate_momentum_confidence(
                bullish_score, abs(sma_20 - sma_50) / sma_50, recent, 'buy'
            )
            
            if confidence >= self.min_confidence:
                signals.append({
                    'symbol': 'TSLA',
                    'signal_type': 'buy',
                    'quantity': self._calculate_position_size(confidence, bullish_score),
                    'confidence': confidence,
                    'strategy': self.strategy_id,
                    'price': current_price,
                    'metadata': {
                        'macd_histogram': macd_histogram,
                        'roc_10': roc_10,
                        'bullish_score': bullish_score,
                        'volume_ratio': volume_ratio,
                        'stoch_k': stoch_k
                    }
                })
        
        elif bearish_score >= 0.6:  # At least 60% of conditions met
            confidence = self._calculate_momentum_confidence(
                bearish_score, abs(sma_20 - sma_50) / sma_50, recent, 'sell'
            )
            
            if confidence >= self.min_confidence:
                signals.append({
                    'symbol': 'TSLA',
                    'signal_type': 'sell',
                    'quantity': self._calculate_position_size(confidence, bearish_score),
                    'confidence': confidence,
                    'strategy': self.strategy_id,
                    'price': current_price,
                    'metadata': {
                        'macd_histogram': macd_histogram,
                        'roc_10': roc_10,
                        'bearish_score': bearish_score,
                        'volume_ratio': volume_ratio,
                        'stoch_k': stoch_k
                    }
                })
        
        return signals
    
    def _calculate_momentum_confidence(self, condition_score: float, trend_strength: float,
                                     recent_data: pd.DataFrame, signal_type: str) -> float:
        """Calculate momentum confidence"""
        
        # Base confidence from condition score
        base_confidence = condition_score
        
        # Trend strength bonus (stronger trends = higher confidence)
        trend_bonus = min(trend_strength * 3, 0.15)  # Up to 15% bonus
        
        # Momentum persistence check
        if len(recent_data) > 3:
            recent_returns = recent_data['close'].pct_change().dropna()
            if len(recent_returns) > 0:
                if signal_type == 'buy':
                    # For buy signals, prefer consistent upward momentum
                    momentum_consistency = max(0, recent_returns.tail(3).mean() * 15)
                else:
                    # For sell signals, prefer consistent downward momentum
                    momentum_consistency = max(0, -recent_returns.tail(3).mean() * 15)
                
                momentum_consistency = min(momentum_consistency, 0.1)  # Cap at 10%
            else:
                momentum_consistency = 0
        else:
            momentum_consistency = 0
        
        # Combine factors
        final_confidence = base_confidence + trend_bonus + momentum_consistency
        
        return min(final_confidence, 1.0)
    
    def _calculate_position_size(self, confidence: float, signal_strength: float) -> int:
        """Calculate position size based on confidence and signal strength"""
        
        base_size = 100
        
        # Scale by confidence
        confidence_multiplier = 0.5 + (confidence * 1.0)  # 0.5x to 1.5x
        
        # Scale by signal strength
        strength_multiplier = 0.8 + (signal_strength * 0.4)  # 0.8x to 1.2x
        
        final_size = base_size * confidence_multiplier * strength_multiplier
        
        return max(int(final_size), 25)  # Minimum 25 shares

class MockRiskManager:
    """Enhanced mock risk manager with realistic institutional constraints"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("MockRiskManager")
        
        # Risk parameters
        self.max_position_size = config.get('max_position_size', 0.15)  # 15% max
        self.min_confidence = config.get('min_signal_confidence', 0.65)
        self.max_daily_trades = config.get('max_daily_trades', 15)
        
        # Tracking
        self.daily_trades = 0
        self.last_trade_date = None
        
    async def authorize_trading_decision(self, request: Dict) -> Dict:
        """Enhanced authorization with institutional risk controls"""
        
        symbol = request.get('symbol', 'TSLA')
        quantity = request.get('quantity', 0)
        confidence = request.get('confidence', 0.0)
        strategy = request.get('strategy', 'unknown')
        
        # Reset daily counter if new day
        current_date = datetime.now().date()
        if self.last_trade_date != current_date:
            self.daily_trades = 0
            self.last_trade_date = current_date
        
        # === RISK CHECKS ===
        
        # 1. Confidence threshold
        if confidence < self.min_confidence:
            return {
                'authorization_level': 'REJECTED',
                'authorized_quantity': 0,
                'rejection_reason': f'Confidence {confidence:.2f} below minimum {self.min_confidence}'
            }
        
        # 2. Daily trade limit
        if self.daily_trades >= self.max_daily_trades:
            return {
                'authorization_level': 'REJECTED',
                'authorized_quantity': 0,
                'rejection_reason': f'Daily trade limit reached ({self.max_daily_trades})'
            }
        
        # 3. Position sizing with confidence scaling
        max_quantity = int(300 * confidence)  # Scale max quantity by confidence
        authorized_qty = min(quantity, max_quantity)
        
        # 4. Minimum viable quantity
        if authorized_qty < 25:
            return {
                'authorization_level': 'REJECTED',
                'authorized_quantity': 0,
                'rejection_reason': 'Quantity below minimum viable size (25 shares)'
            }
        
        # Increment daily trade counter
        self.daily_trades += 1
        
        # Determine authorization level
        if confidence > 0.85:
            auth_level = 'AUTOMATIC'
        elif confidence > 0.75:
            auth_level = 'STANDARD'
        else:
            auth_level = 'ELEVATED'
        
        return {
            'authorization_level': auth_level,
            'authorized_quantity': authorized_qty,
            'rejection_reason': None,
            'risk_score': 1.0 - confidence,
            'daily_trades_used': self.daily_trades
        }

class BacktestExecutionEngine:
    """Enhanced backtest execution with realistic market microstructure"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("BacktestExecutionEngine")
        
        # Enhanced execution parameters
        self.commission_per_share = config.get('commission_per_share', 0.005)
        self.slippage_bps = config.get('slippage_bps', 2)  # 2 bps for TSLA
        
        # Position tracking
        self.positions = {}
        self.cash = config.get('initial_capital', 100000)
        self.trade_history = []
        
        # Performance tracking
        self.total_commission_paid = 0
        self.total_slippage_cost = 0
        
    async def simulate_execution(self, authorization: Dict, market_state: pd.Series, 
                               timestamp: datetime) -> BacktestResult:
        """Enhanced execution simulation with realistic costs"""
        
        try:
            symbol = authorization.get('symbol', 'TSLA')
            side = authorization.get('side', 'buy')
            quantity = authorization.get('authorized_quantity', 0)
            strategy = authorization.get('strategy', 'unknown')
            confidence = authorization.get('confidence', 0.0)
            
            # Get market data
            base_price = market_state.get('close', 0)
            volume = market_state.get('volume', 50000)
            atr = market_state.get('atr', base_price * 0.02)  # Default 2% ATR
            
            # === REALISTIC EXECUTION MODELING ===
            
            # 1. Slippage calculation
            slippage_factor = self.slippage_bps / 10000
            
            # Adjust slippage based on volume and volatility
            volume_impact = min(quantity / volume * 0.05, 0.0005)  # Volume impact
            volatility_impact = (atr / base_price) * 0.05  # Volatility impact
            
            total_slippage = slippage_factor + volume_impact + volatility_impact
            
            # 2. Execution price calculation
            if side.lower() == 'buy':
                execution_price = base_price * (1 + total_slippage)
            else:
                execution_price = base_price * (1 - total_slippage)
            
            # 3. Commission calculation
            commission = quantity * self.commission_per_share
            
            # 4. Total transaction costs
            slippage_cost = abs(execution_price - base_price) * quantity
            total_cost = commission
            
            # === POSITION AND CASH MANAGEMENT ===
            
            trade_value = quantity * execution_price
            
            if side.lower() == 'buy':
                # Check cash availability
                total_required = trade_value + total_cost
                if self.cash >= total_required:
                    self.cash -= total_required
                    self.positions[symbol] = self.positions.get(symbol, 0) + quantity
                    pnl = -total_cost  # Initial cost
                    status = "filled"
                else:
                    return BacktestResult(
                        timestamp=timestamp, symbol=symbol, strategy=strategy,
                        signal_type=side, quantity=0, price=execution_price,
                        pnl=0, status="rejected_insufficient_cash", confidence=confidence
                    )
            else:  # sell
                current_position = self.positions.get(symbol, 0)
                if current_position >= quantity:
                    self.cash += (trade_value - total_cost)
                    self.positions[symbol] = current_position - quantity
                    pnl = -total_cost  # Initial cost
                    status = "filled"
                else:
                    return BacktestResult(
                        timestamp=timestamp, symbol=symbol, strategy=strategy,
                        signal_type=side, quantity=0, price=execution_price,
                        pnl=0, status="rejected_insufficient_position", confidence=confidence
                    )
            
            # === PERFORMANCE TRACKING ===
            self.total_commission_paid += commission
            self.total_slippage_cost += slippage_cost
            
            # Create detailed result
            result = BacktestResult(
                timestamp=timestamp,
                symbol=symbol,
                strategy=strategy,
                signal_type=side,
                quantity=quantity,
                price=execution_price,
                pnl=pnl,
                status=status,
                confidence=confidence
            )
            
            self.trade_history.append(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Execution simulation failed: {e}")
            return BacktestResult(
                timestamp=timestamp, symbol=symbol, strategy=strategy,
                signal_type=side, quantity=0, price=0, pnl=0,
                status="failed", confidence=confidence
            )
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Enhanced portfolio summary with detailed metrics"""
        
        current_position_value = 0
        if self.positions.get('TSLA', 0) > 0 and self.trade_history:
            # Use last known price for position valuation
            last_price = self.trade_history[-1].price
            current_position_value = self.positions['TSLA'] * last_price
        
        total_portfolio_value = self.cash + current_position_value
        
        return {
            'cash': self.cash,
            'positions': self.positions.copy(),
            'position_value': current_position_value,
            'total_portfolio_value': total_portfolio_value,
            'total_trades': len(self.trade_history),
            'total_commission_paid': self.total_commission_paid,
            'total_slippage_cost': self.total_slippage_cost,
            'total_transaction_costs': self.total_commission_paid + self.total_slippage_cost,
            'return_pct': ((total_portfolio_value - 100000) / 100000) * 100
        }

# Main backtest function - Real Core Engine Version
async def run_tsla_real_core_engine_backtest():
    """
    TSLA institutional backtest using REAL core engine components
    """
    
    logger.info("🚀 Starting TSLA REAL Core Engine Institutional Backtest")
    logger.info("📅 Period: 2024-02-01 to 2024-02-29")
    logger.info("📈 Strategies: Advanced Mean Reversion + Advanced Momentum")
    logger.info("🏛️ Using REAL Core Engine Components")
    
    try:
        # ============================================================================
        # PHASE 1: REAL CORE ENGINE INITIALIZATION
        # ============================================================================
        
        logger.info("🔧 Phase 1: Initializing REAL core engine components...")
        
        # Real ClickHouse data manager
        data_config = ClickHouseDataConfig(
            symbols=['TSLA'],
            start_date='2024-02-01',
            end_date='2024-02-29',
            interval='1min',
            enable_caching=True
        )
        
        data_manager = ClickHouseDataManager(data_config)
        
        # Real technical indicators engine
        indicators_engine = EnhancedTechnicalIndicators()
        
        # Enhanced risk management
        risk_manager = MockRiskManager({
            'max_position_size': 0.15,
            'min_signal_confidence': 0.65,
            'max_daily_trades': 15
        })
        
        # Enhanced execution engine
        backtest_engine = BacktestExecutionEngine({
            'initial_capital': 100000,
            'commission_per_share': 0.005,
            'slippage_bps': 2
        })
        
        logger.info("✅ REAL core engine initialization completed")
        
        # ============================================================================
        # PHASE 2: REAL DATA PROCESSING
        # ============================================================================
        
        logger.info("📊 Phase 2: Processing REAL market data...")
        
        # Load REAL market data from ClickHouse
        market_data = data_manager.load_market_data(
            symbols=['TSLA'],
            start_time=datetime(2024, 2, 1),
            end_time=datetime(2024, 2, 29, 23, 59, 59),
            interval="1min"
        )
        
        if market_data is None or market_data.empty:
            logger.error("❌ No REAL market data available")
            return
        
        logger.info(f"📈 Loaded {len(market_data)} REAL data points for TSLA")
        
        # Calculate REAL indicators using core engine
        indicators_df = indicators_engine.calculate_indicators(market_data)
        
        logger.info(f"📊 Calculated REAL indicators: {len(indicators_df)} records")
        logger.info(f"📊 Available indicators: {len([col for col in indicators_df.columns if col not in ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']])}")
        
        # ============================================================================
        # PHASE 3: REAL STRATEGY BACKTESTING
        # ============================================================================
        
        logger.info("🎯 Phase 3: Running REAL strategy backtesting...")
        
        # Initialize strategies with REAL core engine indicators
        mean_reversion_strategy = AdvancedMeanReversionStrategy({
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'volume_threshold': 1.3,
            'min_confidence': 0.65
        })
        
        momentum_strategy = AdvancedMomentumStrategy({
            'momentum_threshold': 0.015,
            'volume_threshold': 1.2,
            'min_confidence': 0.65
        })
        
        backtest_results = []
        
        # Process in 5-minute intervals using REAL column names
        real_columns = {
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum',
            'rsi': 'last',                              # Real column name
            'macd': 'last', 'macd_signal': 'last', 'macd_histogram': 'last',
            'bb_upper': 'last', 'bb_lower': 'last', 'bb_position': 'last',  # Real column names
            'sma_20': 'last', 'sma_50': 'last', 'ema_21': 'last',          # Real column names
            'atr': 'last',                              # Real column name
            'roc_10': 'last',                           # Real column name
            'volume_ratio': 'last',                     # Real column name
            'stoch_k': 'last', 'stoch_d': 'last',      # Real column names
            'price_position': 'last',                   # Real column name
            'volatility_20': 'last'                     # Real column name
        }
        
        # Only include columns that actually exist
        available_columns = {}
        for col, agg in real_columns.items():
            if col in indicators_df.columns:
                available_columns[col] = agg
        
        logger.info(f"📊 Using {len(available_columns)} available indicators for resampling")
        
        indicators_5min = indicators_df.set_index('timestamp').resample('5min').agg(
            available_columns
        ).dropna().reset_index()
        
        logger.info(f"📊 Processing {len(indicators_5min)} REAL 5-minute intervals")
        
        signal_count = 0
        executed_trades = 0
        rejected_trades = 0
        
        for i, row in indicators_5min.iterrows():
            if i < 50:  # Need substantial history
                continue
            
            timestamp = row['timestamp']
            
            # Get historical data up to this point
            historical_data = indicators_5min.iloc[:i+1]
            
            # Generate signals from REAL strategies
            mr_signals = mean_reversion_strategy.generate_signals(historical_data)
            momentum_signals = momentum_strategy.generate_signals(historical_data)
            
            all_signals = mr_signals + momentum_signals
            signal_count += len(all_signals)
            
            # Process signals through risk management
            for signal in all_signals:
                try:
                    # Create request
                    request = {
                        'symbol': signal['symbol'],
                        'side': signal['signal_type'],
                        'quantity': signal['quantity'],
                        'confidence': signal['confidence'],
                        'strategy': signal['strategy']
                    }
                    
                    # Get authorization
                    authorization = await risk_manager.authorize_trading_decision(request)
                    
                    # Execute if authorized
                    if authorization['authorization_level'] != 'REJECTED':
                        auth_dict = {
                            'symbol': signal['symbol'],
                            'side': signal['signal_type'],
                            'authorized_quantity': authorization['authorized_quantity'],
                            'strategy': signal['strategy'],
                            'confidence': signal['confidence']
                        }
                        
                        execution_result = await backtest_engine.simulate_execution(
                            auth_dict, row, timestamp
                        )
                        
                        if execution_result.status == "filled":
                            backtest_results.append(execution_result)
                            executed_trades += 1
                            
                            if executed_trades <= 10 or executed_trades % 10 == 0:  # Log first 10 and every 10th
                                logger.info(f"✅ Trade {executed_trades}: {execution_result.signal_type.upper()} "
                                           f"{execution_result.quantity} TSLA @ ${execution_result.price:.2f} "
                                           f"({execution_result.strategy}) [Conf: {execution_result.confidence:.1%}]")
                        else:
                            rejected_trades += 1
                    else:
                        rejected_trades += 1
                
                except Exception as e:
                    logger.error(f"Error processing signal: {e}")
                    continue
        
        logger.info(f"📊 REAL signal generation completed:")
        logger.info(f"   • Total signals generated: {signal_count}")
        logger.info(f"   • Trades executed: {executed_trades}")
        logger.info(f"   • Trades rejected: {rejected_trades}")
        logger.info(f"   • Execution rate: {executed_trades/signal_count*100:.1f}%" if signal_count > 0 else "   • Execution rate: 0%")
        
        # ============================================================================
        # PHASE 4: REAL PERFORMANCE ANALYTICS
        # ============================================================================
        
        logger.info("📈 Phase 4: Analyzing REAL performance...")
        
        if not backtest_results:
            logger.warning("⚠️ No trades executed - cannot perform performance analysis")
            return
        
        # REAL performance calculations
        portfolio_summary = backtest_engine.get_portfolio_summary()
        
        # Basic metrics
        total_trades = len(backtest_results)
        winning_trades = sum(1 for trade in backtest_results if trade.pnl > 0)
        losing_trades = sum(1 for trade in backtest_results if trade.pnl < 0)
        
        # Enhanced P&L calculation
        total_pnl = sum(trade.pnl for trade in backtest_results)
        total_transaction_costs = portfolio_summary['total_transaction_costs']
        net_pnl = total_pnl - total_transaction_costs
        
        # Strategy breakdown
        strategy_stats = {}
        for trade in backtest_results:
            if trade.strategy not in strategy_stats:
                strategy_stats[trade.strategy] = {
                    'trades': 0, 'pnl': 0, 'winning_trades': 0,
                    'total_quantity': 0, 'avg_confidence': 0
                }
            
            stats = strategy_stats[trade.strategy]
            stats['trades'] += 1
            stats['pnl'] += trade.pnl
            stats['total_quantity'] += trade.quantity
            stats['avg_confidence'] += trade.confidence
            
            if trade.pnl > 0:
                stats['winning_trades'] += 1
        
        # Calculate averages
        for strategy, stats in strategy_stats.items():
            if stats['trades'] > 0:
                stats['avg_confidence'] /= stats['trades']
                stats['avg_quantity'] = stats['total_quantity'] / stats['trades']
        
        # ============================================================================
        # REAL RESULTS DISPLAY
        # ============================================================================
        
        logger.info("=" * 80)
        logger.info("🎯 TSLA REAL CORE ENGINE INSTITUTIONAL BACKTEST RESULTS")
        logger.info("=" * 80)
        
        logger.info(f"📅 Period: 2024-02-01 to 2024-02-29")
        logger.info(f"💰 Initial Capital: $100,000")
        logger.info(f"🏛️ REAL Core Engine Components: ✅")
        logger.info(f"📊 REAL ClickHouse Data: ✅")
        logger.info("")
        
        logger.info("📊 EXECUTION SUMMARY:")
        logger.info(f"   • Signals Generated: {signal_count}")
        logger.info(f"   • Trades Executed: {executed_trades}")
        logger.info(f"   • Trades Rejected: {rejected_trades}")
        logger.info(f"   • Execution Rate: {executed_trades/signal_count*100:.1f}%" if signal_count > 0 else "   • Execution Rate: 0%")
        logger.info(f"   • Win Rate: {winning_trades/total_trades*100:.1f}%" if total_trades > 0 else "   • Win Rate: 0%")
        logger.info("")
        
        logger.info("💰 REAL PERFORMANCE SUMMARY:")
        logger.info(f"   • Gross P&L: ${total_pnl:.2f}")
        logger.info(f"   • Transaction Costs: ${total_transaction_costs:.2f}")
        logger.info(f"     - Commission: ${portfolio_summary['total_commission_paid']:.2f}")
        logger.info(f"     - Slippage: ${portfolio_summary['total_slippage_cost']:.2f}")
        logger.info(f"   • Net P&L: ${net_pnl:.2f}")
        logger.info(f"   • Total Return: {portfolio_summary['return_pct']:.2f}%")
        logger.info(f"   • Final Portfolio Value: ${portfolio_summary['total_portfolio_value']:,.2f}")
        logger.info(f"   • Final Cash: ${portfolio_summary['cash']:,.2f}")
        logger.info(f"   • Final Position: {portfolio_summary['positions'].get('TSLA', 0)} shares")
        logger.info("")
        
        logger.info("🧠 REAL STRATEGY BREAKDOWN:")
        for strategy, stats in strategy_stats.items():
            logger.info(f"   • {strategy.replace('_', ' ').title()}:")
            logger.info(f"     - Trades: {stats['trades']}")
            logger.info(f"     - P&L: ${stats['pnl']:.2f}")
            logger.info(f"     - Win Rate: {stats['winning_trades']/stats['trades']*100:.1f}%" if stats['trades'] > 0 else "     - Win Rate: 0%")
            logger.info(f"     - Avg Confidence: {stats['avg_confidence']:.1%}")
            logger.info(f"     - Avg Quantity: {stats.get('avg_quantity', 0):.0f} shares")
        
        logger.info("=" * 80)
        logger.info("✅ TSLA REAL Core Engine Institutional Backtest Completed Successfully")
        logger.info("=" * 80)
        
        return {
            'total_trades': total_trades,
            'execution_rate': executed_trades/signal_count*100 if signal_count > 0 else 0,
            'win_rate': winning_trades/total_trades*100 if total_trades > 0 else 0,
            'gross_pnl': total_pnl,
            'transaction_costs': total_transaction_costs,
            'net_pnl': net_pnl,
            'total_return_pct': portfolio_summary['return_pct'],
            'strategy_stats': strategy_stats,
            'portfolio_summary': portfolio_summary
        }
        
    except Exception as e:
        logger.error(f"❌ REAL core engine backtest failed: {e}")
        raise

# Entry point
if __name__ == "__main__":
    logger.info("🔧 Running TSLA REAL Core Engine Institutional Backtest")
    asyncio.run(run_tsla_real_core_engine_backtest())
