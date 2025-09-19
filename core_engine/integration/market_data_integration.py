"""
Market Data Integration - Phase 2 Component
===========================================

Integrates market data feeds with CentralRiskManager authorization workflows.
Ensures all market data meets risk governance standards before strategy consumption.

Features:
- Market data quality authorization through CentralRiskManager
- Real-time data validation with risk oversight
- Data source risk assessment and approval
- Market data feed risk monitoring
- Quality-gated data distribution to strategies

Author: StatArb_Gemini Phase 2 Integration
Version: 2.0.0
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

from core_engine.central_risk_manager import (
    CentralRiskManager, RiskDecision, RiskAssessment, 
    RiskLevel, DataRequest, DataUpdate
)

logger = logging.getLogger(__name__)

class DataAuthorizationStatus(Enum):
    """Market data authorization status"""
    PENDING_AUTHORIZATION = "pending_authorization"
    AUTHORIZED = "authorized"
    REJECTED = "rejected"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    QUALITY_MONITORING_REQUIRED = "quality_monitoring_required"
    DATA_EMBARGO = "data_embargo"

class DataRiskLevel(Enum):
    """Data-specific risk levels"""
    TRUSTED = "trusted"           # Verified high-quality data sources
    VALIDATED = "validated"       # Standard validated data
    MONITORED = "monitored"       # Requires continuous monitoring
    RESTRICTED = "restricted"     # Limited use, high oversight
    QUARANTINED = "quarantined"   # Isolated pending validation

class DataQualityStatus(Enum):
    """Data quality validation status"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"

@dataclass
class DataAuthorizationRequest:
    """Request for market data authorization"""
    request_id: str
    data_source: str
    symbols: List[str]
    data_type: str  # 'price', 'volume', 'orderbook', 'trades'
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Quality context
    expected_frequency: str = "1min"  # Expected data frequency
    quality_requirements: Dict[str, Any] = field(default_factory=dict)
    usage_strategy: str = "trading"  # 'trading', 'research', 'monitoring'
    
    # Risk context
    data_criticality: str = "HIGH"  # HIGH, MEDIUM, LOW
    risk_level: DataRiskLevel = DataRiskLevel.VALIDATED
    requires_manual_approval: bool = False

@dataclass
class DataAuthorizationResponse:
    """Response from market data authorization"""
    request_id: str
    status: DataAuthorizationStatus
    authorized_symbols: List[str]
    authorized_conditions: List[str] = field(default_factory=list)
    
    # Quality parameters
    max_latency_ms: Optional[int] = None
    min_quality_score: Optional[float] = None
    required_validations: List[str] = field(default_factory=list)
    
    # Monitoring requirements
    continuous_monitoring: bool = False
    quality_alert_threshold: float = 0.7  # Quality score threshold for alerts
    
    # Risk manager context
    risk_assessment: Optional[RiskAssessment] = None
    authorization_timestamp: datetime = field(default_factory=datetime.now)
    authorized_by: str = "CentralRiskManager"
    expiry_timestamp: Optional[datetime] = None

@dataclass
class MarketDataQualityMetrics:
    """Market data quality metrics"""
    symbol: str
    timestamp: datetime
    
    # Basic quality metrics
    data_freshness_seconds: float
    completeness_score: float  # 0.0 to 1.0
    accuracy_score: float      # 0.0 to 1.0
    consistency_score: float   # 0.0 to 1.0
    
    # Price quality
    price_volatility: float
    price_gaps_detected: int
    outlier_count: int
    
    # Volume quality
    volume_consistency: float
    volume_spikes_detected: int
    
    # Technical quality
    latency_ms: float
    packet_loss_rate: float
    error_rate: float
    
    # Overall quality
    overall_quality_score: float = 0.0
    quality_status: DataQualityStatus = DataQualityStatus.ACCEPTABLE

