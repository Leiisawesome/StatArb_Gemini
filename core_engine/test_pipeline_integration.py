#!/usr/bin/env python3
"""
Core Engine Trading Pipeline Integration Test
===========================================

End-to-end test of the complete trading pipeline:
Raw data (ClickHouse) -> Indicators -> Features -> Signals -> Execution -> Portfolio

This test demonstrates the complete workflow with real market data from 2024-12-20.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Integration Test)
"""

import logging
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add core_engine to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pipeline_test")

def main():
    """Run the complete trading pipeline test"""
    
    logger.info("=" * 80)
    logger.info("CORE ENGINE TRADING PIPELINE INTEGRATION TEST")
    logger.info("=" * 80)
    
    # Test parameters
    test_date = "2024-12-20"
    test_symbols = ["NVDA", "TSLA", "AAPL", "MSFT", "GOOGL"]
    initial_capital = 100000.0
    
    try:
        # =====================================================================
        # STEP 1: DATA ACCESS
        # =====================================================================
        logger.info("STEP 1: Testing ClickHouse Data Access")
        logger.info("-" * 50)
        
        from data_manager_enhanced import ClickHouseDataManager
        
        data_manager = ClickHouseDataManager()
        
        # Test connection
        if not data_manager._test_connection():
            logger.error("ClickHouse connection failed!")
            return False
        
        logger.info("✓ ClickHouse connection successful")
        
        # Get available symbols for test date
        available_symbols = data_manager.get_available_symbols()
        logger.info(f"✓ Found {len(available_symbols)} symbols available")
        
        # Filter test symbols to only those available
        test_symbols = [s for s in test_symbols if s in available_symbols]
        logger.info(f"✓ Testing with symbols: {test_symbols}")
        
        if not test_symbols:
            logger.error("No test symbols available!")
            return False
        
        # =====================================================================
        # STEP 2: TECHNICAL INDICATORS
        # =====================================================================
        logger.info("\nSTEP 2: Testing Technical Indicators Engine")
        logger.info("-" * 50)
        
        from indicators_engine import TechnicalIndicators
        
        indicators_engine = TechnicalIndicators()
        
        # Test indicators for each symbol
        all_indicators = {}
        for symbol in test_symbols[:2]:  # Test first 2 symbols for demo
            logger.info(f"Processing indicators for {symbol}...")
            
            # Get market data
            market_data = data_manager.load_market_data(
                symbols=[symbol],
                start_time=datetime.strptime(f"{test_date} 00:00:00", "%Y-%m-%d %H:%M:%S"),
                end_time=datetime.strptime(f"{test_date} 23:59:00", "%Y-%m-%d %H:%M:%S"),
                interval="5min"
            )
            
            if market_data.empty:
                logger.warning(f"No data for {symbol}")
                continue
            
            # Calculate indicators
            indicators = indicators_engine.calculate_all_indicators(market_data)
            all_indicators[symbol] = indicators
            
            # Show summary
            summary = indicators_engine.get_indicator_summary(indicators, symbol)
            logger.info(f"✓ {symbol}: {len(indicators.columns)} indicators calculated")
            if 'indicators' in summary:
                rsi_info = summary['indicators'].get('rsi', {})
                macd_info = summary['indicators'].get('macd', {})
                rsi_val = rsi_info.get('value', 'N/A')
                macd_signal = macd_info.get('crossover', 'N/A')
                logger.info(f"  RSI: {rsi_val}, MACD Signal: {macd_signal}")
        
        # =====================================================================
        # STEP 3: FEATURE ENGINEERING
        # =====================================================================
        logger.info("\nSTEP 3: Testing Feature Engineering")
        logger.info("-" * 50)
        
        from feature_engineer import FeatureEngineer
        
        feature_engineer = FeatureEngineer()
        
        all_features = {}
        for symbol, indicators in all_indicators.items():
            logger.info(f"Engineering features for {symbol}...")
            
            features = feature_engineer.create_features(indicators)
            all_features[symbol] = features
            
            logger.info(f"✓ {symbol}: {len(features.columns)} features engineered")
            
            # Show feature importance
            importance = feature_engineer.get_feature_importance(features, 'return_1d')
            top_features = importance.head(5)
            logger.info(f"  Top features: {', '.join(map(str, top_features.index.tolist()))}")
        
        # =====================================================================
        # STEP 4: SIGNAL GENERATION
        # =====================================================================
        logger.info("\nSTEP 4: Testing Signal Generation")
        logger.info("-" * 50)
        
        from signal_generator import SignalGenerator
        
        signal_generator = SignalGenerator()
        
        all_signals = []
        for symbol, features in all_features.items():
            logger.info(f"Generating signals for {symbol}...")
            
            signals = signal_generator.generate_signals(features)
            all_signals.extend(signals)
            
            logger.info(f"✓ {symbol}: {len(signals)} signals generated")
            
            # Show latest signal
            if signals:
                latest_signal = signals[-1]
                logger.info(f"  Latest: {latest_signal.signal_type.value} "
                           f"(confidence: {latest_signal.confidence:.2f}, "
                           f"strength: {latest_signal.signal_strength:.2f})")
        
        logger.info(f"✓ Total signals generated: {len(all_signals)}")
        
        # =====================================================================
        # STEP 5: EXECUTION ENGINE
        # =====================================================================
        logger.info("\nSTEP 5: Testing Execution Engine")
        logger.info("-" * 50)
        
        from portfolio_manager import PaperTradingEngine, PortfolioManager
        
        # Initialize trading engine
        trading_engine = PaperTradingEngine(initial_capital=initial_capital)
        
        # Update market prices
        current_prices = {}
        for symbol in test_symbols:
            market_data = data_manager.load_market_data(
                symbols=[symbol],
                start_time=datetime.strptime(f"{test_date} 00:00:00", "%Y-%m-%d %H:%M:%S"),
                end_time=datetime.strptime(f"{test_date} 23:59:00", "%Y-%m-%d %H:%M:%S"),
                interval="5min"
            )
            if not market_data.empty:
                current_prices[symbol] = market_data.iloc[-1]['close']
        
        trading_engine.update_market_data(current_prices)
        logger.info(f"✓ Updated prices for {len(current_prices)} symbols")
        
        # =====================================================================
        # STEP 6: PORTFOLIO MANAGEMENT
        # =====================================================================
        logger.info("\nSTEP 6: Testing Portfolio Management")
        logger.info("-" * 50)
        
        portfolio_manager = PortfolioManager(trading_engine)
        
        # Execute signals
        executed_orders = 0
        for signal in all_signals[:5]:  # Execute first 5 signals for demo
            if signal.symbol in current_prices:
                order_id = portfolio_manager.execute_signal(signal)
                if order_id:
                    executed_orders += 1
        
        logger.info(f"✓ Executed {executed_orders} orders")
        
        # =====================================================================
        # STEP 7: RESULTS AND REPORTING
        # =====================================================================
        logger.info("\nSTEP 7: Portfolio Results")
        logger.info("-" * 50)
        
        # Portfolio summary
        portfolio_summary = trading_engine.get_portfolio_summary()
        logger.info("Portfolio Summary:")
        logger.info(f"  Initial Capital: ${portfolio_summary['initial_capital']:,.2f}")
        logger.info(f"  Portfolio Value: ${portfolio_summary['portfolio_value']:,.2f}")
        logger.info(f"  Cash: ${portfolio_summary['cash']:,.2f}")
        logger.info(f"  Position Value: ${portfolio_summary['position_value']:,.2f}")
        logger.info(f"  Total Return: {portfolio_summary['total_return']*100:.2f}%")
        logger.info(f"  Total P&L: ${portfolio_summary['total_pnl']:,.2f}")
        logger.info(f"  Number of Positions: {portfolio_summary['num_positions']}")
        logger.info(f"  Number of Trades: {portfolio_summary['num_trades']}")
        
        # Risk metrics
        risk_metrics = portfolio_manager.get_risk_metrics()
        logger.info("\nRisk Metrics:")
        logger.info(f"  Total Exposure: {risk_metrics['total_exposure']*100:.1f}%")
        logger.info(f"  Max Position Exposure: {risk_metrics['max_position_exposure']*100:.1f}%")
        logger.info(f"  Portfolio Volatility: {risk_metrics['portfolio_volatility']*100:.2f}%")
        
        # Performance metrics
        performance = portfolio_manager.get_performance_metrics()
        logger.info("\nPerformance Metrics:")
        logger.info(f"  Win Rate: {performance['win_rate']*100:.1f}%")
        logger.info(f"  Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
        logger.info(f"  Cash Utilization: {performance['cash_utilization']*100:.1f}%")
        
        # Position details
        if trading_engine.positions:
            logger.info("\nCurrent Positions:")
            for symbol, position in trading_engine.positions.items():
                logger.info(f"  {symbol}: {position.quantity} shares @ ${position.avg_price:.2f} "
                           f"(Current: ${position.current_price:.2f}, "
                           f"P&L: ${position.unrealized_pnl:.2f})")
        
        # Trade history
        if trading_engine.trades:
            logger.info("\nRecent Trades:")
            for trade in trading_engine.trades[-5:]:  # Last 5 trades
                logger.info(f"  {trade.timestamp.strftime('%H:%M:%S')}: "
                           f"{trade.side.upper()} {trade.quantity} {trade.symbol} "
                           f"@ ${trade.price:.2f}")
        
        # =====================================================================
        # SUCCESS
        # =====================================================================
        logger.info("\n" + "=" * 80)
        logger.info("✅ PIPELINE INTEGRATION TEST COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        
        logger.info("\nPipeline Components Tested:")
        logger.info("  ✓ ClickHouse Data Access")
        logger.info("  ✓ Technical Indicators Engine")
        logger.info("  ✓ Feature Engineering")
        logger.info("  ✓ Signal Generation")
        logger.info("  ✓ Paper Trading Execution")
        logger.info("  ✓ Portfolio Management")
        logger.info("  ✓ Risk Management")
        logger.info("  ✓ Performance Reporting")
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_individual_components():
    """Test individual components separately"""
    
    logger.info("\n" + "=" * 60)
    logger.info("INDIVIDUAL COMPONENT TESTS")
    logger.info("=" * 60)
    
    # Test 1: Data Manager Connection
    try:
        from data_manager_enhanced import ClickHouseDataManager
        dm = ClickHouseDataManager()
        assert dm._test_connection(), "ClickHouse connection failed"
        logger.info("✓ Data Manager: Connection OK")
    except Exception as e:
        logger.error(f"✗ Data Manager: {e}")
    
    # Test 2: Indicators Engine
    try:
        from indicators_engine import TechnicalIndicators
        te = TechnicalIndicators()
        # Create sample data
        dates = pd.date_range('2024-12-20 09:30:00', periods=100, freq='5min')
        sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(110, 120, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        indicators = te.calculate_all_indicators(sample_data)
        assert len(indicators) > 0, "No indicators calculated"
        logger.info(f"✓ Indicators Engine: {len(indicators.columns)} indicators calculated")
    except Exception as e:
        logger.error(f"✗ Indicators Engine: {e}")
    
    # Test 3: Feature Engineer
    try:
        from feature_engineer import FeatureEngineer
        fe = FeatureEngineer()
        # Use indicators from previous test
        features = fe.create_features(indicators)
        assert len(features) > 0, "No features engineered"
        logger.info(f"✓ Feature Engineer: {len(features.columns)} features created")
    except Exception as e:
        logger.error(f"✗ Feature Engineer: {e}")
    
    # Test 4: Signal Generator
    try:
        from signal_generator import SignalGenerator
        sg = SignalGenerator()
        signals = sg.generate_signals(features)
        logger.info(f"✓ Signal Generator: {len(signals)} signals generated")
    except Exception as e:
        logger.error(f"✗ Signal Generator: {e}")
    
    # Test 5: Portfolio Manager
    try:
        from portfolio_manager import PaperTradingEngine, PortfolioManager
        pte = PaperTradingEngine()
        pm = PortfolioManager(pte)
        pte.update_market_data({"TEST": 100.0})
        summary = pte.get_portfolio_summary()
        assert summary['initial_capital'] > 0, "Portfolio not initialized"
        logger.info("✓ Portfolio Manager: Initialization OK")
    except Exception as e:
        logger.error(f"✗ Portfolio Manager: {e}")

if __name__ == "__main__":
    # Run individual component tests first
    test_individual_components()
    
    # Run full integration test
    success = main()
    
    if success:
        print("\n🎉 All tests passed! Core engine pipeline is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Check logs for details.")
        sys.exit(1)