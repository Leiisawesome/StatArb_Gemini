"""
AI Infrastructure Configuration for StatArb Trading System

This module provides AI-specific configuration classes for model management,
LLM integration, vector databases, and AI agent frameworks.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from pathlib import Path
from .base_config import BaseConfig


@dataclass
class ModelConfig(BaseConfig):
    """Configuration for individual ML models"""
    
    # Model identification
    model_id: str = ""
    model_name: str = ""
    model_version: str = "1.0.0"
    model_type: str = ""  # regression, classification, clustering, etc.
    
    # Model artifacts
    model_path: str = ""
    weights_path: Optional[str] = None
    config_path: Optional[str] = None
    metadata_path: Optional[str] = None
    
    # Model parameters
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    feature_names: List[str] = field(default_factory=list)
    target_names: List[str] = field(default_factory=list)
    
    # Training information
    training_start_date: Optional[datetime] = None
    training_end_date: Optional[datetime] = None
    training_samples: int = 0
    validation_score: float = 0.0
    test_score: float = 0.0
    
    # Performance metrics
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_score: Optional[float] = None
    
    # Model lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deployed_at: Optional[datetime] = None
    status: str = "training"  # training, validation, deployed, deprecated
    
    # Resource requirements
    memory_requirement_mb: int = 1024  # 1GB default
    cpu_cores: int = 1
    gpu_required: bool = False
    inference_latency_ms: int = 100
    
    def validate(self) -> None:
        """Validate model configuration"""
        if not self.model_id:
            raise ValueError("Model ID is required")
        
        if not self.model_name:
            raise ValueError("Model name is required")
        
        if not self.model_type:
            raise ValueError("Model type is required")
        
        if self.memory_requirement_mb <= 0:
            raise ValueError("Memory requirement must be positive")
        
        if self.cpu_cores <= 0:
            raise ValueError("CPU cores must be positive")
        
        if self.inference_latency_ms <= 0:
            raise ValueError("Inference latency must be positive")


@dataclass
class LLMConfig(BaseConfig):
    """Large Language Model configuration"""
    
    # Provider settings
    provider: str = "openai"  # openai, anthropic, huggingface, local
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    
    # Model parameters
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Rate limiting
    requests_per_minute: int = 60
    requests_per_day: int = 10000
    token_limit_per_request: int = 4096
    
    # Timeout and retry
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Context management
    context_window: int = 8192
    max_context_length: int = 4096
    context_compression_enabled: bool = True
    
    # Safety and filtering
    content_filter_enabled: bool = True
    safety_threshold: float = 0.8
    pii_detection_enabled: bool = True
    
    def validate(self) -> None:
        """Validate LLM configuration"""
        if not self.provider:
            raise ValueError("LLM provider is required")
        
        if not self.model_name:
            raise ValueError("Model name is required")
        
        if not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        
        if not 0 <= self.top_p <= 1:
            raise ValueError("Top-p must be between 0 and 1")
        
        if self.requests_per_minute <= 0:
            raise ValueError("Requests per minute must be positive")
        
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class VectorDatabaseConfig(BaseConfig):
    """Vector database configuration"""
    
    # Database settings
    provider: str = "chroma"  # chroma, pinecone, weaviate, qdrant
    connection_string: str = ""
    api_key: Optional[str] = None
    
    # Collection settings
    collection_name: str = "trading_knowledge"
    dimension: int = 1536  # OpenAI embedding dimension
    metric: str = "cosine"  # cosine, euclidean, dot_product
    
    # Indexing
    index_type: str = "HNSW"  # HNSW, IVF, FLAT
    ef_construction: int = 200
    ef_search: int = 50
    m_links: int = 16
    
    # Performance settings
    batch_size: int = 100
    max_connections: int = 50
    timeout_seconds: int = 30
    
    # Embedding settings
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimension: int = 1536
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Search settings
    default_top_k: int = 10
    similarity_threshold: float = 0.7
    enable_hybrid_search: bool = True
    
    def validate(self) -> None:
        """Validate vector database configuration"""
        if not self.provider:
            raise ValueError("Vector database provider is required")
        
        if self.dimension <= 0:
            raise ValueError("Dimension must be positive")
        
        if self.metric not in ["cosine", "euclidean", "dot_product"]:
            raise ValueError("Invalid similarity metric")
        
        if self.batch_size <= 0:
            raise ValueError("Batch size must be positive")
        
        if self.max_connections <= 0:
            raise ValueError("Max connections must be positive")
        
        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")


@dataclass
class AgentConfig(BaseConfig):
    """AI Agent configuration"""
    
    # Agent identification
    agent_id: str = ""
    agent_name: str = ""
    agent_type: str = ""  # trading, research, risk, monitoring
    agent_version: str = "1.0.0"
    
    # Capabilities
    enabled_tools: List[str] = field(default_factory=list)
    max_iterations: int = 10
    decision_threshold: float = 0.8
    confidence_threshold: float = 0.7
    
    # Memory and context
    memory_enabled: bool = True
    memory_window_days: int = 30
    context_retrieval_enabled: bool = True
    max_context_items: int = 20
    
    # Interaction settings
    human_in_the_loop: bool = True
    auto_approval_threshold: float = 0.9
    escalation_enabled: bool = True
    
    # Performance monitoring
    track_performance: bool = True
    performance_window_hours: int = 24
    alert_on_degradation: bool = True
    
    def validate(self) -> None:
        """Validate agent configuration"""
        if not self.agent_id:
            raise ValueError("Agent ID is required")
        
        if not self.agent_name:
            raise ValueError("Agent name is required")
        
        if not self.agent_type:
            raise ValueError("Agent type is required")
        
        if self.max_iterations <= 0:
            raise ValueError("Max iterations must be positive")
        
        if not 0 <= self.decision_threshold <= 1:
            raise ValueError("Decision threshold must be between 0 and 1")
        
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")


@dataclass
class AIConfig(BaseConfig):
    """Combined AI infrastructure configuration"""
    
    # Sub-configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    vector_db: VectorDatabaseConfig = field(default_factory=VectorDatabaseConfig)
    
    # Model registry settings
    model_registry_enabled: bool = True
    model_storage_path: str = "/models"
    model_versioning_enabled: bool = True
    model_backup_enabled: bool = True
    
    # Training infrastructure
    training_enabled: bool = True
    distributed_training: bool = False
    gpu_enabled: bool = False
    training_cluster_nodes: int = 1
    
    # Inference settings
    inference_batch_size: int = 32
    inference_timeout_seconds: int = 30
    model_warm_up_enabled: bool = True
    
    # Monitoring and logging
    model_monitoring_enabled: bool = True
    drift_detection_enabled: bool = True
    performance_tracking_enabled: bool = True
    explainability_enabled: bool = True
    
    # Data and features
    feature_store_enabled: bool = True
    feature_caching_enabled: bool = True
    feature_validation_enabled: bool = True
    data_lineage_tracking: bool = True
    
    # Security
    model_encryption_enabled: bool = True
    access_control_enabled: bool = True
    audit_logging_enabled: bool = True
    
    # Agents configuration
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate AI configuration"""
        # Validate sub-configurations
        self.llm.validate()
        self.vector_db.validate()
        
        # Validate agents
        for agent_name, agent_config in self.agents.items():
            agent_config.validate()
        
        # Validate global settings
        if not self.model_storage_path:
            raise ValueError("Model storage path is required")
        
        if self.inference_batch_size <= 0:
            raise ValueError("Inference batch size must be positive")
        
        if self.inference_timeout_seconds <= 0:
            raise ValueError("Inference timeout must be positive")
        
        if self.training_cluster_nodes <= 0:
            raise ValueError("Training cluster nodes must be positive")
    
    def get_model_registry_config(self) -> Dict[str, Any]:
        """Get model registry configuration"""
        return {
            "enabled": self.model_registry_enabled,
            "storage_path": self.model_storage_path,
            "versioning": self.model_versioning_enabled,
            "backup": self.model_backup_enabled
        }
    
    def get_inference_config(self) -> Dict[str, Any]:
        """Get inference configuration"""
        return {
            "batch_size": self.inference_batch_size,
            "timeout_seconds": self.inference_timeout_seconds,
            "warm_up_enabled": self.model_warm_up_enabled,
            "monitoring_enabled": self.model_monitoring_enabled
        }
    
    def add_agent(self, agent_config: AgentConfig):
        """Add agent configuration"""
        self.agents[agent_config.agent_id] = agent_config
    
    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent configuration by ID"""
        return self.agents.get(agent_id)
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent configuration"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