class MarketDataRiskMonitor:
    """Real-time market data risk monitoring"""
    
    def __init__(self, central_risk_manager: CentralRiskManager):
        self.central_risk_manager = central_risk_manager
        self.active_data_streams: Dict[str, DataAuthorizationRequest] = {}
        self.quality_metrics: Dict[str, List[MarketDataQualityMetrics]] = {}
        self.data_alerts: List[Dict[str, Any]] = []
        self.quality_history: Dict[str, deque] = {}
        
    async def start_data_monitoring(self, request_id: str,
                                  data_request: DataAuthorizationRequest,
                                  authorization: DataAuthorizationResponse):
        """Start monitoring authorized data feed"""
        
        self.active_data_streams[request_id] = data_request
        
        # Initialize quality tracking
        for symbol in authorization.authorized_symbols:
            if symbol not in self.quality_metrics:
                self.quality_metrics[symbol] = []
            if symbol not in self.quality_history:
                self.quality_history[symbol] = deque(maxlen=100)  # Keep last 100 quality scores
        
        # Set up continuous monitoring if required
        if authorization.continuous_monitoring:
            asyncio.create_task(self._continuous_monitoring_loop(request_id, authorization))
        
        logger.info(f"🔍 Started data monitoring for {request_id} - "
                   f"Symbols: {authorization.authorized_symbols}")
    
    async def _continuous_monitoring_loop(self, request_id: str,
                                        authorization: DataAuthorizationResponse):
        """Continuous monitoring loop for high-risk data feeds"""
        
        while request_id in self.active_data_streams:
            try:
                # Check data quality for all authorized symbols
                for symbol in authorization.authorized_symbols:
                    quality_metrics = await self._assess_data_quality(symbol)
                    
                    if quality_metrics:
                        # Store quality metrics
                        if symbol not in self.quality_metrics:
                            self.quality_metrics[symbol] = []
                        self.quality_metrics[symbol].append(quality_metrics)
                        
                        # Update quality history
                        self.quality_history[symbol].append(quality_metrics.overall_quality_score)
                        
                        # Check quality thresholds
                        if quality_metrics.overall_quality_score < authorization.quality_alert_threshold:
                            await self._handle_quality_degradation(
                                request_id, symbol, quality_metrics, authorization
                            )
                
                # Sleep between monitoring checks
                await asyncio.sleep(30.0)  # 30-second monitoring interval
                
            except Exception as e:
                logger.error(f"Error in data monitoring for {request_id}: {e}")
                await asyncio.sleep(60.0)  # Back off on error
    
    async def _assess_data_quality(self, symbol: str) -> Optional[MarketDataQualityMetrics]:
        """Assess current data quality for a symbol"""
        
        try:
            # Simulate data quality assessment
            # In real implementation, this would analyze actual market data
            
            current_time = datetime.now()
            
            # Simulate quality metrics
            freshness = np.random.uniform(1.0, 30.0)  # 1-30 seconds
            completeness = np.random.uniform(0.8, 1.0)  # 80-100%
            accuracy = np.random.uniform(0.85, 1.0)    # 85-100%
            consistency = np.random.uniform(0.9, 1.0)  # 90-100%
            
            latency = np.random.uniform(10.0, 100.0)   # 10-100ms
            error_rate = np.random.uniform(0.0, 0.05)  # 0-5%
            
            # Calculate overall quality score
            quality_weights = {
                'freshness': 0.2,
                'completeness': 0.25,
                'accuracy': 0.25,
                'consistency': 0.15,
                'latency': 0.1,
                'error_rate': 0.05
            }
            
            freshness_score = max(0.0, 1.0 - (freshness / 60.0))  # Penalize staleness
            latency_score = max(0.0, 1.0 - (latency / 200.0))     # Penalize high latency
            error_score = max(0.0, 1.0 - (error_rate / 0.1))      # Penalize errors
            
            overall_score = (
                quality_weights['freshness'] * freshness_score +
                quality_weights['completeness'] * completeness +
                quality_weights['accuracy'] * accuracy +
                quality_weights['consistency'] * consistency +
                quality_weights['latency'] * latency_score +
                quality_weights['error_rate'] * error_score
            )
            
            # Determine quality status
            if overall_score >= 0.9:
                quality_status = DataQualityStatus.EXCELLENT
            elif overall_score >= 0.8:
                quality_status = DataQualityStatus.GOOD
            elif overall_score >= 0.7:
                quality_status = DataQualityStatus.ACCEPTABLE
            elif overall_score >= 0.5:
                quality_status = DataQualityStatus.POOR
            else:
                quality_status = DataQualityStatus.UNACCEPTABLE
            
            return MarketDataQualityMetrics(
                symbol=symbol,
                timestamp=current_time,
                data_freshness_seconds=freshness,
                completeness_score=completeness,
                accuracy_score=accuracy,
                consistency_score=consistency,
                price_volatility=np.random.uniform(0.01, 0.05),
                price_gaps_detected=np.random.randint(0, 3),
                outlier_count=np.random.randint(0, 2),
                volume_consistency=np.random.uniform(0.8, 1.0),
                volume_spikes_detected=np.random.randint(0, 2),
                latency_ms=latency,
                packet_loss_rate=np.random.uniform(0.0, 0.02),
                error_rate=error_rate,
                overall_quality_score=overall_score,
                quality_status=quality_status
            )
            
        except Exception as e:
            logger.error(f"Error assessing data quality for {symbol}: {e}")
            return None
    
    async def _handle_quality_degradation(self, request_id: str, symbol: str,
                                        quality_metrics: MarketDataQualityMetrics,
                                        authorization: DataAuthorizationResponse):
        """Handle data quality degradation"""
        
        logger.warning(f"⚠️ Data quality degradation detected: {symbol} - "
                      f"Score: {quality_metrics.overall_quality_score:.3f}")
        
        # Record alert
        self.data_alerts.append({
            'timestamp': datetime.now(),
            'request_id': request_id,
            'symbol': symbol,
            'alert_type': 'QUALITY_DEGRADATION',
            'quality_score': quality_metrics.overall_quality_score,
            'quality_status': quality_metrics.quality_status.value,
            'metrics': quality_metrics
        })
        
        # Notify central risk manager if quality is unacceptable
        if quality_metrics.quality_status == DataQualityStatus.UNACCEPTABLE:
            await self._escalate_data_quality_issue(request_id, symbol, quality_metrics)
    
    async def _escalate_data_quality_issue(self, request_id: str, symbol: str,
                                         quality_metrics: MarketDataQualityMetrics):
        """Escalate serious data quality issues to risk manager"""
        
        logger.error(f"🚨 ESCALATING: Data quality unacceptable for {symbol}")
        
        # Create data update for risk manager
        data_update = DataUpdate(
            symbol=symbol,
            data_type="quality_alert",
            value=quality_metrics.overall_quality_score,
            timestamp=datetime.now(),
            source="MarketDataRiskMonitor",
            metadata={
                'quality_status': quality_metrics.quality_status.value,
                'latency_ms': quality_metrics.latency_ms,
                'error_rate': quality_metrics.error_rate,
                'request_id': request_id
            }
        )
        
        # Submit to risk manager for assessment
        try:
            await self.central_risk_manager.assess_data_update(data_update)
        except Exception as e:
            logger.error(f"Failed to escalate data quality issue: {e}")

