"""
Portfolio Optimization System - Modern Portfolio Theory for Statistical Arbitrage
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from scipy.optimize import minimize, Bounds
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

# Import our components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class PairMetrics:
    """Metrics for individual pairs"""
    pair: Tuple[str, str]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    correlation_with_market: float
    beta: float
    current_spread: float
    z_score: float
    liquidity_score: float
    transaction_cost: float

@dataclass
class PortfolioAllocation:
    """Portfolio allocation result"""
    pair_weights: Dict[Tuple[str, str], float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    diversification_ratio: float
    risk_contribution: Dict[Tuple[str, str], float]
    correlation_matrix: np.ndarray
    optimization_status: str

class CorrelationAnalyzer:
    """Dynamic correlation analysis for pairs"""
    
    def __init__(self, lookback_days: int = 60):
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(__name__)
        
    def calculate_pair_correlations(self, pairs: List[Tuple[str, str]], 
                                  price_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix between pair spreads"""
        
        # Calculate spreads for each pair
        spreads = {}
        for pair in pairs:
            symbol1, symbol2 = pair
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                spread = np.log(price_data[symbol1]) - np.log(price_data[symbol2])
                spreads[f"{symbol1}_{symbol2}"] = spread
        
        # Create DataFrame of spreads
        spreads_df = pd.DataFrame(spreads)
        
        # Calculate correlation matrix
        correlation_matrix = spreads_df.corr()
        
        return correlation_matrix
    
    def identify_redundant_pairs(self, correlation_matrix: pd.DataFrame, 
                               threshold: float = 0.8) -> List[Tuple[str, str]]:
        """Identify pairs with high correlation (redundant)"""
        
        redundant_pairs = []
        
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr = abs(correlation_matrix.iloc[i, j])
                if corr > threshold:
                    pair1 = correlation_matrix.columns[i]
                    pair2 = correlation_matrix.columns[j]
                    redundant_pairs.append((pair1, pair2))
        
        return redundant_pairs
    
    def calculate_diversification_benefits(self, correlation_matrix: pd.DataFrame) -> float:
        """Calculate portfolio diversification ratio"""
        
        # Average correlation
        n = len(correlation_matrix)
        total_corr = correlation_matrix.values.sum() - n  # Subtract diagonal
        avg_correlation = total_corr / (n * (n - 1))
        
        # Diversification ratio (1 = no diversification, 0 = perfect diversification)
        diversification_ratio = 1 - (1 - avg_correlation) * (n - 1) / n
        
        return diversification_ratio

