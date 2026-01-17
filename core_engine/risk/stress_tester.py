"""
Risk Management - Stress Tester
Advanced stress testing framework with scenario analysis and portfolio impact assessment
"""

import logging
import threading
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque

from core_engine.exceptions import ConfigurationRequiredError

logger = logging.getLogger(__name__)

class StressTestType(Enum):
    """Types of stress tests"""
    HISTORICAL = "historical"
    HYPOTHETICAL = "hypothetical"
    MONTE_CARLO = "monte_carlo"
    SENSITIVITY = "sensitivity"
    REVERSE = "reverse"
    CORRELATION_BREAKDOWN = "correlation_breakdown"

class ShockType(Enum):
    """Types of market shocks"""
    ABSOLUTE = "absolute"  # Absolute change
    RELATIVE = "relative"  # Percentage change
    VOLATILITY = "volatility"  # Volatility multiplier
    CORRELATION = "correlation"  # Correlation change

@dataclass
class MarketShock:
    """Market shock definition"""
    factor: str
    shock_type: ShockType
    magnitude: float
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StressScenario:
    """Comprehensive stress test scenario"""
    name: str
    description: str
    test_type: StressTestType
    shocks: List[MarketShock]
    probability: Optional[float] = None
    time_horizon_days: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StressTestResult:
    """Stress test result for individual position or portfolio"""
    scenario_name: str
    position_id: str
    original_value: float
    stressed_value: float
    pnl: float
    pnl_percentage: float
    contribution_to_portfolio: float
    risk_attribution: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PortfolioStressResult:
    """Portfolio-level stress test result"""
    scenario_name: str
    total_pnl: float
    total_pnl_percentage: float
    worst_case_var: float
    position_results: List[StressTestResult]
    risk_breakdown: Dict[str, float] = field(default_factory=dict)
    scenario_probability: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

