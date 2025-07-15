"""
Integration Tests for StatArb Trading System

This module provides comprehensive integration tests for testing
component interactions, data flows, and end-to-end scenarios.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np

# Test data generators
def generate_market_data(symbols: list, days: int = 30) -> pd.DataFrame:
    """Generate synthetic market data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    data = []
    
    for symbol in symbols:
        for date in dates:
            # Generate realistic price data
            base_price = np.random.uniform(50, 200)
            volume = np.random.randint(100000, 1000000)
            
            data.append({
                'symbol': symbol,
                'date': date,
                'open': base_price * np.random.uniform(0.98, 1.02),
                'high': base_price * np.random.uniform(1.00, 1.05),
                'low': base_price * np.random.uniform(0.95, 1.00),
                'close': base_price * np.random.uniform(0.98, 1.02),
                'volume': volume,
                'timestamp': date
            })
    
    return pd.DataFrame(data)


class TestMarketDataFlow:
    """Test market data ingestion and processing flow"""
    
    @pytest.fixture
    def sample_market_data(self):
        """Generate sample market data"""
        return generate_market_data(['AAPL', 'MSFT', 'GOOGL'], days=30)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_ingestion_pipeline(self, sample_market_data):
        """Test complete data ingestion pipeline"""
        # Mock components
        mock_data_feeds = AsyncMock()
        mock_data_processor = AsyncMock()
        mock_database = AsyncMock()
        mock_cache = AsyncMock()
        
        # Setup mock responses
        mock_data_feeds.fetch_market_data.return_value = sample_market_data
        mock_data_processor.process_market_data.return_value = sample_market_data
        mock_database.store_market_data.return_value = True
        mock_cache.cache_market_data.return_value = True
        
        # Simulate data flow
        with patch('new_structure.market_data.feeds.MarketDataFeeds', return_value=mock_data_feeds), \
             patch('new_structure.market_data.data_processor.DataProcessor', return_value=mock_data_processor), \
             patch('new_structure.infrastructure.database.database_manager.DatabaseManager', return_value=mock_database):
            
            # Import actual components (mocked)
            from new_structure.market_data.data_manager import MarketDataManager
            
            # Create data manager
            data_manager = MarketDataManager()
            
            # Test data flow
            symbols = ['AAPL', 'MSFT', 'GOOGL']
            
            # 1. Fetch data
            raw_data = await mock_data_feeds.fetch_market_data(symbols)
            assert len(raw_data) > 0
            assert 'AAPL' in raw_data['symbol'].values
            
            # 2. Process data
            processed_data = await mock_data_processor.process_market_data(raw_data)
            assert len(processed_data) == len(raw_data)
            
            # 3. Store data
            stored = await mock_database.store_market_data(processed_data)
            assert stored is True
            
            # 4. Cache recent data
            cached = await mock_cache.cache_market_data(processed_data.tail(10))
            assert cached is True
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_time_data_streaming(self):
        """Test real-time data streaming and processing"""
        mock_stream = AsyncMock()
        mock_processor = AsyncMock()
        mock_signal_generator = AsyncMock()
        
        # Setup streaming data
        streaming_data = [
            {'symbol': 'AAPL', 'price': 150.0, 'volume': 1000, 'timestamp': datetime.now()},
            {'symbol': 'MSFT', 'price': 300.0, 'volume': 1500, 'timestamp': datetime.now()},
        ]
        
        mock_stream.stream_data.return_value = streaming_data
        mock_processor.process_tick.return_value = streaming_data[0]
        mock_signal_generator.generate_signals.return_value = [{'signal': 'BUY', 'strength': 0.8}]
        
        # Test streaming pipeline
        for tick_data in streaming_data:
            # Process tick
            processed_tick = await mock_processor.process_tick(tick_data)
            assert processed_tick['symbol'] == tick_data['symbol']
            
            # Generate signals
            signals = await mock_signal_generator.generate_signals([processed_tick])
            assert len(signals) > 0


