#!/usr/bin/env python3
"""
Alternative Data Integration System
Integrates news sentiment, options flow, insider trading, and social media data for enhanced pair selection
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Union
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import warnings
import requests
import json
import re
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import yfinance as yf
warnings.filterwarnings('ignore')

class SentimentType(Enum):
    """Types of sentiment analysis"""
    NEWS = "News"
    SOCIAL_MEDIA = "Social Media"
    ANALYST_REPORTS = "Analyst Reports"
    EARNINGS_CALLS = "Earnings Calls"
    SEC_FILINGS = "SEC Filings"

class SentimentPolarity(Enum):
    """Sentiment polarity levels"""
    VERY_NEGATIVE = "Very Negative"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"
    POSITIVE = "Positive"
    VERY_POSITIVE = "Very Positive"

class OptionsFlowType(Enum):
    """Types of options flow signals"""
    UNUSUAL_VOLUME = "Unusual Volume"
    LARGE_BLOCK = "Large Block"
    SWEEP = "Sweep"
    DARK_POOL = "Dark Pool"
    INSTITUTIONAL = "Institutional"

class InsiderActionType(Enum):
    """Types of insider trading actions"""
    BUY = "Buy"
    SELL = "Sell"
    OPTION_EXERCISE = "Option Exercise"
    GIFT = "Gift"
    INHERITANCE = "Inheritance"

@dataclass
class NewsArticle:
    """Individual news article data"""
    symbol: str
    title: str
    content: str
    source: str
    published_date: datetime
    sentiment_score: float  # -1 to 1
    sentiment_polarity: SentimentPolarity
    relevance_score: float  # 0 to 1
    impact_score: float  # 0 to 1
    keywords: List[str]
    
@dataclass
class SentimentSignal:
    """Aggregated sentiment signal"""
    symbol: str
    sentiment_type: SentimentType
    overall_sentiment: float  # -1 to 1
    sentiment_polarity: SentimentPolarity
    confidence: float  # 0 to 1
    article_count: int
    time_window: str  # e.g., "1h", "1d", "1w"
    momentum: float  # Change in sentiment
    volatility: float  # Sentiment volatility
    
@dataclass
class OptionsFlowSignal:
    """Options flow signal data"""
    symbol: str
    flow_type: OptionsFlowType
    strike_price: float
    expiration_date: datetime
    option_type: str  # "CALL" or "PUT"
    volume: int
    open_interest: int
    premium: float
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    unusual_activity_score: float  # 0 to 1
    directional_bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    
@dataclass
class InsiderTradingSignal:
    """Insider trading signal data"""
    symbol: str
    insider_name: str
    insider_title: str
    action_type: InsiderActionType
    transaction_date: datetime
    shares: int
    price: float
    value: float
    ownership_change: float  # Percentage change
    form_type: str  # "4", "5", etc.
    confidence: float  # 0 to 1
    significance_score: float  # 0 to 1
    
@dataclass
class AlternativeDataSignal:
    """Combined alternative data signal"""
    symbol: str
    timestamp: datetime
    sentiment_signal: Optional[SentimentSignal]
    options_signal: Optional[OptionsFlowSignal]
    insider_signal: Optional[InsiderTradingSignal]
    combined_score: float  # -1 to 1
    confidence: float  # 0 to 1
    signal_strength: float  # 0 to 1
    directional_bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    
@dataclass
class PairAlternativeAnalysis:
    """Alternative data analysis for a trading pair"""
    pair: Tuple[str, str]
    symbol1_signals: List[AlternativeDataSignal]
    symbol2_signals: List[AlternativeDataSignal]
    divergence_score: float  # How much signals diverge
    correlation_score: float  # How correlated the signals are
    pair_momentum: float  # Combined momentum signal
    risk_adjustment: float  # Position size adjustment
    confidence: float  # Overall confidence
    recommendation: str  # Trading recommendation
    
class NewsProvider:
    """Base class for news data providers"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_news(self, symbols: List[str], hours_back: int = 24) -> List[NewsArticle]:
        """Get news articles for symbols"""
        raise NotImplementedError