class RiskFactorAnalyzer:
    """Analyze systematic risk factors"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common risk factors
        self.risk_factors = {
            'market': 'SPY',
            'size': 'IWM',
            'value': 'VTV',
            'growth': 'VUG',
            'momentum': 'MTUM',
            'volatility': 'VIX',
            'rates': 'TLT',
            'credit': 'LQD'
        }
    
    def calculate_factor_exposures(self, pairs: List[Tuple[str, str]], 
                                 price_data: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Calculate factor exposures for each pair"""
        
        factor_exposures = {}
        
        # Calculate returns for each pair spread
        for pair in pairs:
            symbol1, symbol2 = pair
            pair_key = f"{symbol1}_{symbol2}"
            
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                # Calculate spread returns
                spread = np.log(price_data[symbol1]) - np.log(price_data[symbol2])
                spread_returns = pd.Series(spread).pct_change().dropna()
                
                # Calculate factor exposures (betas)
                exposures = {}
                for factor_name, factor_symbol in self.risk_factors.items():
                    if factor_symbol in price_data.columns:
                        factor_returns = price_data[factor_symbol].pct_change().dropna()
                        
                        # Align data
                        common_dates = spread_returns.index.intersection(factor_returns.index)
                        if len(common_dates) > 30:  # Need sufficient data
                            spread_aligned = spread_returns.loc[common_dates]
                            factor_aligned = factor_returns.loc[common_dates]
                            
                            # Calculate beta
                            covariance = np.cov(spread_aligned, factor_aligned)[0, 1]
                            factor_variance = np.var(factor_aligned)
                            
                            if factor_variance > 0:
                                beta = covariance / factor_variance
                                exposures[factor_name] = beta
                            else:
                                exposures[factor_name] = 0.0
                        else:
                            exposures[factor_name] = 0.0
                    else:
                        exposures[factor_name] = 0.0
                
                factor_exposures[pair_key] = exposures
        
        return factor_exposures
    
    def calculate_portfolio_factor_exposure(self, pair_weights: Dict[Tuple[str, str], float],
                                          factor_exposures: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate portfolio-level factor exposures"""
        
        portfolio_exposures = {}
        
        # Initialize with zero exposures
        if factor_exposures:
            first_pair = list(factor_exposures.keys())[0]
            for factor in factor_exposures[first_pair].keys():
                portfolio_exposures[factor] = 0.0
        
        # Weight-average individual exposures
        for pair, weight in pair_weights.items():
            pair_key = f"{pair[0]}_{pair[1]}"
            if pair_key in factor_exposures:
                for factor, exposure in factor_exposures[pair_key].items():
                    portfolio_exposures[factor] += weight * exposure
        
        return portfolio_exposures

class PortfolioOptimizer:
    """Modern portfolio theory optimizer for statistical arbitrage pairs"""
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.logger = logging.getLogger(__name__)
        
        # Optimization constraints
        self.max_pair_weight = 0.25  # Maximum 25% allocation per pair
        self.min_pair_weight = 0.0   # Minimum allocation
        self.max_portfolio_concentration = 0.6  # Maximum 60% in any asset class
        
        # Risk management
        self.max_portfolio_volatility = 0.15  # Maximum 15% portfolio volatility
        self.max_factor_exposure = 0.3  # Maximum 30% exposure to any factor
        
    def calculate_pair_metrics(self, pairs: List[Tuple[str, str]], 
                             price_data: pd.DataFrame, 
                             returns_data: pd.DataFrame) -> Dict[Tuple[str, str], PairMetrics]:
        """Calculate comprehensive metrics for each pair"""
        
        pair_metrics = {}
        
        for pair in pairs:
            symbol1, symbol2 = pair
            
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                # Calculate spread
                spread = np.log(price_data[symbol1]) - np.log(price_data[symbol2])
                spread_returns = pd.Series(spread).pct_change().dropna()
                
                # Basic metrics
                expected_return = spread_returns.mean() * 252  # Annualized
                volatility = spread_returns.std() * np.sqrt(252)  # Annualized
                sharpe_ratio = (expected_return - self.risk_free_rate) / volatility if volatility > 0 else 0
                
                # Drawdown calculation
                cumulative = (1 + spread_returns).cumprod()
                peak = cumulative.expanding().max()
                drawdown = (cumulative - peak) / peak
                max_drawdown = drawdown.min()
                
                # Market correlation and beta
                if 'SPY' in price_data.columns:
                    market_returns = price_data['SPY'].pct_change().dropna()
                    common_dates = spread_returns.index.intersection(market_returns.index)
                    
                    if len(common_dates) > 30:
                        spread_aligned = spread_returns.loc[common_dates]
                        market_aligned = market_returns.loc[common_dates]
                        
                        correlation_with_market = np.corrcoef(spread_aligned, market_aligned)[0, 1]
                        
                        # Beta calculation
                        covariance = np.cov(spread_aligned, market_aligned)[0, 1]
                        market_variance = np.var(market_aligned)
                        beta = covariance / market_variance if market_variance > 0 else 0
                    else:
                        correlation_with_market = 0
                        beta = 0
                else:
                    correlation_with_market = 0
                    beta = 0
                
                # Current spread metrics
                spread_series = pd.Series(spread)
                current_spread = spread_series.iloc[-1] if len(spread_series) > 0 else 0
                spread_mean = spread_series.rolling(60).mean().iloc[-1] if len(spread_series) > 60 else spread_series.mean()
                spread_std = spread_series.rolling(60).std().iloc[-1] if len(spread_series) > 60 else spread_series.std()
                z_score = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0
                
                # Liquidity score (simplified)
                avg_volume = (price_data[symbol1].rolling(20).mean().iloc[-1] + 
                            price_data[symbol2].rolling(20).mean().iloc[-1]) / 2
                liquidity_score = min(avg_volume / 1000000, 1.0)  # Normalize to 0-1
                
                # Transaction cost estimate (simplified)
                transaction_cost = 0.001 * (1 / liquidity_score)  # Higher cost for less liquid pairs
                
                pair_metrics[pair] = PairMetrics(
                    pair=pair,
                    expected_return=expected_return,
                    volatility=volatility,
                    sharpe_ratio=sharpe_ratio,
                    max_drawdown=max_drawdown,
                    correlation_with_market=correlation_with_market,
                    beta=beta,
                    current_spread=current_spread,
                    z_score=z_score,
                    liquidity_score=liquidity_score,
                    transaction_cost=transaction_cost
                )
        
        return pair_metrics
    
    def optimize_portfolio(self, pair_metrics: Dict[Tuple[str, str], PairMetrics],
                         correlation_matrix: pd.DataFrame,
                         optimization_objective: str = 'sharpe') -> PortfolioAllocation:
        """Optimize portfolio allocation using modern portfolio theory"""
        
        pairs = list(pair_metrics.keys())
        n_pairs = len(pairs)
        
        if n_pairs == 0:
            return self._empty_allocation()
        
        # Extract metrics
        expected_returns = np.array([pair_metrics[pair].expected_return for pair in pairs])
        volatilities = np.array([pair_metrics[pair].volatility for pair in pairs])
        transaction_costs = np.array([pair_metrics[pair].transaction_cost for pair in pairs])
        
        # Adjust returns for transaction costs
        net_returns = expected_returns - transaction_costs
        
        # Build covariance matrix
        correlation_matrix_aligned = self._align_correlation_matrix(correlation_matrix, pairs)
        covariance_matrix = np.outer(volatilities, volatilities) * correlation_matrix_aligned
        
        # Optimization constraints
        bounds = Bounds(
            lb=np.full(n_pairs, self.min_pair_weight),
            ub=np.full(n_pairs, self.max_pair_weight)
        )
        
        # Constraint: weights sum to 1
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}
        ]
        
        # Volatility constraint
        constraints.append({
            'type': 'ineq',
            'fun': lambda x: self.max_portfolio_volatility**2 - np.dot(x, np.dot(covariance_matrix, x))
        })
        
        # Initial guess (equal weights)
        x0 = np.full(n_pairs, 1.0 / n_pairs)
        
        # Objective function
        if optimization_objective == 'sharpe':
            def objective(weights):
                portfolio_return = np.dot(weights, net_returns)
                portfolio_variance = np.dot(weights, np.dot(covariance_matrix, weights))
                portfolio_volatility = np.sqrt(portfolio_variance)
                
                if portfolio_volatility > 0:
                    sharpe = (portfolio_return - self.risk_free_rate) / portfolio_volatility
                    return -sharpe  # Minimize negative Sharpe
                else:
                    return 1e6  # Large penalty for zero volatility
                    
        elif optimization_objective == 'min_variance':
            def objective(weights):
                return np.dot(weights, np.dot(covariance_matrix, weights))
                
        elif optimization_objective == 'max_return':
            def objective(weights):
                return -np.dot(weights, net_returns)
        
        # Optimize
        try:
            result = minimize(
                objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-9}
            )
            
            if result.success:
                optimal_weights = result.x
                optimization_status = "Success"
            else:
                self.logger.warning(f"Optimization failed: {result.message}")
                optimal_weights = x0  # Fall back to equal weights
                optimization_status = f"Failed: {result.message}"
                
        except Exception as e:
            self.logger.error(f"Optimization error: {e}")
            optimal_weights = x0
            optimization_status = f"Error: {str(e)}"
        
        # Calculate portfolio metrics
        portfolio_return = np.dot(optimal_weights, net_returns)
        portfolio_variance = np.dot(optimal_weights, np.dot(covariance_matrix, optimal_weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        portfolio_sharpe = (portfolio_return - self.risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
        
        # Calculate diversification ratio
        weighted_avg_volatility = np.dot(optimal_weights, volatilities)
        diversification_ratio = portfolio_volatility / weighted_avg_volatility if weighted_avg_volatility > 0 else 1.0
        
        # Calculate risk contributions
        risk_contributions = {}
        for i, pair in enumerate(pairs):
            marginal_risk = np.dot(covariance_matrix[i], optimal_weights)
            risk_contribution = optimal_weights[i] * marginal_risk / portfolio_variance if portfolio_variance > 0 else 0
            risk_contributions[pair] = risk_contribution
        
        # Create weight dictionary
        pair_weights = {pair: weight for pair, weight in zip(pairs, optimal_weights)}
        
        return PortfolioAllocation(
            pair_weights=pair_weights,
            expected_return=portfolio_return,
            expected_volatility=portfolio_volatility,
            sharpe_ratio=portfolio_sharpe,
            diversification_ratio=diversification_ratio,
            risk_contribution=risk_contributions,
            correlation_matrix=correlation_matrix_aligned,
            optimization_status=optimization_status
        )
    
    def _align_correlation_matrix(self, correlation_matrix: pd.DataFrame, 
                                pairs: List[Tuple[str, str]]) -> np.ndarray:
        """Align correlation matrix with pairs list"""
        
        pair_names = [f"{pair[0]}_{pair[1]}" for pair in pairs]
        n_pairs = len(pairs)
        
        # Create aligned correlation matrix
        aligned_matrix = np.eye(n_pairs)  # Default to identity matrix
        
        for i, pair1 in enumerate(pair_names):
            for j, pair2 in enumerate(pair_names):
                if pair1 in correlation_matrix.index and pair2 in correlation_matrix.columns:
                    aligned_matrix[i, j] = correlation_matrix.loc[pair1, pair2]
        
        return aligned_matrix
    
    def _empty_allocation(self) -> PortfolioAllocation:
        """Return empty allocation when no pairs available"""
        return PortfolioAllocation(
            pair_weights={},
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            diversification_ratio=1.0,
            risk_contribution={},
            correlation_matrix=np.array([]),
            optimization_status="No pairs available"
        )

class DynamicHedger:
    """Dynamic hedging system for systematic risk factors"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Hedging instruments
        self.hedge_instruments = {
            'market': ['SPY', 'QQQ', 'IWM'],
            'rates': ['TLT', 'IEF', 'SHY'],
            'volatility': ['VIX', 'UVXY'],
            'credit': ['LQD', 'HYG'],
            'currency': ['UUP', 'FXE']
        }
        
        # Hedging thresholds
        self.hedge_threshold = 0.1  # Hedge when exposure > 10%
        self.rebalance_threshold = 0.05  # Rebalance when drift > 5%
        
    def calculate_hedge_ratios(self, portfolio_exposures: Dict[str, float],
                             target_exposures: Dict[str, float] = None) -> Dict[str, float]:
        """Calculate optimal hedge ratios for risk factors"""
        
        if target_exposures is None:
            target_exposures = {factor: 0.0 for factor in portfolio_exposures.keys()}
        
        hedge_ratios = {}
        
        for factor, current_exposure in portfolio_exposures.items():
            target_exposure = target_exposures.get(factor, 0.0)
            exposure_diff = current_exposure - target_exposure
            
            if abs(exposure_diff) > self.hedge_threshold:
                # Calculate hedge ratio (simplified)
                hedge_ratio = -exposure_diff  # Opposite direction to neutralize
                hedge_ratios[factor] = hedge_ratio
            else:
                hedge_ratios[factor] = 0.0
        
        return hedge_ratios
    
    def generate_hedge_orders(self, hedge_ratios: Dict[str, float],
                            portfolio_value: float) -> List[Dict[str, Any]]:
        """Generate hedge orders based on calculated ratios"""
        
        hedge_orders = []
        
        for factor, ratio in hedge_ratios.items():
            if abs(ratio) > 0.01:  # Only hedge significant exposures
                # Select best hedge instrument
                instruments = self.hedge_instruments.get(factor, [])
                
                if instruments:
                    # Use first instrument (could be optimized)
                    hedge_symbol = instruments[0]
                    
                    # Calculate position size
                    hedge_value = portfolio_value * ratio
                    
                    hedge_orders.append({
                        'symbol': hedge_symbol,
                        'factor': factor,
                        'value': hedge_value,
                        'ratio': ratio,
                        'order_type': 'hedge'
                    })
        
        return hedge_orders

class PortfolioRebalancer:
    """Automated portfolio rebalancing with transaction cost optimization"""
    
    def __init__(self, rebalance_threshold: float = 0.05):
        self.rebalance_threshold = rebalance_threshold
        self.logger = logging.getLogger(__name__)
        
    def calculate_rebalance_trades(self, current_weights: Dict[Tuple[str, str], float],
                                 target_weights: Dict[Tuple[str, str], float],
                                 portfolio_value: float) -> List[Dict[str, Any]]:
        """Calculate trades needed for rebalancing"""
        
        rebalance_trades = []
        
        # Get all pairs
        all_pairs = set(current_weights.keys()) | set(target_weights.keys())
        
        for pair in all_pairs:
            current_weight = current_weights.get(pair, 0.0)
            target_weight = target_weights.get(pair, 0.0)
            
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > self.rebalance_threshold:
                # Calculate trade value
                trade_value = portfolio_value * weight_diff
                
                rebalance_trades.append({
                    'pair': pair,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'weight_diff': weight_diff,
                    'trade_value': trade_value,
                    'action': 'increase' if weight_diff > 0 else 'decrease'
                })
        
        return rebalance_trades
    
    def optimize_rebalancing_sequence(self, rebalance_trades: List[Dict[str, Any]],
                                    transaction_costs: Dict[Tuple[str, str], float]) -> List[Dict[str, Any]]:
        """Optimize the sequence of rebalancing trades to minimize costs"""
        
        # Sort by cost-benefit ratio
        def cost_benefit_ratio(trade):
            pair = trade['pair']
            cost = transaction_costs.get(pair, 0.001)  # Default cost
            benefit = abs(trade['weight_diff'])
            return cost / benefit if benefit > 0 else float('inf')
        
        # Sort trades by cost-benefit ratio (lowest first)
        optimized_trades = sorted(rebalance_trades, key=cost_benefit_ratio)
        
        return optimized_trades

# Demo and testing functions
def run_portfolio_optimization_demo():
    """Run portfolio optimization demonstration"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Portfolio Optimization Demo")
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2024-01-01', freq='D')
    
    # Sample pairs
    pairs = [
        ('SPY', 'UPRO'),
        ('QQQ', 'TQQQ'),
        ('TLT', 'TMF'),
        ('IWM', 'TNA'),
        ('VTI', 'VXUS')
    ]
    
    # Generate sample price data
    symbols = list(set([s for pair in pairs for s in pair]))
    price_data = pd.DataFrame(index=dates)
    
    for symbol in symbols:
        # Generate random walk prices
        returns = np.random.normal(0.001, 0.02, len(dates))
        price = 100
        prices = [price]
        
        for ret in returns[1:]:
            price *= (1 + ret)
            prices.append(price)
        
        price_data[symbol] = prices
    
    # Calculate returns
    returns_data = price_data.pct_change().dropna()
    
    # Initialize components
    correlation_analyzer = CorrelationAnalyzer()
    risk_analyzer = RiskFactorAnalyzer()
    optimizer = PortfolioOptimizer()
    hedger = DynamicHedger()
    rebalancer = PortfolioRebalancer()
    
    # Step 1: Correlation Analysis
    logger.info("Analyzing correlations...")
    correlation_matrix = correlation_analyzer.calculate_pair_correlations(pairs, price_data)
    redundant_pairs = correlation_analyzer.identify_redundant_pairs(correlation_matrix)
    diversification_ratio = correlation_analyzer.calculate_diversification_benefits(correlation_matrix)
    
    logger.info(f"Diversification ratio: {diversification_ratio:.3f}")
    logger.info(f"Redundant pairs: {len(redundant_pairs)}")
    
    # Step 2: Risk Factor Analysis
    logger.info("Analyzing risk factors...")
    factor_exposures = risk_analyzer.calculate_factor_exposures(pairs, price_data)
    
    # Step 3: Calculate Pair Metrics
    logger.info("Calculating pair metrics...")
    pair_metrics = optimizer.calculate_pair_metrics(pairs, price_data, returns_data)
    
    # Step 4: Portfolio Optimization
    logger.info("Optimizing portfolio...")
    allocation = optimizer.optimize_portfolio(pair_metrics, correlation_matrix, 'sharpe')
    
    # Step 5: Factor Hedging
    logger.info("Calculating hedging requirements...")
    portfolio_exposures = risk_analyzer.calculate_portfolio_factor_exposure(
        allocation.pair_weights, factor_exposures
    )
    hedge_ratios = hedger.calculate_hedge_ratios(portfolio_exposures)
    hedge_orders = hedger.generate_hedge_orders(hedge_ratios, 1_000_000)
    
    # Step 6: Rebalancing Analysis
    logger.info("Analyzing rebalancing needs...")
    current_weights = {pair: 1.0/len(pairs) for pair in pairs}  # Equal weights
    rebalance_trades = rebalancer.calculate_rebalance_trades(
        current_weights, allocation.pair_weights, 1_000_000
    )
    
    # Generate report
    print("\n" + "="*60)
    print("PORTFOLIO OPTIMIZATION REPORT")
    print("="*60)
    
    print(f"\nPORTFOLIO METRICS:")
    print(f"Expected Return: {allocation.expected_return:.2%}")
    print(f"Expected Volatility: {allocation.expected_volatility:.2%}")
    print(f"Sharpe Ratio: {allocation.sharpe_ratio:.2f}")
    print(f"Diversification Ratio: {allocation.diversification_ratio:.3f}")
    print(f"Optimization Status: {allocation.optimization_status}")
    
    print(f"\nOPTIMAL ALLOCATION:")
    for pair, weight in allocation.pair_weights.items():
        if weight > 0.01:  # Only show significant allocations
            metrics = pair_metrics[pair]
            print(f"{pair[0]}-{pair[1]}: {weight:.1%} (Sharpe: {metrics.sharpe_ratio:.2f}, Vol: {metrics.volatility:.1%})")
    
    print(f"\nRISK FACTOR EXPOSURES:")
    for factor, exposure in portfolio_exposures.items():
        print(f"{factor}: {exposure:.3f}")
    
    print(f"\nHEDGE RECOMMENDATIONS:")
    for order in hedge_orders:
        print(f"Hedge {order['factor']} with {order['symbol']}: ${order['value']:,.0f} ({order['ratio']:.2%})")
    
    print(f"\nREBALANCE TRADES:")
    for trade in rebalance_trades[:5]:  # Show top 5
        pair = trade['pair']
        print(f"{pair[0]}-{pair[1]}: {trade['current_weight']:.1%} → {trade['target_weight']:.1%} (${trade['trade_value']:,.0f})")
    
    # Save results
    results_df = pd.DataFrame([{
        'timestamp': datetime.now(),
        'expected_return': allocation.expected_return,
        'expected_volatility': allocation.expected_volatility,
        'sharpe_ratio': allocation.sharpe_ratio,
        'diversification_ratio': allocation.diversification_ratio,
        'n_pairs': len(allocation.pair_weights),
        'n_hedge_orders': len(hedge_orders),
        'n_rebalance_trades': len(rebalance_trades)
    }])
    
    results_df.to_csv('portfolio_optimization_results.csv', index=False)
    
    logger.info("Portfolio optimization demo completed")
    return {
        'allocation': allocation,
        'factor_exposures': portfolio_exposures,
        'hedge_orders': hedge_orders,
        'rebalance_trades': rebalance_trades,
        'correlation_matrix': correlation_matrix
    }

if __name__ == "__main__":
    run_portfolio_optimization_demo() 