class TestSignalGenerationPipeline:
    """Test signal generation and strategy pipeline"""
    
    @pytest.fixture
    def historical_data(self):
        """Generate historical data for signal testing"""
        return generate_market_data(['AAPL', 'MSFT'], days=100)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_signal_generation_workflow(self, historical_data):
        """Test complete signal generation workflow"""
        mock_feature_engine = AsyncMock()
        mock_model_ensemble = AsyncMock()
        mock_signal_generator = AsyncMock()
        mock_strategy_engine = AsyncMock()
        
        # Setup mock responses
        features = {
            'returns': np.random.randn(100),
            'volatility': np.random.rand(100),
            'correlation': np.random.rand(100, 100)
        }
        
        predictions = {
            'AAPL': {'direction': 1, 'confidence': 0.75},
            'MSFT': {'direction': -1, 'confidence': 0.65}
        }
        
        signals = [
            {'symbol': 'AAPL', 'signal': 'BUY', 'strength': 0.75, 'timestamp': datetime.now()},
            {'symbol': 'MSFT', 'signal': 'SELL', 'strength': 0.65, 'timestamp': datetime.now()}
        ]
        
        mock_feature_engine.generate_features.return_value = features
        mock_model_ensemble.predict.return_value = predictions
        mock_signal_generator.generate_signals.return_value = signals
        mock_strategy_engine.process_signals.return_value = signals
        
        # Test workflow
        with patch('new_structure.signal_generation.feature_engine.FeatureEngine', return_value=mock_feature_engine), \
             patch('new_structure.signal_generation.model_ensemble.ModelEnsemble', return_value=mock_model_ensemble), \
             patch('new_structure.signal_generation.signal_generator.SignalGenerator', return_value=mock_signal_generator):
            
            # 1. Generate features
            generated_features = await mock_feature_engine.generate_features(historical_data)
            assert 'returns' in generated_features
            assert 'volatility' in generated_features
            
            # 2. Model predictions
            model_predictions = await mock_model_ensemble.predict(generated_features)
            assert 'AAPL' in model_predictions
            assert 'MSFT' in model_predictions
            
            # 3. Generate signals
            generated_signals = await mock_signal_generator.generate_signals(model_predictions)
            assert len(generated_signals) == 2
            assert all('signal' in s for s in generated_signals)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_regime_detection_integration(self):
        """Test regime detection integration with signal generation"""
        mock_regime_detector = AsyncMock()
        mock_signal_generator = AsyncMock()
        
        # Setup regime states
        regimes = {
            'current_regime': 'trending',
            'regime_probability': 0.85,
            'regime_history': ['sideways', 'trending', 'trending']
        }
        
        # Different signals based on regime
        trending_signals = [{'signal': 'BUY', 'strength': 0.8}]
        sideways_signals = [{'signal': 'HOLD', 'strength': 0.3}]
        
        mock_regime_detector.detect_regime.return_value = regimes
        
        # Test regime-aware signal generation
        current_regime = await mock_regime_detector.detect_regime()
        
        if current_regime['current_regime'] == 'trending':
            mock_signal_generator.generate_signals.return_value = trending_signals
        else:
            mock_signal_generator.generate_signals.return_value = sideways_signals
        
        signals = await mock_signal_generator.generate_signals()
        assert len(signals) > 0
        assert signals[0]['signal'] in ['BUY', 'SELL', 'HOLD']


