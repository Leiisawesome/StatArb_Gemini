#!/usr/bin/env python3
"""
Sentiment Analysis
Phase 3: Advanced Analytics & Optimization - Batch 2
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Market sentiment analysis and indicators"""
    
    def __init__(self):
        self.sentiment_indicators = {}
        self.sentiment_history = []
        
        logger.info("Initialized SentimentAnalyzer")
    
    def calculate_fear_greed_index(self, data: pd.DataFrame) -> Dict:
        """Calculate Fear & Greed Index components"""
        
        if len(data) < 20:
            logger.warning(f"Insufficient data for Fear & Greed Index: {len(data)} points")
            return {}
        
        # Calculate components
        components = {}
        
        # 1. Momentum (25% weight)
        momentum = self._calculate_momentum_component(data)
        components['momentum'] = momentum
        
        # 2. Market Volatility (25% weight)
        volatility = self._calculate_volatility_component(data)
        components['volatility'] = volatility
        
        # 3. Market Volume (25% weight)
        volume = self._calculate_volume_component(data)
        components['volume'] = volume
        
        # 4. Put/Call Ratio (25% weight) - Simplified version
        put_call = self._calculate_put_call_component(data)
        components['put_call_ratio'] = put_call
        
        # Calculate composite index
        weights = {'momentum': 0.25, 'volatility': 0.25, 'volume': 0.25, 'put_call_ratio': 0.25}
        composite_score = sum(components[key] * weights[key] for key in weights.keys())
        
        # Classify sentiment
        sentiment_class = self._classify_sentiment(composite_score)
        
        results = {
            'components': components,
            'composite_score': composite_score,
            'sentiment_class': sentiment_class,
            'fear_greed_index': composite_score,
            'calculation_date': datetime.now().isoformat()
        }
        
        # Store sentiment history
        self.sentiment_history.append({
            'timestamp': datetime.now(),
            'fear_greed_index': composite_score,
            'sentiment_class': sentiment_class,
            'components': components
        })
        
        logger.info(f"Fear & Greed Index calculated: {composite_score:.2f} ({sentiment_class})")
        return results
    
    def _calculate_momentum_component(self, data: pd.DataFrame) -> float:
        """Calculate momentum component (0-100 scale)"""
        
        if 'close' not in data.columns:
            return 50.0
        
        # Calculate 12-month momentum
        returns_12m = data['close'].pct_change(252).iloc[-1] if len(data) >= 252 else data['close'].pct_change().iloc[-1]
        
        # Convert to 0-100 scale (assuming normal distribution)
        # Positive momentum = higher score (greed)
        momentum_score = min(100, max(0, 50 + returns_12m * 100))
        
        return momentum_score
    
    def _calculate_volatility_component(self, data: pd.DataFrame) -> float:
        """Calculate volatility component (0-100 scale)"""
        
        if 'close' not in data.columns:
            return 50.0
        
        # Calculate 30-day volatility
        returns = data['close'].pct_change().dropna()
        if len(returns) < 30:
            return 50.0
        
        volatility_30d = returns.rolling(30).std().iloc[-1]
        
        # Convert to 0-100 scale
        # High volatility = lower score (fear)
        volatility_score = max(0, 100 - volatility_30d * 1000)  # Scale factor
        
        return volatility_score
    
    def _calculate_volume_component(self, data: pd.DataFrame) -> float:
        """Calculate volume component (0-100 scale)"""
        
        if 'volume' not in data.columns:
            return 50.0
        
        # Calculate volume relative to moving average
        volume_ma = data['volume'].rolling(30).mean()
        if len(volume_ma) < 1 or volume_ma.iloc[-1] == 0:
            return 50.0
        
        volume_ratio = data['volume'].iloc[-1] / volume_ma.iloc[-1]
        
        # Convert to 0-100 scale
        # High volume = higher score (greed)
        volume_score = min(100, max(0, 50 + (volume_ratio - 1) * 50))
        
        return volume_score
    
    def _calculate_put_call_component(self, data: pd.DataFrame) -> float:
        """Calculate put/call ratio component (0-100 scale)"""
        
        # Simplified version - use price action as proxy
        if 'close' not in data.columns:
            return 50.0
        
        # Calculate recent price action
        recent_returns = data['close'].pct_change(5).iloc[-5:].dropna()
        if len(recent_returns) < 3:
            return 50.0
        
        # Negative returns suggest fear (higher put activity)
        avg_recent_return = recent_returns.mean()
        
        # Convert to 0-100 scale
        # Negative returns = lower score (fear)
        put_call_score = max(0, 100 + avg_recent_return * 100)
        
        return put_call_score
    
    def _classify_sentiment(self, score: float) -> str:
        """Classify sentiment based on score"""
        
        if score >= 80:
            return 'Extreme Greed'
        elif score >= 60:
            return 'Greed'
        elif score >= 40:
            return 'Neutral'
        elif score >= 20:
            return 'Fear'
        else:
            return 'Extreme Fear'
    
    def calculate_vix_style_index(self, data: pd.DataFrame, window: int = 30) -> pd.Series:
        """Calculate VIX-style volatility index"""
        
        if len(data) < window:
            logger.warning(f"Insufficient data for VIX calculation: {len(data)} < {window}")
            return pd.Series()
        
        # Calculate rolling volatility
        returns = data['close'].pct_change().dropna()
        rolling_vol = returns.rolling(window=window).std()
        
        # Annualize volatility (multiply by sqrt(252))
        vix_style = rolling_vol * np.sqrt(252) * 100  # Convert to percentage
        
        logger.info(f"VIX-style index calculated with window {window}")
        return vix_style
    
    def get_sentiment_summary(self) -> Dict:
        """Get sentiment analysis summary"""
        return {
            'sentiment_history_count': len(self.sentiment_history),
            'current_sentiment': self.sentiment_history[-1]['sentiment_class'] if self.sentiment_history else 'Unknown',
            'available_indicators': ['fear_greed_index', 'vix_style_index']
        }
