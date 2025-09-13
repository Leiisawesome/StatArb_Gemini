#!/usr/bin/env python3
"""
Market Condition Analytics Integration Example
=============================================

Demonstrates how the new MarketConditionAnalyticsEngine integrates with the
existing core_structure components for dynamic trading system optimization.

This example shows the complete workflow:
1. Data ingestion from multiple sources
2. Real-time regime detection
3. Dynamic strategy selection
4. Instrument optimization
5. Performance feedback loop

Author: Professional Trading System Architecture
Version: 1.0.0 (Integration Example)
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

# Import existing core_structure components
from core_structure.analytics import CoreAnalyticsEngine, MonitoringAnalyticsEngine, ResearchAnalyticsEngine
from core_structure.strategies import StrategyManager, StrategyType, MomentumStrategy, MeanReversionStrategy
from core_structure.infrastructure.database import DatabaseManager
from core_structure.infrastructure.messaging import MessageBus, Message, MessageType
from core_structure.infrastructure.monitoring import MetricsCollector

# Import new market condition analytics
from core_structure.analytics.market_condition_analytics import (
    MarketConditionAnalyticsEngine,
    StrategySelection,
    PerformanceFeedback
)

logger = logging.getLogger(__name__)


class UnifiedTradingSystemWithMarketConditions:
    """
    Unified trading system enhanced with market condition analytics.
    
    This demonstrates how the new MarketConditionAnalyticsEngine integrates
    seamlessly with existing components to provide intelligent, adaptive trading.
    """
    
    def __init__(self):
        """Initialize the unified trading system"""
        
        # Initialize infrastructure components (existing)
        self.database_manager = DatabaseManager()
        self.message_bus = MessageBus()
        self.metrics_collector = MetricsCollector()
        
        # Initialize existing analytics engines
        self.core_analytics = CoreAnalyticsEngine()
        self.monitoring_analytics = MonitoringAnalyticsEngine()
        self.research_analytics = ResearchAnalyticsEngine()
        
        # Initialize strategy manager (existing)
        self.strategy_manager = StrategyManager()
        
        # Initialize NEW market condition analytics engine
        self.market_condition_engine = MarketConditionAnalyticsEngine(
            database_manager=self.database_manager,
            message_bus=self.message_bus,
            metrics_collector=self.metrics_collector
        )
        
        # Integration state
        self.current_portfolio = {}
        self.active_strategies = {}
        self.performance_tracker = {}
        
        logger.info("🚀 Unified trading system with market conditions initialized")
    
    async def start_system(self) -> None:
        """Start the complete trading system"""
        try:
            logger.info("🔄 Starting unified trading system...")
            
            # Start infrastructure components
            await self.message_bus.start()
            await self.metrics_collector.start()
            
            # Start analytics engines
            await self.market_condition_engine.start()
            
            # Subscribe to market condition changes
            self.message_bus.subscribe(
                MessageType.REGIME_CHANGE,
                self._on_regime_change
            )
            
            # Start periodic analysis
            asyncio.create_task(self._periodic_analysis_loop())
            
            logger.info("✅ Unified trading system started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading system: {e}")
            raise
    
    async def process_market_data(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Process new market data through the complete workflow.
        
        This demonstrates the data-driven flow:
        Market Data → Regime Detection → Strategy Selection → Execution
        """
        try:
            logger.info("📊 Processing market data through complete workflow")
            
            # Step 1: Analyze current market condition
            market_state = await self.market_condition_engine.analyze_current_market_condition(
                market_data=market_data,
                macro_data=await self._get_macro_data(),
                sentiment_data=await self._get_sentiment_data()
            )
            
            logger.info(f"🎯 Current market regime: {market_state.primary_condition.value} "
                       f"(confidence: {market_state.confidence:.2f})")
            
            # Step 2: Get strategy recommendations
            strategy_selection = await self.market_condition_engine.get_strategy_recommendations(
                market_state=market_state,
                portfolio_context=await self._get_portfolio_context()
            )
            
            logger.info(f"📈 Strategy allocation: {strategy_selection.selected_strategies}")
            
            # Step 3: Update strategy allocations if needed
            await self._update_strategy_allocations(strategy_selection)
            
            # Step 4: Generate trading signals using selected strategies
            trading_signals = await self._generate_trading_signals(
                strategy_selection=strategy_selection,
                market_data=market_data
            )
            
            # Step 5: Execute trades (simulation)
            execution_results = await self._execute_trades(trading_signals)
            
            # Step 6: Collect performance feedback
            await self._collect_performance_feedback(
                strategy_selection=strategy_selection,
                execution_results=execution_results
            )
            
            return {
                'market_state': market_state,
                'strategy_selection': strategy_selection,
                'trading_signals': trading_signals,
                'execution_results': execution_results,
                'portfolio_state': self.current_portfolio
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing market data: {e}")
            raise
    
    async def _get_macro_data(self) -> Dict[str, Any]:
        """Get macroeconomic data (placeholder)"""
        # In real implementation, this would fetch from economic data APIs
        return {
            'fed_funds_rate': 5.25,
            'cpi_yoy': 3.2,
            'gdp_growth_qoq': 2.1,
            'unemployment': 3.8,
            'vix': 18.5
        }
    
    async def _get_sentiment_data(self) -> Dict[str, Any]:
        """Get sentiment data (placeholder)"""
        # In real implementation, this would fetch from sentiment APIs
        return {
            'news_sentiment_score': 0.2,
            'social_media_sentiment': 0.1,
            'analyst_sentiment': 0.3,
            'put_call_ratio': 0.8
        }
    
    async def _get_portfolio_context(self) -> Dict[str, Any]:
        """Get current portfolio context"""
        return {
            'total_value': sum(pos.get('value', 0) for pos in self.current_portfolio.values()),
            'positions': len(self.current_portfolio),
            'cash_allocation': 0.1,
            'risk_budget_used': 0.6
        }
    
    async def _update_strategy_allocations(self, strategy_selection: StrategySelection) -> None:
        """Update strategy allocations based on recommendations"""
        try:
            logger.info("🔄 Updating strategy allocations...")
            
            # Compare current allocations with recommendations
            current_allocations = {
                strategy_type: self.active_strategies.get(strategy_type, {}).get('weight', 0.0)
                for strategy_type in StrategyType
            }
            
            recommended_allocations = strategy_selection.selected_strategies
            
            # Check if significant rebalancing is needed
            rebalance_threshold = 0.1  # 10% threshold
            needs_rebalancing = any(
                abs(recommended_allocations.get(st, 0) - current_allocations.get(st, 0)) > rebalance_threshold
                for st in StrategyType
            )
            
            if needs_rebalancing:
                logger.info("📊 Significant allocation change detected - rebalancing strategies")
                
                # Update active strategies
                for strategy_type, weight in recommended_allocations.items():
                    if weight > 0.05:  # Only activate strategies with >5% allocation
                        if strategy_type not in self.active_strategies:
                            # Create new strategy instance
                            strategy = await self._create_strategy_instance(
                                strategy_type=strategy_type,
                                instruments=strategy_selection.instruments_per_strategy.get(strategy_type, [])
                            )
                            self.active_strategies[strategy_type] = {
                                'strategy': strategy,
                                'weight': weight,
                                'instruments': strategy_selection.instruments_per_strategy.get(strategy_type, [])
                            }
                            logger.info(f"✅ Activated {strategy_type.value} strategy (weight: {weight:.2f})")
                        else:
                            # Update existing strategy weight
                            self.active_strategies[strategy_type]['weight'] = weight
                            logger.info(f"🔄 Updated {strategy_type.value} weight to {weight:.2f}")
                    else:
                        # Deactivate strategy if weight too low
                        if strategy_type in self.active_strategies:
                            del self.active_strategies[strategy_type]
                            logger.info(f"❌ Deactivated {strategy_type.value} strategy")
            
        except Exception as e:
            logger.error(f"❌ Error updating strategy allocations: {e}")
    
    async def _create_strategy_instance(self, 
                                      strategy_type: StrategyType,
                                      instruments: List[str]) -> Any:
        """Create a strategy instance based on type"""
        try:
            config = {
                'instruments': instruments,
                'lookback_period': 20,
                'risk_threshold': 0.02
            }
            
            if strategy_type == StrategyType.MOMENTUM:
                return MomentumStrategy(f"momentum_{datetime.now().isoformat()}", config)
            elif strategy_type == StrategyType.MEAN_REVERSION:
                return MeanReversionStrategy(f"mean_reversion_{datetime.now().isoformat()}", config)
            else:
                # For pairs trading or other strategies
                return self.strategy_manager.create_strategy(strategy_type, f"{strategy_type.value}_{datetime.now().isoformat()}", config)
                
        except Exception as e:
            logger.error(f"❌ Error creating strategy instance: {e}")
            raise
    
    async def _generate_trading_signals(self, 
                                      strategy_selection: StrategySelection,
                                      market_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate trading signals using active strategies"""
        try:
            all_signals = []
            
            for strategy_type, strategy_info in self.active_strategies.items():
                strategy = strategy_info['strategy']
                weight = strategy_info['weight']
                instruments = strategy_info['instruments']
                
                # Generate signals for each instrument
                for instrument in instruments[:5]:  # Limit to top 5 instruments
                    try:
                        # Get instrument-specific data
                        instrument_data = market_data[market_data.get('symbol', 'SPY') == instrument]
                        
                        if not instrument_data.empty:
                            # Use existing strategy generate_signals method
                            # signals = await strategy.generate_signals(instrument_data)
                            
                            # Placeholder signal generation
                            signal = {
                                'strategy': strategy_type.value,
                                'instrument': instrument,
                                'signal_type': 'BUY',  # Simplified
                                'strength': 0.7,
                                'weight': weight,
                                'timestamp': datetime.now(),
                                'metadata': {
                                    'regime': strategy_selection.regime.value,
                                    'confidence': strategy_selection.confidence
                                }
                            }
                            all_signals.append(signal)
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Error generating signal for {instrument}: {e}")
            
            logger.info(f"📈 Generated {len(all_signals)} trading signals")
            return all_signals
            
        except Exception as e:
            logger.error(f"❌ Error generating trading signals: {e}")
            return []
    
    async def _execute_trades(self, trading_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute trades based on signals (simulation)"""
        try:
            execution_results = []
            
            for signal in trading_signals:
                # Simulate trade execution
                execution_result = {
                    'signal': signal,
                    'executed': True,
                    'execution_price': 100.0 + np.random.normal(0, 0.5),  # Simulated price
                    'execution_time': datetime.now(),
                    'slippage': np.random.normal(0, 0.001),  # Simulated slippage
                    'commission': 0.005,  # 0.5 bps commission
                    'position_size': signal['weight'] * 10000  # $10K per unit weight
                }
                
                execution_results.append(execution_result)
                
                # Update portfolio
                instrument = signal['instrument']
                if instrument not in self.current_portfolio:
                    self.current_portfolio[instrument] = {
                        'quantity': 0,
                        'value': 0,
                        'avg_price': 0
                    }
                
                # Update position (simplified)
                position = self.current_portfolio[instrument]
                new_quantity = execution_result['position_size'] / execution_result['execution_price']
                position['quantity'] += new_quantity
                position['value'] += execution_result['position_size']
                position['avg_price'] = position['value'] / position['quantity'] if position['quantity'] != 0 else 0
            
            logger.info(f"✅ Executed {len(execution_results)} trades")
            return execution_results
            
        except Exception as e:
            logger.error(f"❌ Error executing trades: {e}")
            return []
    
    async def _collect_performance_feedback(self, 
                                          strategy_selection: StrategySelection,
                                          execution_results: List[Dict[str, Any]]) -> None:
        """Collect performance feedback for continuous improvement"""
        try:
            for result in execution_results:
                signal = result['signal']
                
                # Calculate simple return (placeholder)
                predicted_return = 0.01  # 1% predicted return
                actual_return = np.random.normal(0.008, 0.02)  # Simulated actual return
                
                feedback = PerformanceFeedback(
                    timestamp=datetime.now(),
                    strategy=StrategyType(signal['strategy']),
                    instrument=signal['instrument'],
                    regime=strategy_selection.regime,
                    actual_return=actual_return,
                    predicted_return=predicted_return,
                    prediction_error=abs(actual_return - predicted_return),
                    risk_adjusted_return=actual_return / 0.15,  # Assuming 15% volatility
                    execution_quality=0.95,  # High execution quality
                    regime_accuracy=strategy_selection.confidence,
                    metadata={
                        'slippage': result['slippage'],
                        'commission': result['commission']
                    }
                )
                
                # Update market condition engine with feedback
                await self.market_condition_engine.update_performance_feedback(feedback)
            
            logger.info(f"📊 Collected performance feedback for {len(execution_results)} trades")
            
        except Exception as e:
            logger.error(f"❌ Error collecting performance feedback: {e}")
    
    async def _periodic_analysis_loop(self) -> None:
        """Periodic analysis and optimization loop"""
        while True:
            try:
                await asyncio.sleep(300)  # 5-minute intervals
                
                # Get performance metrics
                performance_metrics = self.market_condition_engine.get_performance_metrics()
                
                # Log system status
                logger.info(f"🔄 System status - Regime accuracy: {performance_metrics.get('recent_regime_accuracy', 0):.2f}, "
                           f"Prediction error: {performance_metrics.get('recent_prediction_error', 0):.2f}")
                
                # Update metrics collector
                if self.metrics_collector:
                    for metric_name, value in performance_metrics.items():
                        if isinstance(value, (int, float)):
                            self.metrics_collector.record_metric(f"market_condition.{metric_name}", value)
                
            except Exception as e:
                logger.error(f"❌ Error in periodic analysis loop: {e}")
    
    def _on_regime_change(self, message: Message) -> None:
        """Handle regime change notifications"""
        try:
            regime_data = message.data
            logger.info(f"🚨 Regime change detected: {regime_data.get('previous_regime')} → {regime_data.get('new_regime')}")
            
            # Trigger immediate strategy rebalancing
            asyncio.create_task(self._handle_regime_change(regime_data))
            
        except Exception as e:
            logger.error(f"❌ Error handling regime change: {e}")
    
    async def _handle_regime_change(self, regime_data: Dict[str, Any]) -> None:
        """Handle regime change by rebalancing strategies"""
        try:
            logger.info("🔄 Handling regime change - triggering strategy rebalancing")
            
            # Get latest market state
            current_state = self.market_condition_engine.get_current_market_state()
            if current_state:
                # Get new strategy recommendations
                new_selection = await self.market_condition_engine.get_strategy_recommendations(
                    market_state=current_state
                )
                
                # Update allocations
                await self._update_strategy_allocations(new_selection)
                
                logger.info("✅ Regime change handling completed")
            
        except Exception as e:
            logger.error(f"❌ Error handling regime change: {e}")


# ================================================================================
# USAGE EXAMPLE
# ================================================================================

async def main():
    """Demonstrate the unified trading system with market conditions"""
    
    print("🚀 Starting Unified Trading System with Market Condition Analytics")
    print("=" * 80)
    
    # Create system instance
    trading_system = UnifiedTradingSystemWithMarketConditions()
    
    try:
        # Start the system
        await trading_system.start_system()
        
        # Generate sample market data
        sample_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1H'),
            'symbol': 'SPY',
            'open': 400 + np.random.randn(100).cumsum() * 0.5,
            'high': 401 + np.random.randn(100).cumsum() * 0.5,
            'low': 399 + np.random.randn(100).cumsum() * 0.5,
            'close': 400 + np.random.randn(100).cumsum() * 0.5,
            'volume': 1000000 + np.random.randint(-100000, 100000, 100)
        })
        
        print("\n📊 Processing market data through complete workflow...")
        
        # Process market data
        results = await trading_system.process_market_data(sample_data)
        
        print(f"\n✅ Workflow completed successfully!")
        print(f"📈 Market Regime: {results['market_state'].primary_condition.value}")
        print(f"🎯 Strategy Allocation: {results['strategy_selection'].selected_strategies}")
        print(f"📊 Generated Signals: {len(results['trading_signals'])}")
        print(f"💼 Portfolio Positions: {len(results['portfolio_state'])}")
        
        # Run for a few more cycles
        print("\n🔄 Running additional analysis cycles...")
        for i in range(3):
            await asyncio.sleep(2)
            
            # Generate new data
            new_data = sample_data.iloc[-10:].copy()  # Last 10 periods
            new_data['close'] = new_data['close'] + np.random.randn(10) * 0.5
            
            results = await trading_system.process_market_data(new_data)
            print(f"Cycle {i+1}: Regime={results['market_state'].primary_condition.value}, "
                  f"Signals={len(results['trading_signals'])}")
        
        print("\n🎉 Demonstration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error in demonstration: {e}")
        raise
    
    finally:
        # Cleanup
        await trading_system.market_condition_engine.stop()


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suppress sklearn warnings
    import warnings
    warnings.filterwarnings('ignore')
    
    asyncio.run(main())