#!/usr/bin/env python3
"""
Polygon.io REST API Data Service
=================================

REST API-based data service for Polygon.io/Massive stocks data.
Provides historical and delayed market data via REST endpoints.

Stocks Plan Features (REST):
    ✅ Historical aggregate bars (minute, hour, day, week, month, quarter, year)
    ✅ Previous day aggregates
    ✅ End-of-day data
    ❌ Real-time quote/trade streaming (requires WebSocket plan access)

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
from collections import deque
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
    max_concurrent_symbol_requests: int = 20

    # Security settings
    allow_insecure_ssl_fallback: bool = False

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
        self._request_times = deque()

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
                self.logger.debug("certifi not installed; using system trust store for SSL verification")
            except Exception as ssl_error:
                if not self.config.allow_insecure_ssl_fallback:
                    self.logger.error(
                        "Failed to build verified SSL context: %s. "
                        "Set allow_insecure_ssl_fallback=True only for development troubleshooting.",
                        ssl_error,
                    )
                    return False
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                self.logger.warning(
                    "SSL certificate verification disabled via allow_insecure_ssl_fallback. "
                    "This is not recommended for production."
                )

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
        while self._request_times and self._request_times[0] <= cutoff:
            self._request_times.popleft()

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
                    # Handle non-JSON responses for 404/403
                    if resp.status == 404:
                        self.logger.debug(f"Resource not found (404): {url}")
                        return {"status": "NOT_FOUND", "results": []}
                    
                    if resp.status == 403:
                        self.logger.debug(f"Not authorized (403): {url}")
                        return {"status": "NOT_AUTHORIZED", "results": []}

                    data = await resp.json()

                    if resp.status == 200:
                        self.logger.debug(f"Request successful. Status: {data.get('status')}, Results count: {len(data.get('results', []))}")
                        return data
                    elif resp.status == 429:  # Rate limited
                        wait = float(resp.headers.get('Retry-After', 60))
                        self.logger.warning(f"Rate limited, waiting {wait}s")
                        await asyncio.sleep(wait)
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

    async def _gather_symbol_tasks(
        self,
        symbols: List[str],
        operation,
    ) -> List[Any]:
        """Run per-symbol async operations with bounded concurrency."""
        if not symbols:
            return []

        max_concurrency = max(1, int(self.config.max_concurrent_symbol_requests))
        semaphore = asyncio.Semaphore(max_concurrency)

        async def run_one(symbol: str) -> Any:
            async with semaphore:
                return await operation(symbol)

        return await asyncio.gather(
            *(run_one(symbol) for symbol in symbols),
            return_exceptions=True,
        )

    @staticmethod
    def _parse_event_timestamp(raw_timestamp: Any) -> Optional[datetime]:
        """Parse event timestamps in seconds/ms/us/ns into UTC datetime."""
        try:
            timestamp_value = float(raw_timestamp)
        except (TypeError, ValueError):
            return None

        abs_value = abs(timestamp_value)
        if abs_value >= 1e17:  # nanoseconds
            seconds = timestamp_value / 1e9
        elif abs_value >= 1e14:  # microseconds
            seconds = timestamp_value / 1e6
        elif abs_value >= 1e11:  # milliseconds
            seconds = timestamp_value / 1e3
        else:  # seconds
            seconds = timestamp_value

        return datetime.fromtimestamp(seconds, tz=timezone.utc)

    @staticmethod
    def _event_timestamp_to_ns(dt_value: datetime) -> int:
        """Convert datetime to nanoseconds since epoch for Polygon v3 timestamp filters."""
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        else:
            dt_value = dt_value.astimezone(timezone.utc)
        return int(dt_value.timestamp() * 1_000_000_000)

    async def _fetch_paginated_v3(self, endpoint: str, params: Dict[str, Any], max_pages: int = 50) -> List[Dict[str, Any]]:
        """Fetch paginated v3 resources using Polygon next_url pagination."""
        all_rows: List[Dict[str, Any]] = []
        page_count = 0
        next_url: Optional[str] = endpoint
        next_params: Optional[Dict[str, Any]] = dict(params)

        while next_url and page_count < max_pages:
            data = await self._request(next_url, next_params)
            page_count += 1

            status = data.get('status')
            if status not in ['OK', 'DELAYED']:
                break

            rows = data.get('results', []) or []
            all_rows.extend(rows)

            next_url = data.get('next_url')
            next_params = None

            if not rows or not next_url:
                break

        return all_rows

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

        # Format dates (Support millisecond timestamps for high-res data)
        if timeframe in ['1s', '1sec']:
            start_str = str(int(start.timestamp() * 1000))
            end_str = str(int(end.timestamp() * 1000))
        else:
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
        async def fetch_bars(symbol: str) -> pd.DataFrame:
            return await self.get_bars(
                symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                days=days,
            )

        batch_results = await self._gather_symbol_tasks(symbols, fetch_bars)
        
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

        Note: Real-time streaming prices require Stock Advanced websocket access.
        """
        async def fetch_previous_day(symbol: str) -> Optional[AggregateBar]:
            return await self.get_previous_day(symbol)

        bars = await self._gather_symbol_tasks(symbols, fetch_previous_day)
        
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
        async def fetch_details(symbol: str) -> Dict[str, Any]:
            return await self.get_ticker_details(symbol)

        batch_results = await self._gather_symbol_tasks(symbols, fetch_details)
        
        results = {}
        for symbol, result in zip(symbols, batch_results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to get ticker details for {symbol}: {result}")
                results[symbol.upper()] = {}
            else:
                results[symbol.upper()] = result
        
        return results

    async def get_adv_multi(self, symbols: List[str], days: int = 30, end_date: Optional[datetime] = None) -> Dict[str, float]:
        """
        Calculate Average Daily Volume (ADV) for multiple symbols.
        """
        async def fetch_daily_bars(symbol: str) -> pd.DataFrame:
            return await self.get_bars(symbol, timeframe='1day', days=days, end=end_date)

        batch_results = await self._gather_symbol_tasks(symbols, fetch_daily_bars)
        
        adv_map = {}
        for symbol, df in zip(symbols, batch_results):
            if isinstance(df, pd.DataFrame) and not df.empty:
                # ADV = Mean of (Close * Volume)
                adv_map[symbol.upper()] = (df['close'] * df['volume']).mean()
            else:
                adv_map[symbol.upper()] = 0.0
        return adv_map

    async def get_upcoming_earnings(self, symbols: List[str], days: int = 7) -> Dict[str, str]:
        """
        Get upcoming earnings dates for symbols using Polygon V3 Events API.
        """
        # Note: Bulk events API is limited. We'll fetch per symbol for the final selection.
        # For a real production system, we'd use a dedicated provider or bulk file.
        earnings_map = {}
        
        async def fetch_earnings(symbol):
            # Try vX or v3. If 404/403, return None.
            url = f"{self.config.base_url}/vX/reference/events?ticker={symbol.upper()}&event_type=earnings"
            try:
                data = await self._request(url)
                if data.get('status') == 'OK' and data.get('results'):
                    events = data['results']
                    return symbol, events[0].get('date')
            except Exception as exc:
                self.logger.debug("Failed to fetch earnings for %s: %s", symbol, exc)
            return symbol, None

        results = await self._gather_symbol_tasks(symbols, fetch_earnings)
        
        for res in results:
            if isinstance(res, tuple) and res[1]:
                earnings_map[res[0]] = res[1]
        
        return earnings_map

    async def get_last_quote_multi(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get latest NBBO quotes for symbols.
        """
        async def fetch_quote(symbol):
            url = f"{self.config.base_url}/v3/quotes/{symbol.upper()}?limit=1"
            try:
                data = await self._request(url)
                if data.get('status') == 'OK' and data.get('results'):
                    q = data['results'][0]
                    return symbol, {
                        'bid': q.get('bid_price', 0),
                        'ask': q.get('ask_price', 0),
                        'bid_size': q.get('bid_size', 0),
                        'ask_size': q.get('ask_size', 0)
                    }
            except Exception as exc:
                self.logger.debug("Failed to fetch last quote for %s: %s", symbol, exc)
            return symbol, {}

        results = await self._gather_symbol_tasks(symbols, fetch_quote)
        
        quote_map = {}
        for res in results:
            if isinstance(res, tuple) and res[1]:
                quote_map[res[0]] = res[1]
        return quote_map

    async def get_historical_trades(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        limit: int = 50000,
        max_pages: int = 25,
    ) -> pd.DataFrame:
        """
        Get historical trades for a symbol from Polygon v3 trades endpoint.

        Returns:
            DataFrame indexed by event timestamp (UTC) with trade fields.
        """
        symbol_upper = symbol.upper()
        endpoint = f"{self.config.base_url}/v3/trades/{symbol_upper}"

        params = {
            'timestamp.gte': self._event_timestamp_to_ns(start),
            'timestamp.lte': self._event_timestamp_to_ns(end),
            'order': 'asc',
            'sort': 'timestamp',
            'limit': min(max(limit, 1), 50000),
        }

        rows = await self._fetch_paginated_v3(endpoint=endpoint, params=params, max_pages=max_pages)
        if not rows:
            return pd.DataFrame(columns=['price', 'size', 'exchange', 'conditions', 'tape'])

        parsed_rows = []
        timestamps = []
        for row in rows:
            timestamp_value = (
                row.get('sip_timestamp')
                or row.get('participant_timestamp')
                or row.get('trf_timestamp')
                or row.get('timestamp')
            )
            event_ts = self._parse_event_timestamp(timestamp_value)
            if event_ts is None:
                continue

            timestamps.append(event_ts)
            parsed_rows.append({
                'price': row.get('price', row.get('p')),
                'size': row.get('size', row.get('s')),
                'exchange': row.get('exchange', row.get('x')),
                'conditions': row.get('conditions', row.get('c', [])),
                'tape': row.get('tape', row.get('z')),
            })

        if not parsed_rows:
            return pd.DataFrame(columns=['price', 'size', 'exchange', 'conditions', 'tape'])

        df = pd.DataFrame(parsed_rows, index=pd.DatetimeIndex(timestamps, tz=timezone.utc))
        df.index.name = 'timestamp'
        return df.sort_index()

    async def get_historical_quotes(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        limit: int = 50000,
        max_pages: int = 25,
    ) -> pd.DataFrame:
        """
        Get historical NBBO quotes for a symbol from Polygon v3 quotes endpoint.

        Returns:
            DataFrame indexed by event timestamp (UTC) with quote fields.
        """
        symbol_upper = symbol.upper()
        endpoint = f"{self.config.base_url}/v3/quotes/{symbol_upper}"

        params = {
            'timestamp.gte': self._event_timestamp_to_ns(start),
            'timestamp.lte': self._event_timestamp_to_ns(end),
            'order': 'asc',
            'sort': 'timestamp',
            'limit': min(max(limit, 1), 50000),
        }

        rows = await self._fetch_paginated_v3(endpoint=endpoint, params=params, max_pages=max_pages)
        if not rows:
            return pd.DataFrame(columns=['bid', 'ask', 'bid_size', 'ask_size', 'bid_exchange', 'ask_exchange'])

        parsed_rows = []
        timestamps = []
        for row in rows:
            timestamp_value = (
                row.get('sip_timestamp')
                or row.get('participant_timestamp')
                or row.get('trf_timestamp')
                or row.get('timestamp')
            )
            event_ts = self._parse_event_timestamp(timestamp_value)
            if event_ts is None:
                continue

            timestamps.append(event_ts)
            parsed_rows.append({
                'bid': row.get('bid_price', row.get('bp', row.get('p'))),
                'ask': row.get('ask_price', row.get('ap', row.get('P'))),
                'bid_size': row.get('bid_size', row.get('bs', row.get('s'))),
                'ask_size': row.get('ask_size', row.get('as', row.get('S'))),
                'bid_exchange': row.get('bid_exchange', row.get('bx')),
                'ask_exchange': row.get('ask_exchange', row.get('ax')),
            })

        if not parsed_rows:
            return pd.DataFrame(columns=['bid', 'ask', 'bid_size', 'ask_size', 'bid_exchange', 'ask_exchange'])

        df = pd.DataFrame(parsed_rows, index=pd.DatetimeIndex(timestamps, tz=timezone.utc))
        df.index.name = 'timestamp'
        return df.sort_index()

    async def get_trade_quote_snapshots_1s(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        forward_fill_quotes: bool = True,
        forward_fill_trades: bool = False,
        limit: int = 50000,
        max_pages: int = 25,
    ) -> pd.DataFrame:
        """
        Build per-second historical snapshots by combining trades and quotes.

        Output columns:
            trade_price, trade_size, trade_exchange,
            quote_bid, quote_ask, quote_bid_size, quote_ask_size,
            spread, trade_count, quote_count
        """
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        start = start.astimezone(timezone.utc)
        end = end.astimezone(timezone.utc)

        if end < start:
            raise ValueError("end must be greater than or equal to start")

        trades_df, quotes_df = await asyncio.gather(
            self.get_historical_trades(symbol, start, end, limit=limit, max_pages=max_pages),
            self.get_historical_quotes(symbol, start, end, limit=limit, max_pages=max_pages),
        )

        second_index = pd.date_range(
            start=start.replace(microsecond=0),
            end=end.replace(microsecond=0),
            freq='1s',
            tz=timezone.utc,
        )

        if trades_df.empty:
            trade_snap = pd.DataFrame(index=second_index, columns=['trade_price', 'trade_size', 'trade_exchange', 'trade_count'])
        else:
            trade_last = trades_df[['price', 'size', 'exchange']].resample('1s').last()
            trade_count = trades_df[['price']].resample('1s').size().rename('trade_count').to_frame()
            trade_snap = trade_last.join(trade_count, how='outer').rename(columns={
                'price': 'trade_price',
                'size': 'trade_size',
                'exchange': 'trade_exchange',
            })
            trade_snap = trade_snap.reindex(second_index)
            if forward_fill_trades:
                trade_snap[['trade_price', 'trade_size', 'trade_exchange']] = trade_snap[
                    ['trade_price', 'trade_size', 'trade_exchange']
                ].ffill()
            trade_snap['trade_count'] = trade_snap['trade_count'].fillna(0).astype(int)

        if quotes_df.empty:
            quote_snap = pd.DataFrame(index=second_index, columns=[
                'quote_bid', 'quote_ask', 'quote_bid_size', 'quote_ask_size', 'quote_count'
            ])
        else:
            quote_last = quotes_df[['bid', 'ask', 'bid_size', 'ask_size']].resample('1s').last()
            quote_count = quotes_df[['bid']].resample('1s').size().rename('quote_count').to_frame()
            quote_snap = quote_last.join(quote_count, how='outer').rename(columns={
                'bid': 'quote_bid',
                'ask': 'quote_ask',
                'bid_size': 'quote_bid_size',
                'ask_size': 'quote_ask_size',
            })
            quote_snap = quote_snap.reindex(second_index)
            if forward_fill_quotes:
                quote_snap[['quote_bid', 'quote_ask', 'quote_bid_size', 'quote_ask_size']] = quote_snap[
                    ['quote_bid', 'quote_ask', 'quote_bid_size', 'quote_ask_size']
                ].ffill()
            quote_snap['quote_count'] = quote_snap['quote_count'].fillna(0).astype(int)

        snapshot_df = trade_snap.join(quote_snap, how='outer')
        snapshot_df['spread'] = snapshot_df['quote_ask'] - snapshot_df['quote_bid']
        snapshot_df.index.name = 'timestamp'
        return snapshot_df

    async def get_borrow_info_multi(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Mock service for borrow costs/availability.
        In production, this would call an IBKR or similar API.
        """
        # Mock: ETFs and Mega Caps are always Easy to Borrow (ETB)
        # Small caps might be Hard to Borrow (HTB)
        borrow_map = {}
        for s in symbols:
            # Placeholder logic
            borrow_map[s] = {
                'status': 'ETB', 
                'fee_pct': 0.25, # 25bps annual
                'available': 1000000
            }
        return borrow_map

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

