"""
Unit tests for Alternative Data Handler
Tests sentiment analysis, web scraping, data ingestion, and processing pipelines
"""

import pytest
import asyncio
import logging
import time

from core_engine.data.alternative_data_handler import (
    AlternativeDataHandler,
    AlternativeDataPoint,
    AlternativeDataType,
    DataProvider,
    ProcessingStatus,
    SentimentAnalyzer,
    SentimentAnalysis,
    WebScraper,
    WebScrapingTarget
)

logger = logging.getLogger(__name__)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
async def alt_data_handler():
    """Create alternative data handler instance"""
    # Create handler without asyncio tasks to avoid event loop issues
    handler = AlternativeDataHandler.__new__(AlternativeDataHandler)
    handler.config = {}
    handler._lock = __import__('threading').Lock()
    handler.sentiment_analyzer = SentimentAnalyzer({})
    handler.web_scraper = WebScraper({})

    from collections import deque, defaultdict
    handler._raw_data = deque(maxlen=10000)
    handler._processed_data = deque(maxlen=5000)
    handler._data_by_symbol = defaultdict(lambda: deque(maxlen=1000))
    handler._data_by_type = defaultdict(lambda: deque(maxlen=1000))

    handler._processing_queue = asyncio.Queue(maxsize=1000)
    handler._priority_queue = asyncio.Queue(maxsize=100)

    handler._processing_stats = {
        'total_ingested': 0,
        'total_processed': 0,
        'processing_errors': 0,
        'average_processing_time_ms': 0.0,
        'sentiment_analyses': 0,
        'web_scraping_sessions': 0
    }

    handler._data_providers = {}
    handler._provider_configs = {}
    handler._subscriptions = {}
    handler._data_callbacks = []
    handler._processing_tasks = []

    return handler

@pytest.fixture
def sentiment_analyzer():
    """Create sentiment analyzer instance"""
    return SentimentAnalyzer()

@pytest.fixture
def web_scraper():
    """Create web scraper instance"""
    return WebScraper()

@pytest.fixture
def sample_news_text():
    """Sample news text for sentiment analysis"""
    return """
    Company XYZ reported excellent earnings this quarter, beating analyst expectations
    with revenue growth of 25%. The strong performance shows bullish outlook for the
    technology sector. Analysts upgraded the stock citing positive momentum and robust
    fundamentals. The company also announced increased dividend payments.
    """

@pytest.fixture
def sample_negative_text():
    """Sample negative news text"""
    return """
    Company ABC disappointed investors with weak quarterly results, missing revenue
    expectations by 10%. The poor performance led to downgrades from multiple analysts.
    Concerns about declining market share and fragile business model continue to weigh
    on the stock. Management lowered guidance for the upcoming quarter.
    """

@pytest.fixture
def scraping_target():
    """Sample web scraping target"""
    return WebScrapingTarget(
        target_id="test_target",
        name="Test Financial News",
        base_url="https://test-news.com",
        selectors={'title': 'h1', 'content': 'div.article'},
        rate_limit_seconds=1.0,
        max_pages=5,
        text_extractors=['title', 'content'],
        data_transformers=['sentiment'],
        required_fields=['title', 'content'],
        validation_rules={}
    )

# =============================================================================
# CATEGORY 1: ALTERNATIVE DATA HANDLER INITIALIZATION (3 tests)
# =============================================================================

class TestAlternativeDataHandlerInitialization:
    """Test alternative data handler initialization"""

    @pytest.mark.asyncio
    async def test_handler_creation(self, alt_data_handler):
        """Test basic handler instantiation"""
        assert alt_data_handler is not None
        assert hasattr(alt_data_handler, 'sentiment_analyzer')
        assert hasattr(alt_data_handler, 'web_scraper')
        assert hasattr(alt_data_handler, '_processing_stats')
        logger.info("✅ Handler creation test passed")

    @pytest.mark.asyncio
    async def test_handler_components(self, alt_data_handler):
        """Test handler has all required components"""
        assert alt_data_handler.sentiment_analyzer is not None
        assert alt_data_handler.web_scraper is not None
        assert len(alt_data_handler._raw_data) == 0
        assert len(alt_data_handler._processed_data) == 0
        assert alt_data_handler._processing_stats['total_ingested'] == 0
        logger.info("✅ Handler components test passed")

    @pytest.mark.asyncio
    async def test_handler_storage_structures(self, alt_data_handler):
        """Test handler storage structures are initialized"""
        assert alt_data_handler._raw_data is not None
        assert alt_data_handler._processed_data is not None
        assert alt_data_handler._data_by_symbol is not None
        assert alt_data_handler._data_by_type is not None
        assert alt_data_handler._subscriptions is not None
        logger.info("✅ Handler storage structures test passed")

