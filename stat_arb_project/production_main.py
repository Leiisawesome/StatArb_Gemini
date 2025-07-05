#!/usr/bin/env python3
"""
Production Entry Point for Statistical Arbitrage Trading System
Handles startup, configuration, and graceful shutdown.
"""
import sys
import signal
import time
import traceback
from pathlib import Path
from typing import Optional
import argparse
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from stat_arb_project.config import get_config
from stat_arb_project.strategies.professional_pair_trading import ProfessionalPairTradingStrategy
from stat_arb_project.data.data_loader import DataLoader
from stat_arb_project.backtesting.production_backtest import ProductionBacktestEngine
from stat_arb_project.utils.production_logging import setup_production_logging, MetricsCollector

class ProductionTradingSystem:
    """
    Production trading system with proper lifecycle management.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = None
        self.logger = None
        self.metrics_collector = None
        self.strategy = None
        self.data_loader = None
        self.backtest_engine = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize(self):
        """Initialize the trading system."""
        try:
            # Load configuration
            self.config = get_config(self.config_path)
            
            # Setup logging
            self.logger = setup_production_logging(self.config.logging.to_dict())
            self.metrics_collector = MetricsCollector(self.logger)
            
            self.logger.logger.info(
                "system_starting",
                environment=self.config.environment,
                debug=self.config.debug
            )
            
            # Initialize components
            self._initialize_components()
            
            self.logger.logger.info("system_initialized_successfully")
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(
                    error_type="initialization_error",
                    error_message=str(e),
                    stack_trace=traceback.format_exc()
                )
            else:
                print(f"Initialization error: {e}")
                traceback.print_exc()
            raise
    
    def _initialize_components(self):
        """Initialize system components."""
        # Initialize data loader
        self.data_loader = DataLoader()
        
        # Initialize strategy
        self.strategy = ProfessionalPairTradingStrategy(
            initial_capital=self.config.trading.initial_capital,
            max_position_size=self.config.trading.max_position_size,
            max_leverage=self.config.trading.max_leverage,
            target_volatility=self.config.trading.target_volatility,
            entry_threshold=self.config.trading.entry_threshold,
            exit_threshold=self.config.trading.exit_threshold,
            stop_loss=self.config.trading.stop_loss,
            take_profit=self.config.trading.take_profit
        )
        
        # Initialize backtest engine
        self.backtest_engine = ProductionBacktestEngine(
            initial_capital=self.config.trading.initial_capital,
            commission_rate=0.001,
            slippage_model='proportional'
        )
        
        self.logger.logger.info("components_initialized")
    
    def run_backtest(self, 
                    symbol1: str = "AAPL",
                    symbol2: str = "MSFT",
                    start_date: str = "2023-01-01",
                    end_date: str = "2023-12-31"):
        """Run production backtest."""
        try:
            self.logger.logger.info(
                "starting_backtest",
                symbol1=symbol1,
                symbol2=symbol2,
                start_date=start_date,
                end_date=end_date
            )
            
            # Load data
            data1 = self.data_loader.load_data(symbol1, start_date, end_date)
            data2 = self.data_loader.load_data(symbol2, start_date, end_date)
            
            if data1 is None or data2 is None:
                raise ValueError("Failed to load data for backtest")
            
            # Run backtest
            results = self.backtest_engine.run_backtest(
                strategy=self.strategy,
                data1=data1,
                data2=data2,
                symbol1=symbol1,
                symbol2=symbol2
            )
            
            # Log results
            self.logger.logger.info(
                "backtest_completed",
                total_return=results['total_return'],
                sharpe_ratio=results['sharpe_ratio'],
                max_drawdown=results['max_drawdown'],
                total_trades=results['total_trades']
            )
            
            # Record metrics
            self.metrics_collector.record_trade_metric(
                'total_return', results['total_return']
            )
            self.metrics_collector.record_trade_metric(
                'sharpe_ratio', results['sharpe_ratio']
            )
            self.metrics_collector.record_risk_metric(
                'max_drawdown', results['max_drawdown']
            )
            
            return results
            
        except Exception as e:
            self.logger.log_error(
                error_type="backtest_error",
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            raise
    
    def run_live_trading(self):
        """Run live trading (placeholder for future implementation)."""
        self.logger.logger.warning(
            "live_trading_not_implemented",
            message="Live trading is not yet implemented"
        )
        raise NotImplementedError("Live trading not yet implemented")
    
    def run_paper_trading(self):
        """Run paper trading simulation."""
        self.logger.logger.info("starting_paper_trading")
        
        # This would implement real-time paper trading
        # For now, just log that it's not implemented
        self.logger.logger.warning(
            "paper_trading_not_implemented",
            message="Paper trading is not yet implemented"
        )
        raise NotImplementedError("Paper trading not yet implemented")
    
    def start(self, mode: str = "backtest", **kwargs):
        """Start the trading system."""
        try:
            self.initialize()
            self.running = True
            
            if mode == "backtest":
                return self.run_backtest(**kwargs)
            elif mode == "live":
                return self.run_live_trading()
            elif mode == "paper":
                return self.run_paper_trading()
            else:
                raise ValueError(f"Unknown mode: {mode}")
                
        except Exception as e:
            self.logger.log_error(
                error_type="startup_error",
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown."""
        if self.running:
            self.running = False
            self.logger.logger.info("system_shutting_down")
            
            # Cleanup resources
            if self.data_loader:
                self.data_loader = None
            
            self.logger.logger.info("system_shutdown_complete")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.logger.info(
            "received_shutdown_signal",
            signal=signum
        )
        self.shutdown()
        sys.exit(0)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Statistical Arbitrage Trading System")
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--mode", 
        choices=["backtest", "live", "paper"], 
        default="backtest",
        help="Trading mode"
    )
    parser.add_argument(
        "--symbol1", 
        type=str, 
        default="AAPL",
        help="First symbol for pair trading"
    )
    parser.add_argument(
        "--symbol2", 
        type=str, 
        default="MSFT",
        help="Second symbol for pair trading"
    )
    parser.add_argument(
        "--start-date", 
        type=str, 
        default="2023-01-01",
        help="Start date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", 
        type=str, 
        default="2023-12-31",
        help="End date for backtest (YYYY-MM-DD)"
    )
    
    args = parser.parse_args()
    
    # Create and run trading system
    trading_system = ProductionTradingSystem(config_path=args.config)
    
    try:
        if args.mode == "backtest":
            results = trading_system.start(
                mode=args.mode,
                symbol1=args.symbol1,
                symbol2=args.symbol2,
                start_date=args.start_date,
                end_date=args.end_date
            )
            
            # Print results
            print("\n" + "="*50)
            print("BACKTEST RESULTS")
            print("="*50)
            print(f"Total Return: {results['total_return']:.2%}")
            print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
            print(f"Max Drawdown: {results['max_drawdown']:.2%}")
            print(f"Total Trades: {results['total_trades']}")
            print(f"Win Rate: {results['win_rate']:.2%}")
            print(f"Profit Factor: {results['profit_factor']:.2f}")
            print("="*50)
            
        else:
            trading_system.start(mode=args.mode)
            
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 