class MockNewsProvider(NewsProvider):
    """Mock news provider for testing"""
    
    def get_news(self, symbols: List[str], hours_back: int = 24) -> List[NewsArticle]:
        """Generate mock news articles"""
        
        articles = []
        
        # Sample news templates
        news_templates = [
            "{} reports strong quarterly earnings, beating expectations",
            "{} announces new product launch, shares rise",
            "{} faces regulatory scrutiny, stock under pressure",
            "{} CEO optimistic about future growth prospects",
            "{} partnership deal could boost revenue significantly",
            "{} warns of supply chain disruptions affecting margins",
            "{} dividend increase signals management confidence",
            "{} analyst upgrade drives institutional buying",
            "{} insider selling raises concerns about valuation",
            "{} technical breakthrough could disrupt industry"
        ]
        
        for symbol in symbols:
            # Generate 3-7 articles per symbol
            num_articles = np.random.randint(3, 8)
            
            for i in range(num_articles):
                # Random sentiment
                sentiment = np.random.normal(0, 0.3)  # Slightly positive bias
                sentiment = np.clip(sentiment, -1, 1)
                
                # Determine polarity
                if sentiment < -0.6:
                    polarity = SentimentPolarity.VERY_NEGATIVE
                elif sentiment < -0.2:
                    polarity = SentimentPolarity.NEGATIVE
                elif sentiment < 0.2:
                    polarity = SentimentPolarity.NEUTRAL
                elif sentiment < 0.6:
                    polarity = SentimentPolarity.POSITIVE
                else:
                    polarity = SentimentPolarity.VERY_POSITIVE
                
                # Random article details
                template = np.random.choice(news_templates)
                title = template.format(symbol)
                
                # Generate content
                content = f"Analysis of {symbol} shows {polarity.value.lower()} sentiment. " \
                         f"Market analysts are {'optimistic' if sentiment > 0 else 'cautious'} about prospects."
                
                # Random timing
                hours_ago = np.random.randint(1, hours_back + 1)
                pub_date = datetime.now() - timedelta(hours=hours_ago)
                
                article = NewsArticle(
                    symbol=symbol,
                    title=title,
                    content=content,
                    source=np.random.choice(["Reuters", "Bloomberg", "CNBC", "WSJ", "MarketWatch"]),
                    published_date=pub_date,
                    sentiment_score=sentiment,
                    sentiment_polarity=polarity,
                    relevance_score=np.random.uniform(0.6, 1.0),
                    impact_score=np.random.uniform(0.3, 0.9),
                    keywords=[symbol, "earnings", "stock", "market"]
                )
                
                articles.append(article)
        
        return articles

class OptionsFlowProvider:
    """Base class for options flow data providers"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_options_flow(self, symbols: List[str], hours_back: int = 24) -> List[OptionsFlowSignal]:
        """Get options flow data for symbols"""
        raise NotImplementedError

class MockOptionsFlowProvider(OptionsFlowProvider):
    """Mock options flow provider for testing"""
    
    def get_options_flow(self, symbols: List[str], hours_back: int = 24) -> List[OptionsFlowSignal]:
        """Generate mock options flow data"""
        
        signals = []
        
        for symbol in symbols:
            # Generate 1-3 options signals per symbol
            num_signals = np.random.randint(1, 4)
            
            for i in range(num_signals):
                # Random option details
                current_price = np.random.uniform(50, 500)  # Mock current price
                strike_price = current_price * np.random.uniform(0.9, 1.1)
                
                # Random expiration (1-30 days)
                exp_days = np.random.randint(1, 31)
                expiration = datetime.now() + timedelta(days=exp_days)
                
                # Random option type
                option_type = np.random.choice(["CALL", "PUT"])
                
                # Generate realistic Greeks
                delta = np.random.uniform(0.2, 0.8) if option_type == "CALL" else np.random.uniform(-0.8, -0.2)
                gamma = np.random.uniform(0.01, 0.05)
                theta = np.random.uniform(-0.1, -0.01)
                vega = np.random.uniform(0.1, 0.3)
                
                # Unusual activity score
                unusual_score = np.random.uniform(0.3, 1.0)
                
                # Directional bias
                if option_type == "CALL" and unusual_score > 0.7:
                    bias = "BULLISH"
                elif option_type == "PUT" and unusual_score > 0.7:
                    bias = "BEARISH"
                else:
                    bias = "NEUTRAL"
                
                signal = OptionsFlowSignal(
                    symbol=symbol,
                    flow_type=np.random.choice([t for t in OptionsFlowType]),
                    strike_price=strike_price,
                    expiration_date=expiration,
                    option_type=option_type,
                    volume=np.random.randint(100, 10000),
                    open_interest=np.random.randint(50, 5000),
                    premium=np.random.uniform(0.5, 50.0),
                    implied_volatility=np.random.uniform(0.15, 0.80),
                    delta=delta,
                    gamma=gamma,
                    theta=theta,
                    vega=vega,
                    unusual_activity_score=unusual_score,
                    directional_bias=bias
                )
                
                signals.append(signal)
        
        return signals

class InsiderTradingProvider:
    """Base class for insider trading data providers"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_insider_trading(self, symbols: List[str], days_back: int = 30) -> List[InsiderTradingSignal]:
        """Get insider trading data for symbols"""
        raise NotImplementedError