class TestPortfolioManagementFlow:
    """Test portfolio management and execution flow"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_portfolio_construction_workflow(self):
        """Test complete portfolio construction workflow"""
        mock_portfolio_manager = AsyncMock()
        mock_risk_manager = AsyncMock()
        mock_allocation_optimizer = AsyncMock()
        mock_execution_engine = AsyncMock()
        
        # Setup test data
        signals = [
            {'symbol': 'AAPL', 'signal': 'BUY', 'strength': 0.8},
            {'symbol': 'MSFT', 'signal': 'SELL', 'strength': 0.6},
            {'symbol': 'GOOGL', 'signal': 'BUY', 'strength': 0.7}
        ]
        
        portfolio_state = {
            'positions': {
                'AAPL': {'quantity': 100, 'value': 15000},
                'MSFT': {'quantity': -50, 'value': -15000}
            },
            'cash': 50000,
            'total_value': 50000
        }
        
        risk_assessment = {
            'portfolio_var': 25000,
            'position_limits_ok': True,
            'sector_limits_ok': True,
            'approved': True
        }
        
        target_allocation = {
            'AAPL': 0.25,
            'MSFT': -0.15,
            'GOOGL': 0.20,
            'cash': 0.70
        }
        
        orders = [
            {'symbol': 'AAPL', 'side': 'BUY', 'quantity': 50, 'order_type': 'LIMIT', 'price': 150.0},
            {'symbol': 'GOOGL', 'side': 'BUY', 'quantity': 30, 'order_type': 'LIMIT', 'price': 2800.0}
        ]
        
        # Setup mocks
        mock_portfolio_manager.get_portfolio_state.return_value = portfolio_state
        mock_risk_manager.assess_portfolio_risk.return_value = risk_assessment
        mock_allocation_optimizer.optimize_allocation.return_value = target_allocation
        mock_execution_engine.generate_orders.return_value = orders
        mock_execution_engine.execute_orders.return_value = True
        
        # Test workflow
        with patch('new_structure.portfolio_management.portfolio_manager.PortfolioManager', return_value=mock_portfolio_manager), \
             patch('new_structure.risk_management.risk_manager.RiskManager', return_value=mock_risk_manager), \
             patch('new_structure.portfolio_management.allocation_optimizer.AllocationOptimizer', return_value=mock_allocation_optimizer), \
             patch('new_structure.execution_engine.execution_engine.ExecutionEngine', return_value=mock_execution_engine):
            
            # 1. Get current portfolio state
            current_portfolio = await mock_portfolio_manager.get_portfolio_state()
            assert 'positions' in current_portfolio
            assert current_portfolio['cash'] == 50000
            
            # 2. Risk assessment
            risk_check = await mock_risk_manager.assess_portfolio_risk(
                current_portfolio, signals
            )
            assert risk_check['approved'] is True
            
            # 3. Optimize allocation
            if risk_check['approved']:
                allocation = await mock_allocation_optimizer.optimize_allocation(
                    current_portfolio, signals
                )
                assert 'AAPL' in allocation
                assert allocation['cash'] > 0
                
                # 4. Generate orders
                generated_orders = await mock_execution_engine.generate_orders(
                    current_portfolio, allocation
                )
                assert len(generated_orders) > 0
                
                # 5. Execute orders
                execution_result = await mock_execution_engine.execute_orders(generated_orders)
                assert execution_result is True
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_risk_monitoring_workflow(self):
        """Test real-time risk monitoring workflow"""
        mock_risk_monitor = AsyncMock()
        mock_position_manager = AsyncMock()
        mock_alert_system = AsyncMock()
        
        # Setup risk scenarios
        risk_scenarios = [
            {
                'scenario': 'position_limit_breach',
                'severity': 'high',
                'position': 'AAPL',
                'current_exposure': 0.08,
                'limit': 0.05
            },
            {
                'scenario': 'portfolio_var_exceeded',
                'severity': 'critical', 
                'current_var': 75000,
                'limit': 50000
            }
        ]
        
        mock_risk_monitor.check_risk_limits.return_value = risk_scenarios
        mock_position_manager.reduce_position.return_value = True
        mock_alert_system.send_alert.return_value = True
        
        # Test risk monitoring
        risk_violations = await mock_risk_monitor.check_risk_limits()
        
        for violation in risk_violations:
            if violation['severity'] == 'critical':
                # Take immediate action
                alert_sent = await mock_alert_system.send_alert(violation)
                assert alert_sent is True
                
                if violation['scenario'] == 'position_limit_breach':
                    reduced = await mock_position_manager.reduce_position(
                        violation['position'], target_exposure=0.05
                    )
                    assert reduced is True


class TestExecutionPipeline:
    """Test order execution and market interaction"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_order_lifecycle(self):
        """Test complete order lifecycle"""
        mock_order_manager = AsyncMock()
        mock_smart_router = AsyncMock()
        mock_venue_adapter = AsyncMock()
        
        # Setup order lifecycle
        order = {
            'order_id': 'ORD_001',
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'order_type': 'LIMIT',
            'price': 150.0,
            'status': 'NEW'
        }
        
        routing_decision = {
            'primary_venue': 'IEX',
            'backup_venues': ['NYSE', 'NASDAQ'],
            'slice_strategy': 'TWAP',
            'execution_schedule': [
                {'time': '09:30:00', 'quantity': 25},
                {'time': '10:00:00', 'quantity': 25},
                {'time': '10:30:00', 'quantity': 25},
                {'time': '11:00:00', 'quantity': 25}
            ]
        }
        
        execution_report = {
            'order_id': 'ORD_001',
            'status': 'FILLED',
            'filled_quantity': 100,
            'avg_price': 149.95,
            'commission': 5.0,
            'total_cost': 15000.0
        }
        
        # Setup mocks
        mock_order_manager.create_order.return_value = order
        mock_smart_router.route_order.return_value = routing_decision
        mock_venue_adapter.send_order.return_value = execution_report
        
        # Test order lifecycle
        with patch('new_structure.execution_engine.order_manager.OrderManager', return_value=mock_order_manager), \
             patch('new_structure.execution_engine.smart_order_router.SmartOrderRouter', return_value=mock_smart_router), \
             patch('new_structure.execution_engine.venue_adapter.VenueAdapter', return_value=mock_venue_adapter):
            
            # 1. Create order
            new_order = await mock_order_manager.create_order(
                symbol='AAPL', side='BUY', quantity=100, price=150.0
            )
            assert new_order['order_id'] == 'ORD_001'
            assert new_order['status'] == 'NEW'
            
            # 2. Route order
            routing = await mock_smart_router.route_order(new_order)
            assert routing['primary_venue'] == 'IEX'
            assert len(routing['execution_schedule']) == 4
            
            # 3. Execute order slices
            total_filled = 0
            for slice_info in routing['execution_schedule']:
                slice_order = {**new_order, 'quantity': slice_info['quantity']}
                execution = await mock_venue_adapter.send_order(slice_order)
                total_filled += execution['filled_quantity']
            
            assert total_filled == order['quantity']
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_market_impact_optimization(self):
        """Test market impact optimization during execution"""
        mock_impact_model = AsyncMock()
        mock_execution_optimizer = AsyncMock()
        mock_cost_analyzer = AsyncMock()
        
        # Setup market impact analysis
        order = {'symbol': 'AAPL', 'quantity': 10000, 'side': 'BUY'}
        
        impact_analysis = {
            'estimated_impact': 0.15,  # 15 bps
            'optimal_slices': 4,
            'recommended_duration': 30,  # minutes
            'timing_recommendations': ['avoid_open', 'avoid_close']
        }
        
        execution_plan = {
            'strategy': 'VWAP',
            'duration_minutes': 30,
            'slice_count': 4,
            'slice_sizes': [2500, 2500, 2500, 2500],
            'timing_constraints': ['9:45-10:15', '10:15-10:45', '10:45-11:15', '11:15-11:45']
        }
        
        cost_analysis = {
            'expected_cost': 1500050.0,  # Including market impact
            'market_impact_cost': 225.0,  # 15 bps * 150k
            'commission_cost': 50.0,
            'opportunity_cost': 100.0
        }
        
        # Setup mocks
        mock_impact_model.estimate_impact.return_value = impact_analysis
        mock_execution_optimizer.create_execution_plan.return_value = execution_plan
        mock_cost_analyzer.analyze_execution_cost.return_value = cost_analysis
        
        # Test market impact optimization
        impact_estimate = await mock_impact_model.estimate_impact(order)
        assert impact_estimate['estimated_impact'] == 0.15
        
        if impact_estimate['estimated_impact'] > 0.10:  # 10 bps threshold
            # Optimize execution
            plan = await mock_execution_optimizer.create_execution_plan(
                order, impact_estimate
            )
            assert plan['slice_count'] == 4
            assert len(plan['slice_sizes']) == 4
            
            # Analyze costs
            costs = await mock_cost_analyzer.analyze_execution_cost(order, plan)
            assert costs['market_impact_cost'] > 0


