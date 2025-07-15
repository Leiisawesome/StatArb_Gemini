"""
Knowledge Base System

Comprehensive knowledge management for AI-powered trading including:
- Market intelligence storage and retrieval
- Trading strategy knowledge base
- Risk management insights
- Performance attribution data
- Regulatory and compliance information
- Real-time knowledge updates and validation

Author: Pro Quant Desk Trader
"""

import asyncio
import json
import logging
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable
import uuid
from abc import ABC, abstractmethod


class KnowledgeType(Enum):
    """Types of knowledge in the system"""
    MARKET_DATA = "market_data"
    TRADING_STRATEGY = "trading_strategy"
    RISK_MANAGEMENT = "risk_management"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    REGULATORY = "regulatory"
    RESEARCH = "research"
    NEWS_SENTIMENT = "news_sentiment"
    ECONOMIC_INDICATORS = "economic_indicators"


class ConfidenceLevel(Enum):
    """Confidence levels for knowledge entries"""
    VERY_HIGH = "very_high"  # 0.9+
    HIGH = "high"           # 0.8-0.9
    MEDIUM = "medium"       # 0.6-0.8
    LOW = "low"            # 0.4-0.6
    VERY_LOW = "very_low"  # <0.4


class KnowledgeStatus(Enum):
    """Status of knowledge entries"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    UNDER_REVIEW = "under_review"
    ARCHIVED = "archived"


@dataclass
class KnowledgeSource:
    """Source information for knowledge entries"""
    source_id: str
    source_type: str  # "research_paper", "market_data", "internal_analysis", etc.
    author: str
    publication_date: datetime
    url: Optional[str] = None
    citation: Optional[str] = None
    reliability_score: float = 1.0


@dataclass
class BaseKnowledge(ABC):
    """Base class for all knowledge entries"""
    knowledge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    knowledge_type: KnowledgeType = KnowledgeType.MARKET_DATA
    content: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    
    # Lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    accessed_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Source information
    sources: List[KnowledgeSource] = field(default_factory=list)
    
    # Validation
    validated: bool = False
    validation_date: Optional[datetime] = None
    validator: Optional[str] = None
    
    def update_access(self):
        """Update access statistics"""
        self.accessed_count += 1
        self.last_accessed = datetime.now()
    
    def add_source(self, source: KnowledgeSource):
        """Add source information"""
        self.sources.append(source)
        self.updated_at = datetime.now()
    
    def validate(self, validator: str):
        """Mark knowledge as validated"""
        self.validated = True
        self.validation_date = datetime.now()
        self.validator = validator
        self.updated_at = datetime.now()
    
    @abstractmethod
    def get_summary(self) -> str:
        """Get a summary of the knowledge entry"""
        pass


@dataclass
class MarketKnowledge(BaseKnowledge):
    """Market-specific knowledge and intelligence"""
    
    def __post_init__(self):
        self.knowledge_type = KnowledgeType.MARKET_DATA
    
    def get_summary(self) -> str:
        """Get market knowledge summary"""
        return f"Market Knowledge: {self.title} - {self.description[:100]}..."
    
    def add_price_data(self, symbol: str, data: pd.DataFrame):
        """Add price data for a symbol"""
        if 'price_data' not in self.content:
            self.content['price_data'] = {}
        
        self.content['price_data'][symbol] = {
            'data': data.to_dict(),
            'last_updated': datetime.now().isoformat(),
            'record_count': len(data)
        }
        self.updated_at = datetime.now()
    
    def add_correlation_analysis(self, correlation_matrix: pd.DataFrame, symbols: List[str]):
        """Add correlation analysis"""
        self.content['correlation_analysis'] = {
            'matrix': correlation_matrix.to_dict(),
            'symbols': symbols,
            'analysis_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def add_volatility_analysis(self, volatility_data: Dict[str, float]):
        """Add volatility analysis"""
        self.content['volatility_analysis'] = {
            'data': volatility_data,
            'calculation_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def get_market_regime(self) -> Optional[str]:
        """Get current market regime"""
        return self.content.get('market_regime', {}).get('current_regime')
    
    def set_market_regime(self, regime: str, confidence: float, indicators: Dict[str, Any]):
        """Set market regime information"""
        self.content['market_regime'] = {
            'current_regime': regime,
            'confidence': confidence,
            'indicators': indicators,
            'detection_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()


@dataclass
class TradingInsight(BaseKnowledge):
    """Trading insights and recommendations"""
    
    def __post_init__(self):
        self.knowledge_type = KnowledgeType.TRADING_STRATEGY
    
    def get_summary(self) -> str:
        """Get trading insight summary"""
        return f"Trading Insight: {self.title} - Confidence: {self.confidence_level.value}"
    
    def add_signal_analysis(self, signal_type: str, strength: float, 
                           entry_criteria: Dict[str, Any], exit_criteria: Dict[str, Any]):
        """Add trading signal analysis"""
        self.content['signal_analysis'] = {
            'signal_type': signal_type,
            'strength': strength,
            'entry_criteria': entry_criteria,
            'exit_criteria': exit_criteria,
            'generated_at': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def add_backtest_results(self, results: Dict[str, Any]):
        """Add backtesting results"""
        self.content['backtest_results'] = {
            'results': results,
            'backtest_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def add_performance_metrics(self, metrics: Dict[str, float]):
        """Add performance metrics"""
        self.content['performance_metrics'] = {
            'metrics': metrics,
            'calculation_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def get_expected_return(self) -> Optional[float]:
        """Get expected return from the insight"""
        return self.content.get('signal_analysis', {}).get('expected_return')
    
    def get_risk_score(self) -> Optional[float]:
        """Get risk score from the insight"""
        return self.content.get('risk_analysis', {}).get('risk_score')


@dataclass
class StrategyKnowledge(BaseKnowledge):
    """Strategy-specific knowledge and parameters"""
    
    def __post_init__(self):
        self.knowledge_type = KnowledgeType.TRADING_STRATEGY
    
    def get_summary(self) -> str:
        """Get strategy knowledge summary"""
        return f"Strategy: {self.title} - Performance: {self.get_performance_summary()}"
    
    def add_parameters(self, parameters: Dict[str, Any]):
        """Add strategy parameters"""
        self.content['parameters'] = {
            'values': parameters,
            'last_updated': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def add_optimization_results(self, optimization: Dict[str, Any]):
        """Add parameter optimization results"""
        self.content['optimization'] = {
            'results': optimization,
            'optimization_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def add_performance_history(self, performance: List[Dict[str, Any]]):
        """Add historical performance data"""
        self.content['performance_history'] = {
            'data': performance,
            'last_updated': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def get_performance_summary(self) -> str:
        """Get performance summary"""
        history = self.content.get('performance_history', {}).get('data', [])
        if not history:
            return "No performance data"
        
        latest = history[-1] if history else {}
        return f"Sharpe: {latest.get('sharpe_ratio', 'N/A')}, Return: {latest.get('total_return', 'N/A')}"
    
    def get_optimal_parameters(self) -> Dict[str, Any]:
        """Get optimized parameters"""
        optimization = self.content.get('optimization', {})
        return optimization.get('results', {}).get('optimal_parameters', {})


@dataclass
class RiskKnowledge(BaseKnowledge):
    """Risk management knowledge and metrics"""
    
    def __post_init__(self):
        self.knowledge_type = KnowledgeType.RISK_MANAGEMENT
    
    def get_summary(self) -> str:
        """Get risk knowledge summary"""
        return f"Risk Knowledge: {self.title} - Severity: {self.get_risk_severity()}"
    
    def add_risk_metrics(self, metrics: Dict[str, float]):
        """Add risk metrics"""
        self.content['risk_metrics'] = {
            'metrics': metrics,
            'calculation_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def add_stress_test_results(self, scenarios: Dict[str, Dict[str, float]]):
        """Add stress testing results"""
        self.content['stress_tests'] = {
            'scenarios': scenarios,
            'test_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def add_var_analysis(self, var_95: float, var_99: float, cvar_95: float):
        """Add VaR analysis"""
        self.content['var_analysis'] = {
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'calculation_date': datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def get_risk_severity(self) -> str:
        """Get risk severity level"""
        metrics = self.content.get('risk_metrics', {}).get('metrics', {})
        max_drawdown = metrics.get('max_drawdown', 0)
        
        if max_drawdown > 0.1:
            return "HIGH"
        elif max_drawdown > 0.05:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_var_95(self) -> Optional[float]:
        """Get 95% VaR"""
        return self.content.get('var_analysis', {}).get('var_95')


class KnowledgeValidator:
    """Knowledge validation and quality control"""
    
    def __init__(self):
        """Initialize knowledge validator"""
        self.logger = logging.getLogger("knowledge_validator")
        self.validation_rules: Dict[KnowledgeType, List[Callable]] = {
            KnowledgeType.MARKET_DATA: [
                self._validate_market_data_completeness,
                self._validate_market_data_quality
            ],
            KnowledgeType.TRADING_STRATEGY: [
                self._validate_strategy_performance,
                self._validate_strategy_parameters
            ],
            KnowledgeType.RISK_MANAGEMENT: [
                self._validate_risk_metrics,
                self._validate_risk_limits
            ]
        }
    
    async def validate_knowledge(self, knowledge: BaseKnowledge) -> Dict[str, Any]:
        """Validate knowledge entry"""
        validation_results = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'score': 1.0
        }
        
        try:
            # Run type-specific validation rules
            rules = self.validation_rules.get(knowledge.knowledge_type, [])
            
            for rule in rules:
                result = await rule(knowledge)
                if not result['valid']:
                    validation_results['valid'] = False
                    validation_results['issues'].extend(result.get('issues', []))
                
                validation_results['warnings'].extend(result.get('warnings', []))
                validation_results['score'] *= result.get('score', 1.0)
            
            # General validation
            general_result = await self._validate_general(knowledge)
            validation_results['valid'] = validation_results['valid'] and general_result['valid']
            validation_results['issues'].extend(general_result.get('issues', []))
            validation_results['warnings'].extend(general_result.get('warnings', []))
            validation_results['score'] *= general_result.get('score', 1.0)
            
            self.logger.info(f"Validation completed for {knowledge.knowledge_id}: {validation_results['valid']}")
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error validating knowledge {knowledge.knowledge_id}: {e}")
            return {
                'valid': False,
                'issues': [f"Validation error: {e}"],
                'warnings': [],
                'score': 0.0
            }
    
    async def _validate_general(self, knowledge: BaseKnowledge) -> Dict[str, Any]:
        """General validation rules"""
        result = {'valid': True, 'issues': [], 'warnings': [], 'score': 1.0}
        
        # Check required fields
        if not knowledge.title:
            result['issues'].append("Title is required")
            result['valid'] = False
        
        if not knowledge.description:
            result['warnings'].append("Description is empty")
            result['score'] *= 0.9
        
        # Check source information
        if not knowledge.sources:
            result['warnings'].append("No source information provided")
            result['score'] *= 0.8
        
        # Check confidence level consistency
        if knowledge.confidence_level == ConfidenceLevel.VERY_HIGH and not knowledge.validated:
            result['warnings'].append("High confidence knowledge should be validated")
            result['score'] *= 0.9
        
        return result
    
    async def _validate_market_data_completeness(self, knowledge: MarketKnowledge) -> Dict[str, Any]:
        """Validate market data completeness"""
        result = {'valid': True, 'issues': [], 'warnings': [], 'score': 1.0}
        
        price_data = knowledge.content.get('price_data', {})
        if not price_data:
            result['warnings'].append("No price data available")
            result['score'] *= 0.7
        
        return result
    
    async def _validate_market_data_quality(self, knowledge: MarketKnowledge) -> Dict[str, Any]:
        """Validate market data quality"""
        result = {'valid': True, 'issues': [], 'warnings': [], 'score': 1.0}
        
        # Check for recent updates
        updated_at = knowledge.updated_at
        if (datetime.now() - updated_at).days > 7:
            result['warnings'].append("Market data is more than 7 days old")
            result['score'] *= 0.8
        
        return result
    
    async def _validate_strategy_performance(self, knowledge: StrategyKnowledge) -> Dict[str, Any]:
        """Validate strategy performance data"""
        result = {'valid': True, 'issues': [], 'warnings': [], 'score': 1.0}
        
        performance = knowledge.content.get('performance_history', {}).get('data', [])
        if not performance:
            result['warnings'].append("No performance history available")
            result['score'] *= 0.6
        
        return result
    
    async def _validate_strategy_parameters(self, knowledge: StrategyKnowledge) -> Dict[str, Any]:
        """Validate strategy parameters"""
        result = {'valid': True, 'issues': [], 'warnings': [], 'score': 1.0}
        
        parameters = knowledge.content.get('parameters', {}).get('values', {})
        if not parameters:
            result['issues'].append("Strategy parameters are required")
            result['valid'] = False
        
        return result
    
    async def _validate_risk_metrics(self, knowledge: RiskKnowledge) -> Dict[str, Any]:
        """Validate risk metrics"""
        result = {'valid': True, 'issues': [], 'warnings': [], 'score': 1.0}
        
        metrics = knowledge.content.get('risk_metrics', {}).get('metrics', {})
        if not metrics:
            result['issues'].append("Risk metrics are required")
            result['valid'] = False
        
        return result
    
    async def _validate_risk_limits(self, knowledge: RiskKnowledge) -> Dict[str, Any]:
        """Validate risk limits"""
        result = {'valid': True, 'issues': [], 'warnings': [], 'score': 1.0}
        
        # Check for extreme risk values
        var_95 = knowledge.get_var_95()
        if var_95 and var_95 > 0.1:  # More than 10% VaR
            result['warnings'].append("High VaR detected (>10%)")
            result['score'] *= 0.8
        
        return result


class KnowledgeBase:
    """
    Comprehensive Knowledge Management System
    
    Professional knowledge base for AI-powered trading including:
    - Structured knowledge storage and retrieval
    - Knowledge validation and quality control
    - Intelligent search and recommendation
    - Knowledge lifecycle management
    - Performance optimization and caching
    """
    
    def __init__(self, vector_database=None):
        """Initialize knowledge base"""
        self.logger = logging.getLogger("knowledge_base")
        self.vector_db = vector_database
        self.validator = KnowledgeValidator()
        
        # In-memory storage for fast access
        self.knowledge_store: Dict[str, BaseKnowledge] = {}
        self.type_index: Dict[KnowledgeType, List[str]] = {kt: [] for kt in KnowledgeType}
        self.tag_index: Dict[str, List[str]] = {}
        
        # Performance tracking
        self.access_count = 0
        self.search_count = 0
        self.cache_hits = 0
        
        self.logger.info("Knowledge base initialized")
    
    async def add_knowledge(self, knowledge: BaseKnowledge, validate: bool = True) -> bool:
        """Add knowledge to the base"""
        try:
            # Validate if requested
            if validate:
                validation_result = await self.validator.validate_knowledge(knowledge)
                if not validation_result['valid']:
                    self.logger.warning(f"Knowledge validation failed: {validation_result['issues']}")
                    return False
                
                # Update confidence based on validation score
                if validation_result['score'] < 0.8:
                    if knowledge.confidence_level == ConfidenceLevel.VERY_HIGH:
                        knowledge.confidence_level = ConfidenceLevel.HIGH
                    elif knowledge.confidence_level == ConfidenceLevel.HIGH:
                        knowledge.confidence_level = ConfidenceLevel.MEDIUM
            
            # Store knowledge
            self.knowledge_store[knowledge.knowledge_id] = knowledge
            
            # Update indexes
            self.type_index[knowledge.knowledge_type].append(knowledge.knowledge_id)
            
            for tag in knowledge.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = []
                self.tag_index[tag].append(knowledge.knowledge_id)
            
            # Add to vector database if available
            if self.vector_db:
                await self._add_to_vector_db(knowledge)
            
            self.logger.info(f"Added knowledge: {knowledge.knowledge_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding knowledge: {e}")
            return False
    
    async def get_knowledge(self, knowledge_id: str) -> Optional[BaseKnowledge]:
        """Get knowledge by ID"""
        knowledge = self.knowledge_store.get(knowledge_id)
        if knowledge:
            knowledge.update_access()
            self.access_count += 1
        return knowledge
    
    async def search_knowledge(self, query: str, knowledge_type: Optional[KnowledgeType] = None,
                             tags: List[str] = None, limit: int = 10) -> List[BaseKnowledge]:
        """Search knowledge base"""
        try:
            self.search_count += 1
            results = []
            
            # Vector search if available
            if self.vector_db:
                vector_results = await self.vector_db.search(
                    query=query,
                    content_type=knowledge_type.value if knowledge_type else None,
                    n_results=limit
                )
                
                for result in vector_results:
                    knowledge = self.knowledge_store.get(result.document_id)
                    if knowledge:
                        results.append(knowledge)
                        knowledge.update_access()
            
            # Fallback to simple text search
            else:
                candidate_ids = set()
                
                # Filter by type if specified
                if knowledge_type:
                    candidate_ids.update(self.type_index.get(knowledge_type, []))
                else:
                    for ids in self.type_index.values():
                        candidate_ids.update(ids)
                
                # Filter by tags if specified
                if tags:
                    tag_ids = set()
                    for tag in tags:
                        tag_ids.update(self.tag_index.get(tag, []))
                    candidate_ids.intersection_update(tag_ids)
                
                # Simple text matching
                query_lower = query.lower()
                for knowledge_id in candidate_ids:
                    knowledge = self.knowledge_store.get(knowledge_id)
                    if knowledge:
                        text_content = f"{knowledge.title} {knowledge.description}".lower()
                        if query_lower in text_content:
                            results.append(knowledge)
                            knowledge.update_access()
                
                # Sort by relevance (access count for now)
                results.sort(key=lambda k: k.accessed_count, reverse=True)
                results = results[:limit]
            
            self.logger.info(f"Search completed: {len(results)} results for '{query}'")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching knowledge: {e}")
            return []
    
    async def get_knowledge_by_type(self, knowledge_type: KnowledgeType) -> List[BaseKnowledge]:
        """Get all knowledge of a specific type"""
        knowledge_ids = self.type_index.get(knowledge_type, [])
        return [self.knowledge_store[kid] for kid in knowledge_ids if kid in self.knowledge_store]
    
    async def get_knowledge_by_tags(self, tags: List[str]) -> List[BaseKnowledge]:
        """Get knowledge by tags"""
        result_ids = set()
        for tag in tags:
            tag_ids = set(self.tag_index.get(tag, []))
            if not result_ids:
                result_ids = tag_ids
            else:
                result_ids.intersection_update(tag_ids)
        
        return [self.knowledge_store[kid] for kid in result_ids if kid in self.knowledge_store]
    
    async def update_knowledge(self, knowledge_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing knowledge"""
        try:
            knowledge = self.knowledge_store.get(knowledge_id)
            if not knowledge:
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(knowledge, key):
                    setattr(knowledge, key, value)
            
            knowledge.updated_at = datetime.now()
            
            # Re-validate if content changed
            if 'content' in updates:
                validation_result = await self.validator.validate_knowledge(knowledge)
                if not validation_result['valid']:
                    self.logger.warning(f"Updated knowledge validation failed: {validation_result['issues']}")
            
            self.logger.info(f"Updated knowledge: {knowledge_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating knowledge: {e}")
            return False
    
    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """Delete knowledge entry"""
        try:
            knowledge = self.knowledge_store.get(knowledge_id)
            if not knowledge:
                return False
            
            # Remove from indexes
            self.type_index[knowledge.knowledge_type].remove(knowledge_id)
            
            for tag in knowledge.tags:
                if tag in self.tag_index:
                    self.tag_index[tag].remove(knowledge_id)
                    if not self.tag_index[tag]:
                        del self.tag_index[tag]
            
            # Remove from main store
            del self.knowledge_store[knowledge_id]
            
            self.logger.info(f"Deleted knowledge: {knowledge_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting knowledge: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        type_counts = {kt.value: len(ids) for kt, ids in self.type_index.items()}
        
        # Calculate confidence distribution
        confidence_dist = {}
        for knowledge in self.knowledge_store.values():
            conf = knowledge.confidence_level.value
            confidence_dist[conf] = confidence_dist.get(conf, 0) + 1
        
        # Calculate validation stats
        validated_count = sum(1 for k in self.knowledge_store.values() if k.validated)
        
        return {
            'total_knowledge': len(self.knowledge_store),
            'by_type': type_counts,
            'confidence_distribution': confidence_dist,
            'validated_percentage': (validated_count / len(self.knowledge_store) * 100) if self.knowledge_store else 0,
            'total_tags': len(self.tag_index),
            'access_count': self.access_count,
            'search_count': self.search_count,
            'cache_hit_rate': (self.cache_hits / max(1, self.access_count)) * 100
        }
    
    async def _add_to_vector_db(self, knowledge: BaseKnowledge):
        """Add knowledge to vector database"""
        try:
            # Prepare document for vector storage
            content = f"{knowledge.title}\n{knowledge.description}\n{json.dumps(knowledge.content)}"
            
            document = {
                'content': content,
                'metadata': {
                    'document_id': knowledge.knowledge_id,
                    'title': knowledge.title,
                    'content_type': knowledge.knowledge_type.value,
                    'source': 'knowledge_base',
                    'author': 'system',
                    'timestamp': knowledge.created_at,
                    'tags': knowledge.tags,
                    'importance_score': self._calculate_importance_score(knowledge)
                }
            }
            
            await self.vector_db.add_documents([document])
            
        except Exception as e:
            self.logger.error(f"Error adding to vector database: {e}")
    
    def _calculate_importance_score(self, knowledge: BaseKnowledge) -> float:
        """Calculate importance score for knowledge"""
        score = 1.0
        
        # Adjust based on confidence level
        confidence_weights = {
            ConfidenceLevel.VERY_HIGH: 1.5,
            ConfidenceLevel.HIGH: 1.2,
            ConfidenceLevel.MEDIUM: 1.0,
            ConfidenceLevel.LOW: 0.8,
            ConfidenceLevel.VERY_LOW: 0.5
        }
        score *= confidence_weights.get(knowledge.confidence_level, 1.0)
        
        # Adjust based on validation
        if knowledge.validated:
            score *= 1.3
        
        # Adjust based on access frequency
        if knowledge.accessed_count > 10:
            score *= 1.2
        elif knowledge.accessed_count > 5:
            score *= 1.1
        
        return min(5.0, score)  # Cap at 5.0 