class StressTester:
    """
    Advanced stress testing framework

    Provides comprehensive stress testing capabilities including historical scenarios,
    hypothetical shocks, Monte Carlo simulations, and reverse stress testing.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize stress tester"""
        self.config = config or {}
        self._lock = threading.Lock()
        self._scenarios = {}
        self._historical_scenarios = {}
        self._test_results = deque(maxlen=1000)

        # Configuration
        self.monte_carlo_runs = self.config.get('monte_carlo_runs', 10000)
        self.confidence_levels = self.config.get('confidence_levels', [0.95, 0.99, 0.999])
        self.correlation_decay = self.config.get('correlation_decay', 0.94)

        # Market factor mappings
        self._factor_mappings = {}
        self._correlation_matrix = {}
        self._volatility_estimates = {}

        # Load predefined scenarios
        self._load_historical_scenarios()
        self._load_hypothetical_scenarios()

        logger.info("StressTester initialized")

    def _load_historical_scenarios(self) -> None:
        """Load historical stress scenarios"""

        # Black Monday 1987
        black_monday = StressScenario(
            name="Black_Monday_1987",
            description="Black Monday stock market crash of October 19, 1987",
            test_type=StressTestType.HISTORICAL,
            shocks=[
                MarketShock("EQUITY_US", ShockType.RELATIVE, -0.22, "S&P 500 -22%"),
                MarketShock("EQUITY_GLOBAL", ShockType.RELATIVE, -0.20, "Global equities -20%"),
                MarketShock("VOLATILITY", ShockType.VOLATILITY, 3.0, "VIX spike"),
                MarketShock("RATES_10Y", ShockType.ABSOLUTE, 0.005, "Flight to quality")
            ],
            probability=0.001,  # Once in 1000 days
            time_horizon_days=1
        )

        # LTCM Crisis 1998
        ltcm_crisis = StressScenario(
            name="LTCM_Crisis_1998",
            description="Long-Term Capital Management crisis",
            test_type=StressTestType.HISTORICAL,
            shocks=[
                MarketShock("EQUITY_US", ShockType.RELATIVE, -0.15, "Equity decline"),
                MarketShock("CREDIT_SPREAD", ShockType.ABSOLUTE, 0.02, "Credit spread widening"),
                MarketShock("LIQUIDITY", ShockType.RELATIVE, -0.50, "Liquidity crisis"),
                MarketShock("CORRELATION", ShockType.CORRELATION, 0.8, "Correlation increase")
            ],
            probability=0.001
        )

        # Dot-com Crash 2000-2002
        dotcom_crash = StressScenario(
            name="Dotcom_Crash_2000",
            description="Technology bubble burst",
            test_type=StressTestType.HISTORICAL,
            shocks=[
                MarketShock("EQUITY_TECH", ShockType.RELATIVE, -0.70, "Tech stocks -70%"),
                MarketShock("EQUITY_US", ShockType.RELATIVE, -0.45, "S&P 500 decline"),
                MarketShock("VOLATILITY", ShockType.VOLATILITY, 2.0, "Volatility increase")
            ],
            probability=0.0004,  # Once in 2500 days
            time_horizon_days=756  # 3 years
        )

        # 2008 Financial Crisis
        financial_crisis_2008 = StressScenario(
            name="Financial_Crisis_2008",
            description="Global financial crisis",
            test_type=StressTestType.HISTORICAL,
            shocks=[
                MarketShock("EQUITY_US", ShockType.RELATIVE, -0.55, "S&P 500 decline"),
                MarketShock("EQUITY_GLOBAL", ShockType.RELATIVE, -0.50, "Global equity decline"),
                MarketShock("CREDIT_SPREAD", ShockType.ABSOLUTE, 0.06, "Credit spread explosion"),
                MarketShock("REAL_ESTATE", ShockType.RELATIVE, -0.30, "Housing market crash"),
                MarketShock("VOLATILITY", ShockType.VOLATILITY, 4.0, "VIX spike to 80+"),
                MarketShock("LIQUIDITY", ShockType.RELATIVE, -0.70, "Liquidity evaporation")
            ],
            probability=0.0003,  # Once in 3333 days (13 years)
            time_horizon_days=517  # Peak to trough
        )

        # European Sovereign Debt Crisis 2010-2012
        euro_crisis = StressScenario(
            name="Euro_Crisis_2010",
            description="European sovereign debt crisis",
            test_type=StressTestType.HISTORICAL,
            shocks=[
                MarketShock("EQUITY_EU", ShockType.RELATIVE, -0.35, "European equities"),
                MarketShock("EUR_USD", ShockType.RELATIVE, -0.15, "Euro depreciation"),
                MarketShock("SOVEREIGN_SPREAD", ShockType.ABSOLUTE, 0.05, "Peripheral spreads"),
                MarketShock("CORRELATION", ShockType.CORRELATION, 0.9, "Correlation spike")
            ],
            probability=0.0005
        )

        # COVID-19 Pandemic 2020
        covid_pandemic = StressScenario(
            name="COVID_Pandemic_2020",
            description="COVID-19 pandemic market shock",
            test_type=StressTestType.HISTORICAL,
            shocks=[
                MarketShock("EQUITY_US", ShockType.RELATIVE, -0.34, "S&P 500 decline"),
                MarketShock("EQUITY_GLOBAL", ShockType.RELATIVE, -0.30, "Global equity decline"),
                MarketShock("OIL", ShockType.RELATIVE, -0.60, "Oil price collapse"),
                MarketShock("VOLATILITY", ShockType.VOLATILITY, 5.0, "VIX spike to 82"),
                MarketShock("CREDIT_SPREAD", ShockType.ABSOLUTE, 0.04, "Credit spread widening"),
                MarketShock("RATES_10Y", ShockType.ABSOLUTE, -0.01, "Flight to quality")
            ],
            probability=0.0003,
            time_horizon_days=33  # Peak decline period
        )

        self._historical_scenarios = {
            'black_monday_1987': black_monday,
            'ltcm_crisis_1998': ltcm_crisis,
            'dotcom_crash_2000': dotcom_crash,
            'financial_crisis_2008': financial_crisis_2008,
            'euro_crisis_2010': euro_crisis,
            'covid_pandemic_2020': covid_pandemic
        }

    def _load_hypothetical_scenarios(self) -> None:
        """Load hypothetical stress scenarios"""

        # Interest rate shock
        rate_shock = StressScenario(
            name="Interest_Rate_Shock",
            description="Parallel shift in yield curve",
            test_type=StressTestType.HYPOTHETICAL,
            shocks=[
                MarketShock("RATES_1Y", ShockType.ABSOLUTE, 0.02, "1Y rate +200bp"),
                MarketShock("RATES_5Y", ShockType.ABSOLUTE, 0.02, "5Y rate +200bp"),
                MarketShock("RATES_10Y", ShockType.ABSOLUTE, 0.02, "10Y rate +200bp"),
                MarketShock("RATES_30Y", ShockType.ABSOLUTE, 0.02, "30Y rate +200bp")
            ]
        )

        # Currency crisis
        currency_crisis = StressScenario(
            name="Currency_Crisis",
            description="Major currency devaluation",
            test_type=StressTestType.HYPOTHETICAL,
            shocks=[
                MarketShock("USD_BASKET", ShockType.RELATIVE, 0.20, "USD strength"),
                MarketShock("EM_FX", ShockType.RELATIVE, -0.30, "EM currency weakness"),
                MarketShock("VOLATILITY_FX", ShockType.VOLATILITY, 2.5, "FX volatility spike")
            ]
        )

        # Commodity shock
        commodity_shock = StressScenario(
            name="Commodity_Shock",
            description="Major commodity price disruption",
            test_type=StressTestType.HYPOTHETICAL,
            shocks=[
                MarketShock("OIL", ShockType.RELATIVE, 0.50, "Oil price spike"),
                MarketShock("GOLD", ShockType.RELATIVE, 0.25, "Gold rally"),
                MarketShock("AGRICULTURE", ShockType.RELATIVE, 0.30, "Food price inflation"),
                MarketShock("INDUSTRIAL_METALS", ShockType.RELATIVE, -0.20, "Industrial metal decline")
            ]
        )

        # Geopolitical crisis
        geopolitical_crisis = StressScenario(
            name="Geopolitical_Crisis",
            description="Major geopolitical event",
            test_type=StressTestType.HYPOTHETICAL,
            shocks=[
                MarketShock("EQUITY_GLOBAL", ShockType.RELATIVE, -0.25, "Risk-off sentiment"),
                MarketShock("OIL", ShockType.RELATIVE, 0.40, "Supply disruption"),
                MarketShock("RATES_10Y", ShockType.ABSOLUTE, -0.01, "Flight to quality"),
                MarketShock("VOLATILITY", ShockType.VOLATILITY, 3.0, "Uncertainty spike"),
                MarketShock("GOLD", ShockType.RELATIVE, 0.15, "Safe haven demand")
            ]
        )

        # Technology disruption
        tech_disruption = StressScenario(
            name="Technology_Disruption",
            description="Major technology sector disruption",
            test_type=StressTestType.HYPOTHETICAL,
            shocks=[
                MarketShock("EQUITY_TECH", ShockType.RELATIVE, -0.40, "Tech sector decline"),
                MarketShock("EQUITY_US", ShockType.RELATIVE, -0.15, "Broader market impact"),
                MarketShock("GROWTH_PREMIUM", ShockType.RELATIVE, -0.50, "Growth factor decline")
            ]
        )

        self._scenarios.update({
            'rate_shock': rate_shock,
            'currency_crisis': currency_crisis,
            'commodity_shock': commodity_shock,
            'geopolitical_crisis': geopolitical_crisis,
            'tech_disruption': tech_disruption
        })

    async def run_stress_test(
        self,
        scenario_name: str,
        positions: Dict[str, Any],
        portfolio_value: float,
        factor_loadings: Optional[Dict[str, Dict[str, float]]] = None
    ) -> PortfolioStressResult:
        """
        Run stress test on portfolio using specified scenario

        Args:
            scenario_name: Name of stress scenario
            positions: Portfolio positions
            portfolio_value: Total portfolio value
            factor_loadings: Optional factor loadings for positions

        Returns:
            Portfolio stress test results
        """
        start_time = time.time()

        try:
            # Defensive type conversion for portfolio_value
            portfolio_value = float(portfolio_value) if portfolio_value is not None else 0.0

            # Get scenario
            scenario = self._get_scenario(scenario_name)
            if not scenario:
                raise ValueError(f"Unknown scenario: {scenario_name}")

            # Calculate position-level impacts
            position_results = []
            total_pnl = 0.0

            for position_id, position in positions.items():
                result = await self._calculate_position_stress(
                    position_id, position, scenario, factor_loadings
                )
                position_results.append(result)
                total_pnl += result.pnl

            # Calculate portfolio-level metrics
            total_pnl_percentage = (total_pnl / portfolio_value * 100) if portfolio_value > 0 else 0

            # Calculate worst-case VaR equivalent
            worst_case_var = abs(total_pnl) if total_pnl < 0 else 0

            # Risk breakdown by factor
            risk_breakdown = self._calculate_risk_breakdown(position_results, scenario)

            portfolio_result = PortfolioStressResult(
                scenario_name=scenario_name,
                total_pnl=total_pnl,
                total_pnl_percentage=total_pnl_percentage,
                worst_case_var=worst_case_var,
                position_results=position_results,
                risk_breakdown=risk_breakdown,
                scenario_probability=scenario.probability
            )

            # Store result
            self._test_results.append({
                'timestamp': datetime.now(),
                'scenario': scenario_name,
                'portfolio_value': portfolio_value,
                'total_pnl': total_pnl,
                'calculation_time': time.time() - start_time
            })

            logger.info(f"Stress test '{scenario_name}' completed: PnL = {total_pnl:.2f} ({total_pnl_percentage:.2f}%)")

            return portfolio_result

        except Exception as e:
            logger.error(f"Error running stress test: {e}")
            raise

    async def _calculate_position_stress(
        self,
        position_id: str,
        position: Dict[str, Any],
        scenario: StressScenario,
        factor_loadings: Optional[Dict[str, Dict[str, float]]] = None
    ) -> StressTestResult:
        """Calculate stress test impact for individual position"""

        original_value = position.get('market_value', 0)

        # Get position characteristics
        position.get('asset_type', 'EQUITY')
        position.get('sector', '')
        position.get('region', '')
        position.get('currency', 'USD')

        # Calculate aggregate shock for this position
        total_shock = 0.0
        risk_attribution = {}

        for shock in scenario.shocks:
            shock_impact = self._calculate_shock_impact(
                shock, position, factor_loadings.get(position_id, {}) if factor_loadings else {}
            )
            total_shock += shock_impact
            risk_attribution[shock.factor] = shock_impact * original_value

        # Apply shock to position value
        stressed_value = original_value * (1 + total_shock)
        pnl = stressed_value - original_value
        pnl_percentage = (pnl / original_value * 100) if original_value != 0 else 0

        return StressTestResult(
            scenario_name=scenario.name,
            position_id=position_id,
            original_value=original_value,
            stressed_value=stressed_value,
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            contribution_to_portfolio=pnl,
            risk_attribution=risk_attribution
        )

    def _calculate_shock_impact(
        self,
        shock: MarketShock,
        position: Dict[str, Any],
        factor_loadings: Dict[str, float]
    ) -> float:
        """Calculate impact of individual shock on position"""

        # Get position sensitivity to this factor
        sensitivity = self._get_position_sensitivity(shock.factor, position, factor_loadings)

        if sensitivity == 0:
            return 0.0

        # Apply shock based on type
        if shock.shock_type == ShockType.RELATIVE:
            return sensitivity * shock.magnitude
        elif shock.shock_type == ShockType.ABSOLUTE:
            # For absolute shocks, need to convert to relative impact
            # This is simplified - in practice would depend on position duration/sensitivity
            return sensitivity * shock.magnitude * 10  # Rough conversion factor
        elif shock.shock_type == ShockType.VOLATILITY:
            # Volatility shocks affect option positions more
            if position.get('asset_type') in ['OPTION', 'WARRANT']:
                return sensitivity * (shock.magnitude - 1) * 0.5  # Vega impact
            else:
                return 0.0
        elif shock.shock_type == ShockType.CORRELATION:
            # Correlation shocks affect correlation-dependent strategies
            return sensitivity * shock.magnitude * 0.1  # Simplified correlation impact

        return 0.0

    def _get_position_sensitivity(
        self,
        factor: str,
        position: Dict[str, Any],
        factor_loadings: Dict[str, float]
    ) -> float:
        """Get position sensitivity to market factor"""

        # Check explicit factor loadings first
        if factor in factor_loadings:
            return factor_loadings[factor]

        # Map position characteristics to factors
        asset_type = position.get('asset_type', 'EQUITY')
        sector = position.get('sector', '').upper()
        region = position.get('region', '').upper()

        # Equity factors
        if factor.startswith('EQUITY'):
            if asset_type in ['EQUITY', 'STOCK']:
                if 'US' in factor and 'US' in region:
                    return 1.0
                elif 'GLOBAL' in factor:
                    return 0.8
                elif 'EU' in factor and 'EUROPE' in region:
                    return 1.0
                elif 'TECH' in factor and 'TECHNOLOGY' in sector:
                    return 1.2
                else:
                    return 0.5
            return 0.0

        # Interest rate factors
        elif factor.startswith('RATES'):
            if asset_type in ['BOND', 'FIXED_INCOME']:
                duration = position.get('duration', 5.0)
                return duration * 0.01  # Duration times 1bp sensitivity
            elif asset_type in ['EQUITY', 'STOCK']:
                return -0.1  # Negative sensitivity for equities
            return 0.0

        # Credit factors
        elif factor.startswith('CREDIT'):
            if asset_type in ['BOND', 'FIXED_INCOME', 'CORPORATE_BOND']:
                return position.get('credit_spread_sensitivity', 1.0)
            elif asset_type in ['EQUITY', 'STOCK'] and 'FINANCIAL' in sector:
                return 0.3  # Bank stocks sensitive to credit
            return 0.0

        # Currency factors
        elif factor.endswith('_USD') or factor.startswith('USD'):
            position_currency = position.get('currency', 'USD')
            if position_currency != 'USD':
                return 1.0
            return 0.0

        # Commodity factors
        elif factor in ['OIL', 'GOLD', 'AGRICULTURE', 'INDUSTRIAL_METALS']:
            if asset_type == 'COMMODITY':
                commodity_type = position.get('commodity_type', '').upper()
                if factor in commodity_type:
                    return 1.0
                else:
                    return 0.2
            elif 'ENERGY' in sector and factor == 'OIL':
                return 0.6
            elif 'MATERIALS' in sector and factor == 'INDUSTRIAL_METALS':
                return 0.4
            return 0.0

        # Volatility factors
        elif factor == 'VOLATILITY':
            if asset_type in ['OPTION', 'WARRANT']:
                return position.get('vega', 1.0)
            else:
                return 0.1  # Small volatility sensitivity for most assets

        # No default - raise exception for unknown asset types
        raise ConfigurationRequiredError(f"Unknown asset type for volatility sensitivity: {asset_type}")

    def _calculate_risk_breakdown(
        self,
        position_results: List[StressTestResult],
        scenario: StressScenario
    ) -> Dict[str, float]:
        """Calculate risk breakdown by factor"""

        risk_breakdown = defaultdict(float)

        for result in position_results:
            for factor, attribution in result.risk_attribution.items():
                risk_breakdown[factor] += attribution

        return dict(risk_breakdown)

    async def run_monte_carlo_stress_test(
        self,
        positions: Dict[str, Any],
        portfolio_value: float,
        num_simulations: Optional[int] = None,
        factor_loadings: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Dict[str, Any]:
        """Run Monte Carlo stress test"""

        if num_simulations is None:
            num_simulations = self.monte_carlo_runs

        start_time = time.time()

        try:
            # Generate random scenarios
            scenarios = self._generate_monte_carlo_scenarios(num_simulations)

            # Run stress tests for all scenarios
            results = []
            for i, scenario_shocks in enumerate(scenarios):
                # Create temporary scenario
                temp_scenario = StressScenario(
                    name=f"MC_Simulation_{i}",
                    description="Monte Carlo simulation",
                    test_type=StressTestType.MONTE_CARLO,
                    shocks=scenario_shocks
                )

                # Calculate portfolio impact
                total_pnl = 0.0
                for position_id, position in positions.items():
                    result = await self._calculate_position_stress(
                        position_id, position, temp_scenario, factor_loadings
                    )
                    total_pnl += result.pnl

                results.append(total_pnl)

            # Calculate statistics
            results_array = np.array(results)

            mc_results = {
                'mean_pnl': float(np.mean(results_array)),
                'std_pnl': float(np.std(results_array)),
                'min_pnl': float(np.min(results_array)),
                'max_pnl': float(np.max(results_array)),
                'var_95': float(np.percentile(results_array, 5)),
                'var_99': float(np.percentile(results_array, 1)),
                'var_999': float(np.percentile(results_array, 0.1)),
                'scenarios_run': num_simulations,
                'calculation_time': time.time() - start_time
            }

            logger.info(f"Monte Carlo stress test completed: {num_simulations} simulations in {time.time() - start_time:.2f}s")

            return mc_results

        except Exception as e:
            logger.error(f"Error running Monte Carlo stress test: {e}")
            raise

    def _generate_monte_carlo_scenarios(self, num_simulations: int) -> List[List[MarketShock]]:
        """Generate random scenarios for Monte Carlo simulation"""

        # Define key risk factors and their distributions
        risk_factors = {
            'EQUITY_US': {'mean': 0, 'std': 0.15, 'distribution': 'normal'},
            'EQUITY_GLOBAL': {'mean': 0, 'std': 0.12, 'distribution': 'normal'},
            'RATES_10Y': {'mean': 0, 'std': 0.008, 'distribution': 'normal'},
            'CREDIT_SPREAD': {'mean': 0, 'std': 0.002, 'distribution': 'normal'},
            'USD_BASKET': {'mean': 0, 'std': 0.08, 'distribution': 'normal'},
            'OIL': {'mean': 0, 'std': 0.25, 'distribution': 'normal'},
            'VOLATILITY': {'mean': 1, 'std': 0.5, 'distribution': 'lognormal'}
        }

        scenarios = []
        np.random.seed(42)  # For reproducibility

        for _ in range(num_simulations):
            scenario_shocks = []

            for factor, params in risk_factors.items():
                if params['distribution'] == 'normal':
                    shock_value = np.random.normal(params['mean'], params['std'])
                    shock_type = ShockType.RELATIVE
                elif params['distribution'] == 'lognormal':
                    shock_value = np.random.lognormal(np.log(params['mean']), params['std'])
                    shock_type = ShockType.VOLATILITY
                else:
                    shock_value = np.random.normal(params['mean'], params['std'])
                    shock_type = ShockType.RELATIVE

                shock = MarketShock(
                    factor=factor,
                    shock_type=shock_type,
                    magnitude=shock_value,
                    description=f"MC simulation shock"
                )
                scenario_shocks.append(shock)

            scenarios.append(scenario_shocks)

        return scenarios

    def _get_scenario(self, scenario_name: str) -> Optional[StressScenario]:
        """Get scenario by name from all available scenarios"""

        # Check user-defined scenarios first
        if scenario_name in self._scenarios:
            return self._scenarios[scenario_name]

        # Check historical scenarios
        if scenario_name in self._historical_scenarios:
            return self._historical_scenarios[scenario_name]

        return None

    def add_custom_scenario(self, scenario: StressScenario) -> None:
        """Add custom stress scenario"""
        self._scenarios[scenario.name] = scenario
        logger.info(f"Added custom stress scenario: {scenario.name}")

    def get_all_scenarios(self) -> Dict[str, StressScenario]:
        """Get all available stress scenarios"""
        all_scenarios = {}
        all_scenarios.update(self._historical_scenarios)
        all_scenarios.update(self._scenarios)
        return all_scenarios

    def get_test_history(self) -> List[Dict[str, Any]]:
        """Get stress test history"""
        with self._lock:
            return list(self._test_results)

    async def run_reverse_stress_test(
        self,
        target_pnl_loss: float,
        primary_factor: str,
        positions: Dict[str, Any],
        portfolio_value: float,
        factor_loadings: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Dict[str, Any]:
        """
        Reverse Stress Test: Find the magnitude of a factor shock
        required to cause a specific target loss in PnL terms.
        """
        # Ensure target_pnl_loss is negative for a loss
        if target_pnl_loss > 0:
            target_pnl_loss = -target_pnl_loss

        # Probing shock: 1% relative shift
        probe_shock = MarketShock(
            factor=primary_factor,
            shock_type=ShockType.RELATIVE,
            magnitude=0.01
        )

        probe_scenario = StressScenario(
            name="Reverse_Stress_Probe",
            description="Internal probe for reverse stress test",
            test_type=StressTestType.REVERSE,
            shocks=[probe_shock]
        )

        try:
            total_probe_pnl = 0.0
            for position_id, position in positions.items():
                result = await self._calculate_position_stress(
                    position_id, position, probe_scenario, factor_loadings
                )
                total_probe_pnl += result.pnl

            # Avoid division by zero
            if abs(total_probe_pnl) < 1e-9:
                return {
                    "factor": primary_factor,
                    "target_loss": target_pnl_loss,
                    "error": "Portfolio has zero or negligible sensitivity to this factor."
                }

            # Solve for required shock (assuming linear sensitivity near current point)
            # shock_needed / probes_shock = target_loss / probe_pnl
            required_shock = (target_pnl_loss / total_probe_pnl) * 0.01

            logger.info(f"Reverse stress test for {primary_factor} found required shock of {required_shock:.2%}")

            return {
                "factor": primary_factor,
                "target_loss": target_pnl_loss,
                "required_shock_magnitude": required_shock,
                "probe_pnl_1pct": total_probe_pnl,
                "is_attainable": True
            }

        except Exception as e:
            logger.error(f"Error in reverse stress test: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup resources"""
        logger.info("StressTester cleanup completed")