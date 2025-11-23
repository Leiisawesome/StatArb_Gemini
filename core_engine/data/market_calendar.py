"""
Market Calendar & Asset Class Definitions
=========================================

Provides market session logic for different asset classes (Stocks, Crypto, Forex).
Enables dynamic trading hours for multi-asset backtesting.

Components:
- AssetClass (Enum)
- MarketSession (Dataclass)
- MarketCalendar (Logic)

Author: StatArb_Gemini Core Engine
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, Optional, Tuple
import logging

class AssetClass(Enum):
    """Asset classes with distinct trading characteristics"""
    US_EQUITY = "us_equity"      # Stocks/ETFs (9:30-16:00 ET)
    CRYPTO = "crypto"            # Cryptocurrencies (24/7)
    FOREX = "forex"              # Currencies (24/5)
    FUTURES = "futures"          # Futures (23/5)
    INTL_EQUITY = "intl_equity"  # International Equities

class MarketStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    HALTED = "halted"

@dataclass
class MarketSession:
    """Market session definition"""
    open_time: time
    close_time: time
    timezone: str = "America/New_York"
    days_of_week: Tuple[int, ...] = (0, 1, 2, 3, 4)  # Mon=0, Sun=6

class MarketCalendar:
    """
    Manages trading hours and sessions for different asset classes.
    Replaces hardcoded 9:30-16:00 logic.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define standard sessions
        self.sessions = {
            AssetClass.US_EQUITY: MarketSession(
                open_time=time(9, 30),
                close_time=time(16, 0),
                timezone="America/New_York",
                days_of_week=(0, 1, 2, 3, 4)
            ),
            AssetClass.CRYPTO: MarketSession(
                open_time=time(0, 0),
                close_time=time(23, 59, 59, 999999),
                timezone="UTC",
                days_of_week=(0, 1, 2, 3, 4, 5, 6)
            ),
            AssetClass.FOREX: MarketSession(
                open_time=time(0, 0),
                close_time=time(23, 59, 59, 999999),
                timezone="UTC",
                days_of_week=(0, 1, 2, 3, 4)  # Sun 5pm ET to Fri 5pm ET (simplified as Mon-Fri for now)
            )
        }
    
    def get_session_times(self, date: datetime, asset_class: AssetClass) -> Tuple[datetime, datetime]:
        """
        Get open and close datetimes for a specific date and asset class.
        
        Args:
            date: The date to check
            asset_class: The asset class (AssetClass enum)
            
        Returns:
            Tuple of (open_dt, close_dt)
        """
        session = self.sessions.get(asset_class)
        if not session:
            # Default to US Equity if unknown
            session = self.sessions[AssetClass.US_EQUITY]
            
        # Check if trading day
        if date.weekday() not in session.days_of_week:
            # Not a trading day - return None or handle appropriately
            # For backtesting data loading, we might want the "range" for that day even if closed
            # But technically it's closed.
            pass

        open_dt = date.replace(
            hour=session.open_time.hour,
            minute=session.open_time.minute,
            second=session.open_time.second,
            microsecond=session.open_time.microsecond
        )
        
        close_dt = date.replace(
            hour=session.close_time.hour,
            minute=session.close_time.minute,
            second=session.close_time.second,
            microsecond=session.close_time.microsecond
        )
        
        return open_dt, close_dt

    def get_asset_class(self, symbol: str) -> AssetClass:
        """
        Determine asset class from symbol.
        
        Heuristics:
        - Ends with '-USD': Crypto (e.g., BTC-USD)
        - Contains '/': Forex (e.g., EUR/USD)
        - Default: US Equity
        """
        if symbol.endswith('-USD') or symbol in ['BTC', 'ETH', 'SOL']:
            return AssetClass.CRYPTO
        elif '/' in symbol and len(symbol) == 7:
            return AssetClass.FOREX
        else:
            return AssetClass.US_EQUITY