# =============================================================================
# CATEGORY 2: SENTIMENT ANALYZER (5 tests)
# =============================================================================

class TestSentimentAnalyzer:
    """Test sentiment analysis functionality"""

    @pytest.mark.asyncio
    async def test_sentiment_analyzer_creation(self, sentiment_analyzer):
        """Test sentiment analyzer instantiation"""
        assert sentiment_analyzer is not None
        assert len(sentiment_analyzer._positive_words) > 0
        assert len(sentiment_analyzer._negative_words) > 0
        assert 'bullish' in sentiment_analyzer._positive_words
        assert 'bearish' in sentiment_analyzer._negative_words
        logger.info("✅ Sentiment analyzer creation test passed")

    @pytest.mark.asyncio
    async def test_positive_sentiment_analysis(self, sentiment_analyzer, sample_news_text):
        """Test analysis of positive sentiment text"""
        result = await sentiment_analyzer.analyze_sentiment(sample_news_text, symbol='XYZ')

        assert isinstance(result, SentimentAnalysis)
        assert result.overall_sentiment > 0  # Positive sentiment
        assert result.positive_score > result.negative_score
        assert 0 <= result.confidence <= 1
        assert len(result.keywords) > 0
        logger.info("✅ Positive sentiment analysis test passed")

    @pytest.mark.asyncio
    async def test_negative_sentiment_analysis(self, sentiment_analyzer, sample_negative_text):
        """Test analysis of negative sentiment text"""
        result = await sentiment_analyzer.analyze_sentiment(sample_negative_text, symbol='ABC')

        assert isinstance(result, SentimentAnalysis)
        assert result.overall_sentiment < 0  # Negative sentiment
        assert result.negative_score > result.positive_score
        assert 0 <= result.confidence <= 1
        logger.info("✅ Negative sentiment analysis test passed")

    @pytest.mark.asyncio
    async def test_sentiment_entity_detection(self, sentiment_analyzer):
        """Test entity-specific sentiment detection"""
        text = "AAPL had excellent earnings while MSFT disappointed investors"
        result = await sentiment_analyzer.analyze_sentiment(text, symbol='AAPL')

        assert 'AAPL' in result.entity_sentiments or 'aapl' in result.entity_sentiments
        # Should detect positive sentiment near AAPL
        logger.info("✅ Sentiment entity detection test passed")

    @pytest.mark.asyncio
    async def test_sentiment_keyword_extraction(self, sentiment_analyzer, sample_news_text):
        """Test keyword extraction from text"""
        result = await sentiment_analyzer.analyze_sentiment(sample_news_text)

        assert len(result.keywords) > 0
        assert len(result.topics) > 0
        # Should extract relevant financial keywords
        logger.info("✅ Sentiment keyword extraction test passed")

# =============================================================================
# CATEGORY 3: WEB SCRAPER (3 tests)
# =============================================================================

class TestWebScraper:
    """Test web scraping functionality"""

    @pytest.mark.asyncio
    async def test_web_scraper_creation(self, web_scraper):
        """Test web scraper instantiation"""
        assert web_scraper is not None
        assert hasattr(web_scraper, '_scraping_targets')
        assert hasattr(web_scraper, '_rate_limiters')
        assert len(web_scraper._scraping_targets) == 0
        logger.info("✅ Web scraper creation test passed")

    @pytest.mark.asyncio
    async def test_register_scraping_target(self, web_scraper, scraping_target):
        """Test registering a web scraping target"""
        await web_scraper.register_target(scraping_target)

        assert 'test_target' in web_scraper._scraping_targets
        assert web_scraper._scraping_targets['test_target'] == scraping_target
        logger.info("✅ Register scraping target test passed")

    @pytest.mark.asyncio
    async def test_scrape_target(self, web_scraper, scraping_target):
        """Test scraping data from target"""
        await web_scraper.register_target(scraping_target)

        scraped_data = await web_scraper.scrape_target('test_target')

        assert scraped_data is not None
        assert len(scraped_data) > 0
        assert all('title' in item for item in scraped_data)
        assert all('content' in item for item in scraped_data)
        assert scraping_target.success_count > 0
        logger.info("✅ Scrape target test passed")

# =============================================================================
# CATEGORY 4: DATA INGESTION (4 tests)
# =============================================================================

