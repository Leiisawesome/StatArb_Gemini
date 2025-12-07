"""
Data Engine - Alternative Data Handler
Advanced alternative data processing with web scraping, sentiment analysis, and multi-source integration
"""

import logging
import threading
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
import re
import hashlib

# Import constants
from .constants import (
    DataIntervals,
    DataRetention,
    AlternativeDataConfig,
)

# Import ISystemComponent for orchestrator integration (Rule 1)
try:
    from ..system.interfaces import ISystemComponent
except ImportError:
    # Fallback for testing
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool: pass
        @abstractmethod
        async def start(self) -> bool: pass
        @abstractmethod
        async def stop(self) -> bool: pass
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]: pass
        @abstractmethod
        def get_status(self) -> Dict[str, Any]: pass

logger = logging.getLogger(__name__)


class AlternativeDataType(Enum):
    """Alternative data types"""
    SENTIMENT = "sentiment"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    SATELLITE = "satellite"
    WEB_SCRAPING = "web_scraping"
    EARNINGS_CALL = "earnings_call"
    CREDIT_DATA = "credit_data"
    PATENT_DATA = "patent_data"
    SUPPLY_CHAIN = "supply_chain"
    ESG_DATA = "esg_data"
    INSIDER_TRADING = "insider_trading"
    OPTION_FLOW = "option_flow"


class DataProvider(Enum):
    """Alternative data providers"""
    TWITTER = "twitter"
    REDDIT = "reddit"
    NEWS_API = "news_api"
    BLOOMBERG_NEWS = "bloomberg_news"
    SATELLITE_PROVIDER = "satellite_provider"
    CUSTOM_SCRAPER = "custom_scraper"
    FUNDAMENTAL_PROVIDER = "fundamental_provider"
    SENTIMENT_PROVIDER = "sentiment_provider"


class ProcessingStatus(Enum):
    """Data processing status"""
    RAW = "raw"
    PROCESSING = "processing"
    PROCESSED = "processed"
    VALIDATED = "validated"
    ENRICHED = "enriched"
    FAILED = "failed"


@dataclass
class AlternativeDataPoint:
    """Alternative data point"""
    data_id: str
    symbol: str
    data_type: AlternativeDataType
    provider: DataProvider

    # Raw data
    raw_content: str
    structured_data: Dict[str, Any]

    # Processed data
    sentiment_score: Optional[float] = None
    relevance_score: Optional[float] = None
    credibility_score: Optional[float] = None
    impact_score: Optional[float] = None

    # Metadata
    source_url: Optional[str] = None
    author: Optional[str] = None
    language: str = "en"

    # Processing information
    processing_status: ProcessingStatus = ProcessingStatus.RAW
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None

    # Temporal data
    event_timestamp: datetime = field(default_factory=datetime.now)
    ingestion_timestamp: datetime = field(default_factory=datetime.now)
    processed_timestamp: Optional[datetime] = None


