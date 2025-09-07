"""
Signal Converter Implementation
==============================

Pure signal conversion logic isolated from the core engine.
Converts raw strategy signals to standardized trading signals.

Author: Professional Trading System Architecture
Version: 1.0.0
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import logging
from dataclasses import dataclass

# Import from core signal engine for now - interfaces to be consolidated later
from ..core.signal_engine import TradingSignal, SignalType

# Temporary definitions until proper interface consolidation
class ComponentValidationError(Exception):
    """Component validation error"""
    pass

class SignalConverterInterface:
    """Interface for signal converters"""
    def convert_to_trading_signals(self, raw_signals):
        raise NotImplementedError

class RawSignal:
    """Temporary raw signal class"""
    def __init__(self, symbol, signal_type, strength, confidence=1.0, metadata=None):
        self.symbol = symbol
        self.signal_type = signal_type
        self.strength = strength
        self.confidence = confidence
        self.metadata = metadata or {}

INTERFACE_VERSION = "1.0.0"


@dataclass
class SignalConversionConfig:
    """Configuration for signal conversion."""
    confidence_threshold: float = 0.5
    position_size_multiplier: float = 1.0
    enable_signal_filtering: bool = True
    max_signals_per_symbol: int = 1
    signal_decay_periods: int = 5


class SignalConverter(SignalConverterInterface):
    """
    Professional-grade signal converter implementation.
    
    This class handles the conversion from strategy-specific raw signals
    to standardized trading signals. It applies professional trading logic
    including confidence thresholds, position sizing, and signal filtering.
    """
    
    def __init__(self, config: Optional[SignalConversionConfig] = None):
        """
        Initialize signal converter.
        
        Args:
            config: Signal conversion configuration
        """
        self.config = config or SignalConversionConfig()
        self.logger = logging.getLogger(__name__)
        self._validate_config()
        
        # Track signal history for filtering
        self._signal_history: Dict[str, List[TradingSignal]] = {}
        
        self.logger.info(f"SignalConverter initialized with config: {self.config}")
    
    def _validate_config(self) -> None:
        """Validate configuration parameters."""
        if not 0.0 <= self.config.confidence_threshold <= 1.0:
            raise ComponentValidationError(
                f"Confidence threshold must be between 0.0 and 1.0, got {self.config.confidence_threshold}"
            )
        
        if self.config.position_size_multiplier <= 0:
            raise ComponentValidationError(
                f"Position size multiplier must be positive, got {self.config.position_size_multiplier}"
            )
        
        if self.config.max_signals_per_symbol <= 0:
            raise ComponentValidationError(
                f"Max signals per symbol must be positive, got {self.config.max_signals_per_symbol}"
            )
    
    def convert_to_trading_signals(self, raw_signals: List[RawSignal]) -> List[TradingSignal]:
        """
        Convert raw signals to standardized trading signals.
        
        Args:
            raw_signals: List of raw signals from strategies
            
        Returns:
            List of standardized trading signals
            
        Raises:
            ComponentValidationError: If raw signals are invalid
        """
        if not raw_signals:
            self.logger.debug("No raw signals to convert")
            return []
        
        self.logger.debug(f"Converting {len(raw_signals)} raw signals")
        
        trading_signals = []
        
        for raw_signal in raw_signals:
            try:
                # Validate raw signal
                self._validate_raw_signal(raw_signal)
                
                # Convert to trading signal
                trading_signal = self._convert_single_signal(raw_signal)
                
                if trading_signal:
                    trading_signals.append(trading_signal)
                    
            except Exception as e:
                self.logger.error(f"Failed to convert raw signal for {raw_signal.symbol}: {e}")
                continue
        
        self.logger.info(f"Converted {len(trading_signals)} trading signals from {len(raw_signals)} raw signals")
        return trading_signals
    
    def _validate_raw_signal(self, raw_signal: RawSignal) -> None:
        """Validate a raw signal."""
        if not raw_signal.symbol:
            raise ComponentValidationError("Raw signal symbol cannot be empty")
        
        if not 0.0 <= raw_signal.confidence <= 1.0:
            raise ComponentValidationError(
                f"Raw signal confidence must be between 0.0 and 1.0, got {raw_signal.confidence}"
            )
        
        if pd.isna(raw_signal.value):
            raise ComponentValidationError("Raw signal value cannot be NaN")
    
    def _convert_single_signal(self, raw_signal: RawSignal) -> Optional[TradingSignal]:
        """
        Convert a single raw signal to trading signal.
        
        Args:
            raw_signal: Raw signal to convert
            
        Returns:
            TradingSignal if conversion successful, None otherwise
        """
        # Check confidence threshold
        if raw_signal.confidence < self.config.confidence_threshold:
            self.logger.debug(
                f"Signal for {raw_signal.symbol} below confidence threshold: "
                f"{raw_signal.confidence} < {self.config.confidence_threshold}"
            )
            return None
        
        # Determine signal type based on signal value
        signal_type = self._determine_signal_type(raw_signal.value)
        
        if signal_type == SignalType.HOLD:
            self.logger.debug(f"Hold signal for {raw_signal.symbol}, skipping")
            return None
        
        # Calculate position size
        position_size = self._calculate_position_size(raw_signal)
        
        # Extract metadata
        metadata = self._extract_signal_metadata(raw_signal)
        
        trading_signal = TradingSignal(
            symbol=raw_signal.symbol,
            signal_type=signal_type,
            confidence=raw_signal.confidence,
            timestamp=raw_signal.timestamp,
            position_size=position_size,
            metadata=metadata
        )
        
        self.logger.debug(f"Converted signal for {raw_signal.symbol}: {signal_type} with confidence {raw_signal.confidence}")
        return trading_signal
    
    def _determine_signal_type(self, signal_value: float) -> SignalType:
        """
        Determine signal type based on signal value.
        
        Args:
            signal_value: Raw signal value
            
        Returns:
            Corresponding SignalType
        """
        # Professional momentum strategy signal interpretation
        if signal_value > 0.01:  # Strong positive momentum
            return SignalType.LONG
        elif signal_value < -0.01:  # Strong negative momentum
            return SignalType.SHORT
        else:  # Weak signal
            return SignalType.HOLD
    
    def _calculate_position_size(self, raw_signal: RawSignal) -> float:
        """
        Calculate position size based on signal strength and confidence.
        
        Args:
            raw_signal: Raw signal data
            
        Returns:
            Position size multiplier
        """
        # Base position size scaled by confidence
        base_size = abs(raw_signal.value) * self.config.position_size_multiplier
        confidence_adjusted_size = base_size * raw_signal.confidence
        
        # Cap position size to reasonable bounds
        max_position_size = 1.0  # 100% of available capital
        min_position_size = 0.01  # 1% of available capital
        
        return max(min_position_size, min(confidence_adjusted_size, max_position_size))
    
    def _extract_signal_metadata(self, raw_signal: RawSignal) -> Dict[str, Any]:
        """Extract and enhance signal metadata."""
        metadata = raw_signal.signal_metadata.copy()
        
        # Add conversion metadata
        metadata.update({
            'converter_version': INTERFACE_VERSION,
            'conversion_timestamp': pd.Timestamp.now(),
            'original_value': raw_signal.value,
            'confidence_threshold': self.config.confidence_threshold
        })
        
        return metadata
    
    def apply_signal_filters(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """
        Apply filtering logic to trading signals.
        
        Args:
            signals: List of trading signals to filter
            
        Returns:
            Filtered list of trading signals
        """
        if not self.config.enable_signal_filtering:
            return signals
        
        self.logger.debug(f"Applying signal filters to {len(signals)} signals")
        
        filtered_signals = []
        
        # Group signals by symbol
        signals_by_symbol = {}
        for signal in signals:
            if signal.symbol not in signals_by_symbol:
                signals_by_symbol[signal.symbol] = []
            signals_by_symbol[signal.symbol].append(signal)
        
        # Apply filters per symbol
        for symbol, symbol_signals in signals_by_symbol.items():
            # Sort by confidence (highest first)
            symbol_signals.sort(key=lambda s: s.confidence, reverse=True)
            
            # Limit number of signals per symbol
            limited_signals = symbol_signals[:self.config.max_signals_per_symbol]
            
            # Apply additional filters
            for signal in limited_signals:
                if self._passes_signal_filters(signal):
                    filtered_signals.append(signal)
        
        self.logger.info(f"Filtered {len(signals)} signals down to {len(filtered_signals)}")
        return filtered_signals
    
    def _passes_signal_filters(self, signal: TradingSignal) -> bool:
        """
        Check if a signal passes all filtering criteria.
        
        Args:
            signal: Trading signal to check
            
        Returns:
            True if signal passes all filters
        """
        # Check for recent signals on same symbol
        if self._has_recent_signal(signal):
            self.logger.debug(f"Filtering out {signal.symbol} due to recent signal")
            return False
        
        # Update signal history
        self._update_signal_history(signal)
        
        return True
    
    def _has_recent_signal(self, signal: TradingSignal) -> bool:
        """Check if there's a recent signal for the same symbol."""
        if signal.symbol not in self._signal_history:
            return False
        
        recent_signals = self._signal_history[signal.symbol]
        if not recent_signals:
            return False
        
        # Check if last signal was within decay periods
        last_signal = recent_signals[-1]
        time_diff = signal.timestamp - last_signal.timestamp
        
        # Simple time-based filtering (can be enhanced with bar-based filtering)
        return time_diff.total_seconds() < (self.config.signal_decay_periods * 60)  # 60 seconds per period
    
    def _update_signal_history(self, signal: TradingSignal) -> None:
        """Update signal history for filtering."""
        if signal.symbol not in self._signal_history:
            self._signal_history[signal.symbol] = []
        
        self._signal_history[signal.symbol].append(signal)
        
        # Keep only recent signals to prevent memory growth
        max_history_length = 100
        if len(self._signal_history[signal.symbol]) > max_history_length:
            self._signal_history[signal.symbol] = self._signal_history[signal.symbol][-max_history_length:]
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """Get signal conversion statistics."""
        total_signals = sum(len(signals) for signals in self._signal_history.values())
        symbols_count = len(self._signal_history)
        
        return {
            'total_signals_processed': total_signals,
            'unique_symbols': symbols_count,
            'conversion_config': self.config.__dict__,
            'interface_version': INTERFACE_VERSION
        }
    
    def reset_signal_history(self) -> None:
        """Reset signal history (useful for testing or new sessions)."""
        self._signal_history.clear()
        self.logger.info("Signal history reset")
