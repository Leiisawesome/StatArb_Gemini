"""
Basic Validation Tests for Consolidated Systems
==============================================

Simple tests to validate that the consolidated systems are working correctly.
"""

import pytest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import_unified_config_manager():
    """Test that UnifiedConfigManager can be imported"""
    try:
        from core_structure.infrastructure.config import UnifiedConfigManager
        config_manager = UnifiedConfigManager()
        assert config_manager is not None
        print("✅ UnifiedConfigManager import and initialization successful")
    except Exception as e:
        pytest.fail(f"Failed to import UnifiedConfigManager: {e}")

def test_import_enhanced_data_manager():
    """Test that EnhancedDataManager can be imported"""
    try:
        from core_structure.market_data import EnhancedDataManager
        data_manager = EnhancedDataManager()
        assert data_manager is not None
        print("✅ EnhancedDataManager import and initialization successful")
    except Exception as e:
        pytest.fail(f"Failed to import EnhancedDataManager: {e}")

def test_import_enhanced_execution_engine():
    """Test that EnhancedExecutionEngine can be imported"""
    try:
        from core_structure.execution_engine import EnhancedExecutionEngine
        execution_engine = EnhancedExecutionEngine()
        assert execution_engine is not None
        print("✅ EnhancedExecutionEngine import and initialization successful")
    except Exception as e:
        pytest.fail(f"Failed to import EnhancedExecutionEngine: {e}")

def test_import_risk_manager():
    """Test that RiskManager can be imported"""
    try:
        from core_structure.risk import RiskManager
        risk_manager = RiskManager()
        assert risk_manager is not None
        print("✅ RiskManager import and initialization successful")
    except Exception as e:
        pytest.fail(f"Failed to import RiskManager: {e}")

def test_import_portfolio_manager():
    """Test that PortfolioManager can be imported"""
    try:
        from core_structure.portfolio import PortfolioManager
        portfolio_manager = PortfolioManager()
        assert portfolio_manager is not None
        print("✅ PortfolioManager import and initialization successful")
    except Exception as e:
        pytest.fail(f"Failed to import PortfolioManager: {e}")

def test_configuration_creation():
    """Test configuration creation functionality"""
    try:
        from core_structure.infrastructure.config import UnifiedConfigManager, Environment
        
        config_manager = UnifiedConfigManager()
        
        # Test backtesting config creation
        config = config_manager.create_backtesting_config(
            strategy_name="test_strategy",
            training_start="2023-01-01",
            training_end="2023-06-30",
            validation_start="2023-07-01",
            validation_end="2023-12-31"
        )
        
        assert config.environment == Environment.BACKTESTING
        assert config.strategy.name == "test_strategy"
        print("✅ Configuration creation successful")
    except Exception as e:
        pytest.fail(f"Failed to create configuration: {e}")

def test_order_management():
    """Test order management functionality"""
    try:
        from core_structure.execution_engine import OrderManager, OrderSide, OrderType
        
        order_manager = OrderManager(initial_capital=100000)
        
        # Create an order
        order = order_manager.create_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        print("✅ Order management successful")
    except Exception as e:
        pytest.fail(f"Failed to test order management: {e}")

def test_data_quality_monitoring():
    """Test data quality monitoring functionality"""
    try:
        from core_structure.market_data import DataQualityMonitor
        import pandas as pd
        
        monitor = DataQualityMonitor()
        
        # Create test data
        test_data = {
            'AAPL': pd.DataFrame({
                'close': [100, 101, 102, 103, 104],
                'volume': [1000, 1100, 1200, 1300, 1400]
            })
        }
        
        quality_report = monitor.check_data_quality(test_data)
        assert isinstance(quality_report, dict)
        assert 'AAPL' in quality_report
        print("✅ Data quality monitoring successful")
    except Exception as e:
        pytest.fail(f"Failed to test data quality monitoring: {e}")

def test_transaction_cost_optimization():
    """Test transaction cost optimization functionality"""
    try:
        from core_structure.execution_engine import TransactionCostOptimizer
        
        optimizer = TransactionCostOptimizer()
        
        costs = optimizer.calculate_transaction_costs(
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )
        
        assert isinstance(costs, dict)
        assert 'total_cost' in costs
        assert 'total_cost_bps' in costs
        print("✅ Transaction cost optimization successful")
    except Exception as e:
        pytest.fail(f"Failed to test transaction cost optimization: {e}")

def test_portfolio_management():
    """Test portfolio management functionality"""
    try:
        from core_structure.portfolio import PortfolioManager
        from datetime import datetime
        
        portfolio_manager = PortfolioManager(initial_capital=100000)
        
        # Process a trade
        success = portfolio_manager.process_trade(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            trade_type="BUY"
        )
        
        print(f"Trade success: {success}")
        print(f"Available capital: {portfolio_manager.available_capital}")
        
        # Check if position exists
        position = portfolio_manager.get_position("AAPL")
        print(f"Position: {position}")
        if position:
            print(f"Position quantity: {position.quantity}")
            print(f"Position avg price: {position.avg_price}")
        else:
            print("Position is None - position was not created")
        
        # Check all positions
        all_positions = portfolio_manager.get_all_positions()
        print(f"All positions: {list(all_positions.keys())}")
        
        # The trade should succeed with 100000 initial capital
        assert success is True  # Check that trade was processed successfully
        assert position.quantity == 100
        assert position.avg_price == 150.0
        print("✅ Portfolio management successful")
    except Exception as e:
        pytest.fail(f"Failed to test portfolio management: {e}")

def test_risk_management():
    """Test risk management functionality"""
    try:
        from core_structure.risk import RiskManager
        
        risk_manager = RiskManager()
        
        # Test with correct position size (number of shares)
        position_risk = risk_manager.calculate_position_risk(
            symbol="AAPL",
            position_size=100.0,  # 100 shares
            current_price=155.0,
            avg_price=150.0
        )
        
        assert position_risk.symbol == "AAPL"
        assert position_risk.unrealized_pnl == 500.0  # (155 - 150) * 100
        print("✅ Risk management successful")
    except Exception as e:
        pytest.fail(f"Failed to test risk management: {e}")

if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"]) 