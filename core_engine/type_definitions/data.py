"""
Core Engine Data Types

Lightweight data management for standalone core_engine.
"""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
import logging

# Import fail-fast exceptions
try:
    from core_engine.exceptions import DataUnavailableError
except ImportError:
    # Fallback for standalone usage
    class DataUnavailableError(Exception):
        """Raised when required data is unavailable"""

class DataSource(Enum):
    """Market data source types"""
    EXCHANGE = "exchange"
    VENDOR = "vendor"
    BROKER = "broker"
    INTERNAL = "internal"
    ALTERNATIVE = "alternative"
    SYNTHETIC = "synthetic"
    CLICKHOUSE = "clickhouse"

class DataType(Enum):
    """Market data types"""
    QUOTE = "quote"
    TRADE = "trade"
    DEPTH = "depth"
    OHLCV = "ohlcv"
    STATISTICS = "statistics"
    NEWS = "news"
    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"

class DataQuality(Enum):
    """Data quality levels"""
    REAL_TIME = "real_time"
    DELAYED = "delayed"
    SNAPSHOT = "snapshot"
    HISTORICAL = "historical"
    ESTIMATED = "estimated"
    DERIVED = "derived"

@dataclass
class DataConfig:
    """Data source configuration"""
    provider: str = "yahoo"  # Default to Yahoo Finance
    update_frequency: str = "1min"  # Data update frequency
    cache_enabled: bool = True
    cache_duration: int = 300  # 5 minutes cache

    # Data quality settings
    fill_missing: bool = True
    validate_data: bool = True
    outlier_detection: bool = True
    outlier_threshold: float = 3.0  # Standard deviations

@dataclass
class MarketData:
    """
    Comprehensive Market Data Container
    Unified across all core_engine bricks (Rule 3: Unified Data Flow)
    """
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    # Extended OHLCV & Pricing
    adjusted_close: Optional[float] = None
    vwap: Optional[float] = None
    transactions: Optional[int] = None

    # Quote Data
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None

    # Corporate Actions
    dividend: Optional[float] = None
    split_ratio: Optional[float] = None

    # Metadata
    source: str = "clickhouse"
    exchange: Optional[str] = None
    quality_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'adjusted_close': self.adjusted_close,
            'vwap': self.vwap,
            'transactions': self.transactions,
            'bid': self.bid,
            'ask': self.ask,
            'bid_size': self.bid_size,
            'ask_size': self.ask_size,
            'dividend': self.dividend,
            'split_ratio': self.split_ratio,
            'source': self.source,
            'exchange': self.exchange
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketData':
        """Create from dictionary"""
        return cls(**data)

class DataProvider(ABC):
    """Abstract data provider interface"""

    @abstractmethod
    def get_historical_data(self, symbol: str, start_date: datetime,
                          end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
        """Get historical market data"""

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""

    @abstractmethod
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols"""

class YahooDataProvider(DataProvider):
    """Yahoo Finance data provider (lightweight implementation)"""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # symbol -> (data, timestamp)
        self._cache_duration = timedelta(minutes=5)

    def get_historical_data(self, symbol: str, start_date: datetime,
                          end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
        """Get historical data from Yahoo Finance"""
        try:
            import yfinance as yf

            # Create ticker
            ticker = yf.Ticker(symbol)

            # Get data
            data = ticker.history(start=start_date, end=end_date, interval=timeframe)

            if data.empty:
                # Return empty DataFrame with required columns
                return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

            # Standardize column names
            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            data.index.name = 'Date'

            return data

        except ImportError as e:
            raise DataUnavailableError(
                f"Required data library not available: {e}. Cannot fetch real market data."
            ) from e
        except Exception as e:
            raise DataUnavailableError(
                f"Error fetching data for {symbol}: {e}. Real market data required."
            ) from e

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        # Check cache first
        cache_key = f"{symbol}_current"
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_duration:
                return data

        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')

            # Cache result
            self._cache[cache_key] = (price, datetime.now())
            return price

        except Exception as e:
            raise DataUnavailableError(
                f"Error fetching current price for {symbol}: {e}. Real market data required."
            ) from e

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols"""
        prices = {}
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price is not None:
                prices[symbol] = price
        return prices

class DataManager:
    """Core data management"""

    def __init__(self, config: DataConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.provider = self._create_provider()
        self._data_cache: Dict[str, pd.DataFrame] = {}
        self._last_update: Dict[str, datetime] = {}

    def _create_provider(self) -> DataProvider:
        """Create data provider based on config"""
        if self.config.provider.lower() == "yahoo":
            return YahooDataProvider()
        else:
            raise ValueError(f"Unsupported data provider: {self.config.provider}")

    def get_data(self, symbol: str, start_date: datetime,
                end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
        """Get market data with caching"""
        cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"

        # Check cache
        if (self.config.cache_enabled and
            cache_key in self._data_cache and
            cache_key in self._last_update):

            cache_age = datetime.now() - self._last_update[cache_key]
            if cache_age.total_seconds() < self.config.cache_duration:
                return self._data_cache[cache_key]

        # Fetch new data
        data = self.provider.get_historical_data(symbol, start_date, end_date, timeframe)

        # Validate and clean data
        if self.config.validate_data:
            data = self._validate_data(data)

        if self.config.fill_missing:
            data = self._fill_missing_data(data)

        if self.config.outlier_detection:
            data = self._handle_outliers(data)

        # Cache result
        if self.config.cache_enabled:
            self._data_cache[cache_key] = data
            self._last_update[cache_key] = datetime.now()

        return data

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for symbols"""
        return self.provider.get_multiple_prices(symbols)

    def _validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate data quality"""
        if data.empty:
            return data

        # Remove rows with invalid prices
        data = data[(data['High'] >= data['Low']) &
                   (data['Close'] > 0) &
                   (data['Volume'] >= 0)]

        # Ensure OHLC consistency
        data = data[(data['Open'] >= data['Low']) & (data['Open'] <= data['High']) &
                   (data['Close'] >= data['Low']) & (data['Close'] <= data['High'])]

        return data

    def _fill_missing_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fill missing data points"""
        if data.empty:
            return data

        # Forward fill missing values
        data = data.ffill()

        # If still missing, backward fill
        data = data.bfill()

        return data

    def _handle_outliers(self, data: pd.DataFrame) -> pd.DataFrame:
        """Handle outlier data points"""
        if data.empty or len(data) < 10:
            return data

        # Calculate returns for outlier detection
        returns = data['Close'].pct_change().dropna()

        # Identify outliers using z-score
        z_scores = np.abs((returns - returns.mean()) / returns.std())
        outlier_mask = z_scores > self.config.outlier_threshold

        # Replace outlier returns with median
        if outlier_mask.any():
            median_return = returns.median()
            outlier_indices = returns[outlier_mask].index

            for idx in outlier_indices:
                if idx in data.index and idx != data.index[0]:
                    prev_idx = data.index[data.index.get_loc(idx) - 1]
                    data.loc[idx, 'Close'] = data.loc[prev_idx, 'Close'] * (1 + median_return)

                    # Adjust OHLC to be consistent with new close
                    data.loc[idx, 'High'] = max(data.loc[idx, 'Close'], data.loc[idx, 'High'])
                    data.loc[idx, 'Low'] = min(data.loc[idx, 'Close'], data.loc[idx, 'Low'])

        return data