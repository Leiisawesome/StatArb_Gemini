#!/usr/bin/env python3
"""
Polygon.io REST API Data Service
=================================

REST API-based data service for Polygon.io Stock Starter subscription.
Provides historical and delayed market data via REST endpoints.

Stock Starter Plan Features:
    ✅ Historical aggregate bars (minute, hour, day, week, month, quarter, year)
    ✅ Previous day aggregates
    ✅ End-of-day data
    ❌ Real-time quotes (requires Stock Developer+)
    ❌ Real-time trades (requires Stock Developer+)
    ❌ WebSocket streaming (requires Stock Developer+)

Usage:
    from core_engine.data.feeds.polygon_rest import PolygonRestService

    service = PolygonRestService(api_key="your_api_key")
    await service.initialize()

    # Get historical minute bars
    df = await service.get_bars("AAPL", timeframe="1min", days=5)

    # Get previous day data
    prev = await service.get_previous_day("AAPL")

    # Get multiple symbols
    df = await service.get_bars_multi(["AAPL", "TSLA", "NVDA"], timeframe="1min", days=1)

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import asyncio
import logging
import os
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class PolygonRestConfig:
    """Configuration for Polygon.io REST API service"""

    # API key (required)
    api_key: str = field(default_factory=lambda: os.getenv("POLYGON_API_KEY", ""))

    # Base URL
    base_url: str = "https://api.polygon.io"

    # Rate limiting (Stock Starter: 5 calls/minute)
    rate_limit_calls: int = 5
    rate_limit_period: float = 60.0  # seconds

    # Request settings
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Data settings
    default_limit: int = 5000  # Max results per request

    def __post_init__(self):
        if not self.api_key:
            raise ValueError(
                "Polygon API key required. Set POLYGON_API_KEY env var or pass api_key."
            )


@dataclass
class AggregateBar:
    """OHLCV aggregate bar"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None
    num_trades: Optional[int] = None


# ============================================================================
# POLYGON REST SERVICE
# ============================================================================