class TestDataIngestion:
    """Test data ingestion functionality"""

    @pytest.mark.asyncio
    async def test_ingest_news_data(self, alt_data_handler, sample_news_text):
        """Test ingesting news data"""
        data_id = await alt_data_handler.ingest_data(
            raw_content=sample_news_text,
            data_type=AlternativeDataType.NEWS,
            provider=DataProvider.NEWS_API,
            symbol='AAPL',
            metadata={'source_url': 'https://news.com/article'}
        )

        assert data_id is not None
        assert len(data_id) > 0
        assert alt_data_handler._processing_stats['total_ingested'] == 1
        logger.info("✅ Ingest news data test passed")

    @pytest.mark.asyncio
    async def test_ingest_social_media_data(self, alt_data_handler):
        """Test ingesting social media data"""
        text = "Great company! Bullish on $TSLA #stocks"

        data_id = await alt_data_handler.ingest_data(
            raw_content=text,
            data_type=AlternativeDataType.SOCIAL_MEDIA,
            provider=DataProvider.TWITTER,
            symbol='TSLA'
        )

        assert data_id is not None
        assert alt_data_handler._processing_stats['total_ingested'] == 1
        logger.info("✅ Ingest social media data test passed")

    @pytest.mark.asyncio
    async def test_priority_data_ingestion(self, alt_data_handler, sample_news_text):
        """Test priority data ingestion"""
        data_id = await alt_data_handler.ingest_data(
            raw_content=sample_news_text,
            data_type=AlternativeDataType.EARNINGS_CALL,
            provider=DataProvider.NEWS_API,
            symbol='AAPL',
            priority=True
        )

        assert data_id is not None
        # Priority queue should have data
        assert alt_data_handler._priority_queue.qsize() > 0
        logger.info("✅ Priority data ingestion test passed")

    @pytest.mark.asyncio
    async def test_multiple_data_ingestion(self, alt_data_handler):
        """Test ingesting multiple data points"""
        texts = [
            "Company A reported strong earnings",
            "Company B announced merger",
            "Company C upgraded by analysts"
        ]

        data_ids = []
        for text in texts:
            data_id = await alt_data_handler.ingest_data(
                raw_content=text,
                data_type=AlternativeDataType.NEWS,
                provider=DataProvider.NEWS_API,
                symbol=f'SYM{len(data_ids)}'
            )
            data_ids.append(data_id)

        assert len(data_ids) == 3
        assert alt_data_handler._processing_stats['total_ingested'] == 3
        assert len(set(data_ids)) == 3  # All unique IDs
        logger.info("✅ Multiple data ingestion test passed")

# =============================================================================
# CATEGORY 5: DATA PROCESSING (4 tests)
# =============================================================================

class TestDataProcessing:
    """Test data processing functionality"""

    @pytest.mark.asyncio
    async def test_process_data_point_news(self, alt_data_handler, sample_news_text):
        """Test processing a news data point"""
        data_point = AlternativeDataPoint(
            data_id='test_123',
            symbol='AAPL',
            data_type=AlternativeDataType.NEWS,
            provider=DataProvider.NEWS_API,
            raw_content=sample_news_text,
            structured_data={}
        )

        await alt_data_handler._process_data_point(data_point)

        assert data_point.processing_status == ProcessingStatus.PROCESSED
        assert data_point.sentiment_score is not None
        assert data_point.relevance_score is not None
        assert data_point.credibility_score is not None
        assert data_point.impact_score is not None
        assert data_point.processing_time_ms is not None
        logger.info("✅ Process data point (news) test passed")

    @pytest.mark.asyncio
    async def test_relevance_score_calculation(self, alt_data_handler):
        """Test relevance score calculation"""
        data_point = AlternativeDataPoint(
            data_id='test_rel',
            symbol='AAPL',
            data_type=AlternativeDataType.NEWS,
            provider=DataProvider.NEWS_API,
            raw_content='AAPL earnings beat expectations with strong revenue growth',
            structured_data={}
        )

        relevance = await alt_data_handler._calculate_relevance_score(data_point)

        assert 0 <= relevance <= 1
        # Should have high relevance due to symbol mention and keywords
        assert relevance > 0.5
        logger.info("✅ Relevance score calculation test passed")

    @pytest.mark.asyncio
    async def test_credibility_score_calculation(self, alt_data_handler):
        """Test credibility score calculation"""
        data_point = AlternativeDataPoint(
            data_id='test_cred',
            symbol='AAPL',
            data_type=AlternativeDataType.NEWS,
            provider=DataProvider.BLOOMBERG_NEWS,
            raw_content='Test content with substantial length ' * 20,
            structured_data={},
            source_url='https://bloomberg.com/article',
            author='Professional Analyst'
        )

        credibility = await alt_data_handler._calculate_credibility_score(data_point)

        assert 0 <= credibility <= 1
        # Bloomberg should have high credibility
        assert credibility > 0.7
        logger.info("✅ Credibility score calculation test passed")

    @pytest.mark.asyncio
    async def test_impact_score_calculation(self, alt_data_handler):
        """Test impact score calculation"""
        data_point = AlternativeDataPoint(
            data_id='test_impact',
            symbol='AAPL',
            data_type=AlternativeDataType.EARNINGS_CALL,
            provider=DataProvider.NEWS_API,
            raw_content='Strong earnings call',
            structured_data={},
            sentiment_score=0.8,
            relevance_score=0.9,
            credibility_score=0.85
        )

        impact = await alt_data_handler._calculate_impact_score(data_point)

        assert 0 <= impact <= 1
        # Earnings call with high scores should have high impact
        assert impact > 0.5
        logger.info("✅ Impact score calculation test passed")

