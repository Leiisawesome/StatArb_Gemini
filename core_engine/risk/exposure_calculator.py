"""
Risk Management - Exposure Calculator
Comprehensive position exposure analysis with sector, geographic, and factor exposure calculations
"""

import logging
import threading
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ExposureType(Enum):
    """Types of exposure calculations"""
    MARKET = "market"
    SECTOR = "sector" 
    REGION = "region"
    CURRENCY = "currency"
    FACTOR = "factor"
    SINGLE_NAME = "single_name"
    CREDIT = "credit"
    DURATION = "duration"
    VOLATILITY = "volatility"


class ExposureDirection(Enum):
    """Direction of exposure"""
    LONG = "long"
    SHORT = "short"
    NET = "net"
    GROSS = "gross"


@dataclass
class ExposureItem:
    """Individual exposure item"""
    identifier: str
    exposure_type: ExposureType
    value: float
    percentage: float
    currency: str = "USD"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExposureBreakdown:
    """Comprehensive exposure breakdown"""
    total_exposure: float
    long_exposure: float
    short_exposure: float
    net_exposure: float
    gross_exposure: float
    exposures: List[ExposureItem] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    

@dataclass
class ExposureLimit:
    """Exposure limit definition"""
    exposure_type: ExposureType
    identifier: str
    max_exposure: float
    warning_threshold: float
    currency: str = "USD"
    is_percentage: bool = True


@dataclass
class ExposureViolation:
    """Exposure limit violation"""
    exposure_item: ExposureItem
    limit: ExposureLimit
    violation_amount: float
    violation_percentage: float
    severity: str  # WARNING, CRITICAL
    timestamp: datetime = field(default_factory=datetime.now)