class MockInsiderTradingProvider(InsiderTradingProvider):
    """Mock insider trading provider for testing"""
    
    def get_insider_trading(self, symbols: List[str], days_back: int = 30) -> List[InsiderTradingSignal]:
        """Generate mock insider trading data"""
        
        signals = []
        
        insider_titles = ["CEO", "CFO", "COO", "Director", "President", "VP", "Chairman"]
        
        for symbol in symbols:
            # Generate 0-2 insider signals per symbol (insider trading is rare)
            num_signals = np.random.randint(0, 3)
            
            for i in range(num_signals):
                # Random transaction details
                action = np.random.choice(list(InsiderActionType))
                shares = np.random.randint(1000, 100000)
                price = np.random.uniform(50, 500)
                value = shares * price
                
                # Random timing
                days_ago = np.random.randint(1, days_back + 1)
                trans_date = datetime.now() - timedelta(days=days_ago)
                
                # Significance score (higher for larger transactions and senior executives)
                title = np.random.choice(insider_titles)
                title_weight = 1.0 if title in ["CEO", "CFO", "Chairman"] else 0.7
                value_weight = min(value / 1000000, 1.0)  # Normalize by $1M
                significance = (title_weight + value_weight) / 2
                
                signal = InsiderTradingSignal(
                    symbol=symbol,
                    insider_name=f"John Smith {i+1}",
                    insider_title=title,
                    action_type=action,
                    transaction_date=trans_date,
                    shares=shares,
                    price=price,
                    value=value,
                    ownership_change=np.random.uniform(-5.0, 5.0),
                    form_type=np.random.choice(["4", "5"]),
                    confidence=np.random.uniform(0.7, 1.0),
                    significance_score=significance
                )
                
                signals.append(signal)
        
        return signals

