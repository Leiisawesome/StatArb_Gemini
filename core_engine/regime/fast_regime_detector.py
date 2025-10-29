"""
Fast Regime Detector - Rapid Market Condition Assessment
Uses leading indicators for 1-5 minute regime detection vs 10-60 min traditional.

Fast Indicators (4 types):
1. VIX Spike Detection - +20% in 5 minutes → Volatility crisis
2. Market Breadth Collapse - >70% stocks declining → High volatility
3. Order Book Imbalance - >80% sell-side → Potential flash crash
4. Volatility Spike - >3x normal intraday → High volatility

Detection Speed:
- Traditional: 10-60 minutes (statistical windows)
- Fast: 1-5 minutes (leading indicators)
- Improvement: 80-95% faster response

Integration with Traditional Detection:
- Fast signal overrides traditional during crises
- Traditional provides baseline regime
- Fast acts as early warning system

Author: Trading System Team
Date: October 25, 2025
Version: 1.0
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
from core_engine.exceptions import ConfigurationRequiredError

logger = logging.getLogger(__name__)


class RegimeType(Enum):
    """Market regime types"""
    LOW_VOLATILITY = "low_volatility"
    NORMAL_VOLATILITY = "normal_volatility"
    HIGH_VOLATILITY = "high_volatility"
    EXTREME_VOLATILITY = "extreme_volatility"
    CRISIS = "crisis"


class FastSignalType(Enum):
    """Fast signal types"""
    VIX_SPIKE = "vix_spike"
    BREADTH_COLLAPSE = "breadth_collapse"
    ORDER_BOOK_IMBALANCE = "order_book_imbalance"
    VOLATILITY_SPIKE = "volatility_spike"


@dataclass
class FastRegimeSignal:
    """
    Fast regime detection signal
    
    Attributes:
        signal_type: Type of fast signal
        new_regime: Detected regime
        severity: Signal severity (1-10)
        confidence: Detection confidence (0-1)
        timestamp: Signal timestamp
        details: Additional details
    """
    signal_type: FastSignalType
    new_regime: RegimeType
    severity: int  # 1-10
    confidence: float  # 0-1
    timestamp: datetime
    details: Dict


class FastRegimeDetector:
    """
    Fast Regime Detector
    
    Detects regime changes in 1-5 minutes using leading indicators.
    Acts as early warning system that overrides traditional detection
    during crisis conditions.
    
    Integration: Called by EnhancedRegimeEngine, overrides traditional detection
    """
    
    def __init__(self, market_data_manager, config: Optional[Dict] = None):
        """
        Initialize fast regime detector
        
        Args:
            market_data_manager: Market data manager instance
            config: Configuration dictionary
        """
        self.market_data_manager = market_data_manager
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Fast Detection Thresholds
        self.vix_spike_threshold = self.config.get('vix_spike_pct', 0.20)  # 20%
        self.breadth_collapse_threshold = self.config.get('breadth_collapse_pct', 0.70)  # 70%
        self.order_imbalance_threshold = self.config.get('order_imbalance_pct', 0.80)  # 80%
        self.volatility_spike_multiplier = self.config.get('volatility_spike_multiplier', 3.0)  # 3x
        
        # Time Windows
        self.vix_window_minutes = 5
        self.breadth_window_minutes = 5
        self.volatility_window_minutes = 15
        
        # State
        self.vix_history = deque(maxlen=100)  # Last 100 VIX readings
        self.breadth_history = deque(maxlen=100)  # Last 100 breadth readings
        self.volatility_history = deque(maxlen=100)  # Last 100 volatility readings
        
        # Recent Signals
        self.recent_signals: List[FastRegimeSignal] = []
        self.max_signal_history = 1000
        
        # Statistics
        self.total_checks = 0
        self.total_signals = 0
        self.signals_by_type: Dict[FastSignalType, int] = {
            signal_type: 0 for signal_type in FastSignalType
        }
        
        self.logger.info("✅ FastRegimeDetector initialized")
        self.logger.info(f"   VIX Spike Threshold: {self.vix_spike_threshold:.0%}")
        self.logger.info(f"   Breadth Collapse: {self.breadth_collapse_threshold:.0%}")
        self.logger.info(f"   Order Imbalance: {self.order_imbalance_threshold:.0%}")
        self.logger.info(f"   Volatility Multiplier: {self.volatility_spike_multiplier}x")
    
    async def check_fast_regime_change(self) -> Optional[FastRegimeSignal]:
        """
        Check for fast regime change using leading indicators
        
        Returns:
            FastRegimeSignal if regime change detected, None otherwise
        """
        self.total_checks += 1
        
        # Check all fast indicators (in severity order)
        
        # CRITICAL: Check 1 - VIX Spike (most critical)
        vix_signal = await self._check_vix_spike()
        if vix_signal and vix_signal.severity >= 8:
            return vix_signal
        
        # CRITICAL: Check 2 - Market Breadth Collapse
        breadth_signal = await self._check_market_breadth()
        if breadth_signal and breadth_signal.severity >= 8:
            return breadth_signal
        
        # HIGH: Check 3 - Order Book Imbalance
        order_signal = await self._check_order_book_imbalance()
        if order_signal and order_signal.severity >= 7:
            return order_signal
        
        # MODERATE: Check 4 - Volatility Spike
        vol_signal = await self._check_volatility_spike()
        if vol_signal and vol_signal.severity >= 6:
            return vol_signal
        
        # Return highest severity signal if any
        all_signals = [s for s in [vix_signal, breadth_signal, order_signal, vol_signal] if s]
        if all_signals:
            return max(all_signals, key=lambda s: s.severity)
        
        return None
    
    async def _check_vix_spike(self) -> Optional[FastRegimeSignal]:
        """
        Check 1: VIX Spike Detection
        
        Threshold: +20% in 5 minutes
        Signal: Volatility crisis regime
        """
        try:
            # Get current VIX
            current_vix = await self._get_current_vix()
            
            # Store in history
            self.vix_history.append({
                'timestamp': datetime.now(),
                'vix': current_vix
            })
            
            # Need at least 2 readings
            if len(self.vix_history) < 2:
                return None
            
            # Get VIX from 5 minutes ago
            cutoff_time = datetime.now() - timedelta(minutes=self.vix_window_minutes)
            historical_vix = [
                h['vix'] for h in self.vix_history 
                if h['timestamp'] >= cutoff_time
            ]
            
            if not historical_vix:
                return None
            
            previous_vix = historical_vix[0]
            
            # Calculate spike
            vix_change = (current_vix - previous_vix) / previous_vix
            
            # Check threshold
            if vix_change >= self.vix_spike_threshold:
                # VIX SPIKE DETECTED
                severity = min(10, int(10 * (vix_change / self.vix_spike_threshold)))
                
                signal = FastRegimeSignal(
                    signal_type=FastSignalType.VIX_SPIKE,
                    new_regime=RegimeType.CRISIS if vix_change > 0.5 else RegimeType.EXTREME_VOLATILITY,
                    severity=severity,
                    confidence=0.9,  # VIX is highly reliable
                    timestamp=datetime.now(),
                    details={
                        'current_vix': current_vix,
                        'previous_vix': previous_vix,
                        'change_pct': vix_change,
                        'window_minutes': self.vix_window_minutes
                    }
                )
                
                self._record_signal(signal)
                
                self.logger.critical(
                    f"🚨 VIX SPIKE DETECTED: {vix_change:+.1%} in {self.vix_window_minutes} min | "
                    f"VIX: {previous_vix:.1f} → {current_vix:.1f} | "
                    f"Regime: {signal.new_regime.value}"
                )
                
                return signal
            
        except Exception as e:
            self.logger.error(f"VIX spike check error: {e}")
        
        return None
    
    async def _check_market_breadth(self) -> Optional[FastRegimeSignal]:
        """
        Check 2: Market Breadth Collapse
        
        Threshold: >70% stocks declining
        Signal: High volatility / crisis regime
        """
        try:
            # Calculate advancing vs declining stocks
            breadth_data = await self._calculate_market_breadth()
            
            if breadth_data is None:
                return None
            
            declining_pct = breadth_data['declining_pct']
            
            # Check threshold
            if declining_pct >= self.breadth_collapse_threshold:
                # BREADTH COLLAPSE DETECTED
                severity = min(10, int(10 * (declining_pct / self.breadth_collapse_threshold)))
                
                signal = FastRegimeSignal(
                    signal_type=FastSignalType.BREADTH_COLLAPSE,
                    new_regime=RegimeType.HIGH_VOLATILITY,
                    severity=severity,
                    confidence=0.85,
                    timestamp=datetime.now(),
                    details=breadth_data
                )
                
                self._record_signal(signal)
                
                self.logger.critical(
                    f"🚨 MARKET BREADTH COLLAPSE: {declining_pct:.1%} stocks declining | "
                    f"Regime: {signal.new_regime.value}"
                )
                
                return signal
            
        except Exception as e:
            self.logger.error(f"Market breadth check error: {e}")
        
        return None
    
    async def _check_order_book_imbalance(self) -> Optional[FastRegimeSignal]:
        """
        Check 3: Order Book Imbalance
        
        Threshold: >80% sell-side pressure
        Signal: Potential flash crash
        """
        try:
            # Analyze order book
            imbalance_data = await self._analyze_order_book_imbalance()
            
            if imbalance_data is None:
                return None
            
            sell_pressure = imbalance_data['sell_pressure_pct']
            
            # Check threshold
            if sell_pressure >= self.order_imbalance_threshold:
                # ORDER BOOK IMBALANCE DETECTED
                severity = min(10, int(10 * (sell_pressure / self.order_imbalance_threshold)))
                
                signal = FastRegimeSignal(
                    signal_type=FastSignalType.ORDER_BOOK_IMBALANCE,
                    new_regime=RegimeType.EXTREME_VOLATILITY,
                    severity=severity,
                    confidence=0.80,
                    timestamp=datetime.now(),
                    details=imbalance_data
                )
                
                self._record_signal(signal)
                
                self.logger.warning(
                    f"⚠️ ORDER BOOK IMBALANCE: {sell_pressure:.1%} sell pressure | "
                    f"Regime: {signal.new_regime.value}"
                )
                
                return signal
            
        except Exception as e:
            self.logger.error(f"Order book imbalance check error: {e}")
        
        return None
    
    async def _check_volatility_spike(self) -> Optional[FastRegimeSignal]:
        """
        Check 4: Volatility Spike (Intraday)
        
        Threshold: >3x normal intraday volatility
        Signal: High volatility regime
        """
        try:
            # Calculate current intraday volatility
            current_vol = await self._calculate_intraday_volatility()
            
            # Get normal volatility (rolling 15-minute)
            cutoff_time = datetime.now() - timedelta(minutes=self.volatility_window_minutes)
            recent_vols = [
                h['volatility'] for h in self.volatility_history 
                if h['timestamp'] >= cutoff_time
            ]
            
            if not recent_vols:
                return None
            
            normal_vol = sum(recent_vols) / len(recent_vols)
            
            # Store current volatility
            self.volatility_history.append({
                'timestamp': datetime.now(),
                'volatility': current_vol
            })
            
            # Calculate multiplier
            vol_multiplier = current_vol / normal_vol if normal_vol > 0 else 1.0
            
            # Check threshold
            if vol_multiplier >= self.volatility_spike_multiplier:
                # VOLATILITY SPIKE DETECTED
                severity = min(10, int(6 * (vol_multiplier / self.volatility_spike_multiplier)))
                
                signal = FastRegimeSignal(
                    signal_type=FastSignalType.VOLATILITY_SPIKE,
                    new_regime=RegimeType.HIGH_VOLATILITY,
                    severity=severity,
                    confidence=0.75,
                    timestamp=datetime.now(),
                    details={
                        'current_volatility': current_vol,
                        'normal_volatility': normal_vol,
                        'multiplier': vol_multiplier
                    }
                )
                
                self._record_signal(signal)
                
                self.logger.warning(
                    f"⚠️ VOLATILITY SPIKE: {vol_multiplier:.1f}x normal | "
                    f"Regime: {signal.new_regime.value}"
                )
                
                return signal
            
        except Exception as e:
            self.logger.error(f"Volatility spike check error: {e}")
        
        return None
    
    # Helper Methods - Require real market data integration
    
    async def _get_current_vix(self) -> float:
        """Get current VIX level"""
        if not hasattr(self, 'market_data_manager') or not self.market_data_manager:
            raise ConfigurationRequiredError("Market data manager required for VIX data")
        
        try:
            vix = await self.market_data_manager.get_vix()
            if vix <= 0:
                raise ConfigurationRequiredError(f"Invalid VIX value: {vix}")
            return vix
        except Exception as e:
            raise ConfigurationRequiredError(f"Failed to get VIX data: {e}")
    
    async def _calculate_market_breadth(self) -> Optional[Dict]:
        """Calculate advancing vs declining stocks"""
        if not hasattr(self, 'market_data_manager') or not self.market_data_manager:
            raise ConfigurationRequiredError("Market data manager required for market breadth calculation")
        
        try:
            stocks_data = await self.market_data_manager.get_all_stocks_snapshot()
            if not stocks_data:
                raise ConfigurationRequiredError("No stocks data available for breadth calculation")
            
            declining = sum(1 for s in stocks_data if s.get('change', 0) < 0)
            total = len(stocks_data)
            return {'declining_pct': declining / total, 'total_stocks': total}
        except Exception as e:
            raise ConfigurationRequiredError(f"Failed to calculate market breadth: {e}")
    
    async def _analyze_order_book_imbalance(self) -> Optional[Dict]:
        """Analyze order book for sell/buy pressure"""
        if not hasattr(self, 'market_data_manager') or not self.market_data_manager:
            raise ConfigurationRequiredError("Market data manager required for order book analysis")
        
        try:
            order_book = await self.market_data_manager.get_order_book_aggregate()
            if not order_book:
                raise ConfigurationRequiredError("No order book data available")
            
            sell_volume = order_book.get('total_sell_volume', 0)
            total_volume = order_book.get('total_volume', 0)
            if total_volume <= 0:
                raise ConfigurationRequiredError("Invalid order book volume data")
            
            return {'sell_pressure_pct': sell_volume / total_volume, 'total_volume': total_volume}
        except Exception as e:
            raise ConfigurationRequiredError(f"Failed to analyze order book: {e}")
    
    async def _calculate_intraday_volatility(self) -> float:
        """Calculate current intraday volatility"""
        if not hasattr(self, 'market_data_manager') or not self.market_data_manager:
            raise ConfigurationRequiredError("Market data manager required for volatility calculation")
        
        try:
            price_data = await self.market_data_manager.get_recent_prices(minutes=15)
            if price_data is None or len(price_data) < 2:
                raise ConfigurationRequiredError("Insufficient price data for volatility calculation")
            
            returns = price_data.pct_change().dropna()
            if len(returns) < 2:
                raise ConfigurationRequiredError("Insufficient returns data for volatility calculation")
            
            volatility = np.std(returns) * np.sqrt(252 * 390 / 15)  # Annualized
            if volatility <= 0:
                raise ConfigurationRequiredError(f"Invalid volatility calculation: {volatility}")
            
            return volatility
        except Exception as e:
            raise ConfigurationRequiredError(f"Failed to calculate intraday volatility: {e}")
    
    def _record_signal(self, signal: FastRegimeSignal):
        """Record fast regime signal"""
        self.total_signals += 1
        self.signals_by_type[signal.signal_type] += 1
        self.recent_signals.append(signal)
        
        # Maintain history size
        if len(self.recent_signals) > self.max_signal_history:
            self.recent_signals = self.recent_signals[-self.max_signal_history:]
    
    # Statistics and Reporting
    
    def get_fast_detection_statistics(self) -> Dict:
        """Get fast detection statistics"""
        return {
            'total_checks': self.total_checks,
            'total_signals': self.total_signals,
            'signals_by_type': {
                signal_type.value: count 
                for signal_type, count in self.signals_by_type.items()
                if count > 0
            },
            'recent_signals_count': len(self.recent_signals)
        }
    
    def generate_fast_detection_report(self) -> str:
        """Generate fast detection report"""
        stats = self.get_fast_detection_statistics()
        
        report = [
            "=" * 60,
            "FAST REGIME DETECTION REPORT",
            "=" * 60,
            f"Total Checks:          {stats['total_checks']:,}",
            f"Total Signals:         {stats['total_signals']:,}",
            "",
            "DETECTION THRESHOLDS:",
            f"  VIX Spike:           {self.vix_spike_threshold:>6.0%} in {self.vix_window_minutes} min",
            f"  Breadth Collapse:    {self.breadth_collapse_threshold:>6.0%} declining",
            f"  Order Imbalance:     {self.order_imbalance_threshold:>6.0%} sell pressure",
            f"  Volatility Spike:    {self.volatility_spike_multiplier:>6.1f}x normal",
            ""
        ]
        
        if stats['signals_by_type']:
            report.append("SIGNALS BY TYPE:")
            for signal_type, count in stats['signals_by_type'].items():
                report.append(f"  {signal_type:25s}: {count}")
            report.append("")
        
        # Show recent signals
        if self.recent_signals:
            report.append("RECENT SIGNALS (Last 10):")
            for signal in self.recent_signals[-10:]:
                report.append(
                    f"  [{signal.timestamp.strftime('%H:%M:%S')}] "
                    f"{signal.signal_type.value:25s} → {signal.new_regime.value} "
                    f"(severity: {signal.severity}/10)"
                )
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)

