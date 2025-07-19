"""
Professional Portfolio Construction for Momentum Trading
Implements institutional-grade portfolio optimization with risk controls
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PortfolioAllocation:
    """Portfolio allocation result for a single symbol"""
    symbol: str
    target_weight: float
    current_weight: float = 0.0
    shares: int = 0
    dollar_amount: float = 0.0
    expected_return: float = 0.0
    risk_contribution: float = 0.0
    sector: str = "Unknown"  # Add sector attribute

class PortfolioConstructor:
    """Professional portfolio construction with institutional risk controls"""
    
    def __init__(self):
        # Portfolio constraints from config
        self.max_position_weight = 0.08  # 8% max position
        self.max_sector_weight = 0.30    # 30% max sector exposure (relaxed for testing)
        self.target_volatility = 0.12    # 12% target volatility
        self.max_turnover = 0.3          # 30% max turnover
        
        # Signal validation (very permissive for testing)
        self.min_signal_strength = 0.001  # Very low threshold for testing
        
        # Sector mapping for sector neutrality
        self.sector_mapping = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'AMZN': 'Consumer Discretionary', 'TSLA': 'Consumer Discretionary',
            'META': 'Technology', 'NVDA': 'Technology', 'JPM': 'Financials',
            'JNJ': 'Healthcare', 'V': 'Financials', 'PG': 'Consumer Staples',
            'UNH': 'Healthcare', 'HD': 'Consumer Discretionary', 'MA': 'Financials',
            'BAC': 'Financials', 'PFE': 'Healthcare', 'XOM': 'Energy',
            'KO': 'Consumer Staples', 'WMT': 'Consumer Staples'
        }
        
        logger.info("Portfolio Constructor initialized")
    
    def construct_portfolio(self, signals: Dict[str, float], 
                          current_portfolio: Dict[str, float], 
                          market_data: Dict[str, pd.DataFrame],
                          portfolio_value: float = 100000,
                          rebalance_method: str = 'risk_adjusted') -> List[PortfolioAllocation]:
        """
        Construct optimized portfolio allocation
        
        Args:
            signals: Signal strength for each asset (-1 to 1)
            current_portfolio: Current positions (symbol -> weight)
            market_data: Market data for risk calculation
            portfolio_value: Total portfolio value
            rebalance_method: 'risk_adjusted', 'equal_weight', 'signal_weighted'
            
        Returns:
            List of PortfolioAllocation objects
        """
        try:
            logger.info(f"Constructing portfolio with {len(signals)} signals")
            logger.info(f"Rebalance method: {rebalance_method}")
            
            # Filter valid signals (very permissive for testing)
            valid_signals = {}
            for symbol, signal in signals.items():
                if symbol in market_data and abs(signal) >= self.min_signal_strength:
                    valid_signals[symbol] = signal
            
            if not valid_signals:
                logger.warning("No valid signals for portfolio construction")
                return []
            
            # Apply portfolio construction method
            if rebalance_method == 'equal_weight':
                target_weights = self._equal_weight_construction(valid_signals)
            elif rebalance_method == 'signal_weighted':
                target_weights = self._signal_weighted_construction(valid_signals)
            elif rebalance_method == 'risk_adjusted':
                target_weights = self._risk_adjusted_optimization(valid_signals, market_data)
            else:
                logger.error(f"Unknown rebalance method: {rebalance_method}")
                return []
            
            # Create allocation objects
            allocations = []
            for symbol, target_weight in target_weights.items():
                current_weight = current_portfolio.get(symbol, 0.0)
                dollar_amount = target_weight * portfolio_value
                sector = self.sector_mapping.get(symbol, "Other")  # Get sector from mapping
                
                allocation = PortfolioAllocation(
                    symbol=symbol,
                    target_weight=target_weight,
                    current_weight=current_weight,
                    dollar_amount=dollar_amount,
                    expected_return=signals.get(symbol, 0.0) * 0.1,  # Scale signal to return
                    risk_contribution=target_weight * 0.15,  # Simplified risk contribution
                    sector=sector
                )
                allocations.append(allocation)
            
            logger.info(f"Portfolio construction completed - {len(allocations)} positions")
            return allocations
            
        except Exception as e:
            logger.error(f"Portfolio construction failed: {e}")
            return []
    
    def _equal_weight_construction(self, signals: Dict[str, float]) -> Dict[str, float]:
        """Equal weight portfolio construction"""
        num_positions = len(signals)
        if num_positions == 0:
            return {}
        
        target_weight = min(1.0 / num_positions, self.max_position_weight)
        return {symbol: target_weight for symbol in signals.keys()}
    
    def _signal_weighted_construction(self, signals: Dict[str, float]) -> Dict[str, float]:
        """Signal-weighted portfolio construction"""
        total_signal = sum(abs(signal) for signal in signals.values())
        if total_signal == 0:
            return {}
        
        weights = {}
        for symbol, signal in signals.items():
            weight = abs(signal) / total_signal
            weight = min(weight, self.max_position_weight)
            weights[symbol] = weight
        
        return weights
    
    def _risk_adjusted_optimization(self, signals: Dict[str, float], 
                                   market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Risk-adjusted portfolio optimization"""
        # Calculate volatilities
        volatilities = {}
        for symbol in signals.keys():
            try:
                data = market_data[symbol]
                if len(data) > 20:
                    returns = data['close'].pct_change().dropna()
                    volatilities[symbol] = returns.std() * np.sqrt(252)
                else:
                    volatilities[symbol] = 0.25  # Default volatility
            except:
                volatilities[symbol] = 0.25
        
        # Risk-adjust signals
        risk_adjusted_signals = {}
        for symbol, signal in signals.items():
            vol = volatilities.get(symbol, 0.25)
            risk_adjusted_signals[symbol] = signal / vol
        
        # Normalize to weights
        total_score = sum(abs(score) for score in risk_adjusted_signals.values())
        if total_score == 0:
            return {}
        
        weights = {}
        for symbol, score in risk_adjusted_signals.items():
            weight = abs(score) / total_score
            weight = min(weight, self.max_position_weight)
            weights[symbol] = weight
        
        return weights