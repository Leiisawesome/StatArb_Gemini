import sys
import os

# Add backtesting_framework directory to Python path
current_dir = os.path.dirname(__file__)
framework_dir = os.path.dirname(current_dir)
sys.path.append(framework_dir)

# Add core_structure directory to Python path
statarb_dir = os.path.dirname(framework_dir)
sys.path.append(statarb_dir)

import logging
import pandas as pd
from datetime import datetime
from strategies.momentum_strategy import MomentumStrategy, MomentumConfig
from core_structure.optimization.performance_optimization.optimize_execution import PortfolioOptimizer

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_mock_data():
    """Create mock market data for testing"""
    dates = pd.date_range(start="2025-01-01", end="2025-06-30", freq="D")
    data = {
        "AAPL": pd.DataFrame({
            "close": [150 + i * 0.1 for i in range(len(dates))],
            "volume": [1000000 + i * 1000 for i in range(len(dates))]
        }, index=dates),
        "MSFT": pd.DataFrame({
            "close": [250 + i * 0.2 for i in range(len(dates))],
            "volume": [2000000 + i * 2000 for i in range(len(dates))]
        }, index=dates)
    }
    return data

def test_momentum_strategy_walkthrough():
    """Test script for MomentumStrategy walkthrough"""
    logger.info("Starting MomentumStrategy walkthrough test")

    # Step 1: Create mock configuration
    config = MomentumConfig(
        name="TestMomentumStrategy",
        symbols=["AAPL", "MSFT"],
        training_start="2025-01-01",
        training_end="2025-06-30",
        trading_start="2025-07-01",
        trading_end="2025-12-31",
        lookback_period=30,
        skip_period=5,
        momentum_threshold=0.05,
        target_volatility=0.2,
        max_weight_per_asset=0.1,
        rebalancing_frequency="monthly",
        commission_rate=0.001
    )

    # Step 2: Initialize strategy
    strategy = MomentumStrategy(config)

    # Step 3: Train strategy
    mock_data = create_mock_data()
    strategy.train(training_data=mock_data)

    # Step 4: Generate signals
    signals = strategy.generate_signals(data=mock_data)
    logger.info(f"Generated signals: {signals}")

    # Step 5: Calculate positions
    current_positions = {}
    available_cash = 1000000  # Mock available cash
    positions = strategy.calculate_positions(signals, current_positions, available_cash)
    logger.info(f"Calculated positions: {positions}")

    # Step 6: Execute trades
    current_prices = {symbol: data["close"].iloc[-1] for symbol, data in mock_data.items()}
    trades = strategy.execute_trades(signals, current_prices)
    logger.info(f"Executed trades: {trades}")

    # Step 7: Get strategy metrics
    metrics = strategy.get_strategy_metrics()
    logger.info(f"Strategy metrics: {metrics}")

if __name__ == "__main__":
    test_momentum_strategy_walkthrough()