class PolygonRestService:
    """
    Polygon.io REST API Service for Stock Starter subscription.

    Provides historical market data via REST endpoints.
    Implements rate limiting to stay within API limits.
    """

    # Timeframe mappings
    TIMEFRAMES = {
        '1s': ('second', 1),
        '1sec': ('second', 1),
        '1min': ('minute', 1),
        '5min': ('minute', 5),
        '15min': ('minute', 15),
        '30min': ('minute', 30),
        '1h': ('hour', 1),
        '1hour': ('hour', 1),
        '4h': ('hour', 4),
        '1d': ('day', 1),
        '1day': ('day', 1),
        '1w': ('week', 1),
        '1week': ('week', 1),
        '1M': ('month', 1),
        '1month': ('month', 1),
    }

    def __init__(self, api_key: Optional[str] = None, config: Optional[PolygonRestConfig] = None):
        """Initialize Polygon REST service"""
        if config:
            self.config = config
        else:
            self.config = PolygonRestConfig(
                api_key=api_key or os.getenv("POLYGON_API_KEY", "")
            )

        self.logger = logging.getLogger(self.__class__.__name__)

        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None

        # Rate limiting
        self._request_times: List[float] = []

        # State
        self.is_initialized = False

    async def initialize(self) -> bool:
        """Initialize the service"""
        try:
            # Create SSL context (handle macOS certificate issues)
            ssl_context = ssl.create_default_context()
            try:
                import certifi
                ssl_context = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)

            self._session = aiohttp.ClientSession(
                connector=connector,
                trust_env=False,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            )

            # Verify API key
            if await self._verify_api_key():
                self.is_initialized = True
                self.logger.info("✅ PolygonRestService initialized")
                return True
            else:
                self.logger.error("API key verification failed")
                return False

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def close(self) -> None:
        """Close the service"""
        if self._session:
            await self._session.close()
            self._session = None
        self.is_initialized = False

    async def _verify_api_key(self) -> bool:
        """Verify API key is valid"""
        try:
            url = f"{self.config.base_url}/v2/aggs/ticker/AAPL/prev"
            data = await self._request(url)
            return data.get('status') == 'OK'
        except Exception as e:
            self.logger.error(f"API key verification failed: {e}")
            return False

    async def _rate_limit(self) -> None:
        """Enforce rate limiting"""
        now = asyncio.get_event_loop().time()

        # Remove old request times
        cutoff = now - self.config.rate_limit_period
        self._request_times = [t for t in self._request_times if t > cutoff]

        # Wait if at limit
        if len(self._request_times) >= self.config.rate_limit_calls:
            wait_time = self._request_times[0] + self.config.rate_limit_period - now
            if wait_time > 0:
                self.logger.debug(f"Rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self._request_times.append(now)

    async def _request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make rate-limited API request"""
        if not self._session:
            raise RuntimeError("Service not initialized")

        await self._rate_limit()

        # Add API key
        if params is None:
            params = {}
        params['apiKey'] = self.config.api_key

        for attempt in range(self.config.max_retries):
            try:
                async with self._session.get(url, params=params) as resp:
                    data = await resp.json()

                    if resp.status == 200:
                        return data
                    elif resp.status == 429:  # Rate limited
                        wait = float(resp.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limited, waiting {wait}s")
                        await asyncio.sleep(wait)
                    else:
                        self.logger.error(f"API error {resp.status}: {data}")
                        return data

            except Exception as e:
                self.logger.error(f"Request failed (attempt {attempt+1}): {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        return {'status': 'ERROR', 'message': 'Max retries exceeded'}

    # ========================================================================
    # DATA RETRIEVAL METHODS
    # ========================================================================

    async def get_previous_day(self, symbol: str) -> Optional[AggregateBar]:
        """
        Get previous day's aggregate bar.

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            AggregateBar with previous day's OHLCV data
        """
        url = f"{self.config.base_url}/v2/aggs/ticker/{symbol.upper()}/prev"
        data = await self._request(url)

        if data.get('status') == 'OK' and data.get('results'):
            r = data['results'][0]
            return AggregateBar(
                symbol=symbol.upper(),
                timestamp=datetime.fromtimestamp(r['t'] / 1000, tz=timezone.utc),
                open=r['o'],
                high=r['h'],
                low=r['l'],
                close=r['c'],
                volume=r['v'],
                vwap=r.get('vw'),
                num_trades=r.get('n'),
            )
        return None

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = '1min',
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        days: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Get historical aggregate bars.

        Args:
            symbol: Stock symbol
            timeframe: Bar timeframe ('1min', '5min', '15min', '1h', '1d', etc.)
            start: Start datetime (or use 'days' parameter)
            end: End datetime (defaults to now)
            days: Number of days to look back (alternative to start/end)
            limit: Max number of results

        Returns:
            DataFrame with columns: timestamp (index), open, high, low, close, volume, vwap
        """
        # Parse timeframe
        if timeframe not in self.TIMEFRAMES:
            raise ValueError(f"Invalid timeframe: {timeframe}. Valid: {list(self.TIMEFRAMES.keys())}")

        multiplier_type, multiplier = self.TIMEFRAMES[timeframe]

        # Determine date range
        if end is None:
            end = datetime.now(timezone.utc)
        elif end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if start is None:
            if days:
                start = end - timedelta(days=days)
            else:
                start = end - timedelta(days=7)  # Default 7 days
        elif start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        # Format dates
        start_str = start.strftime('%Y-%m-%d')
        end_str = end.strftime('%Y-%m-%d')

        # Build URL
        url = f"{self.config.base_url}/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{multiplier_type}/{start_str}/{end_str}"

        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': limit or self.config.default_limit,
        }

        data = await self._request(url, params)

        if data.get('status') == 'OK' and data.get('results'):
            bars = []
            for r in data['results']:
                bars.append({
                    'timestamp': datetime.fromtimestamp(r['t'] / 1000, tz=timezone.utc),
                    'open': r['o'],
                    'high': r['h'],
                    'low': r['l'],
                    'close': r['c'],
                    'volume': r['v'],
                    'vwap': r.get('vw'),
                    'num_trades': r.get('n'),
                })

            df = pd.DataFrame(bars)
            df.set_index('timestamp', inplace=True)
            return df

        # Return empty DataFrame
        return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'vwap', 'num_trades'])

    async def get_bars_multi(
        self,
        symbols: List[str],
        timeframe: str = '1min',
        days: int = 1,
    ) -> Dict[str, pd.DataFrame]:
        """
        Get bars for multiple symbols.

        Args:
            symbols: List of stock symbols
            timeframe: Bar timeframe
            days: Days of history

        Returns:
            Dict mapping symbol to DataFrame
        """
        results = {}

        for symbol in symbols:
            try:
                df = await self.get_bars(symbol, timeframe=timeframe, days=days)
                results[symbol.upper()] = df
                self.logger.debug(f"Got {len(df)} bars for {symbol}")
            except Exception as e:
                self.logger.error(f"Failed to get bars for {symbol}: {e}")
                results[symbol.upper()] = pd.DataFrame()

        return results

    async def get_daily_bars(
        self,
        symbol: str,
        days: int = 30,
    ) -> pd.DataFrame:
        """Get daily OHLCV bars"""
        return await self.get_bars(symbol, timeframe='1d', days=days)

    async def get_minute_bars(
        self,
        symbol: str,
        days: int = 1,
    ) -> pd.DataFrame:
        """Get minute OHLCV bars"""
        return await self.get_bars(symbol, timeframe='1min', days=days)

    async def get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get latest prices for symbols (from previous day close).

        Note: Real-time prices require Stock Developer+ plan.
        """
        prices = {}

        for symbol in symbols:
            bar = await self.get_previous_day(symbol)
            if bar:
                prices[symbol.upper()] = bar.close

        return prices

    def get_ohlcv_for_pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format DataFrame for pipeline (Rule 2).

        Returns DataFrame with standard columns: open, high, low, close, volume
        """
        if df.empty:
            return df

        return df[['open', 'high', 'low', 'close', 'volume']].copy()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def create_polygon_rest_service(
    api_key: Optional[str] = None,
) -> PolygonRestService:
    """
    Create and initialize a Polygon REST service.

    Args:
        api_key: Polygon API key (or set POLYGON_API_KEY env var)

    Returns:
        Initialized PolygonRestService

    Example:
        service = await create_polygon_rest_service()
        df = await service.get_bars("AAPL", timeframe="1min", days=1)
    """
    service = PolygonRestService(api_key=api_key)

    if not await service.initialize():
        raise RuntimeError("Failed to initialize Polygon REST service")

    return service


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'PolygonRestConfig',
    'PolygonRestService',
    'AggregateBar',
    'create_polygon_rest_service',
]

