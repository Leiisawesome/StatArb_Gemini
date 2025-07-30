#!/usr/bin/env python3
"""
Dynamic Asset Allocation
Phase 3: Advanced Analytics & Optimization - Batch 3
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class DynamicAllocation:
    """Dynamic asset allocation strategies"""
    
    def __init__(self):
        self.allocation_history = []
        self.rebalancing_dates = []
        self.performance_tracking = {}
        
        logger.info("Initialized DynamicAllocation")
    
    def momentum_allocation(self, data: pd.DataFrame, lookback_period: int = 60,
                          rebalancing_frequency: str = 'monthly') -> Dict:
        """Momentum-based dynamic allocation"""
        
        if len(data) < lookback_period:
            logger.warning(f"Insufficient data for momentum allocation: {len(data)} < {lookback_period}")
            return {}
        
        try:
            # Calculate returns
            returns = data.pct_change().dropna()
            
            # Calculate momentum (rolling returns)
            momentum = returns.rolling(window=lookback_period).sum()
            
            # Get latest momentum values
            latest_momentum = momentum.iloc[-1]
            
            # Select top performing assets
            top_assets = latest_momentum.nlargest(min(3, len(latest_momentum)))
            
            # Calculate weights based on momentum
            weights = top_assets / top_assets.sum()
            
            # Fill remaining assets with zero weights
            all_weights = pd.Series(0, index=data.columns)
            all_weights[top_assets.index] = weights
            
            # Calculate portfolio metrics
            portfolio_return = np.sum(all_weights * latest_momentum)
            portfolio_volatility = np.sqrt(np.dot(all_weights.T, np.dot(returns.cov() * 252, all_weights)))
            sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            results = {
                'weights': all_weights.to_dict(),
                'momentum_scores': latest_momentum.to_dict(),
                'selected_assets': list(top_assets.index),
                'portfolio_return': portfolio_return,
                'portfolio_volatility': portfolio_volatility,
                'sharpe_ratio': sharpe_ratio,
                'strategy': 'momentum',
                'lookback_period': lookback_period,
                'rebalancing_frequency': rebalancing_frequency,
                'allocation_date': datetime.now().isoformat()
            }
            
            # Store allocation history
            self.allocation_history.append({
                'timestamp': datetime.now(),
                'strategy': 'momentum',
                'weights': all_weights.to_dict(),
                'portfolio_return': portfolio_return,
                'sharpe_ratio': sharpe_ratio
            })
            
            logger.info(f"Momentum allocation completed: {len(top_assets)} assets selected")
            return results
            
        except Exception as e:
            logger.error(f"Momentum allocation failed: {e}")
            return {}
    
    def volatility_allocation(self, data: pd.DataFrame, target_volatility: float = 0.15,
                            rebalancing_frequency: str = 'monthly') -> Dict:
        """Volatility-based dynamic allocation"""
        
        if len(data) < 30:
            logger.warning(f"Insufficient data for volatility allocation: {len(data)} < 30")
            return {}
        
        try:
            # Calculate returns
            returns = data.pct_change().dropna()
            
            # Calculate rolling volatility
            rolling_volatility = returns.rolling(window=30).std() * np.sqrt(252)
            
            # Get latest volatility values
            latest_volatility = rolling_volatility.iloc[-1]
            
            # Calculate inverse volatility weights
            inverse_volatility = 1 / latest_volatility
            weights = inverse_volatility / inverse_volatility.sum()
            
            # Scale weights to achieve target volatility
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
            
            if portfolio_volatility > 0:
                scale_factor = target_volatility / portfolio_volatility
                weights = weights * scale_factor
                weights = weights / weights.sum()  # Renormalize
            
            # Calculate portfolio metrics
            expected_returns = returns.mean() * 252
            portfolio_return = np.sum(weights * expected_returns)
            final_volatility = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
            sharpe_ratio = portfolio_return / final_volatility if final_volatility > 0 else 0
            
            results = {
                'weights': weights.to_dict(),
                'volatility_scores': latest_volatility.to_dict(),
                'portfolio_return': portfolio_return,
                'portfolio_volatility': final_volatility,
                'target_volatility': target_volatility,
                'sharpe_ratio': sharpe_ratio,
                'strategy': 'volatility',
                'rebalancing_frequency': rebalancing_frequency,
                'allocation_date': datetime.now().isoformat()
            }
            
            # Store allocation history
            self.allocation_history.append({
                'timestamp': datetime.now(),
                'strategy': 'volatility',
                'weights': weights.to_dict(),
                'portfolio_return': portfolio_return,
                'sharpe_ratio': sharpe_ratio
            })
            
            logger.info(f"Volatility allocation completed: target vol {target_volatility:.2%}, actual {final_volatility:.2%}")
            return results
            
        except Exception as e:
            logger.error(f"Volatility allocation failed: {e}")
            return {}
    
    def regime_based_allocation(self, data: pd.DataFrame, regime_signal: str,
                              regime_weights: Dict[str, Dict[str, float]]) -> Dict:
        """Regime-based dynamic allocation"""
        
        if regime_signal not in regime_weights:
            logger.error(f"Regime signal '{regime_signal}' not found in regime weights")
            return {}
        
        try:
            # Get weights for current regime
            current_weights = regime_weights[regime_signal]
            
            # Ensure all assets in data have weights
            all_weights = pd.Series(0, index=data.columns)
            for asset, weight in current_weights.items():
                if asset in data.columns:
                    all_weights[asset] = weight
            
            # Normalize weights
            all_weights = all_weights / all_weights.sum()
            
            # Calculate portfolio metrics
            returns = data.pct_change().dropna()
            expected_returns = returns.mean() * 252
            portfolio_return = np.sum(all_weights * expected_returns)
            portfolio_volatility = np.sqrt(np.dot(all_weights.T, np.dot(returns.cov() * 252, all_weights)))
            sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            results = {
                'weights': all_weights.to_dict(),
                'regime_signal': regime_signal,
                'portfolio_return': portfolio_return,
                'portfolio_volatility': portfolio_volatility,
                'sharpe_ratio': sharpe_ratio,
                'strategy': 'regime_based',
                'allocation_date': datetime.now().isoformat()
            }
            
            # Store allocation history
            self.allocation_history.append({
                'timestamp': datetime.now(),
                'strategy': 'regime_based',
                'weights': all_weights.to_dict(),
                'portfolio_return': portfolio_return,
                'sharpe_ratio': sharpe_ratio,
                'regime_signal': regime_signal
            })
            
            logger.info(f"Regime-based allocation completed: regime '{regime_signal}'")
            return results
            
        except Exception as e:
            logger.error(f"Regime-based allocation failed: {e}")
            return {}
    
    def tactical_asset_allocation(self, data: pd.DataFrame, 
                                asset_classes: Dict[str, List[str]],
                                base_weights: Dict[str, float],
                                tactical_overlay: Dict[str, float]) -> Dict:
        """Tactical asset allocation with overlay"""
        
        try:
            # Start with base weights
            all_weights = pd.Series(0, index=data.columns)
            
            # Apply base weights by asset class
            for asset_class, assets in asset_classes.items():
                if asset_class in base_weights:
                    base_weight = base_weights[asset_class]
                    n_assets = len([a for a in assets if a in data.columns])
                    
                    if n_assets > 0:
                        weight_per_asset = base_weight / n_assets
                        for asset in assets:
                            if asset in data.columns:
                                all_weights[asset] = weight_per_asset
            
            # Apply tactical overlay
            for asset, overlay in tactical_overlay.items():
                if asset in data.columns:
                    all_weights[asset] += overlay
            
            # Ensure non-negative weights and normalize
            all_weights = np.maximum(all_weights, 0)
            all_weights = all_weights / all_weights.sum()
            
            # Calculate portfolio metrics
            returns = data.pct_change().dropna()
            expected_returns = returns.mean() * 252
            portfolio_return = np.sum(all_weights * expected_returns)
            portfolio_volatility = np.sqrt(np.dot(all_weights.T, np.dot(returns.cov() * 252, all_weights)))
            sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            results = {
                'weights': all_weights.to_dict(),
                'base_weights': base_weights,
                'tactical_overlay': tactical_overlay,
                'portfolio_return': portfolio_return,
                'portfolio_volatility': portfolio_volatility,
                'sharpe_ratio': sharpe_ratio,
                'strategy': 'tactical',
                'allocation_date': datetime.now().isoformat()
            }
            
            # Store allocation history
            self.allocation_history.append({
                'timestamp': datetime.now(),
                'strategy': 'tactical',
                'weights': all_weights.to_dict(),
                'portfolio_return': portfolio_return,
                'sharpe_ratio': sharpe_ratio
            })
            
            logger.info(f"Tactical allocation completed: {len(tactical_overlay)} tactical overlays")
            return results
            
        except Exception as e:
            logger.error(f"Tactical allocation failed: {e}")
            return {}
    
    def get_allocation_summary(self) -> Dict:
        """Get dynamic allocation summary"""
        if not self.allocation_history:
            return {'total_allocations': 0}
        
        strategies_used = list(set(h['strategy'] for h in self.allocation_history))
        avg_sharpe = np.mean([h['sharpe_ratio'] for h in self.allocation_history])
        
        return {
            'total_allocations': len(self.allocation_history),
            'strategies_used': strategies_used,
            'average_sharpe_ratio': avg_sharpe,
            'latest_allocation': self.allocation_history[-1]['strategy'] if self.allocation_history else None
        }
