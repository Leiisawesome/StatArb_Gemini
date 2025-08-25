#!/usr/bin/env python3
"""
Risk Analyzer - Advanced ML-Powered Risk Assessment
===================================================

Comprehensive risk analysis system with real-time risk modeling, VaR/CVaR calculation,
correlation analysis, stress testing, and portfolio risk assessment.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
import warnings
warnings.filterwarnings('ignore')

# ML and statistical libraries
from sklearn.decomposition import PCA
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from scipy import stats
from scipy.optimize import minimize
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskFactorType(Enum):
    """Risk factor classifications"""
    MARKET = "market"
    SECTOR = "sector"
    STYLE = "style"
    CURRENCY = "currency"
    CREDIT = "credit"
    LIQUIDITY = "liquidity"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"

class RiskLevel(Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class StressScenario(Enum):
    """Stress testing scenarios"""
    MARKET_CRASH = "market_crash"
    VOLATILITY_SPIKE = "volatility_spike"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    INTEREST_RATE_SHOCK = "interest_rate_shock"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    SECTOR_ROTATION = "sector_rotation"
    CURRENCY_CRISIS = "currency_crisis"
    CREDIT_CRISIS = "credit_crisis"

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    timestamp: datetime
    
    # Portfolio level metrics
    portfolio_var_95: float  # 95% Value at Risk
    portfolio_var_99: float  # 99% Value at Risk
    portfolio_cvar_95: float  # 95% Conditional Value at Risk
    portfolio_cvar_99: float  # 99% Conditional Value at Risk
    portfolio_volatility: float
    portfolio_beta: float
    portfolio_tracking_error: float
    
    # Risk decomposition
    systematic_risk: float
    idiosyncratic_risk: float
    factor_exposures: Dict[str, float]
    risk_attribution: Dict[str, float]
    
    # Concentration metrics
    concentration_risk: float
    largest_position_risk: float
    sector_concentration: Dict[str, float]
    
    # Liquidity metrics
    liquidity_risk: float
    time_to_liquidate: float  # Days
    
    # Correlation metrics
    avg_correlation: float
    max_correlation: float
    correlation_stability: float

@dataclass
class RiskFactor:
    """Risk factor definition"""
    factor_id: str
    factor_type: RiskFactorType
    name: str
    description: str
    exposure: float
    volatility: float
    contribution: float  # Contribution to portfolio risk
    significance: float  # Statistical significance

@dataclass
class StressTestResult:
    """Stress test scenario result"""
    scenario: StressScenario
    scenario_name: str
    description: str
    portfolio_pnl: float
    portfolio_return: float
    worst_position_pnl: float
    risk_factors_impact: Dict[str, float]
    probability: float
    confidence: float
    
    # Detailed analysis
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    position_contributions: Dict[str, float] = field(default_factory=dict)
    scenario_probability: float = 0.0

@dataclass
class RiskAlert:
    """Risk alert notification"""
    alert_id: str
    timestamp: datetime
    alert_type: str
    risk_level: RiskLevel
    message: str
    affected_metrics: List[str]
    current_value: float
    threshold_value: float
    recommended_actions: List[str]
    
    # Alert context
    factor_analysis: Dict[str, float] = field(default_factory=dict)
    historical_context: str = ""
    urgency_score: float = 0.0

class RiskAnalyzer:
    """
    Advanced ML-powered risk analysis system
    
    Features:
    - Real-time risk modeling and monitoring
    - ML-based VaR/CVaR calculation
    - Correlation analysis and monitoring
    - Automated stress testing
    - Risk factor decomposition
    - Portfolio risk assessment
    """
    
    def __init__(self,
                 confidence_levels: List[float] = [0.95, 0.99],
                 lookback_window: int = 252,  # Trading days
                 stress_scenarios: int = 1000,
                 rebalance_frequency: int = 5,  # Days
                 correlation_threshold: float = 0.8):
        
        self.confidence_levels = confidence_levels
        self.lookback_window = lookback_window
        self.stress_scenarios = stress_scenarios
        self.rebalance_frequency = rebalance_frequency
        self.correlation_threshold = correlation_threshold
        
        # Risk modeling components
        self.risk_model = None
        self.pca_model = None
        self.scaler = StandardScaler()
        
        # Data storage
        self.returns_history: List[Dict[str, float]] = []
        self.positions_history: List[Dict[str, float]] = []
        self.risk_metrics_history: List[RiskMetrics] = []
        self.stress_test_results: List[StressTestResult] = []
        
        # Risk factors and alerts
        self.risk_factors: Dict[str, RiskFactor] = {}
        self.active_alerts: List[RiskAlert] = []
        
        # Configuration
        self.is_analyzing = False
        self.last_rebalance = None
        self.lock = Lock()
        
        # Risk thresholds
        self.risk_thresholds = {
            'portfolio_var_95': 0.02,  # 2% daily VaR
            'portfolio_var_99': 0.04,  # 4% daily VaR
            'concentration_risk': 0.20,  # 20% max concentration
            'correlation_stability': 0.7,  # Minimum correlation stability
            'liquidity_risk': 0.1  # 10% liquidity risk limit
        }
        
        logger.info("RiskAnalyzer initialized with ML-powered risk modeling")
    
    async def start_analysis(self) -> None:
        """Start risk analysis system"""
        with self.lock:
            if self.is_analyzing:
                logger.warning("Risk analysis already running")
                return
            
            self.is_analyzing = True
            logger.info("Starting ML-powered risk analysis system")
    
    async def stop_analysis(self) -> None:
        """Stop risk analysis system"""
        with self.lock:
            self.is_analyzing = False
            logger.info("Risk analysis system stopped")
    
    def add_returns_data(self, timestamp: datetime, returns: Dict[str, float]) -> None:
        """Add returns data for risk analysis"""
        with self.lock:
            self.returns_history.append({
                'timestamp': timestamp,
                **returns
            })
            
            # Maintain rolling window
            if len(self.returns_history) > self.lookback_window:
                self.returns_history = self.returns_history[-self.lookback_window:]
    
    def add_positions_data(self, timestamp: datetime, positions: Dict[str, float]) -> None:
        """Add positions data for risk analysis"""
        with self.lock:
            self.positions_history.append({
                'timestamp': timestamp,
                **positions
            })
            
            # Maintain rolling window
            if len(self.positions_history) > self.lookback_window:
                self.positions_history = self.positions_history[-self.lookback_window:]
    
    async def calculate_portfolio_risk(self, current_positions: Dict[str, float]) -> RiskMetrics:
        """Calculate comprehensive portfolio risk metrics"""
        if len(self.returns_history) < 30:
            raise ValueError("Insufficient data for risk calculation")
        
        try:
            # Prepare data
            returns_df = pd.DataFrame(self.returns_history)
            returns_df.set_index('timestamp', inplace=True)
            
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(returns_df, current_positions)
            
            # Risk model training if needed
            if self.risk_model is None or self._should_retrain_model():
                await self._train_risk_model(returns_df)
            
            # Calculate VaR and CVaR
            var_metrics = self._calculate_var_cvar(portfolio_returns)
            
            # Factor decomposition
            factor_analysis = await self._analyze_risk_factors(returns_df, current_positions)
            
            # Correlation analysis
            correlation_metrics = self._analyze_correlations(returns_df)
            
            # Concentration analysis
            concentration_metrics = self._analyze_concentration(current_positions)
            
            # Liquidity analysis
            liquidity_metrics = self._analyze_liquidity(current_positions)
            
            # Create comprehensive risk metrics
            risk_metrics = RiskMetrics(
                timestamp=datetime.now(),
                portfolio_var_95=var_metrics['var_95'],
                portfolio_var_99=var_metrics['var_99'],
                portfolio_cvar_95=var_metrics['cvar_95'],
                portfolio_cvar_99=var_metrics['cvar_99'],
                portfolio_volatility=float(np.std(portfolio_returns) * np.sqrt(252)),
                portfolio_beta=factor_analysis.get('market_beta', 1.0),
                portfolio_tracking_error=factor_analysis.get('tracking_error', 0.0),
                systematic_risk=factor_analysis.get('systematic_risk', 0.0),
                idiosyncratic_risk=factor_analysis.get('idiosyncratic_risk', 0.0),
                factor_exposures=factor_analysis.get('factor_exposures', {}),
                risk_attribution=factor_analysis.get('risk_attribution', {}),
                concentration_risk=concentration_metrics['concentration_risk'],
                largest_position_risk=concentration_metrics['largest_position_risk'],
                sector_concentration=concentration_metrics.get('sector_concentration', {}),
                liquidity_risk=liquidity_metrics['liquidity_risk'],
                time_to_liquidate=liquidity_metrics['time_to_liquidate'],
                avg_correlation=correlation_metrics['avg_correlation'],
                max_correlation=correlation_metrics['max_correlation'],
                correlation_stability=correlation_metrics['correlation_stability']
            )
            
            # Store risk metrics
            with self.lock:
                self.risk_metrics_history.append(risk_metrics)
                if len(self.risk_metrics_history) > 100:
                    self.risk_metrics_history = self.risk_metrics_history[-100:]
            
            # Check for risk alerts
            await self._check_risk_alerts(risk_metrics)
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            raise
    
    async def run_stress_tests(self, current_positions: Dict[str, float]) -> List[StressTestResult]:
        """Run comprehensive stress testing scenarios"""
        if len(self.returns_history) < 50:
            raise ValueError("Insufficient data for stress testing")
        
        try:
            stress_results = []
            
            # Prepare returns data
            returns_df = pd.DataFrame(self.returns_history)
            returns_df.set_index('timestamp', inplace=True)
            
            # Define stress scenarios
            scenarios = [
                (StressScenario.MARKET_CRASH, "Market Crash (-20%)", self._scenario_market_crash),
                (StressScenario.VOLATILITY_SPIKE, "Volatility Spike (3x)", self._scenario_volatility_spike),
                (StressScenario.LIQUIDITY_CRISIS, "Liquidity Crisis", self._scenario_liquidity_crisis),
                (StressScenario.INTEREST_RATE_SHOCK, "Interest Rate Shock (+200bp)", self._scenario_interest_rate_shock),
                (StressScenario.CORRELATION_BREAKDOWN, "Correlation Breakdown", self._scenario_correlation_breakdown),
                (StressScenario.SECTOR_ROTATION, "Sector Rotation", self._scenario_sector_rotation),
                (StressScenario.CURRENCY_CRISIS, "Currency Crisis", self._scenario_currency_crisis),
                (StressScenario.CREDIT_CRISIS, "Credit Crisis", self._scenario_credit_crisis)
            ]
            
            # Run scenarios in parallel for efficiency
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                
                for scenario_type, scenario_name, scenario_func in scenarios:
                    future = executor.submit(
                        self._run_stress_scenario,
                        scenario_type,
                        scenario_name,
                        scenario_func,
                        returns_df,
                        current_positions
                    )
                    futures.append(future)
                
                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        stress_results.append(result)
                    except Exception as e:
                        logger.error(f"Stress test scenario failed: {e}")
            
            # Store stress test results
            with self.lock:
                self.stress_test_results.extend(stress_results)
                if len(self.stress_test_results) > 500:
                    self.stress_test_results = self.stress_test_results[-500:]
            
            logger.info(f"Completed {len(stress_results)} stress test scenarios")
            return stress_results
            
        except Exception as e:
            logger.error(f"Error running stress tests: {e}")
            raise
    
    async def analyze_risk_factors(self, current_positions: Dict[str, float]) -> Dict[str, RiskFactor]:
        """Analyze and decompose portfolio risk factors"""
        if len(self.returns_history) < 30:
            raise ValueError("Insufficient data for factor analysis")
        
        try:
            returns_df = pd.DataFrame(self.returns_history)
            returns_df.set_index('timestamp', inplace=True)
            
            # Ensure risk model is trained
            if self.risk_model is None:
                await self._train_risk_model(returns_df)
            
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(returns_df, current_positions)
            
            # Extract risk factors using PCA
            factors = self._extract_risk_factors(returns_df)
            
            # Calculate factor exposures
            exposures = self._calculate_factor_exposures(portfolio_returns, factors)
            
            # Create risk factor objects
            risk_factors = {}
            
            # Market factor
            if 'market_factor' in factors.columns:
                market_exposure = exposures.get('market_factor', 0.0)
                market_vol = float(factors['market_factor'].std() * np.sqrt(252))
                market_contrib = abs(market_exposure) * market_vol
                
                risk_factors['market'] = RiskFactor(
                    factor_id='market',
                    factor_type=RiskFactorType.MARKET,
                    name='Market Factor',
                    description='Broad market exposure risk',
                    exposure=market_exposure,
                    volatility=market_vol,
                    contribution=market_contrib,
                    significance=self._calculate_factor_significance(portfolio_returns, factors['market_factor'])
                )
            
            # Add other significant factors
            for i, col in enumerate(factors.columns):
                if col != 'market_factor' and i < 10:  # Top 10 factors
                    factor_exposure = exposures.get(col, 0.0)
                    factor_vol = float(factors[col].std() * np.sqrt(252))
                    factor_contrib = abs(factor_exposure) * factor_vol
                    
                    # Determine factor type based on properties
                    factor_type = self._classify_factor_type(col, factors[col])
                    
                    risk_factors[f'factor_{i+1}'] = RiskFactor(
                        factor_id=f'factor_{i+1}',
                        factor_type=factor_type,
                        name=f'Factor {i+1}',
                        description=f'Principal component {i+1}',
                        exposure=factor_exposure,
                        volatility=factor_vol,
                        contribution=factor_contrib,
                        significance=self._calculate_factor_significance(portfolio_returns, factors[col])
                    )
            
            # Update stored risk factors
            with self.lock:
                self.risk_factors = risk_factors
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"Error analyzing risk factors: {e}")
            raise
    
    def _calculate_portfolio_returns(self, returns_df: pd.DataFrame, positions: Dict[str, float]) -> np.ndarray:
        """Calculate portfolio returns from positions and asset returns"""
        # Ensure we have overlapping assets
        common_assets = set(positions.keys()) & set(returns_df.columns)
        if not common_assets:
            raise ValueError("No common assets between positions and returns data")
        
        # Calculate weighted returns
        portfolio_returns = []
        for _, row in returns_df.iterrows():
            daily_return = sum(positions.get(asset, 0) * row.get(asset, 0) 
                             for asset in common_assets)
            portfolio_returns.append(daily_return)
        
        return np.array(portfolio_returns)
    
    def _calculate_var_cvar(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate Value at Risk and Conditional Value at Risk"""
        var_95 = float(np.percentile(returns, 5))  # 5th percentile for 95% VaR
        var_99 = float(np.percentile(returns, 1))  # 1st percentile for 99% VaR
        
        # Conditional VaR (Expected Shortfall)
        cvar_95 = float(returns[returns <= var_95].mean())
        cvar_99 = float(returns[returns <= var_99].mean())
        
        return {
            'var_95': abs(var_95),
            'var_99': abs(var_99),
            'cvar_95': abs(cvar_95),
            'cvar_99': abs(cvar_99)
        }
    
    async def _train_risk_model(self, returns_df: pd.DataFrame) -> None:
        """Train ML risk model for factor analysis"""
        try:
            # Prepare features (lagged returns, volatility, etc.)
            features = self._prepare_risk_features(returns_df)
            
            # Principal Component Analysis for factor extraction
            self.pca_model = PCA(n_components=min(10, features.shape[1]))
            factors = self.pca_model.fit_transform(self.scaler.fit_transform(features))
            
            # Train SVR model for risk prediction
            self.risk_model = SVR(kernel='rbf', C=1.0, gamma='scale')
            
            # Use first principal component as target (market factor proxy)
            if factors.shape[1] > 0:
                target = factors[:, 0]
                self.risk_model.fit(features[1:], target[:-1])  # Lagged prediction
            
            self.last_rebalance = datetime.now()
            logger.info("Risk model training completed")
            
        except Exception as e:
            logger.error(f"Error training risk model: {e}")
            raise
    
    def _prepare_risk_features(self, returns_df: pd.DataFrame) -> np.ndarray:
        """Prepare features for risk modeling"""
        features = []
        
        # Rolling statistics
        windows = [5, 10, 20]
        for window in windows:
            # Volatility
            vol = returns_df.rolling(window=window).std().fillna(0)
            features.append(vol.values)
            
            # Momentum
            momentum = returns_df.rolling(window=window).sum().fillna(0)
            features.append(momentum.values)
        
        # Correlation features
        correlation_matrix = returns_df.rolling(window=20).corr()
        avg_corr = correlation_matrix.groupby(level=0).mean().fillna(0)
        features.append(avg_corr.values)
        
        # Combine features
        combined_features = np.column_stack(features)
        return combined_features[~np.isnan(combined_features).any(axis=1)]
    
    def _should_retrain_model(self) -> bool:
        """Check if risk model should be retrained"""
        if self.last_rebalance is None:
            return True
        
        days_since_retrain = (datetime.now() - self.last_rebalance).days
        return days_since_retrain >= self.rebalance_frequency
    
    async def _analyze_risk_factors(self, returns_df: pd.DataFrame, positions: Dict[str, float]) -> Dict[str, Any]:
        """Analyze portfolio risk factor exposures"""
        try:
            # Extract factors using PCA
            factors = self._extract_risk_factors(returns_df)
            
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(returns_df, positions)
            
            # Factor regression
            factor_exposures = {}
            risk_attribution = {}
            
            # Market beta calculation
            if 'market_factor' in factors.columns:
                market_beta, _, r_value, _, _ = stats.linregress(
                    factors['market_factor'].values,
                    portfolio_returns
                )
                factor_exposures['market_beta'] = float(market_beta)
                risk_attribution['market'] = float(abs(market_beta) * factors['market_factor'].std())
            
            # Systematic vs idiosyncratic risk
            systematic_var = sum(risk_attribution.values())**2
            total_var = np.var(portfolio_returns)
            idiosyncratic_var = max(0, total_var - systematic_var)
            
            return {
                'market_beta': factor_exposures.get('market_beta', 1.0),
                'tracking_error': float(np.std(portfolio_returns) * np.sqrt(252)),
                'systematic_risk': float(np.sqrt(systematic_var)),
                'idiosyncratic_risk': float(np.sqrt(idiosyncratic_var)),
                'factor_exposures': factor_exposures,
                'risk_attribution': risk_attribution
            }
            
        except Exception as e:
            logger.error(f"Error in factor analysis: {e}")
            return {}
    
    def _extract_risk_factors(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Extract risk factors using PCA"""
        if self.pca_model is None:
            return pd.DataFrame()
        
        # Prepare features
        features = self._prepare_risk_features(returns_df)
        
        # Transform to factors
        factors = self.pca_model.transform(self.scaler.transform(features))
        
        # Create factor DataFrame
        factor_columns = [f'factor_{i+1}' for i in range(factors.shape[1])]
        factor_columns[0] = 'market_factor'  # First PC as market factor
        
        factor_df = pd.DataFrame(
            factors,
            columns=factor_columns,
            index=returns_df.index[:len(factors)]
        )
        
        return factor_df
    
    def _calculate_factor_exposures(self, portfolio_returns: np.ndarray, factors: pd.DataFrame) -> Dict[str, float]:
        """Calculate portfolio exposures to risk factors"""
        exposures = {}
        
        for factor_name in factors.columns:
            if len(factors[factor_name]) == len(portfolio_returns):
                beta, _, _, _, _ = stats.linregress(
                    factors[factor_name].values,
                    portfolio_returns
                )
                exposures[factor_name] = float(beta)
        
        return exposures
    
    def _calculate_factor_significance(self, portfolio_returns: np.ndarray, factor_returns: pd.Series) -> float:
        """Calculate statistical significance of factor"""
        if len(factor_returns) != len(portfolio_returns):
            return 0.0
        
        _, _, r_value, p_value, _ = stats.linregress(
            factor_returns.values,
            portfolio_returns
        )
        
        # Return R-squared adjusted for p-value
        significance = r_value**2 * (1 - p_value) if p_value < 0.05 else 0.0
        return float(significance)
    
    def _classify_factor_type(self, factor_name: str, factor_data: pd.Series) -> RiskFactorType:
        """Classify factor type based on properties"""
        # Simple heuristic classification
        volatility = factor_data.std()
        autocorr = factor_data.autocorr()
        
        if volatility > factor_data.mean() + 2 * factor_data.std():
            return RiskFactorType.VOLATILITY
        elif abs(autocorr) > 0.3:
            return RiskFactorType.MOMENTUM
        elif 'market' in factor_name.lower():
            return RiskFactorType.MARKET
        else:
            return RiskFactorType.STYLE
    
    def _analyze_correlations(self, returns_df: pd.DataFrame) -> Dict[str, float]:
        """Analyze correlation structure"""
        corr_matrix = returns_df.corr()
        
        # Remove diagonal (perfect correlation with self)
        corr_values = corr_matrix.values
        np.fill_diagonal(corr_values, np.nan)
        
        avg_correlation = float(np.nanmean(corr_values))
        max_correlation = float(np.nanmax(corr_values))
        
        # Correlation stability (consistency over time)
        rolling_corr = returns_df.rolling(window=20).corr()
        corr_stability = 1.0 - float(rolling_corr.groupby(level=0).std().mean().mean())
        
        return {
            'avg_correlation': avg_correlation,
            'max_correlation': max_correlation,
            'correlation_stability': max(0.0, corr_stability)
        }
    
    def _analyze_concentration(self, positions: Dict[str, float]) -> Dict[str, Any]:
        """Analyze portfolio concentration risk"""
        position_values = np.array(list(positions.values()))
        total_exposure = np.sum(np.abs(position_values))
        
        if total_exposure == 0:
            return {
                'concentration_risk': 0.0,
                'largest_position_risk': 0.0,
                'sector_concentration': {}
            }
        
        # Normalized positions
        normalized_positions = np.abs(position_values) / total_exposure
        
        # Concentration metrics
        concentration_risk = float(np.sum(normalized_positions**2))  # Herfindahl index
        largest_position_risk = float(np.max(normalized_positions))
        
        # Sector concentration (simplified - would need sector mapping in practice)
        sector_concentration = {'equity': 0.8, 'fixed_income': 0.2}  # Placeholder
        
        return {
            'concentration_risk': concentration_risk,
            'largest_position_risk': largest_position_risk,
            'sector_concentration': sector_concentration
        }
    
    def _analyze_liquidity(self, positions: Dict[str, float]) -> Dict[str, float]:
        """Analyze portfolio liquidity risk"""
        # Simplified liquidity analysis (would need market data in practice)
        total_exposure = sum(abs(pos) for pos in positions.values())
        
        # Estimate based on position sizes (larger positions = less liquid)
        liquidity_scores = []
        for pos in positions.values():
            pos_weight = abs(pos) / total_exposure if total_exposure > 0 else 0
            # Assume larger positions are harder to liquidate
            liquidity_score = 1.0 - min(pos_weight * 5, 0.9)  # Max 90% illiquidity
            liquidity_scores.append(liquidity_score)
        
        avg_liquidity = np.mean(liquidity_scores) if liquidity_scores else 1.0
        liquidity_risk = 1.0 - avg_liquidity
        
        # Time to liquidate (days) - simplified estimate
        time_to_liquidate = liquidity_risk * 10  # Max 10 days
        
        return {
            'liquidity_risk': float(liquidity_risk),
            'time_to_liquidate': float(time_to_liquidate)
        }
    
    async def _check_risk_alerts(self, risk_metrics: RiskMetrics) -> None:
        """Check for risk threshold breaches and generate alerts"""
        new_alerts = []
        
        # Check VaR thresholds
        if risk_metrics.portfolio_var_95 > self.risk_thresholds['portfolio_var_95']:
            alert = RiskAlert(
                alert_id=f"var_95_{datetime.now().timestamp()}",
                timestamp=datetime.now(),
                alert_type="VaR Threshold Breach",
                risk_level=RiskLevel.HIGH,
                message=f"95% VaR ({risk_metrics.portfolio_var_95:.3f}) exceeds threshold ({self.risk_thresholds['portfolio_var_95']:.3f})",
                affected_metrics=['portfolio_var_95'],
                current_value=risk_metrics.portfolio_var_95,
                threshold_value=self.risk_thresholds['portfolio_var_95'],
                recommended_actions=[
                    "Reduce position sizes",
                    "Increase diversification",
                    "Consider hedging strategies"
                ]
            )
            new_alerts.append(alert)
        
        # Check concentration risk
        if risk_metrics.concentration_risk > self.risk_thresholds['concentration_risk']:
            alert = RiskAlert(
                alert_id=f"concentration_{datetime.now().timestamp()}",
                timestamp=datetime.now(),
                alert_type="Concentration Risk",
                risk_level=RiskLevel.MEDIUM,
                message=f"Portfolio concentration ({risk_metrics.concentration_risk:.3f}) exceeds threshold",
                affected_metrics=['concentration_risk'],
                current_value=risk_metrics.concentration_risk,
                threshold_value=self.risk_thresholds['concentration_risk'],
                recommended_actions=[
                    "Diversify holdings",
                    "Reduce largest positions",
                    "Add uncorrelated assets"
                ]
            )
            new_alerts.append(alert)
        
        # Add new alerts
        if new_alerts:
            with self.lock:
                self.active_alerts.extend(new_alerts)
                # Keep only recent alerts
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.active_alerts = [
                    alert for alert in self.active_alerts 
                    if alert.timestamp > cutoff_time
                ]
        
        if new_alerts:
            logger.warning(f"Generated {len(new_alerts)} new risk alerts")
    
    # Stress test scenario implementations
    def _run_stress_scenario(self, scenario_type: StressScenario, scenario_name: str,
                           scenario_func, returns_df: pd.DataFrame, 
                           positions: Dict[str, float]) -> StressTestResult:
        """Run a specific stress test scenario"""
        try:
            # Apply stress scenario
            stressed_returns = scenario_func(returns_df)
            
            # Calculate portfolio impact
            portfolio_pnl = self._calculate_portfolio_returns(stressed_returns, positions)
            portfolio_return = float(np.sum(portfolio_pnl))
            
            # Find worst position
            position_pnls = {}
            for asset, weight in positions.items():
                if asset in stressed_returns.columns:
                    asset_return = float(stressed_returns[asset].sum())
                    position_pnls[asset] = weight * asset_return
            
            worst_position_pnl = min(position_pnls.values()) if position_pnls else 0.0
            
            # Risk factor impact analysis
            risk_factors_impact = self._analyze_scenario_factors(stressed_returns)
            
            return StressTestResult(
                scenario=scenario_type,
                scenario_name=scenario_name,
                description=f"Stress test: {scenario_name}",
                portfolio_pnl=float(np.sum(portfolio_pnl)),
                portfolio_return=portfolio_return,
                worst_position_pnl=worst_position_pnl,
                risk_factors_impact=risk_factors_impact,
                probability=self._estimate_scenario_probability(scenario_type),
                confidence=0.8,
                position_contributions=position_pnls
            )
            
        except Exception as e:
            logger.error(f"Error running stress scenario {scenario_name}: {e}")
            raise
    
    def _scenario_market_crash(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Market crash scenario: -20% across all assets"""
        stressed = returns_df.copy()
        stressed.iloc[-1] = -0.20  # 20% drop on last day
        return stressed
    
    def _scenario_volatility_spike(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Volatility spike scenario: 3x normal volatility"""
        stressed = returns_df.copy()
        vol_multiplier = 3.0
        stressed.iloc[-5:] = stressed.iloc[-5:] * vol_multiplier
        return stressed
    
    def _scenario_liquidity_crisis(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Liquidity crisis: Increased correlation + volatility"""
        stressed = returns_df.copy()
        # Increase correlations and volatility
        mean_return = stressed.mean()
        stressed.iloc[-3:] = mean_return.values + np.random.normal(0, 0.05, stressed.iloc[-3:].shape)
        return stressed
    
    def _scenario_interest_rate_shock(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Interest rate shock: +200bp impact"""
        stressed = returns_df.copy()
        # Apply duration-based impact (simplified)
        rate_impact = -0.05  # Assume 5% impact for 200bp shock
        stressed.iloc[-1] = rate_impact
        return stressed
    
    def _scenario_correlation_breakdown(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Correlation breakdown: Assets move independently"""
        stressed = returns_df.copy()
        # Add uncorrelated noise
        noise = np.random.normal(0, 0.02, stressed.iloc[-5:].shape)
        stressed.iloc[-5:] = stressed.iloc[-5:] + noise
        return stressed
    
    def _scenario_sector_rotation(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Sector rotation scenario"""
        stressed = returns_df.copy()
        # Simulate sector rotation (some up, some down)
        n_assets = len(stressed.columns)
        rotation_impact = np.random.choice([-0.1, 0.1], size=n_assets)
        stressed.iloc[-1] = rotation_impact
        return stressed
    
    def _scenario_currency_crisis(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Currency crisis scenario"""
        stressed = returns_df.copy()
        # Apply currency impact
        currency_impact = -0.15
        stressed.iloc[-2:] = stressed.iloc[-2:] + currency_impact
        return stressed
    
    def _scenario_credit_crisis(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Credit crisis scenario"""
        stressed = returns_df.copy()
        # Credit spread widening impact
        credit_impact = -0.08
        stressed.iloc[-3:] = stressed.iloc[-3:] + credit_impact
        return stressed
    
    def _analyze_scenario_factors(self, stressed_returns: pd.DataFrame) -> Dict[str, float]:
        """Analyze which risk factors are most impacted in scenario"""
        if self.pca_model is None:
            return {}
        
        try:
            # Extract factors from stressed returns
            features = self._prepare_risk_features(stressed_returns)
            if len(features) == 0:
                return {}
            
            factors = self.pca_model.transform(self.scaler.transform(features))
            
            # Calculate factor impacts
            factor_impacts = {}
            for i in range(min(5, factors.shape[1])):
                impact = float(np.mean(factors[:, i]))
                factor_impacts[f'factor_{i+1}'] = impact
            
            return factor_impacts
            
        except Exception as e:
            logger.error(f"Error analyzing scenario factors: {e}")
            return {}
    
    def _estimate_scenario_probability(self, scenario: StressScenario) -> float:
        """Estimate probability of stress scenario"""
        # Simplified probability estimates
        probabilities = {
            StressScenario.MARKET_CRASH: 0.02,       # 2% annual
            StressScenario.VOLATILITY_SPIKE: 0.10,   # 10% annual
            StressScenario.LIQUIDITY_CRISIS: 0.05,   # 5% annual
            StressScenario.INTEREST_RATE_SHOCK: 0.15, # 15% annual
            StressScenario.CORRELATION_BREAKDOWN: 0.08, # 8% annual
            StressScenario.SECTOR_ROTATION: 0.25,    # 25% annual
            StressScenario.CURRENCY_CRISIS: 0.03,    # 3% annual
            StressScenario.CREDIT_CRISIS: 0.04       # 4% annual
        }
        return probabilities.get(scenario, 0.05)
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk analysis summary"""
        with self.lock:
            latest_metrics = self.risk_metrics_history[-1] if self.risk_metrics_history else None
            
            return {
                'is_analyzing': self.is_analyzing,
                'data_points': len(self.returns_history),
                'latest_metrics': latest_metrics,
                'active_alerts_count': len(self.active_alerts),
                'stress_tests_run': len(self.stress_test_results),
                'risk_factors_identified': len(self.risk_factors),
                'model_last_trained': self.last_rebalance,
                'risk_thresholds': self.risk_thresholds
            }

# Global risk analyzer instance
risk_analyzer = RiskAnalyzer()

# Export main components
__all__ = [
    'RiskAnalyzer',
    'RiskMetrics', 
    'RiskFactor',
    'StressTestResult',
    'RiskAlert',
    'RiskFactorType',
    'RiskLevel',
    'StressScenario',
    'risk_analyzer'
]
