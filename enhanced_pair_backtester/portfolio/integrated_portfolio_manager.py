"""
Integrated Portfolio Management System - Complete Portfolio Optimization for Statistical Arbitrage
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# Import our backtesting components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.enhanced_realistic_backtester import EnhancedRealisticBacktester

@dataclass
class PortfolioPosition:
    """Individual position in the portfolio"""
    pair: Tuple[str, str]
    symbol1_qty: float
    symbol2_qty: float
    entry_price1: float
    entry_price2: float
    current_price1: float
    current_price2: float
    entry_spread: float
    current_spread: float
    pnl: float
    weight: float
    risk_contribution: float
    days_held: int

@dataclass
class PortfolioMetrics:
    """Portfolio-level metrics"""
    total_value: float
    total_pnl: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    var_95: float
    correlation_risk: float
    concentration_risk: float
    active_pairs: int
    total_pairs: int

class IntegratedPortfolioManager:
    """Comprehensive portfolio management system"""
    
    def __init__(self, initial_capital: float = 1_000_000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.cash = initial_capital
        
        # Portfolio state
        self.positions: Dict[Tuple[str, str], PortfolioPosition] = {}
        self.portfolio_history: List[Dict[str, Any]] = []
        
        # Risk management parameters
        self.max_position_size = 0.15  # 15% max per pair
        self.max_portfolio_concentration = 0.6  # 60% max concentration
        self.max_correlation_exposure = 0.8  # 80% max to correlated pairs
        self.var_limit = 0.05  # 5% VaR limit
        
        # Rebalancing parameters
        self.rebalance_threshold = 0.03  # 3% weight drift triggers rebalance
        self.rebalance_frequency = 5  # Rebalance every 5 days
        self.last_rebalance = datetime.now()
        
        # Performance tracking
        self.trades_executed = 0
        self.rebalances_performed = 0
        
        self.logger = logging.getLogger(__name__)
        
    def calculate_pair_correlation_matrix(self, pairs: List[Tuple[str, str]], 
                                        price_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix between pair spreads"""
        
        spreads = {}
        for pair in pairs:
            symbol1, symbol2 = pair
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                spread = np.log(price_data[symbol1]) - np.log(price_data[symbol2])
                spreads[f"{symbol1}_{symbol2}"] = spread
        
        if spreads:
            spreads_df = pd.DataFrame(spreads)
            return spreads_df.corr()
        else:
            return pd.DataFrame()
    
    def calculate_optimal_weights(self, pairs: List[Tuple[str, str]], 
                                price_data: pd.DataFrame) -> Dict[Tuple[str, str], float]:
        """Calculate optimal portfolio weights using simplified optimization"""
        
        # Calculate basic metrics for each pair
        pair_metrics = {}
        
        for pair in pairs:
            symbol1, symbol2 = pair
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                # Calculate spread statistics
                spread = np.log(price_data[symbol1]) - np.log(price_data[symbol2])
                spread_returns = pd.Series(spread).pct_change().dropna()
                
                if len(spread_returns) > 30:
                    # Calculate metrics
                    mean_return = spread_returns.mean() * 252  # Annualized
                    volatility = spread_returns.std() * np.sqrt(252)
                    sharpe = mean_return / volatility if volatility > 0 else 0
                    
                    # Current z-score
                    current_spread = spread.iloc[-1] if len(spread) > 0 else 0
                    spread_mean = spread.rolling(60).mean().iloc[-1] if len(spread) > 60 else spread.mean()
                    spread_std = spread.rolling(60).std().iloc[-1] if len(spread) > 60 else spread.std()
                    z_score = abs((current_spread - spread_mean) / spread_std) if spread_std > 0 else 0
                    
                    # Liquidity score (simplified)
                    avg_volume = (price_data[symbol1].rolling(20).mean().iloc[-1] + 
                                price_data[symbol2].rolling(20).mean().iloc[-1]) / 2
                    liquidity_score = min(avg_volume / 1000000, 1.0)
                    
                    # Combined score
                    signal_strength = min(z_score / 2.0, 1.0)  # Normalize z-score
                    quality_score = (sharpe + 1) * liquidity_score * signal_strength
                    
                    pair_metrics[pair] = {
                        'sharpe': sharpe,
                        'volatility': volatility,
                        'z_score': z_score,
                        'liquidity': liquidity_score,
                        'quality_score': quality_score
                    }
        
        if not pair_metrics:
            return {}
        
        # Calculate correlation matrix
        correlation_matrix = self.calculate_pair_correlation_matrix(pairs, price_data)
        
        # Simple optimization: weight by quality score with correlation penalty
        weights = {}
        total_quality = sum(metrics['quality_score'] for metrics in pair_metrics.values())
        
        for pair, metrics in pair_metrics.items():
            if total_quality > 0:
                base_weight = metrics['quality_score'] / total_quality
                
                # Apply correlation penalty
                pair_name = f"{pair[0]}_{pair[1]}"
                correlation_penalty = 1.0
                
                if pair_name in correlation_matrix.index:
                    # Penalize pairs with high correlation to existing positions
                    for other_pair in self.positions.keys():
                        other_name = f"{other_pair[0]}_{other_pair[1]}"
                        if other_name in correlation_matrix.columns:
                            corr = abs(correlation_matrix.loc[pair_name, other_name])
                            if corr > 0.7:  # High correlation threshold
                                correlation_penalty *= (1 - corr * 0.5)
                
                # Apply position size limits
                adjusted_weight = base_weight * correlation_penalty
                final_weight = min(adjusted_weight, self.max_position_size)
                
                weights[pair] = final_weight
            else:
                weights[pair] = 0.0
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {pair: weight / total_weight for pair, weight in weights.items()}
        
        return weights
    
    def calculate_portfolio_risk(self, price_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive portfolio risk metrics"""
        
        if not self.positions:
            return {
                'total_var': 0.0,
                'concentration_risk': 0.0,
                'correlation_risk': 0.0,
                'volatility': 0.0
            }
        
        # Calculate position values
        position_values = []
        for pair, position in self.positions.items():
            symbol1, symbol2 = pair
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                current_value = (position.symbol1_qty * price_data[symbol1].iloc[-1] + 
                               position.symbol2_qty * price_data[symbol2].iloc[-1])
                position_values.append(abs(current_value))
        
        if not position_values:
            return {
                'total_var': 0.0,
                'concentration_risk': 0.0,
                'correlation_risk': 0.0,
                'volatility': 0.0
            }
        
        # Concentration risk
        total_exposure = sum(position_values)
        max_position = max(position_values)
        concentration_risk = max_position / total_exposure if total_exposure > 0 else 0
        
        # Portfolio volatility (simplified)
        portfolio_returns = []
        for i in range(min(30, len(price_data) - 1)):  # Use last 30 days
            daily_pnl = 0
            for pair, position in self.positions.items():
                symbol1, symbol2 = pair
                if symbol1 in price_data.columns and symbol2 in price_data.columns:
                    price1_change = price_data[symbol1].iloc[-(i+1)] - price_data[symbol1].iloc[-(i+2)]
                    price2_change = price_data[symbol2].iloc[-(i+1)] - price_data[symbol2].iloc[-(i+2)]
                    daily_pnl += position.symbol1_qty * price1_change + position.symbol2_qty * price2_change
            
            if self.current_capital > 0:
                daily_return = daily_pnl / self.current_capital
                portfolio_returns.append(daily_return)
        
        if portfolio_returns:
            portfolio_volatility = np.std(portfolio_returns) * np.sqrt(252)  # Annualized
            var_95 = np.percentile(portfolio_returns, 5) * np.sqrt(252)  # 95% VaR
        else:
            portfolio_volatility = 0.0
            var_95 = 0.0
        
        # Correlation risk (simplified)
        correlation_matrix = self.calculate_pair_correlation_matrix(
            list(self.positions.keys()), price_data
        )
        
        if not correlation_matrix.empty:
            avg_correlation = correlation_matrix.values.mean()
            correlation_risk = max(0, avg_correlation)
        else:
            correlation_risk = 0.0
        
        return {
            'total_var': abs(var_95),
            'concentration_risk': concentration_risk,
            'correlation_risk': correlation_risk,
            'volatility': portfolio_volatility
        }
    
    def should_rebalance(self, current_weights: Dict[Tuple[str, str], float],
                        target_weights: Dict[Tuple[str, str], float]) -> bool:
        """Determine if portfolio should be rebalanced"""
        
        # Time-based rebalancing
        days_since_rebalance = (datetime.now() - self.last_rebalance).days
        if days_since_rebalance >= self.rebalance_frequency:
            return True
        
        # Weight drift rebalancing
        for pair in set(current_weights.keys()) | set(target_weights.keys()):
            current_weight = current_weights.get(pair, 0.0)
            target_weight = target_weights.get(pair, 0.0)
            
            if abs(current_weight - target_weight) > self.rebalance_threshold:
                return True
        
        return False
    
    def execute_rebalancing(self, target_weights: Dict[Tuple[str, str], float],
                          price_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Execute portfolio rebalancing"""
        
        rebalance_trades = []
        
        # Calculate current weights
        current_weights = {}
        total_portfolio_value = self.calculate_portfolio_value(price_data)
        
        for pair, position in self.positions.items():
            symbol1, symbol2 = pair
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                position_value = abs(position.symbol1_qty * price_data[symbol1].iloc[-1] + 
                                   position.symbol2_qty * price_data[symbol2].iloc[-1])
                current_weights[pair] = position_value / total_portfolio_value if total_portfolio_value > 0 else 0
        
        # Generate rebalancing trades
        for pair in set(current_weights.keys()) | set(target_weights.keys()):
            current_weight = current_weights.get(pair, 0.0)
            target_weight = target_weights.get(pair, 0.0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > self.rebalance_threshold:
                trade_value = total_portfolio_value * weight_diff
                
                rebalance_trades.append({
                    'pair': pair,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'trade_value': trade_value,
                    'action': 'increase' if weight_diff > 0 else 'decrease'
                })
        
        # Execute trades (simplified)
        for trade in rebalance_trades:
            self.logger.info(f"Rebalancing {trade['pair']}: {trade['current_weight']:.2%} → {trade['target_weight']:.2%}")
            # In a real system, this would execute actual trades
            self.trades_executed += 1
        
        self.rebalances_performed += 1
        self.last_rebalance = datetime.now()
        
        return rebalance_trades
    
    def calculate_portfolio_value(self, price_data: pd.DataFrame) -> float:
        """Calculate current portfolio value"""
        
        total_value = self.cash
        
        for pair, position in self.positions.items():
            symbol1, symbol2 = pair
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                position_value = (position.symbol1_qty * price_data[symbol1].iloc[-1] + 
                                position.symbol2_qty * price_data[symbol2].iloc[-1])
                total_value += position_value
        
        return total_value
    
    def update_positions(self, price_data: pd.DataFrame):
        """Update all position metrics"""
        
        for pair, position in self.positions.items():
            symbol1, symbol2 = pair
            if symbol1 in price_data.columns and symbol2 in price_data.columns:
                # Update current prices
                position.current_price1 = price_data[symbol1].iloc[-1]
                position.current_price2 = price_data[symbol2].iloc[-1]
                
                # Update spread
                position.current_spread = np.log(position.current_price1) - np.log(position.current_price2)
                
                # Update PnL
                position.pnl = (position.symbol1_qty * (position.current_price1 - position.entry_price1) + 
                               position.symbol2_qty * (position.current_price2 - position.entry_price2))
    
    def run_integrated_portfolio_management(self, pairs: List[Tuple[str, str]], 
                                          start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Run integrated portfolio management system"""
        
        self.logger.info(f"Starting integrated portfolio management from {start_date} to {end_date}")
        
        # Generate sample data using our backtester
        backtester = EnhancedRealisticBacktester(self.initial_capital)
        all_symbols = list(set([s for pair in pairs for s in pair]))
        price_data = backtester.generate_sample_data(all_symbols, start_date, end_date)
        
        # Group by timestamp
        data_by_time = price_data.groupby('timestamp')
        
        portfolio_snapshots = []
        rebalance_events = []
        
        for timestamp, group in data_by_time:
            # Create price DataFrame for this timestamp
            current_prices = pd.DataFrame({
                symbol: [price] for symbol, price in zip(group['symbol'], group['price'])
            })
            
            # Extend to have some history for calculations
            if len(portfolio_snapshots) == 0:
                # Initialize with sample data
                extended_prices = pd.DataFrame(index=pd.date_range(start_date, timestamp, freq='D'))
                for symbol in all_symbols:
                    base_price = current_prices[symbol].iloc[0] if symbol in current_prices.columns else 100
                    extended_prices[symbol] = base_price * (1 + np.random.normal(0, 0.01, len(extended_prices)))
            else:
                # Use accumulated data
                extended_prices = pd.DataFrame(portfolio_snapshots[-min(60, len(portfolio_snapshots)):])
                for symbol in all_symbols:
                    if symbol in current_prices.columns:
                        extended_prices.loc[timestamp, symbol] = current_prices[symbol].iloc[0]
            
            # Update positions
            self.update_positions(extended_prices)
            
            # Calculate current portfolio metrics
            portfolio_value = self.calculate_portfolio_value(extended_prices)
            risk_metrics = self.calculate_portfolio_risk(extended_prices)
            
            # Calculate optimal weights
            target_weights = self.calculate_optimal_weights(pairs, extended_prices)
            
            # Check if rebalancing is needed
            current_weights = {}
            for pair, position in self.positions.items():
                position_value = abs(position.symbol1_qty * extended_prices[pair[0]].iloc[-1] + 
                                   position.symbol2_qty * extended_prices[pair[1]].iloc[-1])
                current_weights[pair] = position_value / portfolio_value if portfolio_value > 0 else 0
            
            if self.should_rebalance(current_weights, target_weights):
                rebalance_trades = self.execute_rebalancing(target_weights, extended_prices)
                rebalance_events.append({
                    'timestamp': timestamp,
                    'trades': rebalance_trades,
                    'portfolio_value': portfolio_value
                })
            
            # Record portfolio snapshot
            portfolio_snapshots.append({
                'timestamp': timestamp,
                'portfolio_value': portfolio_value,
                'cash': self.cash,
                'total_pnl': portfolio_value - self.initial_capital,
                'total_return': (portfolio_value - self.initial_capital) / self.initial_capital,
                'var_95': risk_metrics['total_var'],
                'concentration_risk': risk_metrics['concentration_risk'],
                'correlation_risk': risk_metrics['correlation_risk'],
                'volatility': risk_metrics['volatility'],
                'active_pairs': len(self.positions),
                'rebalances_performed': self.rebalances_performed
            })
        
        # Calculate final performance metrics
        if portfolio_snapshots:
            final_value = portfolio_snapshots[-1]['portfolio_value']
            total_return = (final_value - self.initial_capital) / self.initial_capital
            
            returns = [snapshot['total_return'] for snapshot in portfolio_snapshots]
            if len(returns) > 1:
                return_changes = np.diff(returns)
                sharpe_ratio = np.mean(return_changes) / np.std(return_changes) * np.sqrt(252) if np.std(return_changes) > 0 else 0
                max_drawdown = min(returns) if returns else 0
            else:
                sharpe_ratio = 0
                max_drawdown = 0
        else:
            final_value = self.initial_capital
            total_return = 0
            sharpe_ratio = 0
            max_drawdown = 0
        
        results = {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'trades_executed': self.trades_executed,
            'rebalances_performed': self.rebalances_performed,
            'portfolio_history': portfolio_snapshots,
            'rebalance_events': rebalance_events,
            'final_positions': len(self.positions)
        }
        
        self.logger.info(f"Portfolio management completed. Total return: {total_return:.2%}")
        self.logger.info(f"Rebalances performed: {self.rebalances_performed}")
        
        return results
    
    def generate_portfolio_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive portfolio management report"""
        
        report = f"""
=== INTEGRATED PORTFOLIO MANAGEMENT REPORT ===

PERFORMANCE SUMMARY:
- Initial Capital: ${results['initial_capital']:,.2f}
- Final Value: ${results['final_value']:,.2f}
- Total Return: {results['total_return']:.2%}
- Sharpe Ratio: {results['sharpe_ratio']:.2f}
- Maximum Drawdown: {results['max_drawdown']:.2%}

PORTFOLIO MANAGEMENT:
- Total Trades Executed: {results['trades_executed']}
- Rebalances Performed: {results['rebalances_performed']}
- Final Active Positions: {results['final_positions']}
- Average Portfolio Utilization: {np.mean([h['portfolio_value'] - h['cash'] for h in results['portfolio_history']]) / results['initial_capital']:.1%}

RISK MANAGEMENT:
- Average VaR (95%): {np.mean([h['var_95'] for h in results['portfolio_history']]):.2%}
- Average Concentration Risk: {np.mean([h['concentration_risk'] for h in results['portfolio_history']]):.2%}
- Average Correlation Risk: {np.mean([h['correlation_risk'] for h in results['portfolio_history']]):.2%}
- Portfolio Volatility: {np.mean([h['volatility'] for h in results['portfolio_history']]):.2%}

REBALANCING ACTIVITY:
- Rebalancing Frequency: {len(results['rebalance_events'])} events
- Average Rebalance Impact: {np.mean([len(event['trades']) for event in results['rebalance_events']]) if results['rebalance_events'] else 0:.1f} trades per rebalance
"""
        
        return report

def run_integrated_portfolio_demo():
    """Run integrated portfolio management demonstration"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Integrated Portfolio Management Demo")
    
    # Initialize portfolio manager
    portfolio_manager = IntegratedPortfolioManager(initial_capital=1_000_000)
    
    # Define pairs to manage
    pairs = [
        ('SPY', 'UPRO'),
        ('QQQ', 'TQQQ'),
        ('TLT', 'TMF'),
        ('IWM', 'TNA'),
        ('VTI', 'VXUS')
    ]
    
    # Run portfolio management
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    results = portfolio_manager.run_integrated_portfolio_management(pairs, start_date, end_date)
    
    # Generate report
    report = portfolio_manager.generate_portfolio_report(results)
    print(report)
    
    # Save results
    results_df = pd.DataFrame(results['portfolio_history'])
    results_df.to_csv('integrated_portfolio_results.csv', index=False)
    
    # Save rebalance events
    if results['rebalance_events']:
        rebalance_df = pd.DataFrame([{
            'timestamp': event['timestamp'],
            'portfolio_value': event['portfolio_value'],
            'n_trades': len(event['trades'])
        } for event in results['rebalance_events']])
        rebalance_df.to_csv('portfolio_rebalance_events.csv', index=False)
    
    logger.info("Integrated portfolio management demo completed")
    return results

if __name__ == "__main__":
    run_integrated_portfolio_demo() 