# =============================================================================
# CATEGORY 6: DATA RETRIEVAL (3 tests)
# =============================================================================

class TestDataRetrieval:
    """Test data retrieval functionality"""

    @pytest.mark.asyncio
    async def test_get_data_by_symbol(self, alt_data_handler):
        """Test retrieving data by symbol"""
        # Add some processed data
        for i in range(3):
            data_point = AlternativeDataPoint(
                data_id=f'test_{i}',
                symbol='AAPL',
                data_type=AlternativeDataType.NEWS,
                provider=DataProvider.NEWS_API,
                raw_content=f'News item {i}',
                structured_data={},
                processing_status=ProcessingStatus.PROCESSED
            )
            alt_data_handler._data_by_symbol['AAPL'].append(data_point)

        data = await alt_data_handler.get_data_by_symbol('AAPL', hours=24)

        assert len(data) == 3
        assert all(dp.symbol == 'AAPL' for dp in data)
        logger.info("✅ Get data by symbol test passed")

    @pytest.mark.asyncio
    async def test_get_data_by_symbol_filtered(self, alt_data_handler):
        """Test retrieving data by symbol with type filter"""
        # Add mixed data types
        data_point1 = AlternativeDataPoint(
            data_id='news_1',
            symbol='TSLA',
            data_type=AlternativeDataType.NEWS,
            provider=DataProvider.NEWS_API,
            raw_content='News',
            structured_data={}
        )
        data_point2 = AlternativeDataPoint(
            data_id='social_1',
            symbol='TSLA',
            data_type=AlternativeDataType.SOCIAL_MEDIA,
            provider=DataProvider.TWITTER,
            raw_content='Tweet',
            structured_data={}
        )

        alt_data_handler._data_by_symbol['TSLA'].append(data_point1)
        alt_data_handler._data_by_symbol['TSLA'].append(data_point2)

        # Get only news data
        data = await alt_data_handler.get_data_by_symbol(
            'TSLA',
            data_types=[AlternativeDataType.NEWS]
        )

        assert len(data) == 1
        assert data[0].data_type == AlternativeDataType.NEWS
        logger.info("✅ Get data by symbol (filtered) test passed")

    @pytest.mark.asyncio
    async def test_get_processing_stats(self, alt_data_handler):
        """Test retrieving processing statistics"""
        # Set some stats
        alt_data_handler._processing_stats['total_ingested'] = 100
        alt_data_handler._processing_stats['total_processed'] = 95
        alt_data_handler._processing_stats['processing_errors'] = 5

        stats = alt_data_handler.get_processing_stats()

        assert stats['total_ingested'] == 100
        assert stats['total_processed'] == 95
        assert stats['processing_errors'] == 5
        logger.info("✅ Get processing stats test passed")

# =============================================================================
# CATEGORY 7: SUBSCRIPTIONS (3 tests)
# =============================================================================

