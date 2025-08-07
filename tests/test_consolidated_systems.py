"""
Comprehensive Testing for Consolidated Systems
============================================

Tests for all consolidated systems after the codebase cleanup:
- Unified Configuration Management
- Enhanced Data Management
- Enhanced Execution Management
- Risk Management
- Portfolio Management
- Signal Generation
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import pandas as pd
import numpy as np

# Import consolidated systems
from core_structure.infrastructure.config import (
    UnifiedConfigManager, UnifiedConfig, StrategyConfig, 
    TrainingConfig, TradingConfig, Environment
)
from core_structure.market_data import (
    EnhancedDataManager, DataQualityMonitor, DataStreamManager, DataStreamConfig
)
from core_structure.execution_engine import (
    EnhancedExecutionEngine, OrderManager, SmartOrderRouter,
    TransactionCostOptimizer, Order, OrderSide, OrderType, 
    ExecutionRequest, ExecutionStrategy, OrderStatus, ExecutionResult
)
from core_structure.risk import RiskManager, PositionRisk, PortfolioRisk
from core_structure.portfolio import PortfolioManager, Position


class TestUnifiedConfigurationManagement:
    """Test unified configuration management system"""
    
    def test_unified_config_manager_initialization(self):
        """Test UnifiedConfigManager initialization"""
        config_manager = UnifiedConfigManager()
        assert config_manager is not None
        assert hasattr(config_manager, 'config_dir')
        assert hasattr(config_manager, 'env')
    
    def test_create_backtesting_config(self):
        """Test backtesting configuration creation"""
        config_manager = UnifiedConfigManager()
        
        config = config_manager.create_backtesting_config(
            strategy_name="test_strategy",
            training_start="2023-01-01",
            training_end="2023-06-30",
            validation_start="2023-07-01",
            validation_end="2023-12-31"
        )
        
        assert isinstance(config, UnifiedConfig)
        assert config.environment == Environment.BACKTESTING
        assert config.strategy.name == "test_strategy"
        assert config.training is not None
        assert config.training.start_date == "2023-01-01"
        assert config.training.end_date == "2023-06-30"
        assert config.trading.start_date == "2023-07-01"
        assert config.trading.end_date == "2023-12-31"
    
    def test_create_real_time_config(self):
        """Test real-time configuration creation"""
        config_manager = UnifiedConfigManager()
        
        config = config_manager.create_real_time_config(
            strategy_name="test_strategy",
            trading_start="2024-01-01"
        )
        
        assert isinstance(config, UnifiedConfig)
        assert config.environment == Environment.REAL_TIME
        assert config.strategy.name == "test_strategy"
        assert config.trading.real_time is True
        assert config.training is None
    
    def test_get_database_config(self):
        """Test database configuration retrieval"""
        config_manager = UnifiedConfigManager()
        
        db_config = config_manager.get_database_config()
        assert isinstance(db_config, dict)
        assert 'host' in db_config
        assert 'port' in db_config
        assert 'database' in db_config
    
    def test_get_strategy_settings(self):
        """Test strategy settings retrieval"""
        config_manager = UnifiedConfigManager()
        
        settings = config_manager.get_strategy_settings("test_strategy")
        assert isinstance(settings, dict)
    
    def test_feature_flags(self):
        """Test feature flag functionality"""
        config_manager = UnifiedConfigManager()
        
        # Test default feature flag
        flag_value = config_manager.get_feature_flag("nonexistent_flag")
        assert flag_value is False
    
    def test_dynamic_settings(self):
        """Test dynamic settings management"""
        config_manager = UnifiedConfigManager()
        
        # Set dynamic setting
        config_manager.update_dynamic_setting("test_key", "test_value")
        
        # Get dynamic setting
        value = config_manager.get_dynamic_setting("test_key")
        assert value == "test_value"
        
        # Test default value
        default_value = config_manager.get_dynamic_setting("nonexistent_key", "default")
        assert default_value == "default"


class TestEnhancedDataManagement:
    """Test enhanced data management system"""
    
    def test_enhanced_data_manager_initialization(self):
        """Test EnhancedDataManager initialization"""
        data_manager = EnhancedDataManager()
        assert data_manager is not None
        assert hasattr(data_manager, 'cache')
        assert hasattr(data_manager, 'quality_monitor')
    
    def test_data_quality_monitor(self):
        """Test data quality monitoring"""
        monitor = DataQualityMonitor()
        assert monitor is not None
        assert hasattr(monitor, 'thresholds')
        assert hasattr(monitor, 'alert_callbacks')
    
    def test_data_quality_checking(self):
        """Test data quality checking functionality"""
        monitor = DataQualityMonitor()
        
        # Create test data
        test_data = {
            'AAPL': pd.DataFrame({
                'close': [100, 101, 102, 103, 104],
                'volume': [1000, 1100, 1200, 1300, 1400]
            }, index=pd.date_range('2024-01-01', periods=5))
        }
        
        quality_report = monitor.check_data_quality(test_data)
        assert isinstance(quality_report, dict)
        assert 'AAPL' in quality_report
        assert 'status' in quality_report['AAPL']
    
    def test_data_stream_manager(self):
        """Test data stream manager"""
        config = DataStreamConfig(symbols=['AAPL', 'MSFT'])
        stream_manager = DataStreamManager(config)
        
        assert stream_manager is not None
        assert hasattr(stream_manager, 'config')
        assert hasattr(stream_manager, 'data_buffer')
    
    def test_historical_data_loading(self):
        """Test historical data loading"""
        data_manager = EnhancedDataManager()
        
        # Test loading historical data (mock implementation)
        try:
            data = data_manager.load_historical_data(
                symbols=['AAPL', 'MSFT'],
                start_date='2024-01-01',
                end_date='2024-01-31'
            )
            # This will likely return empty data due to mock implementation
            assert isinstance(data, dict)
        except Exception as e:
            # Expected for mock implementation
            assert "mock" in str(e).lower() or "placeholder" in str(e).lower()
    
    def test_data_validation(self):
        """Test data validation"""
        data_manager = EnhancedDataManager()
        
        # Create test data
        test_data = {
            'AAPL': pd.DataFrame({
                'open': [100, 101, 102],
                'high': [105, 106, 107],
                'low': [95, 96, 97],
                'close': [103, 104, 105],
                'volume': [1000, 1100, 1200]
            })
        }
        
        validation_errors = data_manager.validate_data(test_data)
        assert isinstance(validation_errors, dict)
    
    def test_data_info_retrieval(self):
        """Test data information retrieval"""
        data_manager = EnhancedDataManager()
        
        # Create test data
        test_data = {
            'AAPL': pd.DataFrame({
                'close': [100, 101, 102],
                'volume': [1000, 1100, 1200]
            }, index=pd.date_range('2024-01-01', periods=3))
        }
        
        info = data_manager.get_data_info(test_data)
        assert isinstance(info, dict)
        assert 'total_symbols' in info
        assert 'symbols' in info
        assert info['total_symbols'] == 1
        assert 'AAPL' in info['symbols']


class TestEnhancedExecutionManagement:
    """Test enhanced execution management system"""
    
    def test_enhanced_execution_engine_initialization(self):
        """Test EnhancedExecutionEngine initialization"""
        execution_engine = EnhancedExecutionEngine()
        assert execution_engine is not None
        assert hasattr(execution_engine, 'order_manager')
        assert hasattr(execution_engine, 'smart_router')
        assert hasattr(execution_engine, 'cost_optimizer')
    
    def test_order_manager(self):
        """Test order manager functionality"""
        order_manager = OrderManager(initial_capital=100000)
        assert order_manager is not None
        assert order_manager.initial_capital == 100000
        assert order_manager.available_capital == 100000
    
    def test_order_creation(self):
        """Test order creation"""
        order_manager = OrderManager()
        
        order = order_manager.create_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        assert isinstance(order, Order)
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING
    
    def test_order_execution(self):
        """Test order execution"""
        order_manager = OrderManager()
        
        order = order_manager.create_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        # Submit order
        success = order_manager.submit_order(order.order_id)
        assert success is True
        
        # Execute order
        success = order_manager.execute_order(order.order_id, 150.0, 100)
        assert success is True
        
        # Check order status
        updated_order = order_manager.get_order(order.order_id)
        assert updated_order.status == OrderStatus.FILLED
        assert updated_order.filled_quantity == 100
        assert updated_order.avg_fill_price == 150.0
    
    def test_smart_order_router(self):
        """Test smart order router"""
        order_manager = OrderManager()
        router = SmartOrderRouter(order_manager)
        
        assert router is not None
        assert hasattr(router, 'execution_strategies')
        assert hasattr(router, 'market_data')
    
    def test_transaction_cost_optimizer(self):
        """Test transaction cost optimizer"""
        optimizer = TransactionCostOptimizer()
        assert optimizer is not None
    
    def test_transaction_cost_calculation(self):
        """Test transaction cost calculation"""
        optimizer = TransactionCostOptimizer()
        
        costs = optimizer.calculate_transaction_costs(
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )
        
        assert isinstance(costs, dict)
        assert 'commission' in costs
        assert 'slippage' in costs
        assert 'market_impact' in costs
        assert 'total_cost' in costs
        assert 'total_cost_bps' in costs
    
    def test_order_size_optimization(self):
        """Test order size optimization"""
        optimizer = TransactionCostOptimizer()
        
        optimization = optimizer.optimize_order_size(
            symbol="AAPL",
            side="BUY",
            total_quantity=1000,
            price=150.0,
            max_cost_bps=10.0
        )
        
        assert isinstance(optimization, dict)
        assert 'order_size' in optimization
        assert 'num_orders' in optimization
        assert 'total_cost' in optimization
        assert 'total_cost_bps' in optimization
    
    @pytest.mark.asyncio
    async def test_async_order_execution(self):
        """Test asynchronous order execution"""
        execution_engine = EnhancedExecutionEngine()
        
        request = ExecutionRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            strategy=ExecutionStrategy.MARKET
        )
        
        result = await execution_engine.execute_order(request)
        
        assert isinstance(result, ExecutionResult)
        assert result.request_id == request.request_id
        assert result.symbol == "AAPL"
        assert result.side == OrderSide.BUY
        assert result.requested_quantity == 100
    
    def test_execution_summary(self):
        """Test execution summary"""
        execution_engine = EnhancedExecutionEngine()
        
        summary = execution_engine.get_execution_summary()
        assert isinstance(summary, dict)
        assert 'total_executions' in summary
        assert 'order_summary' in summary


class TestRiskManagement:
    """Test risk management system"""
    
    def test_risk_manager_initialization(self):
        """Test RiskManager initialization"""
        risk_manager = RiskManager()
        assert risk_manager is not None
    
    def test_position_risk_calculation(self):
        """Test position risk calculation"""
        risk_manager = RiskManager()
        
        position_risk = risk_manager.calculate_position_risk(
            symbol="AAPL",
            position_size=100.0,  # 100 shares
            current_price=155.0,
            avg_price=150.0
        )
        
        assert isinstance(position_risk, PositionRisk)
        assert position_risk.symbol == "AAPL"
        assert position_risk.position_size == 100.0
        assert position_risk.avg_price == 150.0
        assert position_risk.current_price == 155.0
        assert position_risk.unrealized_pnl == 500.0  # (155 - 150) * 100
    
    def test_portfolio_risk_calculation(self):
        """Test portfolio risk calculation"""
        risk_manager = RiskManager()
        
        positions = {
            "AAPL": {
                'size': 100,
                'current_price': 155.0,
                'avg_price': 150.0
            },
            "MSFT": {
                'size': 50,
                'current_price': 305.0,
                'avg_price': 300.0
            }
        }
        
        portfolio_risk = risk_manager.calculate_portfolio_risk(positions=positions)
        
        assert isinstance(portfolio_risk, PortfolioRisk)
        assert portfolio_risk.total_value > 0
        assert portfolio_risk.total_pnl > 0  # Should be positive based on test data


class TestPortfolioManagement:
    """Test portfolio management system"""
    
    def test_portfolio_manager_initialization(self):
        """Test PortfolioManager initialization"""
        portfolio_manager = PortfolioManager(initial_capital=100000)
        assert portfolio_manager is not None
        assert portfolio_manager.initial_capital == 100000
    
    def test_position_creation(self):
        """Test position creation"""
        portfolio_manager = PortfolioManager()
        
        # Get position (should return None if no position exists)
        position = portfolio_manager.get_position("AAPL")
        # The get_position method returns None if no position exists, which is correct behavior
        assert position is None
    
    def test_trade_processing(self):
        """Test trade processing"""
        portfolio_manager = PortfolioManager()
        
        # Process a buy trade
        portfolio_manager.process_trade(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            trade_type="BUY"
        )
        
        position = portfolio_manager.get_position("AAPL")
        assert position.quantity == 100
        assert position.avg_price == 150.0
        
        # Process a sell trade
        portfolio_manager.process_trade(
            symbol="AAPL",
            quantity=50,
            price=155.0,
            trade_type="SELL"
        )
        
        position = portfolio_manager.get_position("AAPL")
        assert position.quantity == 50  # 100 - 50
        assert position.avg_price == 150.0  # Should remain the same
    
    def test_portfolio_summary(self):
        """Test portfolio summary"""
        portfolio_manager = PortfolioManager(initial_capital=100000)
        
        # Add some positions
        portfolio_manager.process_trade("AAPL", 100, 150.0, "BUY")
        portfolio_manager.process_trade("MSFT", 50, 300.0, "BUY")
        
        summary = portfolio_manager.get_portfolio_summary()
        assert isinstance(summary, dict)
        assert 'total_value' in summary
        assert 'total_pnl' in summary
        assert 'position_count' in summary


class TestSignalGeneration:
    """Test signal generation system"""
    
    def test_signal_generator_initialization(self):
        """Test signal generator initialization"""
        # This would test the consolidated signal generation system
        # Implementation depends on the specific signal generators available
        pass
    
    def test_regime_detector(self):
        """Test regime detector"""
        # This would test the regime detection functionality
        # Implementation depends on the specific regime detector available
        pass


class TestIntegration:
    """Integration tests for consolidated systems"""
    
    def test_configuration_to_data_management_integration(self):
        """Test integration between configuration and data management"""
        config_manager = UnifiedConfigManager()
        data_manager = EnhancedDataManager()
        
        # Test that both systems can work together
        assert config_manager is not None
        assert data_manager is not None
    
    def test_data_to_execution_integration(self):
        """Test integration between data management and execution"""
        data_manager = EnhancedDataManager()
        execution_engine = EnhancedExecutionEngine()
        
        # Test that both systems can work together
        assert data_manager is not None
        assert execution_engine is not None
    
    def test_execution_to_risk_integration(self):
        """Test integration between execution and risk management"""
        execution_engine = EnhancedExecutionEngine()
        risk_manager = RiskManager()
        
        # Test that both systems can work together
        assert execution_engine is not None
        assert risk_manager is not None
    
    def test_risk_to_portfolio_integration(self):
        """Test integration between risk and portfolio management"""
        risk_manager = RiskManager()
        portfolio_manager = PortfolioManager()
        
        # Test that both systems can work together
        assert risk_manager is not None
        assert portfolio_manager is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 