class AlternativeDataIntegrator:
    """
    Comprehensive alternative data integration system
    
    Features:
    - News sentiment analysis
    - Options flow monitoring
    - Insider trading tracking
    - Social media sentiment
    - Multi-source data fusion
    - Pair-specific analysis
    - Risk-adjusted signals
    """
    
    def __init__(self, 
                 news_provider: Optional[NewsProvider] = None,
                 options_provider: Optional[OptionsFlowProvider] = None,
                 insider_provider: Optional[InsiderTradingProvider] = None):
        
        self.news_provider = news_provider or MockNewsProvider()
        self.options_provider = options_provider or MockOptionsFlowProvider()
        self.insider_provider = insider_provider or MockInsiderTradingProvider()
        
        self.logger = logging.getLogger(__name__)
        
        # Signal weights for combination
        self.signal_weights = {
            'sentiment': 0.4,
            'options': 0.35,
            'insider': 0.25
        }
        
        # Cache for data
        self.data_cache = {}
        
    def analyze_sentiment(self, articles: List[NewsArticle], symbol: str) -> SentimentSignal:
        """Analyze sentiment from news articles"""
        
        if not articles:
            return SentimentSignal(
                symbol=symbol,
                sentiment_type=SentimentType.NEWS,
                overall_sentiment=0.0,
                sentiment_polarity=SentimentPolarity.NEUTRAL,
                confidence=0.0,
                article_count=0,
                time_window="24h",
                momentum=0.0,
                volatility=0.0
            )
        
        # Filter articles for this symbol
        symbol_articles = [a for a in articles if a.symbol == symbol]
        
        if not symbol_articles:
            return SentimentSignal(
                symbol=symbol,
                sentiment_type=SentimentType.NEWS,
                overall_sentiment=0.0,
                sentiment_polarity=SentimentPolarity.NEUTRAL,
                confidence=0.0,
                article_count=0,
                time_window="24h",
                momentum=0.0,
                volatility=0.0
            )
        
        # Calculate weighted sentiment
        total_weight = 0
        weighted_sentiment = 0
        
        for article in symbol_articles:
            weight = article.relevance_score * article.impact_score
            weighted_sentiment += article.sentiment_score * weight
            total_weight += weight
        
        overall_sentiment = weighted_sentiment / total_weight if total_weight > 0 else 0
        
        # Determine polarity
        if overall_sentiment < -0.6:
            polarity = SentimentPolarity.VERY_NEGATIVE
        elif overall_sentiment < -0.2:
            polarity = SentimentPolarity.NEGATIVE
        elif overall_sentiment < 0.2:
            polarity = SentimentPolarity.NEUTRAL
        elif overall_sentiment < 0.6:
            polarity = SentimentPolarity.POSITIVE
        else:
            polarity = SentimentPolarity.VERY_POSITIVE
        
        # Calculate confidence based on article count and consistency
        confidence = min(len(symbol_articles) / 5, 1.0)  # More articles = higher confidence
        
        # Calculate momentum (recent vs older articles)
        recent_articles = [a for a in symbol_articles if (datetime.now() - a.published_date).total_seconds() <= 6 * 3600]
        older_articles = [a for a in symbol_articles if (datetime.now() - a.published_date).total_seconds() > 6 * 3600]
        
        recent_sentiment = np.mean([a.sentiment_score for a in recent_articles]) if recent_articles else 0
        older_sentiment = np.mean([a.sentiment_score for a in older_articles]) if older_articles else 0
        momentum = recent_sentiment - older_sentiment
        
        # Calculate volatility
        sentiments = [a.sentiment_score for a in symbol_articles]
        volatility = np.std(sentiments) if len(sentiments) > 1 else 0
        
        return SentimentSignal(
            symbol=symbol,
            sentiment_type=SentimentType.NEWS,
            overall_sentiment=overall_sentiment,
            sentiment_polarity=polarity,
            confidence=confidence,
            article_count=len(symbol_articles),
            time_window="24h",
            momentum=momentum,
            volatility=volatility
        )
    
    def analyze_options_flow(self, options_signals: List[OptionsFlowSignal], symbol: str) -> Optional[OptionsFlowSignal]:
        """Analyze options flow for a symbol"""
        
        symbol_signals = [s for s in options_signals if s.symbol == symbol]
        
        if not symbol_signals:
            return None
        
        # Find the most significant signal
        best_signal = max(symbol_signals, key=lambda x: x.unusual_activity_score)
        
        return best_signal
    
    def analyze_insider_trading(self, insider_signals: List[InsiderTradingSignal], symbol: str) -> Optional[InsiderTradingSignal]:
        """Analyze insider trading for a symbol"""
        
        symbol_signals = [s for s in insider_signals if s.symbol == symbol]
        
        if not symbol_signals:
            return None
        
        # Find the most significant signal
        best_signal = max(symbol_signals, key=lambda x: x.significance_score)
        
        return best_signal
    
    def combine_signals(self, sentiment: Optional[SentimentSignal], 
                       options: Optional[OptionsFlowSignal], 
                       insider: Optional[InsiderTradingSignal], 
                       symbol: str) -> AlternativeDataSignal:
        """Combine multiple alternative data signals"""
        
        signals = []
        weights = []
        
        # Sentiment signal
        if sentiment:
            signals.append(sentiment.overall_sentiment)
            weights.append(self.signal_weights['sentiment'] * sentiment.confidence)
        
        # Options signal
        if options:
            # Convert options bias to numeric signal
            if options.directional_bias == "BULLISH":
                options_signal = options.unusual_activity_score
            elif options.directional_bias == "BEARISH":
                options_signal = -options.unusual_activity_score
            else:
                options_signal = 0
            
            signals.append(options_signal)
            weights.append(self.signal_weights['options'])
        
        # Insider signal
        if insider:
            # Convert insider action to numeric signal
            if insider.action_type == InsiderActionType.BUY:
                insider_signal = insider.significance_score
            elif insider.action_type == InsiderActionType.SELL:
                insider_signal = -insider.significance_score
            else:
                insider_signal = 0
            
            signals.append(insider_signal)
            weights.append(self.signal_weights['insider'] * insider.confidence)
        
        # Calculate combined score
        if signals and weights:
            combined_score = np.average(signals, weights=weights)
            combined_score = np.clip(combined_score, -1, 1)
            
            total_weight = sum(weights)
            confidence = min(total_weight / sum(self.signal_weights.values()), 1.0)
            signal_strength = abs(combined_score) * confidence
        else:
            combined_score = 0
            confidence = 0
            signal_strength = 0
        
        # Determine directional bias
        if combined_score > 0.3:
            bias = "BULLISH"
        elif combined_score < -0.3:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
        
        return AlternativeDataSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            sentiment_signal=sentiment,
            options_signal=options,
            insider_signal=insider,
            combined_score=combined_score,
            confidence=confidence,
            signal_strength=signal_strength,
            directional_bias=bias
        )
    
    def analyze_pair_divergence(self, signal1: AlternativeDataSignal, 
                              signal2: AlternativeDataSignal) -> Tuple[float, float]:
        """Analyze divergence and correlation between pair signals"""
        
        # Divergence: how different the signals are
        divergence = abs(signal1.combined_score - signal2.combined_score)
        
        # Correlation: how similar the signal patterns are
        # This is a simplified correlation based on directional bias
        if signal1.directional_bias == signal2.directional_bias:
            correlation = 1.0 - divergence  # High correlation if same direction
        else:
            correlation = -0.5  # Negative correlation if opposite directions
        
        return divergence, correlation
    
    def calculate_pair_momentum(self, signal1: AlternativeDataSignal, 
                              signal2: AlternativeDataSignal) -> float:
        """Calculate combined momentum signal for pair"""
        
        # For pairs trading, we want divergence (one up, one down)
        if signal1.directional_bias != signal2.directional_bias and \
           signal1.directional_bias != "NEUTRAL" and signal2.directional_bias != "NEUTRAL":
            # Perfect divergence - good for pairs trading
            momentum = (signal1.signal_strength + signal2.signal_strength) / 2
        else:
            # Same direction or neutral - less attractive for pairs
            momentum = 0.0
        
        return momentum
    
    def analyze_pair_alternative_data(self, pair: Tuple[str, str], 
                                    hours_back: int = 24) -> PairAlternativeAnalysis:
        """Analyze alternative data for a trading pair"""
        
        symbol1, symbol2 = pair
        
        self.logger.info(f"Analyzing alternative data for pair {symbol1}/{symbol2}")
        
        # Get all data sources
        news_articles = self.news_provider.get_news([symbol1, symbol2], hours_back)
        options_signals = self.options_provider.get_options_flow([symbol1, symbol2], hours_back)
        insider_signals = self.insider_provider.get_insider_trading([symbol1, symbol2], 30)
        
        # Analyze each symbol
        symbol1_sentiment = self.analyze_sentiment(news_articles, symbol1)
        symbol1_options = self.analyze_options_flow(options_signals, symbol1)
        symbol1_insider = self.analyze_insider_trading(insider_signals, symbol1)
        
        symbol2_sentiment = self.analyze_sentiment(news_articles, symbol2)
        symbol2_options = self.analyze_options_flow(options_signals, symbol2)
        symbol2_insider = self.analyze_insider_trading(insider_signals, symbol2)
        
        # Combine signals for each symbol
        symbol1_combined = self.combine_signals(symbol1_sentiment, symbol1_options, symbol1_insider, symbol1)
        symbol2_combined = self.combine_signals(symbol2_sentiment, symbol2_options, symbol2_insider, symbol2)
        
        # Analyze pair dynamics
        divergence, correlation = self.analyze_pair_divergence(symbol1_combined, symbol2_combined)
        momentum = self.calculate_pair_momentum(symbol1_combined, symbol2_combined)
        
        # Calculate risk adjustment
        risk_adjustment = self._calculate_risk_adjustment(symbol1_combined, symbol2_combined, divergence)
        
        # Calculate overall confidence
        confidence = (symbol1_combined.confidence + symbol2_combined.confidence) / 2
        
        # Generate recommendation
        recommendation = self._generate_pair_recommendation(momentum, divergence, confidence)
        
        return PairAlternativeAnalysis(
            pair=pair,
            symbol1_signals=[symbol1_combined],
            symbol2_signals=[symbol2_combined],
            divergence_score=divergence,
            correlation_score=correlation,
            pair_momentum=momentum,
            risk_adjustment=risk_adjustment,
            confidence=confidence,
            recommendation=recommendation
        )
    
    def _calculate_risk_adjustment(self, signal1: AlternativeDataSignal, 
                                 signal2: AlternativeDataSignal, 
                                 divergence: float) -> float:
        """Calculate risk adjustment for position sizing"""
        
        # Higher divergence = higher confidence = larger position
        divergence_factor = min(divergence * 2, 1.0)
        
        # Higher signal strength = larger position
        strength_factor = (signal1.signal_strength + signal2.signal_strength) / 2
        
        # Combined risk adjustment (0.5 to 1.5 multiplier)
        risk_adjustment = 0.5 + (divergence_factor * strength_factor)
        
        return min(risk_adjustment, 1.5)
    
    def _generate_pair_recommendation(self, momentum: float, divergence: float, confidence: float) -> str:
        """Generate trading recommendation for pair"""
        
        # Score based on momentum, divergence, and confidence
        score = (momentum * 0.4 + divergence * 0.4 + confidence * 0.2)
        
        if score > 0.7:
            return "STRONG BUY - High momentum with strong divergence signals"
        elif score > 0.5:
            return "BUY - Good alternative data signals support entry"
        elif score > 0.3:
            return "HOLD - Moderate signals, monitor for changes"
        elif score > 0.1:
            return "CAUTION - Weak signals, consider reducing position"
        else:
            return "AVOID - No clear alternative data signals"
    
    def run_comprehensive_analysis(self, pairs: List[Tuple[str, str]], 
                                 hours_back: int = 24) -> Dict[str, any]:
        """Run comprehensive alternative data analysis"""
        
        self.logger.info(f"Running alternative data analysis for {len(pairs)} pairs")
        
        pair_analyses = []
        
        # Analyze each pair
        for pair in pairs:
            try:
                analysis = self.analyze_pair_alternative_data(pair, hours_back)
                pair_analyses.append(analysis)
            except Exception as e:
                self.logger.warning(f"Error analyzing pair {pair}: {e}")
                continue
        
        # Generate summary statistics
        summary = self._generate_analysis_summary(pair_analyses)
        
        return {
            'pair_analyses': pair_analyses,
            'summary': summary,
            'analysis_timestamp': datetime.now()
        }
    
    def _generate_analysis_summary(self, pair_analyses: List[PairAlternativeAnalysis]) -> Dict[str, any]:
        """Generate analysis summary"""
        
        if not pair_analyses:
            return {'error': 'No pair analyses available'}
        
        # Calculate statistics
        avg_momentum = np.mean([p.pair_momentum for p in pair_analyses])
        avg_divergence = np.mean([p.divergence_score for p in pair_analyses])
        avg_confidence = np.mean([p.confidence for p in pair_analyses])
        avg_risk_adjustment = np.mean([p.risk_adjustment for p in pair_analyses])
        
        # Recommendation distribution
        recommendations = [p.recommendation for p in pair_analyses]
        recommendation_counts = {rec: recommendations.count(rec) for rec in set(recommendations)}
        
        # Signal strength distribution
        high_momentum_pairs = len([p for p in pair_analyses if p.pair_momentum > 0.5])
        high_divergence_pairs = len([p for p in pair_analyses if p.divergence_score > 0.5])
        high_confidence_pairs = len([p for p in pair_analyses if p.confidence > 0.7])
        
        return {
            'total_pairs_analyzed': len(pair_analyses),
            'average_momentum': avg_momentum,
            'average_divergence': avg_divergence,
            'average_confidence': avg_confidence,
            'average_risk_adjustment': avg_risk_adjustment,
            'recommendation_distribution': recommendation_counts,
            'high_momentum_pairs': high_momentum_pairs,
            'high_divergence_pairs': high_divergence_pairs,
            'high_confidence_pairs': high_confidence_pairs,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def generate_alternative_data_report(self, analysis_results: Dict[str, any]) -> str:
        """Generate comprehensive alternative data report"""
        
        report = f"""
=== ALTERNATIVE DATA ANALYSIS REPORT ===

Analysis Date: {analysis_results['analysis_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

EXECUTIVE SUMMARY:
- Total Pairs Analyzed: {analysis_results['summary']['total_pairs_analyzed']}
- Average Momentum Score: {analysis_results['summary']['average_momentum']:.3f}
- Average Divergence Score: {analysis_results['summary']['average_divergence']:.3f}
- Average Confidence: {analysis_results['summary']['average_confidence']:.3f}
- Average Risk Adjustment: {analysis_results['summary']['average_risk_adjustment']:.3f}

SIGNAL STRENGTH DISTRIBUTION:
- High Momentum Pairs: {analysis_results['summary']['high_momentum_pairs']}
- High Divergence Pairs: {analysis_results['summary']['high_divergence_pairs']}
- High Confidence Pairs: {analysis_results['summary']['high_confidence_pairs']}

PAIR RECOMMENDATIONS:
"""
        
        for rec, count in analysis_results['summary']['recommendation_distribution'].items():
            report += f"  {rec}: {count} pairs\n"
        
        report += f"""
DETAILED PAIR ANALYSIS:
"""
        
        for analysis in analysis_results['pair_analyses'][:10]:  # Top 10
            report += f"""
Pair: {analysis.pair[0]}/{analysis.pair[1]}
  Momentum Score: {analysis.pair_momentum:.3f}
  Divergence Score: {analysis.divergence_score:.3f}
  Confidence: {analysis.confidence:.3f}
  Risk Adjustment: {analysis.risk_adjustment:.3f}
  Recommendation: {analysis.recommendation}
  
  Symbol 1 ({analysis.pair[0]}) Signals:
"""
            
            for signal in analysis.symbol1_signals:
                report += f"    Combined Score: {signal.combined_score:.3f}\n"
                report += f"    Directional Bias: {signal.directional_bias}\n"
                report += f"    Signal Strength: {signal.signal_strength:.3f}\n"
                
                if signal.sentiment_signal:
                    report += f"    Sentiment: {signal.sentiment_signal.overall_sentiment:.3f} ({signal.sentiment_signal.sentiment_polarity.value})\n"
                
                if signal.options_signal:
                    report += f"    Options: {signal.options_signal.directional_bias} (Score: {signal.options_signal.unusual_activity_score:.3f})\n"
                
                if signal.insider_signal:
                    report += f"    Insider: {signal.insider_signal.action_type.value} (Significance: {signal.insider_signal.significance_score:.3f})\n"
            
            report += f"  Symbol 2 ({analysis.pair[1]}) Signals:\n"
            
            for signal in analysis.symbol2_signals:
                report += f"    Combined Score: {signal.combined_score:.3f}\n"
                report += f"    Directional Bias: {signal.directional_bias}\n"
                report += f"    Signal Strength: {signal.signal_strength:.3f}\n"
                
                if signal.sentiment_signal:
                    report += f"    Sentiment: {signal.sentiment_signal.overall_sentiment:.3f} ({signal.sentiment_signal.sentiment_polarity.value})\n"
                
                if signal.options_signal:
                    report += f"    Options: {signal.options_signal.directional_bias} (Score: {signal.options_signal.unusual_activity_score:.3f})\n"
                
                if signal.insider_signal:
                    report += f"    Insider: {signal.insider_signal.action_type.value} (Significance: {signal.insider_signal.significance_score:.3f})\n"
        
        return report 