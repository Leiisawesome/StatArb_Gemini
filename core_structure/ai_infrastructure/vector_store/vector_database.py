"""
Vector Database System

Professional vector database for AI knowledge storage and retrieval including:
- Document embedding and storage
- Semantic search and similarity matching
- Knowledge retrieval for AI agents
- Market intelligence storage
- Trading insight management
- Performance optimization

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid


class EmbeddingModel(Enum):
    """Supported embedding models"""
    SENTENCE_TRANSFORMERS = "all-MiniLM-L6-v2"
    FINANCIAL_BERT = "ProsusAI/finbert"
    OPENAI_ADA = "text-embedding-ada-002"
    CUSTOM = "custom"


@dataclass
class VectorConfig:
    """Vector database configuration"""
    model_name: str = "all-MiniLM-L6-v2"
    collection_name: str = "trading_knowledge"
    persist_directory: str = "./vector_db"
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_documents: int = 100000
    similarity_threshold: float = 0.7
    batch_size: int = 100
    
    # Performance settings
    enable_gpu: bool = False
    cache_embeddings: bool = True
    max_cache_size: int = 10000


@dataclass
class DocumentMetadata:
    """Document metadata structure"""
    document_id: str
    title: str
    content_type: str  # market_data, analysis, strategy, research
    source: str
    author: str
    timestamp: datetime
    tags: List[str] = field(default_factory=list)
    importance_score: float = 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class SearchResult:
    """Search result structure"""
    document_id: str
    content: str
    metadata: DocumentMetadata
    similarity_score: float
    relevance_score: float
    embedding: Optional[List[float]] = None


class DocumentStore:
    """
    Document Storage and Management
    
    Handles document processing, chunking, and metadata management
    for the vector database system.
    """
    
    def __init__(self, config: VectorConfig):
        """Initialize document store"""
        self.config = config
        self.logger = logging.getLogger("vector_db.document_store")
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.metadata_index: Dict[str, DocumentMetadata] = {}
        
    def add_document(self, content: str, metadata: DocumentMetadata) -> List[str]:
        """
        Add document to store with chunking
        
        Returns list of chunk IDs
        """
        try:
            # Chunk the document
            chunks = self._chunk_document(content)
            chunk_ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{metadata.document_id}_chunk_{i}"
                
                # Store chunk
                self.documents[chunk_id] = {
                    'content': chunk,
                    'metadata': metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
                
                # Update metadata index
                self.metadata_index[chunk_id] = metadata
                chunk_ids.append(chunk_id)
            
            self.logger.info(f"Added document {metadata.document_id} with {len(chunks)} chunks")
            return chunk_ids
            
        except Exception as e:
            self.logger.error(f"Error adding document {metadata.document_id}: {e}")
            return []
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        return self.documents.get(document_id)
    
    def update_access_stats(self, document_id: str):
        """Update document access statistics"""
        if document_id in self.metadata_index:
            metadata = self.metadata_index[document_id]
            metadata.access_count += 1
            metadata.last_accessed = datetime.now()
    
    def get_documents_by_type(self, content_type: str) -> List[str]:
        """Get document IDs by content type"""
        return [doc_id for doc_id, metadata in self.metadata_index.items()
                if metadata.content_type == content_type]
    
    def _chunk_document(self, content: str) -> List[str]:
        """Chunk document into smaller pieces"""
        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap
        
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                # Find last sentence ending
                for i in range(end - 1, start + chunk_size // 2, -1):
                    if content[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
            if start >= len(content):
                break
        
        return chunks


class VectorDatabase:
    """
    Professional Vector Database System
    
    Comprehensive vector database for AI knowledge management including:
    - High-performance embedding generation and storage
    - Semantic search with multiple similarity metrics
    - Knowledge retrieval optimization for AI agents
    - Real-time indexing and search capabilities
    - Performance monitoring and optimization
    """
    
    def __init__(self, config: VectorConfig):
        """Initialize vector database"""
        self.config = config
        self.logger = logging.getLogger("vector_database")
        
        # Initialize components
        self.document_store = DocumentStore(config)
        self.embedding_model = None
        self.client = None
        self.collection = None
        
        # Performance tracking
        self.search_count = 0
        self.average_search_time = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Embedding cache
        self.embedding_cache: Dict[str, List[float]] = {}
        
    async def initialize(self):
        """Initialize vector database components"""
        try:
            # Initialize ChromaDB
            self.client = chromadb.PersistentClient(
                path=self.config.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.config.collection_name
                )
                self.logger.info(f"Loaded existing collection: {self.config.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.config.collection_name,
                    metadata={"description": "Trading knowledge and market intelligence"}
                )
                self.logger.info(f"Created new collection: {self.config.collection_name}")
            
            # Initialize embedding model
            await self._initialize_embedding_model()
            
            self.logger.info("Vector database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize vector database: {e}")
            raise
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple documents to the database
        
        Args:
            documents: List of documents with 'content' and 'metadata'
            
        Returns:
            List of document IDs
        """
        try:
            all_chunk_ids = []
            embeddings = []
            contents = []
            metadatas = []
            ids = []
            
            for doc in documents:
                content = doc['content']
                metadata = DocumentMetadata(**doc['metadata'])
                
                # Add to document store and get chunks
                chunk_ids = self.document_store.add_document(content, metadata)
                
                for chunk_id in chunk_ids:
                    chunk_doc = self.document_store.get_document(chunk_id)
                    if chunk_doc:
                        # Generate embedding
                        embedding = await self._get_embedding(chunk_doc['content'])
                        
                        embeddings.append(embedding)
                        contents.append(chunk_doc['content'])
                        ids.append(chunk_id)
                        
                        # Prepare metadata for ChromaDB
                        chroma_metadata = {
                            'document_id': metadata.document_id,
                            'title': metadata.title,
                            'content_type': metadata.content_type,
                            'source': metadata.source,
                            'author': metadata.author,
                            'timestamp': metadata.timestamp.isoformat(),
                            'tags': json.dumps(metadata.tags),
                            'importance_score': metadata.importance_score,
                            'chunk_index': chunk_doc['chunk_index'],
                            'total_chunks': chunk_doc['total_chunks']
                        }
                        metadatas.append(chroma_metadata)
                
                all_chunk_ids.extend(chunk_ids)
            
            # Batch insert to ChromaDB
            if embeddings:
                self.collection.add(
                    embeddings=embeddings,
                    documents=contents,
                    metadatas=metadatas,
                    ids=ids
                )
            
            self.logger.info(f"Added {len(documents)} documents with {len(all_chunk_ids)} chunks")
            return all_chunk_ids
            
        except Exception as e:
            self.logger.error(f"Error adding documents: {e}")
            return []
    
    async def search(self, query: str, n_results: int = 10, 
                    content_type: Optional[str] = None,
                    similarity_threshold: Optional[float] = None) -> List[SearchResult]:
        """
        Semantic search in the knowledge base
        
        Args:
            query: Search query text
            n_results: Number of results to return
            content_type: Filter by content type
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of search results
        """
        try:
            start_time = datetime.now()
            
            # Generate query embedding
            query_embedding = await self._get_embedding(query)
            
            # Prepare filters
            where_filter = {}
            if content_type:
                where_filter['content_type'] = content_type
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, 100),
                where=where_filter if where_filter else None,
                include=['documents', 'metadatas', 'distances', 'embeddings']
            )
            
            # Process results
            search_results = []
            threshold = similarity_threshold or self.config.similarity_threshold
            
            for i, (doc_id, document, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                # Convert distance to similarity score (cosine similarity)
                similarity_score = 1 - distance
                
                if similarity_score >= threshold:
                    # Calculate relevance score (similarity + importance + recency)
                    relevance_score = self._calculate_relevance_score(
                        similarity_score, metadata
                    )
                    
                    # Create search result
                    doc_metadata = DocumentMetadata(
                        document_id=metadata['document_id'],
                        title=metadata['title'],
                        content_type=metadata['content_type'],
                        source=metadata['source'],
                        author=metadata['author'],
                        timestamp=datetime.fromisoformat(metadata['timestamp']),
                        tags=json.loads(metadata['tags']),
                        importance_score=metadata['importance_score']
                    )
                    
                    search_result = SearchResult(
                        document_id=doc_id,
                        content=document,
                        metadata=doc_metadata,
                        similarity_score=similarity_score,
                        relevance_score=relevance_score,
                        embedding=results.get('embeddings', [None])[0][i] if results.get('embeddings') else None
                    )
                    
                    search_results.append(search_result)
                    
                    # Update access stats
                    self.document_store.update_access_stats(doc_id)
            
            # Sort by relevance score
            search_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Update search metrics
            search_time = (datetime.now() - start_time).total_seconds()
            self._update_search_metrics(search_time)
            
            self.logger.info(f"Search completed: {len(search_results)} results in {search_time:.3f}s")
            return search_results[:n_results]
            
        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            return []
    
    async def search_similar_documents(self, document_id: str, 
                                     n_results: int = 5) -> List[SearchResult]:
        """Find documents similar to a given document"""
        try:
            # Get document content
            document = self.document_store.get_document(document_id)
            if not document:
                return []
            
            # Search using document content
            return await self.search(
                query=document['content'],
                n_results=n_results + 1  # +1 to exclude self
            )
            
        except Exception as e:
            self.logger.error(f"Error finding similar documents: {e}")
            return []
    
    async def get_knowledge_summary(self, topic: str, max_chunks: int = 5) -> str:
        """Get a summary of knowledge on a specific topic"""
        try:
            # Search for relevant documents
            results = await self.search(topic, n_results=max_chunks)
            
            if not results:
                return f"No knowledge found for topic: {topic}"
            
            # Combine relevant content
            knowledge_pieces = []
            for result in results:
                knowledge_pieces.append(f"[Score: {result.similarity_score:.2f}] {result.content}")
            
            return "\n\n".join(knowledge_pieces)
            
        except Exception as e:
            self.logger.error(f"Error getting knowledge summary: {e}")
            return f"Error retrieving knowledge for topic: {topic}"
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            collection_count = self.collection.count()
            
            return {
                "total_documents": len(self.document_store.documents),
                "total_chunks": collection_count,
                "search_count": self.search_count,
                "average_search_time": self.average_search_time,
                "cache_hit_rate": (
                    self.cache_hits / (self.cache_hits + self.cache_misses) * 100
                    if (self.cache_hits + self.cache_misses) > 0 else 0
                ),
                "embedding_cache_size": len(self.embedding_cache),
                "config": {
                    "model_name": self.config.model_name,
                    "collection_name": self.config.collection_name,
                    "chunk_size": self.config.chunk_size,
                    "similarity_threshold": self.config.similarity_threshold
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
    
    async def _initialize_embedding_model(self):
        """Initialize the embedding model"""
        try:
            if self.config.model_name == EmbeddingModel.SENTENCE_TRANSFORMERS.value:
                self.embedding_model = SentenceTransformer(self.config.model_name)
                if self.config.enable_gpu:
                    self.embedding_model = self.embedding_model.cuda()
                    
            elif self.config.model_name == EmbeddingModel.FINANCIAL_BERT.value:
                self.embedding_model = SentenceTransformer(self.config.model_name)
                
            else:
                # Default to sentence transformers
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            
            self.logger.info(f"Initialized embedding model: {self.config.model_name}")
            
        except Exception as e:
            self.logger.error(f"Error initializing embedding model: {e}")
            raise
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text with caching"""
        # Check cache first
        text_hash = str(hash(text))
        if text_hash in self.embedding_cache:
            self.cache_hits += 1
            return self.embedding_cache[text_hash]
        
        self.cache_misses += 1
        
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            embedding_list = embedding.tolist()
            
            # Cache if enabled and cache not full
            if (self.config.cache_embeddings and 
                len(self.embedding_cache) < self.config.max_cache_size):
                self.embedding_cache[text_hash] = embedding_list
            
            return embedding_list
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 384  # Default dimension for MiniLM
    
    def _calculate_relevance_score(self, similarity_score: float, 
                                 metadata: Dict[str, Any]) -> float:
        """Calculate relevance score combining similarity, importance, and recency"""
        try:
            # Base similarity score (weight: 70%)
            relevance = similarity_score * 0.7
            
            # Importance score (weight: 20%)
            importance = metadata.get('importance_score', 1.0)
            relevance += (importance / 5.0) * 0.2  # Normalize to 0-1 range
            
            # Recency bonus (weight: 10%)
            timestamp = datetime.fromisoformat(metadata['timestamp'])
            days_old = (datetime.now() - timestamp).days
            recency_factor = max(0, 1 - (days_old / 365))  # Decay over 1 year
            relevance += recency_factor * 0.1
            
            return min(1.0, relevance)  # Cap at 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {e}")
            return similarity_score
    
    def _update_search_metrics(self, search_time: float):
        """Update search performance metrics"""
        self.search_count += 1
        
        if self.average_search_time == 0:
            self.average_search_time = search_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.average_search_time = (
                alpha * search_time + 
                (1 - alpha) * self.average_search_time
            ) 