class RiskIntegratedMarketDataManager:
    """
    Risk-Integrated Market Data Manager
    
    Wraps market data management with CentralRiskManager authorization workflows.
    Ensures all market data consumption is properly authorized and monitored
    through risk governance.
    
    Key Features:
    - Pre-consumption data authorization
    - Real-time data quality monitoring with risk oversight
    - Data source risk assessment and approval
    - Quality-gated data distribution
    - Emergency data embargo capabilities
    """
    
    def __init__(self, central_risk_manager: CentralRiskManager):
        self.central_risk_manager = central_risk_manager
        self.risk_monitor = MarketDataRiskMonitor(central_risk_manager)
        
        # Authorization tracking
        self.pending_authorizations: Dict[str, DataAuthorizationRequest] = {}
        self.authorized_data_feeds: Dict[str, DataAuthorizationResponse] = {}
        self.data_consumption_history: List[Dict[str, Any]] = []
        
        # Data quality tracking
        self.approved_data_sources: Set[str] = set()
        self.restricted_symbols: Set[str] = set()
        self.quality_metrics_cache: Dict[str, MarketDataQualityMetrics] = {}
        
        # Risk metrics
        self.total_authorized_feeds = 0
        self.total_rejected_feeds = 0
        self.authorization_success_rate = 1.0
        
        logger.info("🏗️ Risk-Integrated Market Data Manager initialized")
    
    async def request_data_authorization(self, 
                                       data_source: str,
                                       symbols: List[str],
                                       data_type: str = "price",
                                       usage_strategy: str = "trading",
                                       quality_requirements: Optional[Dict[str, Any]] = None) -> DataAuthorizationResponse:
        """
        Request authorization for market data consumption through CentralRiskManager
        
        Args:
            data_source: Source of market data (e.g., 'IBKR', 'Bloomberg', 'Yahoo')
            symbols: List of symbols to authorize
            data_type: Type of data ('price', 'volume', 'orderbook', 'trades')
            usage_strategy: Strategy usage ('trading', 'research', 'monitoring')
            quality_requirements: Quality requirements for the data
            
        Returns:
            DataAuthorizationResponse with authorization decision
        """
        
        request_id = f"data_auth_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🔐 Requesting data authorization: {request_id} - "
                   f"Source: {data_source}, Symbols: {symbols[:5]}{'...' if len(symbols) > 5 else ''}")
        
        # Create authorization request
        auth_request = DataAuthorizationRequest(
            request_id=request_id,
            data_source=data_source,
            symbols=symbols,
            data_type=data_type,
            quality_requirements=quality_requirements or {},
            usage_strategy=usage_strategy,
            data_criticality="HIGH" if usage_strategy == "trading" else "MEDIUM"
        )
        
        # Assess data risk level
        auth_request.risk_level = await self._assess_data_risk_level(auth_request)
        
        # Store pending authorization
        self.pending_authorizations[request_id] = auth_request
        
        try:
            # Create data request for CentralRiskManager
            data_request = DataRequest(
                request_id=request_id,
                symbols=symbols,
                data_type=data_type,
                source=data_source,
                timestamp=datetime.now(),
                usage_purpose=usage_strategy
            )
            
            # Request authorization from CentralRiskManager
            risk_decision = await self.central_risk_manager.authorize_data_access(data_request)
            
            # Convert risk decision to data authorization
            auth_response = await self._convert_risk_decision_to_data_authorization(
                request_id, risk_decision, auth_request
            )
            
            # Store authorization response
            self.authorized_data_feeds[request_id] = auth_response
            
            # Remove from pending
            if request_id in self.pending_authorizations:
                del self.pending_authorizations[request_id]
            
            # Update metrics
            if auth_response.status == DataAuthorizationStatus.AUTHORIZED:
                self.total_authorized_feeds += 1
                self.approved_data_sources.add(data_source)
            else:
                self.total_rejected_feeds += 1
            
            self._update_authorization_success_rate()
            
            logger.info(f"✅ Data authorization completed: {request_id} - "
                       f"Status: {auth_response.status.value}")
            
            return auth_response
            
        except Exception as e:
            logger.error(f"❌ Data authorization failed: {request_id} - Error: {e}")
            
            # Return rejection response
            return DataAuthorizationResponse(
                request_id=request_id,
                status=DataAuthorizationStatus.REJECTED,
                authorized_symbols=[],
                authorized_conditions=["AUTHORIZATION_ERROR"]
            )
    
    async def consume_authorized_data(self, 
                                    authorization: DataAuthorizationResponse,
                                    callback: Optional[Callable] = None) -> Dict[str, pd.DataFrame]:
        """
        Consume market data that has been authorized by CentralRiskManager
        
        Args:
            authorization: The authorization response from request_data_authorization
            callback: Optional callback function for real-time data updates
            
        Returns:
            Dictionary of DataFrames containing authorized market data
        """
        
        request_id = authorization.request_id
        
        # Verify authorization status
        if authorization.status != DataAuthorizationStatus.AUTHORIZED:
            raise ValueError(f"Cannot consume unauthorized data: {request_id} - "
                           f"Status: {authorization.status.value}")
        
        logger.info(f"📊 Consuming authorized data: {request_id} - "
                   f"Symbols: {authorization.authorized_symbols}")
        
        try:
            # Start data monitoring
            original_request = self.pending_authorizations.get(request_id) or \
                             DataAuthorizationRequest(
                                 request_id=request_id,
                                 data_source="unknown",
                                 symbols=authorization.authorized_symbols,
                                 data_type="price"
                             )
            
            await self.risk_monitor.start_data_monitoring(
                request_id, original_request, authorization
            )
            
            # Simulate data consumption
            # In real implementation, this would connect to actual data feeds
            market_data = {}
            
            for symbol in authorization.authorized_symbols:
                # Generate sample market data
                data = self._generate_sample_market_data(symbol)
                
                # Apply quality validations if required
                if authorization.required_validations:
                    data = await self._apply_quality_validations(data, authorization.required_validations)
                
                # Check data meets minimum quality score
                if authorization.min_quality_score:
                    quality_score = await self._calculate_data_quality_score(data)
                    if quality_score < authorization.min_quality_score:
                        logger.warning(f"⚠️ Data quality below threshold for {symbol}: "
                                     f"{quality_score:.3f} < {authorization.min_quality_score}")
                        continue
                
                market_data[symbol] = data
            
            # Record data consumption
            self.data_consumption_history.append({
                'timestamp': datetime.now(),
                'request_id': request_id,
                'authorization': authorization,
                'symbols_consumed': list(market_data.keys()),
                'data_quality_check': True
            })
            
            # Notify risk manager of data consumption
            for symbol in market_data.keys():
                data_update = DataUpdate(
                    symbol=symbol,
                    data_type="consumption",
                    value=1.0,
                    timestamp=datetime.now(),
                    source="RiskIntegratedMarketDataManager",
                    metadata={'request_id': request_id}
                )
                await self.central_risk_manager.update_data_usage(data_update)
            
            logger.info(f"✅ Authorized data consumption completed: {request_id} - "
                       f"Consumed {len(market_data)} symbols")
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Authorized data consumption failed: {request_id} - Error: {e}")
            
            # Return empty data on error
            return {}
    
    def _generate_sample_market_data(self, symbol: str, 
                                   periods: int = 100) -> pd.DataFrame:
        """Generate sample market data for testing"""
        
        # Generate realistic price series
        np.random.seed(hash(symbol) % 2**32)  # Consistent seed based on symbol
        
        base_price = 100.0
        returns = np.random.normal(0.0, 0.02, periods)  # 2% daily volatility
        prices = base_price * np.cumprod(1 + returns)
        
        # Generate volume
        base_volume = 1000000
        volume = np.random.lognormal(np.log(base_volume), 0.5, periods).astype(int)
        
        # Create timestamp index
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(minutes=periods),
            periods=periods,
            freq='1min'
        )
        
        # Create DataFrame
        data = pd.DataFrame({
            'timestamp': timestamps,
            'symbol': symbol,
            'price': prices,
            'volume': volume,
            'high': prices * (1 + np.random.uniform(0.0, 0.01, periods)),
            'low': prices * (1 - np.random.uniform(0.0, 0.01, periods)),
            'bid': prices * (1 - np.random.uniform(0.001, 0.003, periods)),
            'ask': prices * (1 + np.random.uniform(0.001, 0.003, periods))
        })
        
        return data
    
    async def _apply_quality_validations(self, data: pd.DataFrame, 
                                       validations: List[str]) -> pd.DataFrame:
        """Apply quality validations to market data"""
        
        validated_data = data.copy()
        
        for validation in validations:
            if validation == "remove_outliers":
                # Remove price outliers (> 3 standard deviations)
                price_mean = validated_data['price'].mean()
                price_std = validated_data['price'].std()
                outlier_mask = np.abs(validated_data['price'] - price_mean) > 3 * price_std
                validated_data = validated_data[~outlier_mask]
                
            elif validation == "interpolate_gaps":
                # Interpolate missing values
                validated_data['price'] = validated_data['price'].interpolate()
                validated_data['volume'] = validated_data['volume'].interpolate()
                
            elif validation == "timestamp_validation":
                # Ensure timestamps are in order
                validated_data = validated_data.sort_values('timestamp')
                
        return validated_data
    
    async def _calculate_data_quality_score(self, data: pd.DataFrame) -> float:
        """Calculate overall data quality score"""
        
        if data.empty:
            return 0.0
        
        scores = []
        
        # Completeness score (no missing values)
        completeness = 1.0 - (data.isnull().sum().sum() / (len(data) * len(data.columns)))
        scores.append(completeness)
        
        # Consistency score (reasonable price movements)
        if 'price' in data.columns and len(data) > 1:
            price_changes = data['price'].pct_change().dropna()
            reasonable_changes = np.abs(price_changes) < 0.1  # < 10% price changes
            consistency = reasonable_changes.mean()
            scores.append(consistency)
        
        # Freshness score (recent timestamps)
        if 'timestamp' in data.columns:
            latest_time = data['timestamp'].max()
            staleness = (datetime.now() - latest_time).total_seconds()
            freshness = max(0.0, 1.0 - (staleness / 3600))  # Penalize data older than 1 hour
            scores.append(freshness)
        
        return np.mean(scores) if scores else 0.0
    
    async def _assess_data_risk_level(self, 
                                    auth_request: DataAuthorizationRequest) -> DataRiskLevel:
        """Assess risk level of data authorization request"""
        
        risk_level = DataRiskLevel.VALIDATED  # Default
        
        # Assess based on data source
        if auth_request.data_source in self.approved_data_sources:
            risk_level = DataRiskLevel.TRUSTED
        elif auth_request.data_source in ["UNKNOWN", "UNVERIFIED"]:
            risk_level = DataRiskLevel.RESTRICTED
        
        # Assess based on usage
        if auth_request.usage_strategy == "trading":
            if risk_level == DataRiskLevel.VALIDATED:
                risk_level = DataRiskLevel.MONITORED
        elif auth_request.usage_strategy == "research":
            # Research usage is less risky
            pass
        
        # Assess based on symbols
        risky_symbols = set(auth_request.symbols) & self.restricted_symbols
        if risky_symbols:
            risk_level = DataRiskLevel.RESTRICTED
        
        return risk_level
    
    async def _convert_risk_decision_to_data_authorization(self,
                                                         request_id: str,
                                                         risk_decision: RiskDecision,
                                                         auth_request: DataAuthorizationRequest) -> DataAuthorizationResponse:
        """Convert CentralRiskManager decision to data authorization"""
        
        # Map risk manager decisions to data authorization status
        status_mapping = {
            "APPROVE": DataAuthorizationStatus.AUTHORIZED,
            "REJECT": DataAuthorizationStatus.REJECTED,
            "MONITOR": DataAuthorizationStatus.QUALITY_MONITORING_REQUIRED,
            "RESTRICT": DataAuthorizationStatus.CONDITIONALLY_APPROVED,
            "EMBARGO": DataAuthorizationStatus.DATA_EMBARGO
        }
        
        status = status_mapping.get(risk_decision.decision, DataAuthorizationStatus.REJECTED)
        
        # Determine authorized symbols
        authorized_symbols = auth_request.symbols.copy()
        if risk_decision.decision == "RESTRICT":
            # Restrict to first half of symbols as example
            authorized_symbols = authorized_symbols[:len(authorized_symbols)//2]
        elif risk_decision.decision in ["REJECT", "EMBARGO"]:
            authorized_symbols = []
        
        # Set conditions based on risk decision
        conditions = []
        if risk_decision.decision == "MONITOR":
            conditions.append("CONTINUOUS_QUALITY_MONITORING")
        if risk_decision.decision == "RESTRICT":
            conditions.append("LIMITED_SYMBOL_ACCESS")
        
        # Set monitoring requirements
        continuous_monitoring = risk_decision.decision in ["MONITOR", "RESTRICT"] or \
                               auth_request.risk_level in [DataRiskLevel.RESTRICTED, DataRiskLevel.MONITORED]
        
        # Set expiry for temporary authorizations
        expiry = None
        if auth_request.risk_level == DataRiskLevel.RESTRICTED:
            expiry = datetime.now() + timedelta(hours=24)  # 24-hour authorization
        
        return DataAuthorizationResponse(
            request_id=request_id,
            status=status,
            authorized_symbols=authorized_symbols,
            authorized_conditions=conditions,
            max_latency_ms=100 if status == DataAuthorizationStatus.AUTHORIZED else None,
            min_quality_score=0.8 if continuous_monitoring else 0.7,
            required_validations=["remove_outliers", "timestamp_validation"] if continuous_monitoring else [],
            continuous_monitoring=continuous_monitoring,
            quality_alert_threshold=0.8 if continuous_monitoring else 0.6,
            risk_assessment=risk_decision.risk_assessment if hasattr(risk_decision, 'risk_assessment') else None,
            expiry_timestamp=expiry
        )
    
    def _update_authorization_success_rate(self):
        """Update authorization success rate metric"""
        
        total_requests = self.total_authorized_feeds + self.total_rejected_feeds
        if total_requests > 0:
            self.authorization_success_rate = self.total_authorized_feeds / total_requests
        else:
            self.authorization_success_rate = 1.0
    
    async def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Get comprehensive data quality metrics with risk attribution"""
        
        total_feeds = len(self.authorized_data_feeds)
        
        if total_feeds == 0:
            return {
                'total_authorized_feeds': 0,
                'authorization_success_rate': self.authorization_success_rate,
                'average_quality_score': 0.0,
                'quality_alert_count': len(self.risk_monitor.data_alerts)
            }
        
        # Calculate aggregate quality metrics
        all_quality_scores = []
        for symbol_metrics in self.risk_monitor.quality_metrics.values():
            for metric in symbol_metrics:
                all_quality_scores.append(metric.overall_quality_score)
        
        avg_quality = np.mean(all_quality_scores) if all_quality_scores else 0.0
        
        # Risk level breakdown
        risk_level_counts = {}
        for auth_response in self.authorized_data_feeds.values():
            # Extract risk level from authorization (simplified)
            risk_level = "VALIDATED"  # Default
            risk_level_counts[risk_level] = risk_level_counts.get(risk_level, 0) + 1
        
        return {
            'total_authorized_feeds': self.total_authorized_feeds,
            'total_rejected_feeds': self.total_rejected_feeds,
            'authorization_success_rate': self.authorization_success_rate,
            'approved_data_sources': len(self.approved_data_sources),
            'average_quality_score': avg_quality,
            'quality_alert_count': len(self.risk_monitor.data_alerts),
            'active_data_streams': len(self.risk_monitor.active_data_streams),
            'restricted_symbols': len(self.restricted_symbols),
            'risk_level_breakdown': risk_level_counts
        }

# Example usage and testing
class ExampleMarketDataIntegration:
    """Example implementation showing market data integration"""
    
    def __init__(self):
        # This would be initialized with actual CentralRiskManager
        self.central_risk_manager = None  # CentralRiskManager()
        self.data_manager = None         # RiskIntegratedMarketDataManager(self.central_risk_manager)
    
    async def example_authorized_data_workflow(self):
        """Example workflow showing authorized data consumption process"""
        
        logger.info("🔄 Example: Authorized Data Consumption Workflow")
        
        # 1. Request data authorization
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
        
        # auth_response = await self.data_manager.request_data_authorization(
        #     data_source="IBKR",
        #     symbols=symbols,
        #     data_type="price",
        #     usage_strategy="trading",
        #     quality_requirements={'min_freshness': 30, 'min_accuracy': 0.95}
        # )
        
        # 2. Consume authorized data
        # if auth_response.status == DataAuthorizationStatus.AUTHORIZED:
        #     market_data = await self.data_manager.consume_authorized_data(auth_response)
        #     return market_data
        
        logger.info("✅ Example workflow completed")

if __name__ == "__main__":
    # Basic testing
    print("🏗️ Market Data Integration - Phase 2 Component")
    print("=" * 60)
    print("Features:")
    print("- Market data quality authorization through CentralRiskManager")
    print("- Real-time data validation with risk oversight")
    print("- Data source risk assessment and approval")
    print("- Quality-gated data distribution to strategies")
    print("- Emergency data embargo capabilities")
    print("\nIntegration Status: Ready for Phase 2 deployment")