"""
AI Infrastructure Module

Comprehensive AI infrastructure for institutional-grade trading system including:
- AI Agent Framework with LLM integration
- Vector Database for knowledge storage
- Knowledge Base for market intelligence
- AI-powered trading agents
- AI monitoring and performance tracking

Author: Pro Quant Desk Trader
"""

# Core agent framework (always available)
from .agents.agent_framework import (
    BaseAgent, AgentManager, AgentType, AgentStatus,
    TradingAgent, RiskAgent, MarketAnalysisAgent
)

# LLM integration (may need API keys)
try:
    from .llm_integration.llm_client import (
        LLMClient, LLMConfig, ModelType, LLMResponse
    )
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    LLMClient = None
    LLMConfig = None
    ModelType = None
    LLMResponse = None

# Vector database (requires chromadb, sentence-transformers)
try:
    from .vector_store.vector_database import (
        VectorDatabase, VectorConfig, EmbeddingModel,
        DocumentStore, SearchResult
    )
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False
    VectorDatabase = None
    VectorConfig = None
    EmbeddingModel = None
    DocumentStore = None
    SearchResult = None

# Knowledge base (may depend on vector database)
try:
    from .knowledge.knowledge_base import (
        KnowledgeBase, MarketKnowledge, TradingInsight,
        StrategyKnowledge, RiskKnowledge
    )
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_BASE_AVAILABLE = False
    KnowledgeBase = None
    MarketKnowledge = None
    TradingInsight = None
    StrategyKnowledge = None
    RiskKnowledge = None

# AI monitoring
try:
    from .monitoring.ai_monitor import AIMonitor
    AI_MONITOR_AVAILABLE = True
except ImportError:
    AI_MONITOR_AVAILABLE = False
    AIMonitor = None

# Trading agents
try:
    from .agents.trading_agents import (
        AdvancedMarketAnalysisAgent, IntelligentRiskAgent
    )
    TRADING_AGENTS_AVAILABLE = True
except ImportError:
    TRADING_AGENTS_AVAILABLE = False
    AdvancedMarketAnalysisAgent = None
    IntelligentRiskAgent = None

# AI integration
try:
    from .ai_integration import (
        AISystemIntegrator, AITradingOrchestrator, TradingDecision
    )
    AI_INTEGRATION_AVAILABLE = True
except ImportError:
    AI_INTEGRATION_AVAILABLE = False
    AISystemIntegrator = None
    AITradingOrchestrator = None
    TradingDecision = None

# Build __all__ list with available components
__all__ = [
    # Agent Framework (always available)
    'BaseAgent', 'AgentManager', 'AgentType', 'AgentStatus',
    'TradingAgent', 'RiskAgent', 'MarketAnalysisAgent',
]

# Add optional components if available
if LLM_AVAILABLE:
    __all__.extend(['LLMClient', 'LLMConfig', 'ModelType', 'LLMResponse'])

if VECTOR_DB_AVAILABLE:
    __all__.extend(['VectorDatabase', 'VectorConfig', 'EmbeddingModel', 'DocumentStore', 'SearchResult'])

if KNOWLEDGE_BASE_AVAILABLE:
    __all__.extend(['KnowledgeBase', 'MarketKnowledge', 'TradingInsight', 'StrategyKnowledge', 'RiskKnowledge'])

if AI_MONITOR_AVAILABLE:
    __all__.append('AIMonitor')

if TRADING_AGENTS_AVAILABLE:
    __all__.extend(['AdvancedMarketAnalysisAgent', 'IntelligentRiskAgent'])

if AI_INTEGRATION_AVAILABLE:
    __all__.extend(['AISystemIntegrator', 'AITradingOrchestrator', 'TradingDecision'])

__version__ = "1.0.0"
__author__ = "Pro Quant Desk Trader" 