@dataclass
class AlternativeDataRequest:
    """Alternative data request"""
    data_type: str
    symbols: List[str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlternativeDataResponse:
    """Alternative data response"""
    success: bool
    data: Any
    error_message: Optional[str] = None


@dataclass
class SentimentAnalysis:
    """Sentiment analysis result"""
    text: str
    overall_sentiment: float  # -1 to 1
    confidence: float  # 0 to 1

    # Detailed sentiment
    positive_score: float
    negative_score: float
    neutral_score: float

    # Entity sentiment
    entity_sentiments: Dict[str, float] = field(default_factory=dict)

    # Keywords and topics
    keywords: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    # Analysis metadata
    model_version: str = "1.0"
    processing_time_ms: float = 0.0
    language: str = "en"


@dataclass
class NewsAnalysis:
    """News analysis result"""
    headline: str
    content: str
    source: str

    # Analysis results
    sentiment_analysis: SentimentAnalysis
    relevance_scores: Dict[str, float]  # Symbol -> relevance score
    impact_prediction: Dict[str, float]  # Symbol -> impact score

    # Categorization
    categories: List[str]
    tags: List[str]
    entities: List[str]

    # Quality metrics
    credibility_score: float
    timeliness_score: float
    completeness_score: float

    # Publishing information
    publish_time: datetime
    ingestion_time: datetime = field(default_factory=datetime.now)


@dataclass
class WebScrapingTarget:
    """Web scraping target configuration"""
    target_id: str
    name: str
    base_url: str

    # Scraping configuration
    selectors: Dict[str, str]  # CSS selectors for data extraction
    rate_limit_seconds: float
    max_pages: int

    # Data processing
    text_extractors: List[str]
    data_transformers: List[str]

    # Validation
    required_fields: List[str]
    validation_rules: Dict[str, Any]

    # State
    last_scrape_time: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0
    is_active: bool = True


class SentimentAnalyzer:
    """Advanced sentiment analysis engine"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Sentiment lexicons
        self._positive_words = set([
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'bullish', 'positive', 'growth', 'profit', 'gain', 'rise', 'up',
            'increase', 'strong', 'robust', 'solid', 'beat', 'outperform'
        ])

        self._negative_words = set([
            'bad', 'terrible', 'awful', 'horrible', 'disappointing', 'poor',
            'bearish', 'negative', 'decline', 'loss', 'fall', 'down',
            'decrease', 'weak', 'fragile', 'miss', 'underperform', 'crash'
        ])

        # Financial terms
        self._financial_terms = {
            'earnings', 'revenue', 'profit', 'loss', 'growth', 'margin',
            'dividend', 'buyback', 'merger', 'acquisition', 'ipo', 'split'
        }

        # Sentiment modifiers
        self._intensifiers = {'very': 1.5, 'extremely': 2.0, 'highly': 1.3, 'really': 1.2}
        self._diminishers = {'somewhat': 0.7, 'slightly': 0.5, 'barely': 0.3}

    async def analyze_sentiment(self, text: str, symbol: Optional[str] = None) -> SentimentAnalysis:
        """Analyze sentiment of text"""

        start_time = time.time()

        # Clean and tokenize text
        words = self._tokenize_text(text.lower())

        # Calculate base sentiment scores
        positive_count = 0
        negative_count = 0
        total_words = len(words)

        # Entity-specific sentiment if symbol provided
        entity_sentiment = 0.0
        entity_context_window = 5  # Words around entity

        for i, word in enumerate(words):
            # Check for sentiment words
            if word in self._positive_words:
                weight = self._get_word_weight(words, i)
                positive_count += weight

                # Check if near symbol
                if symbol and self._is_near_entity(words, i, symbol.lower(), entity_context_window):
                    entity_sentiment += weight

            elif word in self._negative_words:
                weight = self._get_word_weight(words, i)
                negative_count += weight

                # Check if near symbol
                if symbol and self._is_near_entity(words, i, symbol.lower(), entity_context_window):
                    entity_sentiment -= weight

        # Calculate sentiment scores
        if total_words > 0:
            positive_score = positive_count / total_words
            negative_score = negative_count / total_words
        else:
            positive_score = negative_score = 0.0

        neutral_score = max(0, 1.0 - positive_score - negative_score)

        # Overall sentiment (-1 to 1)
        overall_sentiment = positive_score - negative_score

        # Confidence based on sentiment strength and financial term presence
        financial_term_count = sum(1 for word in words if word in self._financial_terms)
        financial_relevance = min(1.0, financial_term_count / 10)

        confidence = min(1.0, abs(overall_sentiment) + financial_relevance * 0.3)

        # Extract keywords and topics
        keywords = self._extract_keywords(words)
        topics = self._extract_topics(text)

        # Entity sentiments
        entity_sentiments = {}
        if symbol:
            entity_sentiments[symbol] = entity_sentiment / max(1, total_words)

        processing_time = (time.time() - start_time) * 1000

        return SentimentAnalysis(
            text=text,
            overall_sentiment=max(-1, min(1, overall_sentiment)),
            confidence=confidence,
            positive_score=positive_score,
            negative_score=negative_score,
            neutral_score=neutral_score,
            entity_sentiments=entity_sentiments,
            keywords=keywords,
            topics=topics,
            processing_time_ms=processing_time
        )

    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Simple tokenization - in practice, use more sophisticated NLP
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    def _get_word_weight(self, words: List[str], index: int) -> float:
        """Get weight for sentiment word based on modifiers"""
        weight = 1.0

        # Check for intensifiers/diminishers in context
        for i in range(max(0, index - 2), min(len(words), index + 3)):
            if i != index:
                modifier_word = words[i]
                if modifier_word in self._intensifiers:
                    weight *= self._intensifiers[modifier_word]
                elif modifier_word in self._diminishers:
                    weight *= self._diminishers[modifier_word]

        return weight

    def _is_near_entity(self, words: List[str], word_index: int, entity: str, window: int) -> bool:
        """Check if sentiment word is near entity"""
        start = max(0, word_index - window)
        end = min(len(words), word_index + window + 1)

        for i in range(start, end):
            if entity in words[i]:
                return True

        return False

    def _extract_keywords(self, words: List[str]) -> List[str]:
        """Extract important keywords"""
        # Simple keyword extraction - frequency based
        word_freq = defaultdict(int)
        for word in words:
            if len(word) > 3 and word not in {'this', 'that', 'with', 'from', 'they', 'have', 'been'}:
                word_freq[word] += 1

        # Return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10] if freq > 1]

    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text"""
        # Simple topic extraction based on financial keywords
        topics = []

        topic_keywords = {
            'earnings': ['earnings', 'eps', 'income', 'profit'],
            'revenue': ['revenue', 'sales', 'income'],
            'guidance': ['guidance', 'outlook', 'forecast', 'projection'],
            'merger': ['merger', 'acquisition', 'deal', 'buyout'],
            'dividend': ['dividend', 'payout', 'yield'],
            'analyst': ['analyst', 'rating', 'upgrade', 'downgrade']
        }

        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)

        return topics


