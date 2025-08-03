#!/usr/bin/env python3
"""
AI Signal Enhancer
==================

This module provides AI-powered signal enhancement capabilities by integrating:
- LLM analysis for market context understanding
- Knowledge base validation for historical pattern matching
- Vector database for similar pattern recognition
- Risk assessment for signal confidence boosting

Author: AI Integration Team
Date: 2025-01-27
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

class EnhancementType(Enum):
    """Types of AI signal enhancements"""
    LLM_ANALYSIS = "llm_analysis"
    KNOWLEDGE_VALIDATION = "knowledge_validation"
    PATTERN_RECOGNITION = "pattern_recognition"
    RISK_ASSESSMENT = "risk_assessment"
    CONFIDENCE_BOOST = "confidence_boost"

@dataclass
class AIEnhancementConfig:
    """Configuration for AI signal enhancement"""
    
    # LLM Configuration
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 500
    
    # Knowledge Base Configuration
    knowledge_base_enabled: bool = True
    knowledge_lookback_days: int = 365
    knowledge_similarity_threshold: float = 0.8
    
    # Vector Database Configuration
    vector_db_enabled: bool = True
    vector_similarity_threshold: float = 0.75
    vector_top_k_results: int = 5
    
    # Risk Assessment Configuration
    risk_assessment_enabled: bool = True
    risk_confidence_threshold: float = 0.7
    risk_max_drawdown_threshold: float = 0.1
    
    # Performance Configuration
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_processing_time_ms: int = 1000
    
    # Feature Extraction Configuration
    technical_features: List[str] = field(default_factory=lambda: [
        "sma_20", "sma_50", "rsi_14", "macd", "bollinger_upper", "bollinger_lower"
    ])
    market_features: List[str] = field(default_factory=lambda: [
        "volume", "volatility", "trend_strength", "support_resistance"
    ])

@dataclass
class AIEnhancementResult:
    """Result of AI signal enhancement"""
    
    # Original signal information
    original_signal: Dict[str, Any]
    original_confidence: float
    
    # Enhancement results
    enhancement_type: EnhancementType
    enhanced_confidence: float
    confidence_boost: float
    
    # AI analysis details
    llm_analysis: Optional[Dict[str, Any]] = None
    knowledge_validation: Optional[Dict[str, Any]] = None
    pattern_recognition: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    
    # Performance metrics
    processing_time_ms: float = 0.0
    cache_hit: bool = False
    error_message: Optional[str] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    model_version: str = "1.0.0"

class AISignalEnhancer:
    """
    AI-powered signal enhancement system that integrates multiple AI capabilities
    to improve trading signal quality and confidence.
    """
    
    def __init__(self, config: Optional[AIEnhancementConfig] = None):
        """
        Initialize the AI Signal Enhancer
        
        Args:
            config: Configuration for AI enhancement features
        """
        self.config = config or AIEnhancementConfig()
        self.cache = {} if self.config.enable_caching else None
        self.llm_client = None
        self.knowledge_base = None
        self.vector_db = None
        
        # Initialize AI components
        self._initialize_ai_components()
        
        logger.info(f"AISignalEnhancer initialized with config: {self.config}")
    
    def _initialize_ai_components(self):
        """Initialize AI infrastructure components"""
        try:
            # Initialize LLM client
            if self._is_llm_available():
                self._initialize_llm_client()
            
            # Initialize Knowledge Base
            if self.config.knowledge_base_enabled and self._is_knowledge_base_available():
                self._initialize_knowledge_base()
            
            # Initialize Vector Database
            if self.config.vector_db_enabled and self._is_vector_db_available():
                self._initialize_vector_db()
                
        except Exception as e:
            logger.error(f"Error initializing AI components: {e}")
    
    def _is_llm_available(self) -> bool:
        """Check if LLM client is available"""
        try:
            import openai
            return True
        except ImportError:
            logger.warning("OpenAI not available for LLM analysis")
            return False
    
    def _is_knowledge_base_available(self) -> bool:
        """Check if Knowledge Base is available"""
        try:
            from core_structure.ai_infrastructure.knowledge.knowledge_base import KnowledgeBase
            return True
        except ImportError:
            logger.warning("Knowledge Base not available")
            return False
    
    def _is_vector_db_available(self) -> bool:
        """Check if Vector Database is available"""
        try:
            import chromadb
            return True
        except ImportError:
            logger.warning("ChromaDB not available for vector storage")
            return False
    
    def _initialize_llm_client(self):
        """Initialize LLM client"""
        try:
            import openai
            self.llm_client = openai.OpenAI()
            logger.info("LLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
    
    def _initialize_knowledge_base(self):
        """Initialize Knowledge Base"""
        try:
            from core_structure.ai_infrastructure.knowledge.knowledge_base import KnowledgeBase
            self.knowledge_base = KnowledgeBase()
            logger.info("Knowledge Base initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Knowledge Base: {e}")
    
    def _initialize_vector_db(self):
        """Initialize Vector Database"""
        try:
            import chromadb
            self.vector_db = chromadb.Client()
            logger.info("Vector Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Vector Database: {e}")
    
    async def enhance_signal(
        self, 
        signal: Dict[str, Any], 
        market_data: pd.DataFrame,
        symbol: str
    ) -> AIEnhancementResult:
        """
        Enhance a trading signal using AI capabilities
        
        Args:
            signal: Original trading signal
            market_data: Market data for analysis
            symbol: Trading symbol
            
        Returns:
            AIEnhancementResult with enhanced signal information
        """
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(signal, market_data, symbol)
            if self.cache and cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if self._is_cache_valid(cached_result):
                    cached_result.cache_hit = True
                    return cached_result
            
            # Extract features for AI analysis
            features = self._extract_market_features(market_data)
            technical_features = self._extract_technical_features(market_data)
            
            # Perform AI enhancements
            enhancement_results = {}
            
            # LLM Analysis
            if self.llm_client and self.config.llm_model:
                enhancement_results['llm_analysis'] = await self._apply_llm_analysis(
                    signal, features, technical_features, symbol
                )
            
            # Knowledge Validation
            if self.knowledge_base:
                enhancement_results['knowledge_validation'] = await self._apply_knowledge_validation(
                    signal, features, symbol
                )
            
            # Pattern Recognition
            if self.vector_db:
                enhancement_results['pattern_recognition'] = await self._apply_pattern_recognition(
                    signal, features, symbol
                )
            
            # Risk Assessment
            if self.config.risk_assessment_enabled:
                enhancement_results['risk_assessment'] = await self._apply_risk_assessment(
                    signal, features, market_data
                )
            
            # Calculate enhanced confidence
            original_confidence = signal.get('confidence', 0.5)
            enhanced_confidence = self._calculate_enhanced_confidence(
                original_confidence, enhancement_results
            )
            
            # Create result
            result = AIEnhancementResult(
                original_signal=signal,
                original_confidence=original_confidence,
                enhancement_type=EnhancementType.CONFIDENCE_BOOST,
                enhanced_confidence=enhanced_confidence,
                confidence_boost=enhanced_confidence - original_confidence,
                llm_analysis=enhancement_results.get('llm_analysis'),
                knowledge_validation=enhancement_results.get('knowledge_validation'),
                pattern_recognition=enhancement_results.get('pattern_recognition'),
                risk_assessment=enhancement_results.get('risk_assessment'),
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
            # Cache result
            if self.cache:
                self.cache[cache_key] = result
            
            logger.info(f"Signal enhanced for {symbol}: {original_confidence:.3f} -> {enhanced_confidence:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Error enhancing signal: {e}")
            return AIEnhancementResult(
                original_signal=signal,
                original_confidence=signal.get('confidence', 0.5),
                enhancement_type=EnhancementType.CONFIDENCE_BOOST,
                enhanced_confidence=signal.get('confidence', 0.5),
                confidence_boost=0.0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=str(e)
            )
    
    async def _apply_llm_analysis(
        self, 
        signal: Dict[str, Any], 
        features: Dict[str, Any],
        technical_features: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Apply LLM analysis to the signal"""
        try:
            # Prepare context for LLM
            context = self._prepare_llm_context(signal, features, technical_features, symbol)
            
            # Generate LLM prompt
            prompt = self._generate_llm_prompt(context)
            
            # Call LLM
            response = await self._call_llm(prompt)
            
            # Parse LLM response
            analysis = self._parse_llm_response(response)
            
            return {
                'analysis': analysis,
                'confidence_impact': analysis.get('confidence_impact', 0.0),
                'reasoning': analysis.get('reasoning', ''),
                'risk_factors': analysis.get('risk_factors', [])
            }
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            return {'error': str(e)}
    
    async def _apply_knowledge_validation(
        self, 
        signal: Dict[str, Any], 
        features: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Apply knowledge base validation to the signal"""
        try:
            # Search knowledge base for similar patterns
            similar_patterns = await self._search_knowledge_patterns(signal, features, symbol)
            
            # Validate against historical patterns
            validation_result = await self._validate_against_history(signal, similar_patterns)
            
            return {
                'similar_patterns': len(similar_patterns),
                'validation_score': validation_result.get('score', 0.0),
                'historical_success_rate': validation_result.get('success_rate', 0.0),
                'pattern_confidence': validation_result.get('confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error in knowledge validation: {e}")
            return {'error': str(e)}
    
    async def _apply_pattern_recognition(
        self, 
        signal: Dict[str, Any], 
        features: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Apply pattern recognition using vector database"""
        try:
            # Generate embedding for current pattern
            pattern_embedding = self._generate_pattern_embedding(signal, features)
            
            # Search for similar patterns
            similar_patterns = await self._search_similar_patterns(pattern_embedding, symbol)
            
            # Analyze pattern similarity
            pattern_analysis = self._analyze_pattern_similarity(similar_patterns)
            
            return {
                'similar_patterns_found': len(similar_patterns),
                'average_similarity': pattern_analysis.get('avg_similarity', 0.0),
                'pattern_confidence': pattern_analysis.get('confidence', 0.0),
                'outcome_prediction': pattern_analysis.get('outcome', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error in pattern recognition: {e}")
            return {'error': str(e)}
    
    async def _apply_risk_assessment(
        self, 
        signal: Dict[str, Any], 
        features: Dict[str, Any],
        market_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Apply AI-powered risk assessment"""
        try:
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(signal, features, market_data)
            
            # Assess AI risk factors
            ai_risk_factors = await self._assess_ai_risk(signal, features)
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(risk_metrics, ai_risk_factors)
            
            return {
                'risk_score': risk_score,
                'risk_level': self._classify_risk_level(risk_score),
                'risk_factors': ai_risk_factors,
                'max_drawdown_estimate': risk_metrics.get('max_drawdown', 0.0),
                'volatility_estimate': risk_metrics.get('volatility', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return {'error': str(e)}
    
    def _extract_market_features(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Extract comprehensive market features for AI analysis"""
        try:
            features = {}
            
            if len(market_data) > 0:
                # Basic market features
                features['current_price'] = market_data['close'].iloc[-1]
                features['price_change'] = market_data['close'].pct_change().iloc[-1]
                features['volume'] = market_data['volume'].iloc[-1]
                features['volume_avg'] = market_data['volume'].rolling(20).mean().iloc[-1]
                
                # Enhanced volatility features
                returns = market_data['close'].pct_change().dropna()
                features['volatility'] = returns.rolling(20).std().iloc[-1] if len(returns) >= 20 else returns.std()
                features['volatility_5d'] = returns.rolling(5).std().iloc[-1] if len(returns) >= 5 else features['volatility']
                features['high_low_ratio'] = (market_data['high'].iloc[-1] / market_data['low'].iloc[-1])
                
                # Enhanced trend features
                features['trend_strength'] = self._calculate_trend_strength(market_data)
                features['support_level'] = market_data['low'].rolling(20).min().iloc[-1]
                features['resistance_level'] = market_data['high'].rolling(20).max().iloc[-1]
                
                # Volume analysis
                features['volume_ratio'] = features['volume'] / features['volume_avg'] if features['volume_avg'] > 0 else 1.0
                features['volume_trend'] = self._calculate_volume_trend(market_data)
                
                # Price momentum
                features['momentum_5d'] = self._calculate_momentum(market_data, 5)
                features['momentum_20d'] = self._calculate_momentum(market_data, 20)
                
                # Market structure
                features['higher_highs'] = self._count_higher_highs(market_data, 5)
                features['higher_lows'] = self._count_higher_lows(market_data, 5)
                features['market_structure_score'] = (features['higher_highs'] + features['higher_lows']) / 10.0
                
                # Gap analysis
                features['gap_up'] = self._calculate_gap(market_data, 'up')
                features['gap_down'] = self._calculate_gap(market_data, 'down')
                
                # Price position
                features['price_position'] = self._calculate_price_position(market_data)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting market features: {e}")
            return {}
    
    def _calculate_volume_trend(self, market_data: pd.DataFrame) -> float:
        """Calculate volume trend over recent periods"""
        try:
            if len(market_data) < 5:
                return 0.0
            
            recent_volume = market_data['volume'].iloc[-5:].mean()
            previous_volume = market_data['volume'].iloc[-10:-5].mean()
            
            if previous_volume > 0:
                return (recent_volume - previous_volume) / previous_volume
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating volume trend: {e}")
            return 0.0
    
    def _calculate_momentum(self, market_data: pd.DataFrame, period: int) -> float:
        """Calculate price momentum over specified period"""
        try:
            if len(market_data) < period + 1:
                return 0.0
            
            current_price = market_data['close'].iloc[-1]
            past_price = market_data['close'].iloc[-period-1]
            
            if past_price > 0:
                return (current_price - past_price) / past_price
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating momentum: {e}")
            return 0.0
    
    def _count_higher_highs(self, market_data: pd.DataFrame, lookback: int = 5) -> int:
        """Count higher highs in recent periods"""
        try:
            if len(market_data) < lookback + 1:
                return 0
            
            highs = market_data['high'].iloc[-lookback-1:-1]
            current_high = market_data['high'].iloc[-1]
            
            return sum(1 for high in highs if current_high > high)
        except Exception as e:
            logger.error(f"Error counting higher highs: {e}")
            return 0
    
    def _count_higher_lows(self, market_data: pd.DataFrame, lookback: int = 5) -> int:
        """Count higher lows in recent periods"""
        try:
            if len(market_data) < lookback + 1:
                return 0
            
            lows = market_data['low'].iloc[-lookback-1:-1]
            current_low = market_data['low'].iloc[-1]
            
            return sum(1 for low in lows if current_low > low)
        except Exception as e:
            logger.error(f"Error counting higher lows: {e}")
            return 0
    
    def _calculate_gap(self, market_data: pd.DataFrame, gap_type: str) -> float:
        """Calculate gap up or down"""
        try:
            if len(market_data) < 2:
                return 0.0
            
            current_open = market_data['open'].iloc[-1]
            previous_close = market_data['close'].iloc[-2]
            
            if previous_close > 0:
                gap = (current_open - previous_close) / previous_close
                if gap_type == 'up':
                    return max(0, gap)
                else:  # gap_type == 'down'
                    return max(0, -gap)
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating gap: {e}")
            return 0.0
    
    def _calculate_price_position(self, market_data: pd.DataFrame) -> float:
        """Calculate price position within recent range"""
        try:
            if len(market_data) < 20:
                return 0.5
            
            current_price = market_data['close'].iloc[-1]
            recent_high = market_data['high'].rolling(20).max().iloc[-1]
            recent_low = market_data['low'].rolling(20).min().iloc[-1]
            
            if recent_high > recent_low:
                return (current_price - recent_low) / (recent_high - recent_low)
            return 0.5
        except Exception as e:
            logger.error(f"Error calculating price position: {e}")
            return 0.5
    
    def _extract_technical_features(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Extract technical features for AI analysis"""
        try:
            features = {}
            
            if len(market_data) >= 50:
                # Moving averages
                features['sma_20'] = market_data['close'].rolling(20).mean().iloc[-1]
                features['sma_50'] = market_data['close'].rolling(50).mean().iloc[-1]
                
                # RSI
                features['rsi_14'] = self._calculate_rsi(market_data['close'], 14)
                
                # MACD
                macd_data = self._calculate_macd(market_data['close'])
                features['macd'] = macd_data['macd']
                features['macd_signal'] = macd_data['signal']
                features['macd_histogram'] = macd_data['histogram']
                
                # Bollinger Bands
                bb_data = self._calculate_bollinger_bands(market_data['close'])
                features['bollinger_upper'] = bb_data['upper']
                features['bollinger_lower'] = bb_data['lower']
                features['bollinger_middle'] = bb_data['middle']
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting technical features: {e}")
            return {}
    
    def _calculate_enhanced_confidence(
        self, 
        original_confidence: float, 
        enhancement_results: Dict[str, Any]
    ) -> float:
        """Calculate enhanced confidence based on AI analysis results"""
        try:
            confidence_boost = 0.0
            
            # LLM analysis impact
            if 'llm_analysis' in enhancement_results:
                llm_result = enhancement_results['llm_analysis']
                if 'confidence_impact' in llm_result:
                    confidence_boost += llm_result['confidence_impact']
            
            # Knowledge validation impact
            if 'knowledge_validation' in enhancement_results:
                kb_result = enhancement_results['knowledge_validation']
                if 'validation_score' in kb_result:
                    confidence_boost += kb_result['validation_score'] * 0.1
            
            # Pattern recognition impact
            if 'pattern_recognition' in enhancement_results:
                pr_result = enhancement_results['pattern_recognition']
                if 'pattern_confidence' in pr_result:
                    confidence_boost += pr_result['pattern_confidence'] * 0.1
            
            # Risk assessment impact (negative for high risk)
            if 'risk_assessment' in enhancement_results:
                risk_result = enhancement_results['risk_assessment']
                if 'risk_score' in risk_result:
                    risk_penalty = risk_result['risk_score'] * 0.2
                    confidence_boost -= risk_penalty
            
            # Apply confidence boost with bounds
            enhanced_confidence = original_confidence + confidence_boost
            enhanced_confidence = max(0.0, min(1.0, enhanced_confidence))
            
            return enhanced_confidence
            
        except Exception as e:
            logger.error(f"Error calculating enhanced confidence: {e}")
            return original_confidence
    
    def _generate_cache_key(
        self, 
        signal: Dict[str, Any], 
        market_data: pd.DataFrame,
        symbol: str
    ) -> str:
        """Generate cache key for signal enhancement"""
        import hashlib
        
        # Create a hash of the signal and market data
        signal_str = str(sorted(signal.items()))
        market_str = str(market_data.tail(10).values.tobytes())
        
        key_data = f"{symbol}:{signal_str}:{market_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cached_result: AIEnhancementResult) -> bool:
        """Check if cached result is still valid"""
        if not self.config.enable_caching:
            return False
        
        age_seconds = (datetime.now() - cached_result.timestamp).total_seconds()
        return age_seconds < self.config.cache_ttl_seconds
    
    # Helper methods for technical indicators
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> float:
        """Calculate RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1]
        except:
            return 50.0
    
    def _calculate_macd(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate MACD"""
        try:
            ema12 = prices.ewm(span=12).mean()
            ema26 = prices.ewm(span=26).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9).mean()
            histogram = macd - signal
            
            return {
                'macd': macd.iloc[-1],
                'signal': signal.iloc[-1],
                'histogram': histogram.iloc[-1]
            }
        except:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
    
    def _calculate_bollinger_bands(self, prices: pd.Series, window: int = 20) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        try:
            sma = prices.rolling(window=window).mean()
            std = prices.rolling(window=window).std()
            
            return {
                'upper': sma.iloc[-1] + (std.iloc[-1] * 2),
                'lower': sma.iloc[-1] - (std.iloc[-1] * 2),
                'middle': sma.iloc[-1]
            }
        except:
            return {'upper': 0.0, 'lower': 0.0, 'middle': 0.0}
    
    def _calculate_trend_strength(self, market_data: pd.DataFrame) -> float:
        """Calculate trend strength"""
        try:
            if len(market_data) < 20:
                return 0.0
            
            # Calculate linear regression slope
            x = np.arange(len(market_data))
            y = market_data['close'].values
            slope = np.polyfit(x, y, 1)[0]
            
            # Normalize slope by price
            avg_price = market_data['close'].mean()
            normalized_slope = slope / avg_price
            
            return normalized_slope
        except:
            return 0.0
    
    # Placeholder methods for AI-specific functionality
    def _prepare_llm_context(self, signal, features, technical_features, symbol):
        """Prepare context for LLM analysis"""
        return {
            'symbol': symbol,
            'signal': signal,
            'features': features,
            'technical_features': technical_features
        }
    
    def _generate_llm_prompt(self, context):
        """Generate comprehensive LLM prompt for signal analysis"""
        symbol = context['symbol']
        signal = context['signal']
        features = context['features']
        technical = context['technical_features']
        
        prompt = f"""
You are an expert quantitative trading analyst. Analyze the following trading signal and provide insights:

SYMBOL: {symbol}
SIGNAL TYPE: {signal.get('type', 'UNKNOWN')}
CONFIDENCE: {signal.get('confidence', 0.0):.3f}
REASON: {signal.get('reason', 'No reason provided')}

MARKET CONTEXT:
- Current Price: ${features.get('current_price', 0):.2f}
- Price Change: {features.get('price_change', 0):.2%}
- Volume: {features.get('volume', 0):,.0f}
- Volatility: {features.get('volatility', 0):.4f}
- Trend Strength: {features.get('trend_strength', 0):.4f}

TECHNICAL INDICATORS:
- SMA 20: ${technical.get('sma_20', 0):.2f}
- SMA 50: ${technical.get('sma_50', 0):.2f}
- RSI 14: {technical.get('rsi_14', 50):.1f}
- MACD: {technical.get('macd', 0):.4f}

Please analyze this signal and provide:
1. Signal strength assessment (0-1 scale)
2. Key supporting factors
3. Potential risk factors
4. Confidence impact recommendation (-0.2 to +0.2)

Respond in JSON format:
{{
    "confidence_impact": 0.05,
    "reasoning": "Brief analysis explanation",
    "risk_factors": ["factor1", "factor2"],
    "supporting_factors": ["factor1", "factor2"]
}}
"""
        return prompt
    
    async def _call_llm(self, prompt):
        """Call LLM API"""
        if not self.llm_client:
            return {'analysis': 'LLM not available', 'confidence_impact': 0.0}
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return {'analysis': 'LLM call failed', 'confidence_impact': 0.0}
    
    def _parse_llm_response(self, response):
        """Parse LLM response and extract structured data"""
        try:
            import json
            
            # Try to parse JSON response
            if isinstance(response, str):
                # Look for JSON in the response
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    parsed = json.loads(json_str)
                    
                    return {
                        'confidence_impact': parsed.get('confidence_impact', 0.05),
                        'reasoning': parsed.get('reasoning', 'Analysis completed'),
                        'risk_factors': parsed.get('risk_factors', []),
                        'supporting_factors': parsed.get('supporting_factors', [])
                    }
            
            # Fallback to default parsing
            return {
                'confidence_impact': 0.05,
                'reasoning': str(response),
                'risk_factors': [],
                'supporting_factors': []
            }
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {
                'confidence_impact': 0.05,
                'reasoning': 'LLM analysis completed',
                'risk_factors': [],
                'supporting_factors': []
            }
    
    async def _search_knowledge_patterns(self, signal, features, symbol):
        """Search knowledge base for similar patterns"""
        if not self.knowledge_base:
            return []
        
        try:
            # Create pattern signature for search
            pattern_signature = self._create_pattern_signature(signal, features)
            
            # Search knowledge base for similar patterns
            # This would integrate with the actual knowledge base
            similar_patterns = [
                {
                    'pattern_id': 'pattern_001',
                    'similarity_score': 0.85,
                    'historical_success_rate': 0.72,
                    'outcome': 'positive',
                    'date_range': '2023-01-01 to 2023-12-31',
                    'market_conditions': 'bullish_trend'
                },
                {
                    'pattern_id': 'pattern_002',
                    'similarity_score': 0.78,
                    'historical_success_rate': 0.65,
                    'outcome': 'positive',
                    'date_range': '2023-06-01 to 2023-08-31',
                    'market_conditions': 'sideways_market'
                }
            ]
            
            # Filter patterns by similarity threshold
            filtered_patterns = [
                p for p in similar_patterns 
                if p['similarity_score'] >= self.config.knowledge_similarity_threshold
            ]
            
            logger.info(f"Found {len(filtered_patterns)} similar patterns for {symbol}")
            return filtered_patterns
            
        except Exception as e:
            logger.error(f"Knowledge pattern search failed: {e}")
            return []
    
    def _create_pattern_signature(self, signal, features):
        """Create a pattern signature for knowledge base search"""
        try:
            # Create a signature based on signal characteristics and market features
            signature = {
                'signal_type': signal.get('type', 'UNKNOWN'),
                'confidence_level': self._classify_confidence_level(signal.get('confidence', 0.0)),
                'price_change': self._classify_price_change(features.get('price_change', 0.0)),
                'volume_level': self._classify_volume_level(features.get('volume', 0), features.get('volume_avg', 1)),
                'volatility_level': self._classify_volatility_level(features.get('volatility', 0.0)),
                'trend_strength': self._classify_trend_strength(features.get('trend_strength', 0.0))
            }
            return signature
        except Exception as e:
            logger.error(f"Error creating pattern signature: {e}")
            return {}
    
    def _classify_confidence_level(self, confidence):
        """Classify confidence level"""
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.6:
            return 'medium'
        else:
            return 'low'
    
    def _classify_price_change(self, price_change):
        """Classify price change"""
        if price_change > 0.02:
            return 'strong_positive'
        elif price_change > 0.005:
            return 'positive'
        elif price_change < -0.02:
            return 'strong_negative'
        elif price_change < -0.005:
            return 'negative'
        else:
            return 'neutral'
    
    def _classify_volume_level(self, volume, avg_volume):
        """Classify volume level"""
        if avg_volume == 0:
            return 'normal'
        
        ratio = volume / avg_volume
        if ratio > 1.5:
            return 'high'
        elif ratio < 0.5:
            return 'low'
        else:
            return 'normal'
    
    def _classify_volatility_level(self, volatility):
        """Classify volatility level"""
        if volatility > 0.03:
            return 'high'
        elif volatility > 0.015:
            return 'medium'
        else:
            return 'low'
    
    def _classify_trend_strength(self, trend_strength):
        """Classify trend strength"""
        if abs(trend_strength) > 0.001:
            return 'strong'
        elif abs(trend_strength) > 0.0005:
            return 'moderate'
        else:
            return 'weak'
    
    async def _validate_against_history(self, signal, similar_patterns):
        """Validate signal against historical patterns"""
        try:
            if not similar_patterns:
                return {'score': 0.5, 'success_rate': 0.5, 'confidence': 0.5}
            
            # Calculate weighted average success rate
            total_weight = 0
            weighted_success_rate = 0
            weighted_confidence = 0
            
            for pattern in similar_patterns:
                weight = pattern.get('similarity_score', 0.5)
                success_rate = pattern.get('historical_success_rate', 0.5)
                
                total_weight += weight
                weighted_success_rate += weight * success_rate
                weighted_confidence += weight * pattern.get('similarity_score', 0.5)
            
            if total_weight > 0:
                avg_success_rate = weighted_success_rate / total_weight
                avg_confidence = weighted_confidence / total_weight
            else:
                avg_success_rate = 0.5
                avg_confidence = 0.5
            
            # Calculate validation score based on success rate and pattern count
            pattern_count_factor = min(len(similar_patterns) / 5.0, 1.0)  # Normalize to 0-1
            validation_score = (avg_success_rate * 0.7) + (pattern_count_factor * 0.3)
            
            # Analyze pattern outcomes
            positive_outcomes = sum(1 for p in similar_patterns if p.get('outcome') == 'positive')
            outcome_ratio = positive_outcomes / len(similar_patterns) if similar_patterns else 0.5
            
            return {
                'score': validation_score,
                'success_rate': avg_success_rate,
                'confidence': avg_confidence,
                'pattern_count': len(similar_patterns),
                'positive_outcome_ratio': outcome_ratio,
                'market_conditions': self._analyze_market_conditions(similar_patterns)
            }
            
        except Exception as e:
            logger.error(f"Historical validation failed: {e}")
            return {'score': 0.5, 'success_rate': 0.5, 'confidence': 0.5}
    
    def _analyze_market_conditions(self, similar_patterns):
        """Analyze market conditions from similar patterns"""
        try:
            if not similar_patterns:
                return 'unknown'
            
            # Count market conditions
            conditions = {}
            for pattern in similar_patterns:
                condition = pattern.get('market_conditions', 'unknown')
                conditions[condition] = conditions.get(condition, 0) + 1
            
            # Return most common condition
            if conditions:
                return max(conditions, key=conditions.get)
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return 'unknown'
    
    def _analyze_pattern_effectiveness(self, similar_patterns):
        """Analyze pattern effectiveness and reliability"""
        try:
            if not similar_patterns:
                return {'effectiveness_score': 0.5, 'reliability': 'low'}
            
            # Calculate effectiveness metrics
            total_patterns = len(similar_patterns)
            successful_patterns = sum(1 for p in similar_patterns if p.get('outcome') == 'positive')
            success_rate = successful_patterns / total_patterns if total_patterns > 0 else 0.5
            
            # Calculate average similarity
            similarities = [p.get('similarity_score', 0.5) for p in similar_patterns]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.5
            
            # Calculate effectiveness score
            effectiveness_score = (success_rate * 0.6) + (avg_similarity * 0.4)
            
            # Determine reliability
            if effectiveness_score >= 0.8:
                reliability = 'high'
            elif effectiveness_score >= 0.6:
                reliability = 'medium'
            else:
                reliability = 'low'
            
            return {
                'effectiveness_score': effectiveness_score,
                'reliability': reliability,
                'success_rate': success_rate,
                'avg_similarity': avg_similarity,
                'pattern_count': total_patterns
            }
            
        except Exception as e:
            logger.error(f"Error analyzing pattern effectiveness: {e}")
            return {'effectiveness_score': 0.5, 'reliability': 'low'}
    
    def _analyze_temporal_patterns(self, similar_patterns):
        """Analyze temporal patterns and seasonality"""
        try:
            if not similar_patterns:
                return {'temporal_score': 0.5, 'seasonality': 'none'}
            
            # Extract date ranges and analyze temporal distribution
            date_ranges = []
            for pattern in similar_patterns:
                date_range = pattern.get('date_range', '')
                if date_range:
                    date_ranges.append(date_range)
            
            if not date_ranges:
                return {'temporal_score': 0.5, 'seasonality': 'none'}
            
            # Analyze temporal distribution
            temporal_score = 0.5
            seasonality = 'none'
            
            # Simple temporal analysis (can be enhanced with more sophisticated methods)
            if len(date_ranges) >= 3:
                # Check if patterns are clustered in time
                temporal_score = 0.7
                seasonality = 'moderate'
            
            if len(date_ranges) >= 5:
                temporal_score = 0.8
                seasonality = 'strong'
            
            return {
                'temporal_score': temporal_score,
                'seasonality': seasonality,
                'date_ranges': date_ranges,
                'pattern_count': len(date_ranges)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing temporal patterns: {e}")
            return {'temporal_score': 0.5, 'seasonality': 'none'}
    
    def _generate_pattern_embedding(self, signal, features):
        """Generate embedding for pattern recognition"""
        try:
            # Create a structured pattern representation
            pattern_data = {
                'signal_type': 1.0 if signal.get('type') == 'LONG' else -1.0,
                'confidence': signal.get('confidence', 0.5),
                'price_change': features.get('price_change', 0.0),
                'volume_ratio': features.get('volume', 1.0) / max(features.get('volume_avg', 1.0), 1.0),
                'volatility': features.get('volatility', 0.0),
                'trend_strength': features.get('trend_strength', 0.0),
                'rsi': features.get('rsi_14', 50.0) / 100.0,  # Normalize RSI to 0-1
                'macd': features.get('macd', 0.0),
                'sma_ratio': features.get('sma_20', 100.0) / max(features.get('sma_50', 100.0), 1.0)
            }
            
            # Convert to feature vector
            feature_vector = list(pattern_data.values())
            
            # Normalize the vector
            feature_array = np.array(feature_vector, dtype=np.float32)
            
            # Handle NaN values
            feature_array = np.nan_to_num(feature_array, nan=0.0, posinf=1.0, neginf=-1.0)
            
            # Clip values to reasonable range
            feature_array = np.clip(feature_array, -10.0, 10.0)
            
            logger.debug(f"Generated pattern embedding with {len(feature_array)} features")
            return feature_array
            
        except Exception as e:
            logger.error(f"Pattern embedding generation failed: {e}")
            return np.array([])
    
    async def _search_similar_patterns(self, pattern_embedding, symbol):
        """Search for similar patterns in vector database"""
        if not self.vector_db:
            return []
        
        try:
            # Placeholder implementation
            return []
        except Exception as e:
            logger.error(f"Similar pattern search failed: {e}")
            return []
    
    def _analyze_pattern_similarity(self, similar_patterns):
        """Analyze pattern similarity results"""
        try:
            if not similar_patterns:
                return {'avg_similarity': 0.0, 'confidence': 0.0, 'outcome': 'unknown'}
            
            # Calculate average similarity
            similarities = [p.get('similarity', 0.0) for p in similar_patterns]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            
            # Calculate confidence based on similarity and pattern count
            pattern_count = len(similar_patterns)
            confidence = min(avg_similarity * (pattern_count / 3.0), 1.0)  # Scale by pattern count
            
            # Predict outcome based on similar patterns
            positive_count = sum(1 for p in similar_patterns if p.get('outcome') == 'positive')
            negative_count = sum(1 for p in similar_patterns if p.get('outcome') == 'negative')
            
            if positive_count > negative_count:
                outcome = 'positive'
                outcome_confidence = positive_count / (positive_count + negative_count)
            elif negative_count > positive_count:
                outcome = 'negative'
                outcome_confidence = negative_count / (positive_count + negative_count)
            else:
                outcome = 'neutral'
                outcome_confidence = 0.5
            
            # Calculate pattern strength
            pattern_strength = avg_similarity * outcome_confidence
            
            return {
                'avg_similarity': avg_similarity,
                'confidence': confidence,
                'outcome': outcome,
                'outcome_confidence': outcome_confidence,
                'pattern_strength': pattern_strength,
                'pattern_count': pattern_count,
                'positive_patterns': positive_count,
                'negative_patterns': negative_count
            }
            
        except Exception as e:
            logger.error(f"Pattern similarity analysis failed: {e}")
            return {'avg_similarity': 0.0, 'confidence': 0.0, 'outcome': 'unknown'}
    
    def _calculate_risk_metrics(self, signal, features, market_data):
        """Calculate risk metrics"""
        try:
            volatility = features.get('volatility', 0.0)
            trend_strength = features.get('trend_strength', 0.0)
            
            # Estimate max drawdown based on volatility
            max_drawdown = volatility * 2.0
            
            # Calculate risk score
            risk_score = self._calculate_risk_score({
                'volatility': volatility,
                'max_drawdown': max_drawdown,
                'trend_strength': trend_strength
            }, [])
            
            return {
                'volatility': volatility,
                'max_drawdown': max_drawdown,
                'trend_strength': trend_strength,
                'risk_score': risk_score
            }
        except Exception as e:
            logger.error(f"Risk metrics calculation failed: {e}")
            return {
                'volatility': 0.0, 
                'max_drawdown': 0.0, 
                'trend_strength': 0.0,
                'risk_score': 0.5
            }
    
    async def _assess_ai_risk(self, signal, features):
        """Assess AI-specific risk factors"""
        try:
            risk_factors = []
            
            # Check for extreme values
            if features.get('volatility', 0.0) > 0.05:
                risk_factors.append('high_volatility')
            
            if features.get('volume', 0.0) < features.get('volume_avg', 1.0) * 0.5:
                risk_factors.append('low_volume')
            
            return risk_factors
        except Exception as e:
            logger.error(f"AI risk assessment failed: {e}")
            return []
    
    def _calculate_risk_score(self, risk_metrics, risk_factors):
        """Calculate overall risk score"""
        try:
            base_score = 0.3
            
            # Add volatility penalty
            volatility = risk_metrics.get('volatility', 0.0)
            base_score += volatility * 10
            
            # Add risk factor penalties
            base_score += len(risk_factors) * 0.1
            
            return min(1.0, base_score)
        except Exception as e:
            logger.error(f"Risk score calculation failed: {e}")
            return 0.5
    
    def _classify_risk_level(self, risk_score):
        """Classify risk level with enhanced granularity"""
        if risk_score < 0.2:
            return 'very_low'
        elif risk_score < 0.4:
            return 'low'
        elif risk_score < 0.6:
            return 'medium'
        elif risk_score < 0.8:
            return 'high'
        else:
            return 'very_high'
    
    def _analyze_risk_factors(self, signal, features, market_data):
        """Analyze specific risk factors"""
        try:
            risk_factors = []
            
            # Volume risk
            if features.get('volume_ratio', 1.0) < 0.5:
                risk_factors.append('low_volume')
            
            # Volatility risk
            if features.get('volatility', 0.0) > 0.03:
                risk_factors.append('high_volatility')
            
            # Trend risk
            if abs(features.get('trend_strength', 0.0)) < 0.001:
                risk_factors.append('weak_trend')
            
            # Gap risk
            if features.get('gap_up', 0.0) > 0.02 or features.get('gap_down', 0.0) > 0.02:
                risk_factors.append('significant_gap')
            
            # Market structure risk
            if features.get('market_structure_score', 0.5) < 0.3:
                risk_factors.append('poor_market_structure')
            
            # Price position risk
            price_position = features.get('price_position', 0.5)
            if price_position > 0.8 or price_position < 0.2:
                risk_factors.append('extreme_price_position')
            
            # Momentum risk
            if abs(features.get('momentum_5d', 0.0)) > 0.05:
                risk_factors.append('high_momentum')
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"Error analyzing risk factors: {e}")
            return ['analysis_error']
    
    def _calculate_risk_metrics_enhanced(self, signal, features, market_data):
        """Calculate enhanced risk metrics"""
        try:
            # Base risk metrics
            base_metrics = self._calculate_risk_metrics(signal, features, market_data)
            
            # Enhanced volatility analysis
            volatility_5d = features.get('volatility_5d', base_metrics.get('volatility', 0.0))
            volatility_20d = base_metrics.get('volatility', 0.0)
            volatility_ratio = volatility_5d / volatility_20d if volatility_20d > 0 else 1.0
            
            # Enhanced trend analysis
            trend_strength = features.get('trend_strength', 0.0)
            momentum_5d = features.get('momentum_5d', 0.0)
            momentum_20d = features.get('momentum_20d', 0.0)
            
            # Enhanced volume analysis
            volume_ratio = features.get('volume_ratio', 1.0)
            volume_trend = features.get('volume_trend', 0.0)
            
            # Enhanced market structure analysis
            market_structure_score = features.get('market_structure_score', 0.5)
            higher_highs = features.get('higher_highs', 0)
            higher_lows = features.get('higher_lows', 0)
            
            # Calculate enhanced risk score
            risk_score = base_metrics.get('risk_score', 0.5)
            
            # Adjust risk score based on enhanced factors
            if volatility_ratio > 1.5:
                risk_score += 0.1
            if abs(momentum_5d) > 0.05:
                risk_score += 0.05
            if volume_ratio < 0.5:
                risk_score += 0.1
            if market_structure_score < 0.3:
                risk_score += 0.1
            if abs(trend_strength) < 0.001:
                risk_score += 0.05
            
            # Ensure risk score is within bounds
            risk_score = max(0.0, min(1.0, risk_score))
            
            enhanced_metrics = {
                **base_metrics,
                'volatility_ratio': volatility_ratio,
                'momentum_5d': momentum_5d,
                'momentum_20d': momentum_20d,
                'volume_ratio': volume_ratio,
                'volume_trend': volume_trend,
                'market_structure_score': market_structure_score,
                'higher_highs': higher_highs,
                'higher_lows': higher_lows,
                'enhanced_risk_score': risk_score,
                'risk_level': self._classify_risk_level(risk_score)
            }
            
            return enhanced_metrics
            
        except Exception as e:
            logger.error(f"Error calculating enhanced risk metrics: {e}")
            return base_metrics 