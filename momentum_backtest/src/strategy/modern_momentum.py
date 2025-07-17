"""
Modern Multi-Timeframe Momentum Strategy

Optimized for your specific case:
- 4 tech stocks (TSLA, NVDA, VNET, GDS) 
- $100K capital
- Daily rebalancing
- Based on Barroso & Santa-Clara (2015) + modern enhancements

Key Features:
1. Multi-scale momentum (3/10/20 days)
2. Volatility scaling for risk management
3. Volume-weighted signals
4. Transaction cost awareness
5. Dynamic position sizing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ModernMomentumStrategy:
    """
    Modern momentum strategy incorporating latest research
    Optimized for tech stocks and high-frequency rebalancing
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with modern momentum parameters"""
        self.config = config
        self.strategy_config = config.get('strategy', {})
        
        # Multi-timeframe momentum (modern approach)
        self.short_momentum = self.strategy_config.get('short_momentum_days', 3)
        self.medium_momentum = self.strategy_config.get('medium_momentum_days', 10) 
        self.long_momentum = self.strategy_config.get('long_momentum_days', 20)
        
        # Volatility scaling (Barroso & Santa-Clara 2015)
        self.vol_target = self.strategy_config.get('vol_target', 0.15)
        self.vol_scaling = self.strategy_config.get('vol_scaling', True)
        self.vol_lookback = self.strategy_config.get('vol_lookback', 15)
        
        # Volume weighting and transaction costs
        self.volume_weight = self.strategy_config.get('volume_weight', True)
        self.transaction_costs = self.strategy_config.get('transaction_costs', 0.001)
        self.min_momentum_threshold = self.strategy_config.get('min_momentum_threshold', 0.01)
        
        # Position sizing
        self.top_n_long = self.strategy_config.get('top_n_long', 2)
        self.top_n_short = self.strategy_config.get('top_n_short', 1)
        
        # Risk controls
        self.max_position_size = self.strategy_config.get('max_position_size', 1.0)  # Max position weight
        self.volatility_filter = self.strategy_config.get('volatility_filter', True)
        self.max_volatility = self.strategy_config.get('max_volatility', 0.5)  # 50% daily vol threshold
        
        logger.info(f"ModernMomentumStrategy initialized: {self.short_momentum}/{self.medium_momentum}/{self.long_momentum} day momentum")
        logger.info(f"Vol target: {self.vol_target:.1%}, Vol scaling: {self.vol_scaling}")
    
    def generate_signals(self, data: pd.DataFrame, current_date: pd.Timestamp) -> Dict[str, str]:
        """
        Generate modern momentum signals with multi-timeframe analysis
        """
        try:
            scores_df = self.calculate_momentum_scores(data, current_date)
            
            if scores_df.empty:
                logger.warning(f"No momentum scores calculated for {current_date}")
                return {}
            
            # Filter for sufficient data and significant momentum
            valid_scores = scores_df[
                (scores_df['has_sufficient_data']) & 
                (scores_df['volume_ok']) & 
                (abs(scores_df['final_score']) > self.min_momentum_threshold)
            ].copy()
            
            if valid_scores.empty:
                logger.debug(f"No valid momentum signals for {current_date}")
                return {}
            
            # Rank by final momentum score
            valid_scores = valid_scores.sort_values('final_score', ascending=False)
            
            signals = {}
            
            # Long positions (positive momentum)
            positive_momentum = valid_scores[valid_scores['final_score'] > 0]
            n_long = min(self.top_n_long, len(positive_momentum))
            if n_long > 0:
                long_symbols = positive_momentum.head(n_long).index
                for symbol in long_symbols:
                    signals[symbol] = 'LONG'
            
            # Short positions (negative momentum)
            negative_momentum = valid_scores[valid_scores['final_score'] < 0]
            n_short = min(self.top_n_short, len(negative_momentum))
            if n_short > 0:
                short_symbols = negative_momentum.tail(n_short).index
                for symbol in short_symbols:
                    signals[symbol] = 'SHORT'
            
            if signals:
                logger.debug(f"Generated {len(signals)} signals for {current_date}: {signals}")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating momentum signals for {current_date}: {e}")
            return {}
    
    def calculate_momentum_scores(self, data: pd.DataFrame, current_date: pd.Timestamp) -> pd.DataFrame:
        """
        Calculate multi-timeframe momentum scores with modern enhancements
        """
        scores = []
        
        # Get historical data up to current date
        historical_data = data[data.index.get_level_values('date') <= current_date]
        
        if historical_data.empty:
            return pd.DataFrame()
        
        symbols = historical_data.index.get_level_values('symbol').unique()
        
        for symbol in symbols:
            try:
                symbol_data = historical_data.xs(symbol, level='symbol')
                
                # Initialize score record
                score_record = {
                    'symbol': symbol,
                    'has_sufficient_data': False,
                    'volume_ok': False,
                    'data_points': len(symbol_data),
                    'short_momentum': np.nan,
                    'medium_momentum': np.nan,
                    'long_momentum': np.nan,
                    'realized_vol': np.nan,
                    'vol_scalar': 1.0,
                    'volume_weight': 1.0,
                    'combined_momentum': np.nan,
                    'final_score': np.nan
                }
                
                # Check minimum data requirement
                if len(symbol_data) < max(self.long_momentum, self.vol_lookback):
                    scores.append(score_record)
                    continue
                
                score_record['has_sufficient_data'] = True
                
                # Volume validation
                recent_volume = symbol_data['volume'].tail(5).mean()
                if recent_volume <= 0:
                    scores.append(score_record)
                    continue
                
                score_record['volume_ok'] = True
                
                # Calculate multi-timeframe momentum
                short_mom = self._calculate_momentum(symbol_data, self.short_momentum)
                medium_mom = self._calculate_momentum(symbol_data, self.medium_momentum)
                long_mom = self._calculate_momentum(symbol_data, self.long_momentum)
                
                score_record['short_momentum'] = short_mom
                score_record['medium_momentum'] = medium_mom
                score_record['long_momentum'] = long_mom
                
                # Skip if any momentum calculation failed
                if any(np.isnan(x) for x in [short_mom, medium_mom, long_mom]):
                    scores.append(score_record)
                    continue
                
                # Volume weighting (recent volume activity)
                if self.volume_weight:
                    recent_vol = symbol_data['volume'].tail(self.medium_momentum).mean()
                    avg_vol = symbol_data['volume'].mean()
                    volume_weight = min(recent_vol / max(avg_vol, 1), 2.0)  # Cap at 2x
                    score_record['volume_weight'] = volume_weight
                else:
                    volume_weight = 1.0
                
                # Combine momentum scores (weighted average)
                combined_momentum = (
                    0.5 * short_mom +    # Recent momentum (highest weight)
                    0.3 * medium_mom +   # Intermediate momentum 
                    0.2 * long_mom       # Long-term momentum (trend confirmation)
                ) * volume_weight
                
                score_record['combined_momentum'] = combined_momentum
                
                # Volatility scaling (Barroso & Santa-Clara 2015)
                if self.vol_scaling:
                    realized_vol = self._calculate_realized_volatility(symbol_data)
                    vol_scalar = self.vol_target / max(realized_vol, 0.05)  # Min vol floor
                    vol_scalar = min(vol_scalar, 3.0)  # Cap scaling at 3x
                    
                    score_record['realized_vol'] = realized_vol
                    score_record['vol_scalar'] = vol_scalar
                    
                    final_score = combined_momentum * vol_scalar
                else:
                    final_score = combined_momentum
                
                score_record['final_score'] = final_score
                scores.append(score_record)
                
            except Exception as e:
                logger.warning(f"Error calculating momentum for {symbol}: {e}")
                continue
        
        if not scores:
            return pd.DataFrame()
        
        # Convert to DataFrame
        scores_df = pd.DataFrame(scores)
        scores_df.set_index('symbol', inplace=True)
        
        return scores_df
    
    def _calculate_momentum(self, symbol_data: pd.DataFrame, window: int) -> float:
        """
        Calculate momentum score using log returns (better statistical properties)
        """
        try:
            if len(symbol_data) < window + 1:
                return np.nan
            
            # Use log returns for momentum calculation
            prices = symbol_data['close'].tail(window + 1)
            
            if prices.iloc[0] <= 0 or prices.iloc[-1] <= 0:
                return np.nan
            
            # Log momentum (more stable than simple returns)
            log_momentum = np.log(prices.iloc[-1] / prices.iloc[0])
            
            return log_momentum
            
        except Exception as e:
            logger.warning(f"Error in momentum calculation: {e}")
            return np.nan
    
    def _calculate_realized_volatility(self, symbol_data: pd.DataFrame) -> float:
        """
        Calculate realized volatility for risk scaling
        """
        try:
            if len(symbol_data) < self.vol_lookback:
                return self.vol_target  # Use target as default
            
            # Calculate log returns
            returns = np.log(symbol_data['close'] / symbol_data['close'].shift(1)).dropna()
            
            if len(returns) < 2:
                return self.vol_target
            
            # Recent volatility
            recent_returns = returns.tail(self.vol_lookback)
            realized_vol = recent_returns.std() * np.sqrt(252)  # Annualized
            
            # Floor volatility to prevent extreme scaling
            return max(realized_vol, 0.05)
            
        except Exception as e:
            logger.warning(f"Error in volatility calculation: {e}")
            return self.vol_target
    
    def get_target_positions(self, signals: Dict[str, str], current_date: pd.Timestamp) -> Dict[str, float]:
        """
        Convert signals to target position weights with risk controls
        
        Args:
            signals: Dict mapping symbols to signal strings ('LONG', 'SHORT', 'HOLD')
            current_date: Current date
            
        Returns:
            Dict mapping symbols to target weights (0.0 to 1.0)
        """
        target_positions = {}
        
        # Count active signals
        long_signals = [symbol for symbol, signal in signals.items() if signal == 'LONG']
        short_signals = [symbol for symbol, signal in signals.items() if signal == 'SHORT']
        
        # Use our internal max position size (more conservative than config default)
        max_position_size = min(self.max_position_size, 
                               self.config.get('risk_management', {}).get('max_position_size', 0.4))
        
        # For long-only strategy, allocate conservatively among long signals
        if long_signals:
            # More conservative position sizing - don't use full 100% allocation
            total_allocation = min(0.8, 1.0)  # Use max 80% of capital
            weight_per_position = min(max_position_size, total_allocation / len(long_signals))
            
            for symbol in long_signals:
                target_positions[symbol] = weight_per_position
        
        # For short signals (if strategy allows shorts)
        if short_signals and not self.config.get('long_only', True):
            total_short_allocation = min(0.3, 1.0)  # Conservative short allocation
            weight_per_position = min(max_position_size, total_short_allocation / len(short_signals))
            for symbol in short_signals:
                target_positions[symbol] = -weight_per_position
        
        return target_positions

    def calculate_scores(self, data: pd.DataFrame, current_date: pd.Timestamp) -> pd.DataFrame:
        """
        Compatibility method for existing backtest infrastructure
        """
        return self.calculate_momentum_scores(data, current_date)

# Export for use in backtest
__all__ = ['ModernMomentumStrategy']
