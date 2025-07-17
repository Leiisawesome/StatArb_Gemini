"""
Data validation and preprocessing for momentum backtesting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import sys
import os

# Add parent directory to path to import from new_structure
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'new_structure'))

try:
    from signal_generation.indicators.technical_indicators import TechnicalIndicatorEngine
    from signal_generation.indicators.feature_engineering import FeatureEngineeringPipeline
except ImportError as e:
    logging.warning(f"Could not import from new_structure: {e}")
    TechnicalIndicatorEngine = None
    FeatureEngineeringPipeline = None

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Validates and preprocesses data for momentum backtesting
    """
    
    def __init__(self, config: Dict):
        self.config = config.get('data', {})
        self.max_price_gap = self.config.get('max_price_gap', 0.15)
        self.min_price = self.config.get('min_price', 5.0)
        self.max_price = self.config.get('max_price', 1000.0)
        
        # Initialize technical indicators engine if available
        self.indicators_engine = None
        if TechnicalIndicatorEngine:
            self.indicators_engine = TechnicalIndicatorEngine()
    
    def validate_and_clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean price data
        
        Args:
            data: DataFrame with MultiIndex (date, symbol) and OHLCV columns
            
        Returns:
            Cleaned DataFrame
        """
        logger.info("Starting data validation and cleaning...")
        
        initial_records = len(data)
        
        # Remove rows with missing critical data
        data = data.dropna(subset=['close', 'volume'])
        
        # Price filters
        data = data[
            (data['close'] >= self.min_price) & 
            (data['close'] <= self.max_price) &
            (data['volume'] > 0)
        ]
        
        # Remove extreme price gaps
        data = self._remove_price_gaps(data)
        
        # Forward fill minor missing data
        data = data.groupby(level='symbol').fillna(method='ffill')
        
        final_records = len(data)
        logger.info(f"Data cleaning completed: {initial_records} -> {final_records} records")
        
        return data
    
    def _remove_price_gaps(self, data: pd.DataFrame) -> pd.DataFrame:
        """Remove data points with extreme price gaps"""
        cleaned_data = []
        
        for symbol in data.index.get_level_values('symbol').unique():
            symbol_data = data.xs(symbol, level='symbol').copy()
            
            # Calculate daily returns
            symbol_data['returns'] = symbol_data['close'].pct_change()
            
            # Remove extreme gaps
            extreme_gaps = abs(symbol_data['returns']) > self.max_price_gap
            symbol_data = symbol_data[~extreme_gaps]
            
            # Add symbol back to index
            symbol_data['symbol'] = symbol
            symbol_data = symbol_data.reset_index().set_index(['date', 'symbol'])
            
            cleaned_data.append(symbol_data.drop('returns', axis=1))
        
        return pd.concat(cleaned_data).sort_index()
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for each symbol
        
        Args:
            data: Price data with MultiIndex (date, symbol)
            
        Returns:
            DataFrame with technical indicators added
        """
        if not self.indicators_engine:
            logger.warning("Technical indicators engine not available")
            return data
        
        logger.info("Calculating technical indicators...")
        
        indicators_data = []
        
        for symbol in data.index.get_level_values('symbol').unique():
            symbol_data = data.xs(symbol, level='symbol').copy()
            
            try:
                # Calculate indicators using new_structure engine
                indicators_result = self.indicators_engine.calculate_all_indicators(
                    symbol_data, symbol=symbol
                )
                
                # Convert indicators to DataFrame
                indicators_df = pd.DataFrame([indicators_result.indicators], 
                                           index=[symbol_data.index[-1]])
                
                # Broadcast to all dates for this symbol (simplified approach)
                # In production, you'd calculate rolling indicators
                for date in symbol_data.index:
                    indicators_df_dated = indicators_df.copy()
                    indicators_df_dated.index = [date]
                    indicators_df_dated['symbol'] = symbol
                    indicators_df_dated = indicators_df_dated.reset_index().set_index(['date', 'symbol'])
                    indicators_data.append(indicators_df_dated)
                    
            except Exception as e:
                logger.warning(f"Error calculating indicators for {symbol}: {e}")
                continue
        
        if indicators_data:
            indicators_combined = pd.concat(indicators_data)
            # Merge with original data
            data = data.join(indicators_combined, how='left')
        
        logger.info("Technical indicators calculation completed")
        return data
    
    def prepare_features_for_momentum(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare momentum-specific features
        
        Args:
            data: Price data with technical indicators
            
        Returns:
            DataFrame with momentum features
        """
        logger.info("Preparing momentum features...")
        
        momentum_data = []
        
        for symbol in data.index.get_level_values('symbol').unique():
            symbol_data = data.xs(symbol, level='symbol').copy()
            
            # Core momentum features
            symbol_data = self._calculate_momentum_features(symbol_data)
            
            # Add symbol back to index
            symbol_data['symbol'] = symbol
            symbol_data = symbol_data.reset_index().set_index(['date', 'symbol'])
            
            momentum_data.append(symbol_data)
        
        result = pd.concat(momentum_data).sort_index()
        
        logger.info("Momentum features preparation completed")
        return result
    
    def _calculate_momentum_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate momentum features for a single symbol"""
        
        # Price momentum (various lookback periods)
        for period in [21, 63, 126, 252]:  # 1M, 3M, 6M, 12M
            data[f'momentum_{period}d'] = data['close'].pct_change(period)
            data[f'cumulative_return_{period}d'] = (1 + data['close'].pct_change()).rolling(period).apply(
                lambda x: x.prod() - 1, raw=False
            )
        
        # Skip period momentum (Jegadeesh & Titman standard)
        data['momentum_12_1'] = data['close'].pct_change(252) - data['close'].pct_change(21)
        
        # Volatility-adjusted momentum
        for period in [63, 126]:
            returns = data['close'].pct_change()
            vol = returns.rolling(period).std()
            data[f'vol_adjusted_momentum_{period}d'] = (
                data[f'momentum_{period}d'] / vol.shift(1)
            ).fillna(0)
        
        # Moving average trends
        data['sma_20'] = data['close'].rolling(20).mean()
        data['sma_50'] = data['close'].rolling(50).mean()
        data['sma_200'] = data['close'].rolling(200).mean()
        
        # Price relative to moving averages
        data['price_to_sma_20'] = data['close'] / data['sma_20'] - 1
        data['price_to_sma_50'] = data['close'] / data['sma_50'] - 1
        data['price_to_sma_200'] = data['close'] / data['sma_200'] - 1
        
        # Moving average slopes (trend strength)
        data['sma_20_slope'] = data['sma_20'].pct_change(5)
        data['sma_50_slope'] = data['sma_50'].pct_change(10)
        
        # Volume momentum
        data['volume_ma_20'] = data['volume'].rolling(20).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma_20']
        
        # Price-volume momentum
        data['pv_momentum'] = data['momentum_21d'] * np.log(data['volume_ratio'])
        
        return data
    
    def get_data_summary(self, data: pd.DataFrame) -> Dict:
        """Generate summary statistics for the dataset"""
        symbols = data.index.get_level_values('symbol').unique()
        dates = data.index.get_level_values('date').unique()
        
        summary = {
            'symbols_count': len(symbols),
            'trading_days': len(dates),
            'date_range': (dates.min(), dates.max()),
            'total_records': len(data),
            'columns': list(data.columns),
            'missing_data_pct': (data.isnull().sum() / len(data) * 100).to_dict()
        }
        
        # Per-symbol statistics
        symbol_stats = {}
        for symbol in symbols[:5]:  # First 5 symbols for summary
            symbol_data = data.xs(symbol, level='symbol')
            symbol_stats[symbol] = {
                'records': len(symbol_data),
                'avg_price': symbol_data['close'].mean(),
                'avg_volume': symbol_data['volume'].mean(),
                'volatility': symbol_data['close'].pct_change().std() * np.sqrt(252)
            }
        
        summary['symbol_statistics'] = symbol_stats
        
        return summary