class ExposureCalculator:
    """
    Comprehensive exposure calculator for portfolio positions
    
    Calculates various types of exposures including market, sector, regional,
    currency, and factor exposures with limit monitoring and alerts.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize exposure calculator"""
        self.config = config or {}
        self._lock = threading.Lock()
        self._exposure_cache = {}
        self._cache_ttl = self.config.get('cache_ttl_seconds', 300)  # 5 minutes
        self._limits = {}
        self._violations = []
        self._calculation_history = deque(maxlen=1000)
        
        # Exposure calculation settings
        self.include_derivatives = self.config.get('include_derivatives', True)
        self.include_cash = self.config.get('include_cash', False)
        self.base_currency = self.config.get('base_currency', 'USD')
        
        # Factor loadings for factor exposure
        self._factor_loadings = {}
        
        # Sector mappings
        self._sector_mappings = self._load_sector_mappings()
        
        # Geographic mappings
        self._geographic_mappings = self._load_geographic_mappings()
        
        logger.info("ExposureCalculator initialized")
    
    def _load_sector_mappings(self) -> Dict[str, str]:
        """Load sector mappings for instruments"""
        # In production, this would come from a reference data service
        return {
            'AAPL': 'Technology',
            'MSFT': 'Technology', 
            'GOOGL': 'Technology',
            'TSLA': 'Consumer Discretionary',
            'JPM': 'Financials',
            'BAC': 'Financials',
            'XOM': 'Energy',
            'JNJ': 'Healthcare',
            'PG': 'Consumer Staples'
        }
    
    def _load_geographic_mappings(self) -> Dict[str, str]:
        """Load geographic mappings for instruments"""
        # In production, this would come from a reference data service
        return {
            'AAPL': 'North America',
            'MSFT': 'North America',
            'GOOGL': 'North America', 
            'TSLA': 'North America',
            'JPM': 'North America',
            'BAC': 'North America',
            'XOM': 'North America',
            'JNJ': 'North America',
            'PG': 'North America'
        }
    
    async def calculate_exposures(
        self,
        positions: Dict[str, Any],
        portfolio_value: float,
        exposure_types: Optional[List[ExposureType]] = None
    ) -> Dict[ExposureType, ExposureBreakdown]:
        """
        Calculate comprehensive exposures for portfolio positions
        
        Args:
            positions: Dictionary of positions {symbol: position_data}
            portfolio_value: Total portfolio value for percentage calculations
            exposure_types: Specific exposure types to calculate (default: all)
            
        Returns:
            Dictionary mapping exposure types to breakdown details
        """
        if exposure_types is None:
            exposure_types = list(ExposureType)
        
        start_time = time.time()
        
        try:
            with self._lock:
                exposures = {}
                
                # Calculate each exposure type
                for exposure_type in exposure_types:
                    exposures[exposure_type] = await self._calculate_exposure_type(
                        exposure_type, positions, portfolio_value
                    )
                
                # Store calculation in history
                calculation_record = {
                    'timestamp': datetime.now(),
                    'positions_count': len(positions),
                    'portfolio_value': portfolio_value,
                    'exposure_types': [et.value for et in exposure_types],
                    'calculation_time': time.time() - start_time
                }
                self._calculation_history.append(calculation_record)
                
                logger.info(f"Calculated {len(exposure_types)} exposure types in {time.time() - start_time:.3f}s")
                
                return exposures
                
        except Exception as e:
            logger.error(f"Error calculating exposures: {e}")
            raise
    
    async def _calculate_exposure_type(
        self,
        exposure_type: ExposureType,
        positions: Dict[str, Any],
        portfolio_value: float
    ) -> ExposureBreakdown:
        """Calculate specific exposure type"""
        
        if exposure_type == ExposureType.MARKET:
            return await self._calculate_market_exposure(positions, portfolio_value)
        elif exposure_type == ExposureType.SECTOR:
            return await self._calculate_sector_exposure(positions, portfolio_value)
        elif exposure_type == ExposureType.REGION:
            return await self._calculate_regional_exposure(positions, portfolio_value)
        elif exposure_type == ExposureType.CURRENCY:
            return await self._calculate_currency_exposure(positions, portfolio_value)
        elif exposure_type == ExposureType.FACTOR:
            return await self._calculate_factor_exposure(positions, portfolio_value)
        elif exposure_type == ExposureType.SINGLE_NAME:
            return await self._calculate_single_name_exposure(positions, portfolio_value)
        else:
            logger.warning(f"Unsupported exposure type: {exposure_type}")
            return ExposureBreakdown(0, 0, 0, 0, 0, [])
    
    async def _calculate_market_exposure(
        self,
        positions: Dict[str, Any],
        portfolio_value: float
    ) -> ExposureBreakdown:
        """Calculate overall market exposure"""
        
        total_long = 0
        total_short = 0
        exposures = []
        
        for symbol, position in positions.items():
            if not self._should_include_position(position):
                continue
                
            market_value = position.get('market_value', 0)
            quantity = position.get('quantity', 0)
            
            if quantity > 0:
                total_long += market_value
            elif quantity < 0:
                total_short += abs(market_value)
            
            # Add individual position exposure
            if market_value != 0:
                exposure_item = ExposureItem(
                    identifier="MARKET",
                    exposure_type=ExposureType.MARKET,
                    value=market_value,
                    percentage=(market_value / portfolio_value * 100) if portfolio_value > 0 else 0
                )
                exposures.append(exposure_item)
        
        net_exposure = total_long - total_short
        gross_exposure = total_long + total_short
        
        return ExposureBreakdown(
            total_exposure=gross_exposure,
            long_exposure=total_long,
            short_exposure=total_short,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            exposures=exposures
        )
    
    async def _calculate_sector_exposure(
        self,
        positions: Dict[str, Any],
        portfolio_value: float
    ) -> ExposureBreakdown:
        """Calculate sector exposure breakdown"""
        
        sector_exposures = defaultdict(float)
        total_long = 0
        total_short = 0
        exposures = []
        
        for symbol, position in positions.items():
            if not self._should_include_position(position):
                continue
            
            market_value = position.get('market_value', 0)
            quantity = position.get('quantity', 0)
            sector = self._sector_mappings.get(symbol, 'Unknown')
            
            sector_exposures[sector] += market_value
            
            if quantity > 0:
                total_long += market_value
            elif quantity < 0:
                total_short += abs(market_value)
        
        # Create exposure items for each sector
        for sector, value in sector_exposures.items():
            if value != 0:
                exposure_item = ExposureItem(
                    identifier=sector,
                    exposure_type=ExposureType.SECTOR,
                    value=value,
                    percentage=(value / portfolio_value * 100) if portfolio_value > 0 else 0
                )
                exposures.append(exposure_item)
        
        net_exposure = total_long - total_short
        gross_exposure = total_long + total_short
        
        return ExposureBreakdown(
            total_exposure=gross_exposure,
            long_exposure=total_long,
            short_exposure=total_short,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            exposures=exposures
        )
    
    async def _calculate_regional_exposure(
        self,
        positions: Dict[str, Any],
        portfolio_value: float
    ) -> ExposureBreakdown:
        """Calculate regional/geographic exposure breakdown"""
        
        regional_exposures = defaultdict(float)
        total_long = 0
        total_short = 0
        exposures = []
        
        for symbol, position in positions.items():
            if not self._should_include_position(position):
                continue
            
            market_value = position.get('market_value', 0)
            quantity = position.get('quantity', 0)
            region = self._geographic_mappings.get(symbol, 'Unknown')
            
            regional_exposures[region] += market_value
            
            if quantity > 0:
                total_long += market_value
            elif quantity < 0:
                total_short += abs(market_value)
        
        # Create exposure items for each region
        for region, value in regional_exposures.items():
            if value != 0:
                exposure_item = ExposureItem(
                    identifier=region,
                    exposure_type=ExposureType.REGION,
                    value=value,
                    percentage=(value / portfolio_value * 100) if portfolio_value > 0 else 0
                )
                exposures.append(exposure_item)
        
        net_exposure = total_long - total_short
        gross_exposure = total_long + total_short
        
        return ExposureBreakdown(
            total_exposure=gross_exposure,
            long_exposure=total_long,
            short_exposure=total_short,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            exposures=exposures
        )
    
    async def _calculate_currency_exposure(
        self,
        positions: Dict[str, Any],
        portfolio_value: float
    ) -> ExposureBreakdown:
        """Calculate currency exposure breakdown"""
        
        currency_exposures = defaultdict(float)
        total_long = 0
        total_short = 0
        exposures = []
        
        for symbol, position in positions.items():
            if not self._should_include_position(position):
                continue
            
            market_value = position.get('market_value', 0)
            quantity = position.get('quantity', 0)
            currency = position.get('currency', 'USD')
            
            currency_exposures[currency] += market_value
            
            if quantity > 0:
                total_long += market_value
            elif quantity < 0:
                total_short += abs(market_value)
        
        # Create exposure items for each currency
        for currency, value in currency_exposures.items():
            if value != 0:
                exposure_item = ExposureItem(
                    identifier=currency,
                    exposure_type=ExposureType.CURRENCY,
                    value=value,
                    percentage=(value / portfolio_value * 100) if portfolio_value > 0 else 0
                )
                exposures.append(exposure_item)
        
        net_exposure = total_long - total_short
        gross_exposure = total_long + total_short
        
        return ExposureBreakdown(
            total_exposure=gross_exposure,
            long_exposure=total_long,
            short_exposure=total_short,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            exposures=exposures
        )
    
    async def _calculate_factor_exposure(
        self,
        positions: Dict[str, Any],
        portfolio_value: float
    ) -> ExposureBreakdown:
        """Calculate factor exposure breakdown"""
        
        # For simplicity, using basic factor categories
        # In production, this would use actual factor loadings
        factor_exposures = {
            'Value': 0,
            'Growth': 0,
            'Momentum': 0,
            'Quality': 0,
            'Size': 0,
            'Volatility': 0
        }
        
        total_long = 0
        total_short = 0
        exposures = []
        
        for symbol, position in positions.items():
            if not self._should_include_position(position):
                continue
            
            market_value = position.get('market_value', 0)
            quantity = position.get('quantity', 0)
            
            # Simplified factor attribution (would use actual factor loadings)
            factor_loadings = self._get_factor_loadings(symbol)
            
            for factor, loading in factor_loadings.items():
                factor_exposures[factor] += market_value * loading
            
            if quantity > 0:
                total_long += market_value
            elif quantity < 0:
                total_short += abs(market_value)
        
        # Create exposure items for each factor
        for factor, value in factor_exposures.items():
            if abs(value) > 0.01:  # Threshold for small exposures
                exposure_item = ExposureItem(
                    identifier=factor,
                    exposure_type=ExposureType.FACTOR,
                    value=value,
                    percentage=(value / portfolio_value * 100) if portfolio_value > 0 else 0
                )
                exposures.append(exposure_item)
        
        net_exposure = total_long - total_short
        gross_exposure = total_long + total_short
        
        return ExposureBreakdown(
            total_exposure=gross_exposure,
            long_exposure=total_long,
            short_exposure=total_short,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            exposures=exposures
        )
    
    async def _calculate_single_name_exposure(
        self,
        positions: Dict[str, Any],
        portfolio_value: float
    ) -> ExposureBreakdown:
        """Calculate single name concentration exposure"""
        
        total_long = 0
        total_short = 0
        exposures = []
        
        for symbol, position in positions.items():
            if not self._should_include_position(position):
                continue
            
            market_value = position.get('market_value', 0)
            quantity = position.get('quantity', 0)
            
            if quantity > 0:
                total_long += market_value
            elif quantity < 0:
                total_short += abs(market_value)
            
            # Add individual position as single name exposure
            if market_value != 0:
                exposure_item = ExposureItem(
                    identifier=symbol,
                    exposure_type=ExposureType.SINGLE_NAME,
                    value=market_value,
                    percentage=(market_value / portfolio_value * 100) if portfolio_value > 0 else 0
                )
                exposures.append(exposure_item)
        
        # Sort by absolute exposure value
        exposures.sort(key=lambda x: abs(x.value), reverse=True)
        
        net_exposure = total_long - total_short
        gross_exposure = total_long + total_short
        
        return ExposureBreakdown(
            total_exposure=gross_exposure,
            long_exposure=total_long,
            short_exposure=total_short,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            exposures=exposures
        )
    
    def _get_factor_loadings(self, symbol: str) -> Dict[str, float]:
        """Get factor loadings for a symbol"""
        # Simplified factor loadings - in production this would come from risk model
        loadings = {
            'Value': np.random.uniform(-0.5, 0.5),
            'Growth': np.random.uniform(-0.5, 0.5),
            'Momentum': np.random.uniform(-0.5, 0.5),
            'Quality': np.random.uniform(-0.5, 0.5),
            'Size': np.random.uniform(-0.5, 0.5),
            'Volatility': np.random.uniform(-0.5, 0.5)
        }
        return loadings
    
    def _should_include_position(self, position: Dict[str, Any]) -> bool:
        """Determine if position should be included in exposure calculations"""
        
        # Skip cash positions if not configured to include
        if not self.include_cash and position.get('asset_type') == 'CASH':
            return False
        
        # Skip derivatives if not configured to include
        if not self.include_derivatives and position.get('asset_type') in ['OPTION', 'FUTURE', 'SWAP']:
            return False
        
        # Skip zero quantity positions
        if position.get('quantity', 0) == 0:
            return False
        
        return True
    
    async def check_exposure_limits(
        self,
        exposures: Dict[ExposureType, ExposureBreakdown],
        portfolio_value: float
    ) -> List[ExposureViolation]:
        """Check exposure limits and identify violations"""
        
        violations = []
        
        for exposure_type, breakdown in exposures.items():
            # Check limits for this exposure type
            for exposure_item in breakdown.exposures:
                limit_key = f"{exposure_type.value}_{exposure_item.identifier}"
                
                if limit_key in self._limits:
                    limit = self._limits[limit_key]
                    violation = self._check_single_limit(exposure_item, limit, portfolio_value)
                    
                    if violation:
                        violations.append(violation)
        
        # Store violations
        self._violations.extend(violations)
        
        # Keep only recent violations (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self._violations = [v for v in self._violations if v.timestamp >= cutoff_time]
        
        return violations
    
    def _check_single_limit(
        self,
        exposure_item: ExposureItem,
        limit: ExposureLimit,
        portfolio_value: float
    ) -> Optional[ExposureViolation]:
        """Check a single exposure against its limit"""
        
        exposure_value = abs(exposure_item.value)
        
        if limit.is_percentage:
            exposure_pct = (exposure_value / portfolio_value * 100) if portfolio_value > 0 else 0
            max_allowed = limit.max_exposure
            warning_threshold = limit.warning_threshold
            current_level = exposure_pct
        else:
            max_allowed = limit.max_exposure
            warning_threshold = limit.warning_threshold
            current_level = exposure_value
        
        if current_level > max_allowed:
            violation_amount = current_level - max_allowed
            violation_pct = (violation_amount / max_allowed * 100) if max_allowed > 0 else 0
            
            return ExposureViolation(
                exposure_item=exposure_item,
                limit=limit,
                violation_amount=violation_amount,
                violation_percentage=violation_pct,
                severity="CRITICAL"
            )
        
        elif current_level > warning_threshold:
            violation_amount = current_level - warning_threshold
            violation_pct = (violation_amount / warning_threshold * 100) if warning_threshold > 0 else 0
            
            return ExposureViolation(
                exposure_item=exposure_item,
                limit=limit,
                violation_amount=violation_amount,
                violation_percentage=violation_pct,
                severity="WARNING"
            )
        
        return None
    
    def set_exposure_limit(self, limit: ExposureLimit) -> None:
        """Set an exposure limit"""
        limit_key = f"{limit.exposure_type.value}_{limit.identifier}"
        
        with self._lock:
            self._limits[limit_key] = limit
            
        logger.info(f"Set exposure limit: {limit_key} = {limit.max_exposure}")
    
    def remove_exposure_limit(self, exposure_type: ExposureType, identifier: str) -> None:
        """Remove an exposure limit"""
        limit_key = f"{exposure_type.value}_{identifier}"
        
        with self._lock:
            if limit_key in self._limits:
                del self._limits[limit_key]
                logger.info(f"Removed exposure limit: {limit_key}")
    
    def get_exposure_limits(self) -> Dict[str, ExposureLimit]:
        """Get all current exposure limits"""
        with self._lock:
            return self._limits.copy()
    
    def get_exposure_violations(self, severity: Optional[str] = None) -> List[ExposureViolation]:
        """Get current exposure violations"""
        with self._lock:
            violations = self._violations.copy()
        
        if severity:
            violations = [v for v in violations if v.severity == severity]
        
        return violations
    
    def get_calculation_history(self) -> List[Dict[str, Any]]:
        """Get calculation history"""
        with self._lock:
            return list(self._calculation_history)
    
    def clear_cache(self) -> None:
        """Clear exposure calculation cache"""
        with self._lock:
            self._exposure_cache.clear()
            
        logger.info("Exposure calculation cache cleared")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        logger.info("ExposureCalculator cleanup completed")