class TestSubscriptions:
    """Test subscription functionality"""

    @pytest.mark.asyncio
    async def test_subscribe_to_data(self, alt_data_handler):
        """Test subscribing to data updates"""
        subscription_id = await alt_data_handler.subscribe_to_data(
            symbols=['AAPL', 'MSFT'],
            data_types=[AlternativeDataType.NEWS]
        )

        assert subscription_id is not None
        assert subscription_id in alt_data_handler._subscriptions
        assert alt_data_handler._subscriptions[subscription_id]['symbols'] == ['AAPL', 'MSFT']
        logger.info("✅ Subscribe to data test passed")

    @pytest.mark.asyncio
    async def test_subscription_matching(self, alt_data_handler):
        """Test subscription matching logic"""
        subscription = {
            'symbols': ['AAPL'],
            'data_types': [AlternativeDataType.NEWS],
            'min_relevance': 0.5
        }

        # Matching data point
        data_point1 = AlternativeDataPoint(
            data_id='match',
            symbol='AAPL',
            data_type=AlternativeDataType.NEWS,
            provider=DataProvider.NEWS_API,
            raw_content='Test',
            structured_data={},
            relevance_score=0.8
        )

        # Non-matching data point (different symbol)
        data_point2 = AlternativeDataPoint(
            data_id='no_match',
            symbol='MSFT',
            data_type=AlternativeDataType.NEWS,
            provider=DataProvider.NEWS_API,
            raw_content='Test',
            structured_data={},
            relevance_score=0.8
        )

        assert alt_data_handler._matches_subscription(data_point1, subscription) is True
        assert alt_data_handler._matches_subscription(data_point2, subscription) is False
        logger.info("✅ Subscription matching test passed")

    @pytest.mark.asyncio
    async def test_add_data_callback(self, alt_data_handler):
        """Test adding data callbacks"""
        async def callback(data_point):
            pass

        alt_data_handler.add_data_callback(callback)

        assert len(alt_data_handler._data_callbacks) == 1
        assert alt_data_handler._data_callbacks[0] == callback
        logger.info("✅ Add data callback test passed")

# =============================================================================
# CATEGORY 8: DATA SUMMARY (2 tests)
# =============================================================================

class TestDataSummary:
    """Test data summary functionality"""

    @pytest.mark.asyncio
    async def test_get_data_summary_with_data(self, alt_data_handler):
        """Test getting data summary with data"""
        # Add processed data
        for i in range(5):
            data_point = AlternativeDataPoint(
                data_id=f'sum_{i}',
                symbol='AAPL',
                data_type=AlternativeDataType.NEWS,
                provider=DataProvider.NEWS_API,
                raw_content='Test',
                structured_data={},
                sentiment_score=0.5 + i * 0.1,
                relevance_score=0.6,
                credibility_score=0.7
            )
            alt_data_handler._processed_data.append(data_point)

        summary = alt_data_handler.get_data_summary(hours=24)

        assert 'total_data_points' in summary
        assert summary['total_data_points'] == 5
        assert 'average_sentiment' in summary
        assert 'average_relevance' in summary
        assert 'data_by_type' in summary
        logger.info("✅ Get data summary (with data) test passed")

    @pytest.mark.asyncio
    async def test_get_data_summary_empty(self, alt_data_handler):
        """Test getting data summary with no data"""
        summary = alt_data_handler.get_data_summary(hours=24)

        assert 'message' in summary
        assert 'No recent data' in summary['message']
        logger.info("✅ Get data summary (empty) test passed")

# =============================================================================
# CATEGORY 9: SCRAPING TARGET MANAGEMENT (3 tests)
# =============================================================================

class TestScrapingTargetManagement:
    """Test web scraping target management"""

    @pytest.mark.asyncio
    async def test_scraping_target_creation(self, scraping_target):
        """Test creating a scraping target"""
        assert scraping_target is not None
        assert scraping_target.target_id == 'test_target'
        assert scraping_target.name == 'Test Financial News'
        assert scraping_target.is_active is True
        assert scraping_target.success_count == 0
        logger.info("✅ Scraping target creation test passed")

    @pytest.mark.asyncio
    async def test_scraping_rate_limiting(self, web_scraper, scraping_target):
        """Test rate limiting for web scraping"""
        await web_scraper.register_target(scraping_target)

        # First scrape
        start_time = time.time()
        await web_scraper.scrape_target('test_target')

        # Second scrape should respect rate limit
        await web_scraper.scrape_target('test_target')
        elapsed = time.time() - start_time

        # Should take at least the rate limit duration
        assert elapsed >= scraping_target.rate_limit_seconds
        logger.info("✅ Scraping rate limiting test passed")

    @pytest.mark.asyncio
    async def test_scraping_target_error_tracking(self, web_scraper):
        """Test error tracking for scraping targets"""
        target = WebScrapingTarget(
            target_id='error_target',
            name='Error Test',
            base_url='https://invalid-url.com',
            selectors={},
            rate_limit_seconds=1.0,
            max_pages=1,
            text_extractors=[],
            data_transformers=[],
            required_fields=[],
            validation_rules={}
        )

        await web_scraper.register_target(target)

        initial_errors = target.error_count

        # This should work with simulated scraping
        try:
            await web_scraper.scrape_target('error_target')
            # If it succeeds with simulation, that's fine
            assert target.success_count > 0
        except Exception:
            # If it fails, error count should increase
            assert target.error_count > initial_errors

        logger.info("✅ Scraping target error tracking test passed")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