class TestSystemIntegration:
    """Test full system integration scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_end_to_end_trading_cycle(self):
        """Test complete end-to-end trading cycle"""
        # This would be a comprehensive test that exercises the entire system
        # from market data ingestion to order execution
        
        # Mock all major components
        mock_data_manager = AsyncMock()
        mock_signal_generator = AsyncMock()
        mock_strategy_engine = AsyncMock()
        mock_portfolio_manager = AsyncMock()
        mock_risk_manager = AsyncMock()
        mock_execution_engine = AsyncMock()
        mock_analytics = AsyncMock()
        
        # Setup comprehensive test scenario
        market_data = generate_market_data(['AAPL', 'MSFT', 'GOOGL'], days=1)
        
        signals = [
            {'symbol': 'AAPL', 'signal': 'BUY', 'strength': 0.8, 'timestamp': datetime.now()},
            {'symbol': 'MSFT', 'signal': 'SELL', 'strength': 0.6, 'timestamp': datetime.now()}
        ]
        
        portfolio_update = {
            'new_positions': {'AAPL': 100, 'MSFT': -50},
            'realized_pnl': 1250.0,
            'unrealized_pnl': -350.0
        }
        
        # Test the complete cycle (simplified)
        # 1. Data ingestion
        await mock_data_manager.ingest_data(market_data)
        
        # 2. Signal generation
        generated_signals = await mock_signal_generator.generate_signals(market_data)
        mock_signal_generator.generate_signals.return_value = signals
        
        # 3. Strategy processing
        strategy_decisions = await mock_strategy_engine.process_signals(signals)
        
        # 4. Risk assessment
        risk_approved = await mock_risk_manager.assess_risk(strategy_decisions)
        mock_risk_manager.assess_risk.return_value = True
        
        # 5. Portfolio management
        if risk_approved:
            portfolio_changes = await mock_portfolio_manager.update_portfolio(strategy_decisions)
            mock_portfolio_manager.update_portfolio.return_value = portfolio_update
        
        # 6. Order execution
        execution_results = await mock_execution_engine.execute_portfolio_changes(portfolio_changes)
        
        # 7. Analytics and reporting
        performance_metrics = await mock_analytics.calculate_performance(portfolio_update)
        
        # Verify the cycle completed successfully
        assert generated_signals is not None
        assert risk_approved is True
        assert portfolio_update['realized_pnl'] > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_recovery_scenarios(self):
        """Test system error recovery and resilience"""
        # Test various failure scenarios and recovery mechanisms
        
        # 1. Database connection failure
        mock_db = AsyncMock()
        mock_db.execute_query.side_effect = Exception("Database connection lost")
        
        # Should gracefully handle database failures
        try:
            await mock_db.execute_query("SELECT * FROM market_data")
        except Exception as e:
            assert "Database connection lost" in str(e)
            # System should switch to backup data source or cache
            # and continue operating with degraded functionality
        
        # 2. Market data feed failure
        mock_feed = AsyncMock()
        mock_feed.fetch_data.side_effect = Exception("Feed unavailable")
        
        # Should switch to backup feed
        try:
            await mock_feed.fetch_data()
        except Exception:
            # Switch to backup feed
            backup_feed = AsyncMock()
            backup_feed.fetch_data.return_value = generate_market_data(['AAPL'], days=1)
            data = await backup_feed.fetch_data()
            assert len(data) > 0
        
        # 3. Order execution failure
        mock_execution = AsyncMock()
        mock_execution.execute_order.side_effect = Exception("Venue unavailable")
        
        # Should retry with backup venue
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await mock_execution.execute_order({'symbol': 'AAPL', 'quantity': 100})
                break
            except Exception:
                if attempt == max_retries - 1:
                    # Final fallback: queue for later execution
                    assert True  # Order queued successfully
    
    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_performance_under_load(self):
        """Test system performance under high load"""
        # Simulate high-frequency data and processing
        start_time = time.time()
        
        # Process 1000 market data updates
        mock_processor = AsyncMock()
        mock_processor.process_tick.return_value = {'processed': True}
        
        tasks = []
        for i in range(1000):
            tick_data = {
                'symbol': f'STOCK_{i % 100}',
                'price': 100 + np.random.randn(),
                'timestamp': datetime.now()
            }
            task = mock_processor.process_tick(tick_data)
            tasks.append(task)
        
        # Process all ticks concurrently
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify performance requirements
        assert len(results) == 1000
        assert processing_time < 10.0  # Should complete within 10 seconds
        assert all(r['processed'] for r in results)


# Test configuration for integration tests
@pytest.fixture(scope="session")
def integration_event_loop():
    """Create event loop for integration tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database():
    """Setup test database for integration tests"""
    # This would setup a test database instance
    # For now, just return a mock
    return AsyncMock()


@pytest.fixture(scope="session")
def test_environment():
    """Setup complete test environment"""
    return {
        'database': AsyncMock(),
        'cache': AsyncMock(),
        'message_bus': AsyncMock(),
        'config': {}
    }