class WebScraper:
    """Advanced web scraping engine"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._scraping_targets = {}
        self._rate_limiters = defaultdict(float)

    async def register_target(self, target: WebScrapingTarget) -> None:
        """Register a web scraping target"""
        self._scraping_targets[target.target_id] = target
        logger.info(f"Registered scraping target: {target.name}")

    async def scrape_target(self, target_id: str) -> List[Dict[str, Any]]:
        """Scrape data from target"""

        target = self._scraping_targets.get(target_id)
        if not target:
            raise ValueError(f"Scraping target {target_id} not found")

        # Check rate limiting
        current_time = time.time()
        last_scrape = self._rate_limiters.get(target_id, 0)

        if current_time - last_scrape < target.rate_limit_seconds:
            wait_time = target.rate_limit_seconds - (current_time - last_scrape)
            await asyncio.sleep(wait_time)

        try:
            # Simulate web scraping (in practice, use requests/selenium)
            scraped_data = await self._simulate_scraping(target)

            target.last_scrape_time = datetime.now()
            target.success_count += 1
            self._rate_limiters[target_id] = time.time()

            logger.info(f"Successfully scraped {len(scraped_data)} items from {target.name}")

            return scraped_data

        except Exception as e:
            target.error_count += 1
            logger.error(f"Error scraping {target.name}: {e}")
            raise

    async def _simulate_scraping(self, target: WebScrapingTarget) -> List[Dict[str, Any]]:
        """Simulate web scraping (replace with actual implementation)"""

        # Simulate scraping delay
        await asyncio.sleep(np.random.uniform(0.5, 2.0))

        # Generate simulated data
        scraped_data = []
        num_items = np.random.randint(5, 20)

        for i in range(num_items):
            item = {
                'title': f"Article {i + 1} from {target.name}",
                'content': self._generate_sample_content(),
                'url': f"{target.base_url}/article/{i + 1}",
                'timestamp': datetime.now() - timedelta(minutes=np.random.randint(0, 60)),
                'author': f"Author {i % 5 + 1}",
                'category': np.random.choice(['earnings', 'market', 'company', 'analyst'])
            }
            scraped_data.append(item)

        return scraped_data

    def _generate_sample_content(self) -> str:
        """Generate sample content for simulation"""
        templates = [
            "Company reported strong earnings beating expectations with revenue growth of {growth}%. The positive results show {sentiment} outlook for the sector.",
            "Analysts {action} the stock after {event}. The {metric} performance indicates {trend} momentum in the market.",
            "Recent developments in {sector} sector show {direction} trends. Investors are {reaction} to the new guidance.",
            "The company announced {announcement} which is expected to {impact} future performance. Market reaction has been {response}."
        ]

        template = np.random.choice(templates)

        replacements = {
            'growth': str(np.random.randint(5, 25)),
            'sentiment': np.random.choice(['bullish', 'positive', 'optimistic']),
            'action': np.random.choice(['upgraded', 'downgraded', 'maintained']),
            'event': np.random.choice(['earnings', 'guidance', 'announcement']),
            'metric': np.random.choice(['financial', 'operational', 'strategic']),
            'trend': np.random.choice(['positive', 'negative', 'mixed']),
            'sector': np.random.choice(['technology', 'healthcare', 'finance']),
            'direction': np.random.choice(['upward', 'downward', 'sideways']),
            'reaction': np.random.choice(['optimistic', 'cautious', 'concerned']),
            'announcement': np.random.choice(['merger', 'partnership', 'expansion']),
            'impact': np.random.choice(['boost', 'improve', 'enhance']),
            'response': np.random.choice(['positive', 'mixed', 'negative'])
        }

        content = template
        for key, value in replacements.items():
            content = content.replace(f'{{{key}}}', value)

        return content


class AlternativeDataHandler(ISystemComponent):
    """
    Advanced alternative data handler

    Processes alternative data from multiple sources including news, social media,
    satellite data, and web scraping with sentiment analysis and relevance scoring.

    Implements ISystemComponent for orchestrator integration (Rule 1).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize alternative data handler"""
        self.config = config or {}
        self._lock = threading.Lock()

        # ISystemComponent state (Rule 1)
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)

        # Core components
        self.sentiment_analyzer = SentimentAnalyzer(self.config.get('sentiment', {}))
        self.web_scraper = WebScraper(self.config.get('scraping', {}))

        # Data storage
        self._raw_data = deque(maxlen=10000)
        self._processed_data = deque(maxlen=5000)
        self._data_by_symbol = defaultdict(lambda: deque(maxlen=1000))
        self._data_by_type = defaultdict(lambda: deque(maxlen=1000))

        # Processing queues
        self._processing_queue = asyncio.Queue(maxsize=1000)
        self._priority_queue = asyncio.Queue(maxsize=100)

        # Performance tracking
        self._processing_stats = {
            'total_ingested': 0,
            'total_processed': 0,
            'processing_errors': 0,
            'average_processing_time_ms': 0.0,
            'sentiment_analyses': 0,
            'web_scraping_sessions': 0
        }

        # Data providers
        self._data_providers = {}
        self._provider_configs = {}

        # Subscriptions and callbacks
        self._subscriptions = {}
        self._data_callbacks = []

        # Background processing
        self._processing_tasks = []

        # Note: Background tasks will be started in start() method (ISystemComponent lifecycle)
        self.logger.info("✅ AlternativeDataHandler created (call initialize() and start() for full activation)")

    # ========================================================================
    # ISystemComponent Lifecycle Methods (Rule 1)
    # ========================================================================

    async def initialize(self) -> bool:
        """Initialize alternative data handler"""
        try:
            self.logger.info("Initializing AlternativeDataHandler...")

            # Initialize default providers
            await self._initialize_providers()

            self.is_initialized = True
            self.logger.info("✅ AlternativeDataHandler initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ AlternativeDataHandler initialization failed: {e}")
            return False

    async def start(self) -> bool:
        """Start alternative data handler operations"""
        try:
            if not self.is_initialized:
                self.logger.error("Cannot start - not initialized. Call initialize() first.")
                return False

            self.logger.info("Starting AlternativeDataHandler background processing...")

            # Start background processing tasks
            await self._start_processing()

            self.is_operational = True
            self.logger.info("✅ AlternativeDataHandler started successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ AlternativeDataHandler start failed: {e}")
            return False

    async def stop(self) -> bool:
        """Stop alternative data handler operations"""
        try:
            self.logger.info("Stopping AlternativeDataHandler...")

            # Cancel all background tasks
            for task in self._processing_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            if self._processing_tasks:
                await asyncio.gather(*self._processing_tasks, return_exceptions=True)

            self.is_operational = False
            self.logger.info("✅ AlternativeDataHandler stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ AlternativeDataHandler stop failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on alternative data handler"""
        processing_stats = self.get_processing_stats()

        # Determine health status
        error_rate = 0.0
        if processing_stats['total_processed'] > 0:
            error_rate = processing_stats['processing_errors'] / processing_stats['total_processed']

        is_healthy = (
            self.is_operational and
            self.is_initialized and
            error_rate < AlternativeDataConfig.MAX_ERROR_RATE and  # Error rate threshold
            len(self._processing_tasks) > 0  # Background tasks running
        )

        return {
            'healthy': is_healthy,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'component_type': 'AlternativeDataHandler',
            'processing_stats': processing_stats,
            'error_rate': error_rate,
            'active_tasks': len([t for t in self._processing_tasks if not t.done()]),
            'queue_size': self._processing_queue.qsize() if hasattr(self._processing_queue, 'qsize') else 0
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of alternative data handler"""
        return {
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'component_type': 'AlternativeDataHandler',
            'total_ingested': self._processing_stats.get('total_ingested', 0),
            'total_processed': self._processing_stats.get('total_processed', 0),
            'processing_errors': self._processing_stats.get('processing_errors', 0),
            'active_subscriptions': len(self._subscriptions),
            'data_callbacks': len(self._data_callbacks)
        }

    # ========================================================================
    # Original AlternativeDataHandler Methods
    # ========================================================================

    async def _initialize_providers(self) -> None:
        """Initialize default data providers"""

        # News scraping targets
        news_targets = [
            WebScrapingTarget(
                target_id="financial_news",
                name="Financial News Site",
                base_url="https://financialnews.com",
                selectors={
                    'title': 'h1.headline',
                    'content': 'div.article-content',
                    'author': 'span.author',
                    'timestamp': 'time.publish-date'
                },
                rate_limit_seconds=2.0,
                max_pages=10,
                text_extractors=['title', 'content'],
                data_transformers=['sentiment_analysis', 'relevance_scoring'],
                required_fields=['title', 'content']
            ),

            WebScrapingTarget(
                target_id="earnings_transcripts",
                name="Earnings Call Transcripts",
                base_url="https://earnings-transcripts.com",
                selectors={
                    'title': 'h2.call-title',
                    'content': 'div.transcript-content',
                    'company': 'span.company-name',
                    'quarter': 'span.quarter'
                },
                rate_limit_seconds=5.0,
                max_pages=5,
                text_extractors=['content'],
                data_transformers=['sentiment_analysis', 'keyword_extraction'],
                required_fields=['title', 'content', 'company']
            )
        ]

        # Register scraping targets
        for target in news_targets:
            await self.web_scraper.register_target(target)

    async def _start_processing(self) -> None:
        """Start background processing tasks"""

        # Start processing workers
        self._processing_tasks = [
            asyncio.create_task(self._process_data_worker()),
            asyncio.create_task(self._priority_processor()),
            asyncio.create_task(self._periodic_scraping()),
            asyncio.create_task(self._cleanup_old_data())
        ]

        logger.info("Started alternative data processing")

    async def ingest_data(
        self,
        raw_content: str,
        data_type: AlternativeDataType,
        provider: DataProvider,
        symbol: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: bool = False
    ) -> str:
        """
        Ingest raw alternative data

        Args:
            raw_content: Raw text content
            data_type: Type of alternative data
            provider: Data provider
            symbol: Associated symbol
            metadata: Additional metadata
            priority: High priority processing

        Returns:
            Data ID
        """

        # Generate data ID using SHA-256 (more secure than MD5)
        data_id = hashlib.sha256(f"{raw_content[:100]}{time.time()}".encode()).hexdigest()[:32]

        # Create data point
        data_point = AlternativeDataPoint(
            data_id=data_id,
            symbol=symbol or "UNKNOWN",
            data_type=data_type,
            provider=provider,
            raw_content=raw_content,
            structured_data=metadata or {},
            source_url=metadata.get('source_url') if metadata else None,
            author=metadata.get('author') if metadata else None,
            language=metadata.get('language', 'en') if metadata else 'en'
        )

        # Store raw data
        with self._lock:
            self._raw_data.append(data_point)
            self._processing_stats['total_ingested'] += 1

        # Queue for processing
        try:
            if priority:
                await self._priority_queue.put(data_point)
            else:
                await self._processing_queue.put(data_point)
        except asyncio.QueueFull:
            logger.warning("Processing queue full, dropping data point")

        logger.debug(f"Ingested data: {data_id} ({data_type.value})")

        return data_id

    async def _process_data_worker(self) -> None:
        """Background worker for processing data"""

        while True:
            try:
                # Get data from queue
                data_point = await self._processing_queue.get()

                # Process the data
                await self._process_data_point(data_point)

                # Mark task done
                self._processing_queue.task_done()

            except Exception as e:
                logger.error(f"Error in data processing worker: {e}")
                with self._lock:
                    self._processing_stats['processing_errors'] += 1
                await asyncio.sleep(1)

    async def _priority_processor(self) -> None:
        """High priority data processor"""

        while True:
            try:
                # Get priority data
                data_point = await self._priority_queue.get()

                # Process immediately
                await self._process_data_point(data_point)

                # Mark task done
                self._priority_queue.task_done()

            except Exception as e:
                logger.error(f"Error in priority processor: {e}")
                await asyncio.sleep(1)

    async def _process_data_point(self, data_point: AlternativeDataPoint) -> None:
        """Process individual data point"""

        start_time = time.time()
        data_point.processing_status = ProcessingStatus.PROCESSING

        try:
            # Sentiment analysis for text data
            if data_point.data_type in [AlternativeDataType.NEWS, AlternativeDataType.SOCIAL_MEDIA,
                                       AlternativeDataType.EARNINGS_CALL]:
                sentiment = await self.sentiment_analyzer.analyze_sentiment(
                    data_point.raw_content, data_point.symbol
                )

                data_point.sentiment_score = sentiment.overall_sentiment
                data_point.structured_data['sentiment_analysis'] = {
                    'overall_sentiment': sentiment.overall_sentiment,
                    'confidence': sentiment.confidence,
                    'positive_score': sentiment.positive_score,
                    'negative_score': sentiment.negative_score,
                    'keywords': sentiment.keywords,
                    'topics': sentiment.topics
                }

                with self._lock:
                    self._processing_stats['sentiment_analyses'] += 1

            # Calculate relevance score
            relevance_score = await self._calculate_relevance_score(data_point)
            data_point.relevance_score = relevance_score

            # Calculate credibility score
            credibility_score = await self._calculate_credibility_score(data_point)
            data_point.credibility_score = credibility_score

            # Calculate impact score
            impact_score = await self._calculate_impact_score(data_point)
            data_point.impact_score = impact_score

            # Update processing status
            processing_time = (time.time() - start_time) * 1000
            data_point.processing_time_ms = processing_time
            data_point.processing_status = ProcessingStatus.PROCESSED
            data_point.processed_timestamp = datetime.now()

            # Store processed data
            with self._lock:
                self._processed_data.append(data_point)
                self._data_by_symbol[data_point.symbol].append(data_point)
                self._data_by_type[data_point.data_type].append(data_point)

                # Update statistics
                self._processing_stats['total_processed'] += 1

                # Update average processing time
                current_avg = self._processing_stats['average_processing_time_ms']
                processed_count = self._processing_stats['total_processed']
                self._processing_stats['average_processing_time_ms'] = (
                    (current_avg * (processed_count - 1) + processing_time) / processed_count
                )

            # Call callbacks
            await self._notify_subscribers(data_point)

            logger.debug(f"Processed data point: {data_point.data_id}")

        except Exception as e:
            data_point.processing_status = ProcessingStatus.FAILED
            data_point.error_message = str(e)

            with self._lock:
                self._processing_stats['processing_errors'] += 1

            logger.error(f"Error processing data point {data_point.data_id}: {e}")

    async def _calculate_relevance_score(self, data_point: AlternativeDataPoint) -> float:
        """Calculate relevance score for data point"""

        relevance = 0.5  # Base relevance

        # Symbol mention
        if data_point.symbol and data_point.symbol.lower() in data_point.raw_content.lower():
            relevance += 0.3

        # Financial keywords
        financial_keywords = ['earnings', 'revenue', 'profit', 'guidance', 'analyst', 'rating']
        keyword_count = sum(1 for keyword in financial_keywords
                           if keyword in data_point.raw_content.lower())
        relevance += min(0.2, keyword_count * 0.05)

        # Data type specific scoring
        if data_point.data_type == AlternativeDataType.EARNINGS_CALL:
            relevance += 0.2
        elif data_point.data_type == AlternativeDataType.NEWS:
            relevance += 0.1

        # Recency bonus
        age_hours = (datetime.now() - data_point.event_timestamp).total_seconds() / 3600
        if age_hours < 1:
            relevance += 0.1
        elif age_hours < 24:
            relevance += 0.05

        return min(1.0, relevance)

    async def _calculate_credibility_score(self, data_point: AlternativeDataPoint) -> float:
        """Calculate credibility score for data point"""

        credibility = 0.5  # Base credibility

        # Provider credibility (use constants)
        provider_scores = {
            DataProvider.BLOOMBERG_NEWS: AlternativeDataConfig.CREDIBILITY_BLOOMBERG,
            DataProvider.NEWS_API: AlternativeDataConfig.CREDIBILITY_NEWS_API,
            DataProvider.TWITTER: AlternativeDataConfig.CREDIBILITY_TWITTER,
            DataProvider.REDDIT: AlternativeDataConfig.CREDIBILITY_REDDIT,
            DataProvider.CUSTOM_SCRAPER: AlternativeDataConfig.CREDIBILITY_CUSTOM_SCRAPER
        }

        credibility = provider_scores.get(data_point.provider, 0.5)

        # Author credibility (if available)
        if data_point.author:
            credibility += AlternativeDataConfig.AUTHOR_CREDIBILITY_BONUS

        # Content quality indicators
        content_length = len(data_point.raw_content)
        if content_length > AlternativeDataConfig.SUBSTANTIAL_CONTENT_LENGTH:
            credibility += AlternativeDataConfig.CONTENT_LENGTH_BONUS

        # Source URL credibility
        if data_point.source_url:
            if any(domain in data_point.source_url for domain in AlternativeDataConfig.TRUSTED_DOMAINS):
                credibility += AlternativeDataConfig.TRUSTED_DOMAIN_BONUS

        return min(1.0, credibility)

    async def _calculate_impact_score(self, data_point: AlternativeDataPoint) -> float:
        """Calculate potential market impact score"""

        impact = 0.0

        # Sentiment impact
        if data_point.sentiment_score is not None:
            impact += abs(data_point.sentiment_score) * 0.3

        # Relevance impact
        if data_point.relevance_score is not None:
            impact += data_point.relevance_score * 0.3

        # Credibility impact
        if data_point.credibility_score is not None:
            impact += data_point.credibility_score * 0.2

        # Data type impact
        type_impacts = {
            AlternativeDataType.EARNINGS_CALL: 0.8,
            AlternativeDataType.NEWS: 0.6,
            AlternativeDataType.INSIDER_TRADING: 0.9,
            AlternativeDataType.OPTION_FLOW: 0.7,
            AlternativeDataType.SOCIAL_MEDIA: 0.3
        }

        impact += type_impacts.get(data_point.data_type, 0.2)

        # Timeliness impact
        age_hours = (datetime.now() - data_point.event_timestamp).total_seconds() / 3600
        timeliness_factor = max(0.1, 1.0 - age_hours / 24)  # Decay over 24 hours
        impact *= timeliness_factor

        return min(1.0, impact)

    async def _notify_subscribers(self, data_point: AlternativeDataPoint) -> None:
        """Notify subscribers of new processed data"""

        # Call data callbacks
        for callback in self._data_callbacks:
            try:
                await callback(data_point)
            except Exception as e:
                logger.warning(f"Data callback error: {e}")

        # Check subscriptions
        for subscription_id, subscription in self._subscriptions.items():
            if self._matches_subscription(data_point, subscription):
                if subscription.get('callback'):
                    try:
                        await subscription['callback'](data_point)
                    except Exception as e:
                        logger.warning(f"Subscription callback error: {e}")

    def _matches_subscription(self, data_point: AlternativeDataPoint, subscription: Dict[str, Any]) -> bool:
        """Check if data point matches subscription criteria"""

        # Symbol filter
        if 'symbols' in subscription:
            if data_point.symbol not in subscription['symbols']:
                return False

        # Data type filter
        if 'data_types' in subscription:
            if data_point.data_type not in subscription['data_types']:
                return False

        # Quality thresholds
        if 'min_relevance' in subscription:
            if data_point.relevance_score is None or data_point.relevance_score < subscription['min_relevance']:
                return False

        if 'min_credibility' in subscription:
            if data_point.credibility_score is None or data_point.credibility_score < subscription['min_credibility']:
                return False

        return True

    async def _periodic_scraping(self) -> None:
        """Periodic web scraping"""

        while True:
            try:
                await asyncio.sleep(DataIntervals.WEB_SCRAPING_SECONDS)

                # Scrape registered targets
                for target_id in self.web_scraper._scraping_targets:
                    try:
                        scraped_data = await self.web_scraper.scrape_target(target_id)

                        # Process scraped items
                        for item in scraped_data:
                            await self.ingest_data(
                                raw_content=item.get('content', ''),
                                data_type=AlternativeDataType.WEB_SCRAPING,
                                provider=DataProvider.CUSTOM_SCRAPER,
                                metadata={
                                    'title': item.get('title'),
                                    'source_url': item.get('url'),
                                    'author': item.get('author'),
                                    'category': item.get('category'),
                                    'scraping_target': target_id
                                }
                            )

                        with self._lock:
                            self._processing_stats['web_scraping_sessions'] += 1

                    except Exception as e:
                        logger.error(f"Error scraping target {target_id}: {e}")

            except Exception as e:
                logger.error(f"Error in periodic scraping: {e}")
                await asyncio.sleep(60)

    async def _cleanup_old_data(self) -> None:
        """Cleanup old data to manage memory"""

        while True:
            try:
                await asyncio.sleep(DataIntervals.DATA_CLEANUP_SECONDS)

                cutoff_time = datetime.now() - timedelta(days=DataRetention.ALT_DATA_RETENTION_DAYS)

                with self._lock:
                    # Cleanup by symbol
                    for symbol_data in self._data_by_symbol.values():
                        while symbol_data and symbol_data[0].ingestion_timestamp < cutoff_time:
                            symbol_data.popleft()

                    # Cleanup by type
                    for type_data in self._data_by_type.values():
                        while type_data and type_data[0].ingestion_timestamp < cutoff_time:
                            type_data.popleft()

                logger.info("Completed alternative data cleanup")

            except Exception as e:
                logger.error(f"Error in data cleanup: {e}")
                await asyncio.sleep(DataIntervals.DATA_CLEANUP_SECONDS)

    async def subscribe_to_data(
        self,
        symbols: Optional[List[str]] = None,
        data_types: Optional[List[AlternativeDataType]] = None,
        callback: Optional[Callable] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Subscribe to alternative data updates"""

        subscription_id = f"alt_sub_{int(time.time() * 1000)}"

        subscription = {
            'subscription_id': subscription_id,
            'symbols': symbols,
            'data_types': data_types,
            'callback': callback,
            'created_time': datetime.now()
        }

        if filters:
            subscription.update(filters)

        with self._lock:
            self._subscriptions[subscription_id] = subscription

        logger.info(f"Created alternative data subscription: {subscription_id}")

        return subscription_id

    def add_data_callback(self, callback: Callable) -> None:
        """Add data callback"""
        self._data_callbacks.append(callback)

    async def get_data_by_symbol(
        self,
        symbol: str,
        data_types: Optional[List[AlternativeDataType]] = None,
        hours: int = 24
    ) -> List[AlternativeDataPoint]:
        """Get alternative data for symbol"""

        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            symbol_data = list(self._data_by_symbol.get(symbol, []))

        # Filter by time and data types
        filtered_data = [
            data_point for data_point in symbol_data
            if (data_point.ingestion_timestamp >= cutoff_time and
                (not data_types or data_point.data_type in data_types))
        ]

        # Sort by timestamp (newest first)
        filtered_data.sort(key=lambda x: x.ingestion_timestamp, reverse=True)

        return filtered_data

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        with self._lock:
            return self._processing_stats.copy()

    def get_data_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get data summary"""

        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_data = [
                data_point for data_point in self._processed_data
                if data_point.ingestion_timestamp >= cutoff_time
            ]

        if not recent_data:
            return {'message': 'No recent data available'}

        # Calculate statistics
        sentiment_scores = [dp.sentiment_score for dp in recent_data if dp.sentiment_score is not None]
        relevance_scores = [dp.relevance_score for dp in recent_data if dp.relevance_score is not None]
        credibility_scores = [dp.credibility_score for dp in recent_data if dp.credibility_score is not None]

        # Data by type
        type_counts = defaultdict(int)
        for data_point in recent_data:
            type_counts[data_point.data_type.value] += 1

        # Data by provider
        provider_counts = defaultdict(int)
        for data_point in recent_data:
            provider_counts[data_point.provider.value] += 1

        return {
            'total_data_points': len(recent_data),
            'average_sentiment': np.mean(sentiment_scores) if sentiment_scores else None,
            'average_relevance': np.mean(relevance_scores) if relevance_scores else None,
            'average_credibility': np.mean(credibility_scores) if credibility_scores else None,
            'data_by_type': dict(type_counts),
            'data_by_provider': dict(provider_counts),
            'processing_stats': self._processing_stats.copy()
        }

    async def cleanup(self) -> None:
        """Cleanup alternative data handler resources"""

        # Cancel processing tasks
        for task in self._processing_tasks:
            task.cancel()

        # Clear data
        with self._lock:
            self._raw_data.clear()
            self._processed_data.clear()
            self._data_by_symbol.clear()
            self._data_by_type.clear()
            self._subscriptions.clear()

        logger.info("AlternativeDataHandler cleanup completed")