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

    # Rate limiting (Unlimited plan adjusted)
    rate_limit_calls: int = 500
    rate_limit_period: float = 1.0  # seconds

    # Request settings
    timeout_seconds: float = 60.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Data settings
    default_limit: int = 50000  # Max results per request

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

        self.logger.debug(f"Requesting URL: {url} with params: { {k:v for k,v in params.items() if k != 'apiKey'} }")

        for attempt in range(self.config.max_retries):
            try:
                async with self._session.get(url, params=params) as resp:
                    data = await resp.json()

                    if resp.status == 200:
                        self.logger.debug(f"Request successful. Status: {data.get('status')}, Results count: {len(data.get('results', []))}")
                        return data
                    elif resp.status == 429:  # Rate limited
                        wait = float(resp.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limited, waiting {wait}s")
                        await asyncio.sleep(wait)
                    elif resp.status == 404:
                        self.logger.info(f"Ticker not found (404): {url}")
                        return data
                    else:
                        self.logger.error(f"API error {resp.status} for {url}: {data}")
                        return data

            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    self.logger.warning(f"Request failed (attempt {attempt+1}), retrying in {self.config.retry_delay_seconds}s: {e}")
                    await asyncio.sleep(self.config.retry_delay_seconds)
                else:
                    self.logger.error(f"Request failed (final attempt {attempt+1}): {e}")

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

        if data.get('status') in ['OK', 'DELAYED'] and data.get('results'):
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

    async def get_grouped_daily_bars(self, date: datetime) -> pd.DataFrame:
        """
        Get grouped daily bars for the entire market for a specific date.

        Args:
            date: Date to fetch data for

        Returns:
            DataFrame with symbol as index and OHLCV data columns
        """
        date_str = date.strftime('%Y-%m-%d')
        url = f"{self.config.base_url}/v2/aggs/grouped/locale/us/market/stocks/{date_str}"

        data = await self._request(url)

        if data.get('status') in ['OK', 'DELAYED'] and data.get('results'):
            bars = []
            symbols = []
            for r in data['results']:
                symbols.append(r['T'])
                bars.append({
                    'open': r['o'],
                    'high': r['h'],
                    'low': r['l'],
                    'close': r['c'],
                    'volume': r['v'],
                    'vwap': r.get('vw'),
                    'num_trades': r.get('n'),
                    'timestamp': datetime.fromtimestamp(r['t'] / 1000, tz=timezone.utc)
                })

            df = pd.DataFrame(bars, index=symbols)
            df.index.name = 'symbol'
            return df
        
        return pd.DataFrame()

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

        if data.get('status') in ['OK', 'DELAYED'] and data.get('results'):
            bars = []
            timestamps = []
            for r in data['results']:
                timestamps.append(datetime.fromtimestamp(r['t'] / 1000, tz=timezone.utc))
                bars.append({
                    'open': r['o'],
                    'high': r['h'],
                    'low': r['l'],
                    'close': r['c'],
                    'volume': r['v'],
                    'vwap': r.get('vw'),
                    'num_trades': r.get('n'),
                })

            df = pd.DataFrame(bars, index=timestamps)
            df.index.name = 'timestamp'
            return df

        # Return empty DataFrame
        return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'vwap', 'num_trades'])

    async def get_bars_multi(
        self,
        symbols: List[str],
        timeframe: str = '1min',
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        days: int = 1,
    ) -> Dict[str, pd.DataFrame]:
        """
        Get bars for multiple symbols concurrently.

        Args:
            symbols: List of stock symbols
            timeframe: Bar timeframe
            start: Start datetime
            end: End datetime
            days: Days of history (if start/end not provided)

        Returns:
            Dict mapping symbol to DataFrame
        """
        tasks = [self.get_bars(symbol, timeframe=timeframe, start=start, end=end, days=days) for symbol in symbols]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for symbol, result in zip(symbols, batch_results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to get bars for {symbol}: {result}")
                results[symbol.upper()] = pd.DataFrame()
            else:
                results[symbol.upper()] = result
                self.logger.debug(f"Got {len(result)} bars for {symbol}")
        
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
        tasks = [self.get_previous_day(symbol) for symbol in symbols]
        bars = await asyncio.gather(*tasks, return_exceptions=True)
        
        prices = {}
        for symbol, bar in zip(symbols, bars):
            if isinstance(bar, AggregateBar):
                prices[symbol.upper()] = bar.close
            elif isinstance(bar, Exception):
                self.logger.error(f"Failed to get latest price for {symbol}: {bar}")

        return prices

    async def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker details (Market Cap, Sector, Industry, etc.).
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict containing ticker metadata
        """
        url = f"{self.config.base_url}/v3/reference/tickers/{symbol.upper()}"
        data = await self._request(url)
        
        if data.get('status') == 'OK' and data.get('results'):
            return data['results']
        
        return {}

    async def get_ticker_details_multi(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get ticker details for multiple symbols concurrently.
        """
        tasks = [self.get_ticker_details(symbol) for symbol in symbols]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for symbol, result in zip(symbols, batch_results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to get ticker details for {symbol}: {result}")
                results[symbol.upper()] = {}
            else:
                results[symbol.upper()] = result
        
        return results

    async def get_upcoming_earnings(self, symbols: List[str], days: int = 7) -> Dict[str, str]:
        """
        Get upcoming earnings dates for symbols.
        Note: This uses the /vX/reference/financials or similar if available,
        but for simplicity we'll implement a mock/stub if direct endpoint isn't clear
        for the current subscription. Polygon's 'events' API is often V3 reference.
        """
        # Placeholder implementation - Polygon's V3 Events API
        # GET /v3/reference/events?ticker={ticker}&event_type=earnings
        # This is a bit complex for bulk. Let's provide the method anyway.
        earnings_dates = {}
        # ... (implementation logic if needed) ...
        return earnings_dates

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

