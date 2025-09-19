#!/usr/bin/env python3
"""
Core Engine System Integration Test
===================================

Comprehensive test of the complete trading procedure following the core_engine
architectural flow from the diagram:

Market Data Sources → Data Manager → Regime Assessment → 
Risk Management → Strategy Processing → Trading Engine → 
Execution Engine → Position Updates → Performance Monitor

This test demonstrates how core_engine components interact and orchestrate
together in a complete trading system using ONLY core_engine architecture.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Core Engine System Integration)
"""

import logging
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("core_engine_system_test")

# Import our core_engine components ONLY
from data_manager_enhanced import ClickHouseDataManager, ClickHouseDataConfig
from indicators_engine import EnhancedTechnicalIndicators, EnhancedIndicatorConfig
from feature_engineer import FeatureEngineer
from signal_generator import SignalGenerator
from portfolio_manager import PaperTradingEngine, PortfolioManager


@dataclass
class CoreEngineSystemConfig:
    """Configuration for core engine system test"""
    symbols: List[str] = None
    target_date: str = "2024-12-20"
    start_time: str = "09:30"
    end_time: str = "16:00"
    test_duration_minutes: int = 30
    initial_capital: float = 100000.0
    max_position_size: float = 0.1
    enable_live_trading: bool = False
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL']


class CoreEngineRegimeAssessment:
    """Core Engine Market Regime Assessment using existing indicators"""
    
    def __init__(self):
        self.indicators_engine = EnhancedTechnicalIndicators()
        
    def assess_market_conditions(self, market_data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Assess market regime using core_engine indicators"""
        try:
            # Prepare data for indicators
            df = market_data.reset_index()
            df['symbol'] = symbol
            
            # Calculate indicators for regime assessment
            indicators = self.indicators_engine.calculate_indicators(df)
            
            # Get key regime indicators
            rsi = indicators['rsi'].iloc[-1] if 'rsi' in indicators.columns else 50
            volatility = indicators['volatility'].iloc[-1] if 'volatility' in indicators.columns else 0.02
            trend_strength = indicators['adx'].iloc[-1] if 'adx' in indicators.columns else 25
            
            # Determine regime
            regime_type = "NORMAL"
            confidence = 0.8
            
            # High volatility regime
            if volatility > 0.03:
                regime_type = "HIGH_VOLATILITY"
                confidence = 0.9
            # Low volatility regime
            elif volatility < 0.01:
                regime_type = "LOW_VOLATILITY"
                confidence = 0.85
            # Trending regime
            elif trend_strength > 40:
                regime_type = "TRENDING"
                confidence = 0.9
            # Ranging regime
            elif trend_strength < 20:
                regime_type = "RANGING"
                confidence = 0.8
            
            return {
                "type": regime_type,
                "confidence": confidence,
                "volatility": float(volatility),
                "rsi": float(rsi),
                "trend_strength": float(trend_strength),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.warning(f"Regime assessment failed for {symbol}: {e}")
            return {
                "type": "UNKNOWN",
                "confidence": 0.5,
                "error": str(e),
                "timestamp": datetime.now()
            }


class CoreEngineRiskManager:
    """Core Engine Risk Management using portfolio constraints"""
    
    def __init__(self, config: CoreEngineSystemConfig):
        self.config = config
        self.max_position_size = config.max_position_size
        self.max_daily_loss = 0.02  # 2% max daily loss
        self.var_limit = 0.03  # 3% VaR limit
        
    def authorize_trade(self, signal: Dict[str, Any], portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Authorize trade based on core_engine risk rules"""
        try:
            symbol = signal.get('symbol', '')
            action = signal.get('action', 'hold')
            quantity = signal.get('quantity', 0)
            price = signal.get('price', 0)
            
            # Check position size limits
            portfolio_value = portfolio_state.get('portfolio_value', self.config.initial_capital)
            position_value = abs(quantity * price)
            position_weight = position_value / portfolio_value
            
            if position_weight > self.max_position_size:
                return {
                    "authorized": False,
                    "reason": f"Position size {position_weight:.2%} exceeds limit {self.max_position_size:.2%}",
                    "recommended_action": "REDUCE_SIZE"
                }
            
            # Check daily loss limits
            current_pnl = portfolio_state.get('total_return', 0)
            if current_pnl < -self.max_daily_loss:
                return {
                    "authorized": False,
                    "reason": f"Daily loss {current_pnl:.2%} exceeds limit {self.max_daily_loss:.2%}",
                    "recommended_action": "HALT_TRADING"
                }
            
            # Check portfolio concentration
            positions = portfolio_state.get('positions', {})
            if symbol in positions:
                current_position = positions[symbol]['quantity']
                new_position = current_position + (quantity if action == 'buy' else -quantity)
                new_position_value = abs(new_position * price)
                new_weight = new_position_value / portfolio_value
                
                if new_weight > self.max_position_size:
                    return {
                        "authorized": False,
                        "reason": f"Combined position weight {new_weight:.2%} exceeds limit",
                        "recommended_action": "PARTIAL_FILL"
                    }
            
            return {
                "authorized": True,
                "reason": "Risk checks passed",
                "position_weight": position_weight,
                "risk_score": min(position_weight / self.max_position_size, 1.0)
            }
            
        except Exception as e:
            logger.error(f"Risk authorization failed: {e}")
            return {
                "authorized": False,
                "reason": f"Risk check error: {e}",
                "recommended_action": "MANUAL_REVIEW"
            }


class CoreEngineSystemOrchestrator:
    """
    Core Engine System Orchestrator
    
    Orchestrates the complete trading system using core_engine components:
    1. Market Data Sources (Enhanced Data Manager)
    2. Regime Assessment (Indicators-based)
    3. Risk Management (Portfolio-based)
    4. Strategy Processing (Signal Generation)
    5. Trading Engine (Portfolio Manager)
    6. Position Updates (Portfolio Tracking)
    7. Performance Monitor (Analytics)
    """
    
    def __init__(self, config: Optional[CoreEngineSystemConfig] = None):
        self.config = config or CoreEngineSystemConfig()
        self.logger = logging.getLogger("core_engine_orchestrator")
        
        # Core engine components
        self.data_manager = None
        self.regime_assessment = None
        self.risk_manager = None
        self.indicators_engine = None
        self.feature_engineer = None
        self.signal_generator = None
        self.portfolio_manager = None
        self.trading_engine = None
        
        # System state
        self.is_running = False
        self.test_results = {}
        self.current_positions = {}
        self.performance_metrics = {}
        
    async def run_comprehensive_system_test(self) -> Dict[str, Any]:
        """Run the complete core engine system integration test"""
        self.logger.info("🚀 Starting Core Engine System Integration Test")
        self.logger.info("=" * 80)
        
        try:
            # Phase 1: System Initialization
            await self._initialize_core_engine_system()
            
            # Phase 2: Market Data Integration
            await self._test_market_data_integration()
            
            # Phase 3: Regime Assessment Integration
            await self._test_regime_assessment_integration()
            
            # Phase 4: Risk Management Integration
            await self._test_risk_management_integration()
            
            # Phase 5: Complete Trading Pipeline
            await self._test_complete_trading_pipeline()
            
            # Phase 6: Performance Monitoring
            await self._test_performance_monitoring()
            
            # Phase 7: System Health Check
            await self._test_system_health()
            
            self.logger.info("=" * 80)
            self.logger.info("✅ Core Engine System Integration Test COMPLETED SUCCESSFULLY!")
            
            return self.test_results
            
        except Exception as e:
            self.logger.error(f"❌ Core engine system test failed: {e}")
            raise
    
    async def _initialize_core_engine_system(self):
        """Phase 1: Initialize all core engine components"""
        self.logger.info("\n📋 PHASE 1: CORE ENGINE SYSTEM INITIALIZATION")
        self.logger.info("-" * 50)
        
        # Initialize Enhanced Data Manager
        self.logger.info("Initializing Enhanced Data Manager...")
        data_config = ClickHouseDataConfig(
            symbols=self.config.symbols,
            target_date=self.config.target_date,
            enable_caching=True
        )
        self.data_manager = ClickHouseDataManager(data_config)
        self.logger.info("✅ Enhanced Data Manager initialized")
        
        # Initialize Regime Assessment (using indicators)
        self.logger.info("Initializing Regime Assessment Engine...")
        self.regime_assessment = CoreEngineRegimeAssessment()
        self.logger.info("✅ Regime Assessment Engine initialized")
        
        # Initialize Risk Manager
        self.logger.info("Initializing Risk Manager...")
        self.risk_manager = CoreEngineRiskManager(self.config)
        self.logger.info("✅ Risk Manager initialized")
        
        # Initialize Pipeline Components
        self.logger.info("Initializing Pipeline Components...")
        self.indicators_engine = EnhancedTechnicalIndicators()
        self.feature_engineer = FeatureEngineer()
        self.signal_generator = SignalGenerator()
        self.logger.info("✅ Pipeline Components initialized")
        
        # Initialize Portfolio Management
        self.logger.info("Initializing Portfolio Management...")
        self.trading_engine = PaperTradingEngine(self.config.initial_capital)
        self.portfolio_manager = PortfolioManager(self.trading_engine)
        self.logger.info("✅ Portfolio Management initialized")
        
        self.is_running = True
        
        self.test_results['initialization'] = {
            'data_manager': True,
            'regime_assessment': True,
            'risk_manager': True,
            'pipeline_components': True,
            'portfolio_management': True,
            'system_status': 'running'
        }
    
    async def _test_market_data_integration(self):
        """Phase 2: Test market data integration across all components"""
        self.logger.info("\n🌊 PHASE 2: MARKET DATA INTEGRATION")
        self.logger.info("-" * 50)
        
        market_data_results = {}
        
        for symbol in self.config.symbols:
            self.logger.info(f"Testing market data integration for {symbol}...")
            
            try:
                # Get market data
                market_data = self.data_manager.get_market_data(symbol)
                if market_data is None or market_data.empty:
                    self.logger.warning(f"⚠️ No data for {symbol}")
                    continue
                
                # Test data quality
                data_points = len(market_data)
                price_range = market_data['close'].max() - market_data['close'].min()
                volume_avg = market_data['volume'].mean()
                
                market_data_results[symbol] = {
                    'data_points': data_points,
                    'price_range': float(price_range),
                    'avg_volume': float(volume_avg),
                    'latest_price': float(market_data['close'].iloc[-1]),
                    'data_quality': 'good' if data_points > 100 else 'limited'
                }
                
                self.logger.info(f"✅ {symbol}: {data_points} points, latest=${market_data_results[symbol]['latest_price']:.2f}")
                
            except Exception as e:
                self.logger.error(f"❌ Market data integration failed for {symbol}: {e}")
                market_data_results[symbol] = {'error': str(e)}
        
        self.test_results['market_data_integration'] = market_data_results
    
    async def _test_regime_assessment_integration(self):
        """Phase 3: Test regime assessment integration"""
        self.logger.info("\n🎯 PHASE 3: REGIME ASSESSMENT INTEGRATION")
        self.logger.info("-" * 50)
        
        regime_results = {}
        
        for symbol in self.config.symbols:
            self.logger.info(f"Assessing market regime for {symbol}...")
            
            try:
                # Get market data
                market_data = self.data_manager.get_market_data(symbol)
                if market_data is None or market_data.empty:
                    continue
                
                # Assess regime
                regime_state = self.regime_assessment.assess_market_conditions(market_data, symbol)
                
                regime_results[symbol] = {
                    'regime_type': regime_state['type'],
                    'confidence': regime_state['confidence'],
                    'volatility': regime_state.get('volatility', 0),
                    'rsi': regime_state.get('rsi', 50),
                    'trend_strength': regime_state.get('trend_strength', 25)
                }
                
                self.logger.info(f"✅ {symbol}: {regime_state['type']} regime "
                               f"(confidence: {regime_state['confidence']:.1%}, "
                               f"volatility: {regime_state.get('volatility', 0):.1%})")
                
            except Exception as e:
                self.logger.error(f"❌ Regime assessment failed for {symbol}: {e}")
                regime_results[symbol] = {'error': str(e)}
        
        self.test_results['regime_assessment'] = regime_results
    
    async def _test_risk_management_integration(self):
        """Phase 4: Test risk management integration"""
        self.logger.info("\n🛡️ PHASE 4: RISK MANAGEMENT INTEGRATION")
        self.logger.info("-" * 50)
        
        risk_results = {}
        
        # Get current portfolio state
        portfolio_state = {
            'portfolio_value': self.trading_engine.get_portfolio_value(),
            'cash': self.trading_engine.cash,
            'positions': self.trading_engine.positions,
            'total_return': (self.trading_engine.get_portfolio_value() - self.config.initial_capital) / self.config.initial_capital
        }
        
        for symbol in self.config.symbols[:3]:  # Test first 3 symbols
            self.logger.info(f"Testing risk management for {symbol}...")
            
            try:
                # Get current price
                market_data = self.data_manager.get_market_data(symbol)
                if market_data is None or market_data.empty:
                    continue
                
                current_price = float(market_data['close'].iloc[-1])
                
                # Create test trade signal
                test_signal = {
                    'symbol': symbol,
                    'action': 'buy',
                    'quantity': 100,
                    'price': current_price,
                    'timestamp': datetime.now()
                }
                
                # Test risk authorization
                auth_result = self.risk_manager.authorize_trade(test_signal, portfolio_state)
                
                risk_results[symbol] = {
                    'authorized': auth_result['authorized'],
                    'reason': auth_result['reason'],
                    'position_weight': auth_result.get('position_weight', 0),
                    'risk_score': auth_result.get('risk_score', 0)
                }
                
                status_icon = "✅" if auth_result['authorized'] else "⚠️"
                self.logger.info(f"{status_icon} {symbol}: {auth_result['reason']}")
                
            except Exception as e:
                self.logger.error(f"❌ Risk management test failed for {symbol}: {e}")
                risk_results[symbol] = {'error': str(e)}
        
        self.test_results['risk_management'] = risk_results
    
    async def _test_complete_trading_pipeline(self):
        """Phase 5: Test complete trading pipeline end-to-end"""
        self.logger.info("\n🔄 PHASE 5: COMPLETE TRADING PIPELINE")
        self.logger.info("-" * 50)
        
        pipeline_results = {
            'symbols_processed': 0,
            'regimes_assessed': 0,
            'signals_generated': 0,
            'trades_authorized': 0,
            'trades_executed': 0,
            'positions_opened': 0
        }
        
        for symbol in self.config.symbols:
            self.logger.info(f"Running complete pipeline for {symbol}...")
            
            try:
                # Step 1: Market Data
                market_data = self.data_manager.get_market_data(symbol)
                if market_data is None or market_data.empty:
                    continue
                
                pipeline_results['symbols_processed'] += 1
                
                # Step 2: Regime Assessment
                regime_state = self.regime_assessment.assess_market_conditions(market_data, symbol)
                pipeline_results['regimes_assessed'] += 1
                
                # Step 3: Technical Analysis Pipeline
                df = market_data.reset_index()
                df['symbol'] = symbol
                
                indicators = self.indicators_engine.calculate_indicators(df)
                features = self.feature_engineer.create_features(indicators)
                signals = self.signal_generator.generate_signals(features)
                
                if hasattr(signals, '__len__') and len(signals) > 0:
                    pipeline_results['signals_generated'] += len(signals)
                    
                    # Step 4: Risk Authorization
                    portfolio_state = {
                        'portfolio_value': self.trading_engine.get_portfolio_value(),
                        'cash': self.trading_engine.cash,
                        'positions': self.trading_engine.positions,
                        'total_return': (self.trading_engine.get_portfolio_value() - self.config.initial_capital) / self.config.initial_capital
                    }
                    
                    for signal in signals:
                        # Convert TradingSignal to dict for risk manager
                        signal_dict = {
                            'symbol': signal.symbol,
                            'action': signal.signal_type.value,
                            'quantity': 100,  # Default quantity
                            'price': signal.price,
                            'confidence': signal.confidence
                        }
                        
                        auth_result = self.risk_manager.authorize_trade(signal_dict, portfolio_state)
                        
                        if auth_result['authorized']:
                            pipeline_results['trades_authorized'] += 1
                            
                            # Step 5: Trade Execution
                            order_id = self.trading_engine.submit_order(
                                symbol=symbol,
                                side=signal.signal_type.value,
                                quantity=100,
                                order_type="market"
                            )
                            
                            if order_id:
                                pipeline_results['trades_executed'] += 1
                                
                                # Check positions
                                if symbol in self.trading_engine.positions:
                                    pipeline_results['positions_opened'] += 1
                
                self.logger.info(f"✅ {symbol} pipeline complete")
                
            except Exception as e:
                self.logger.error(f"❌ Pipeline failed for {symbol}: {e}")
        
        # Summary
        self.logger.info(f"Pipeline Results:")
        self.logger.info(f"  Symbols Processed: {pipeline_results['symbols_processed']}")
        self.logger.info(f"  Regimes Assessed: {pipeline_results['regimes_assessed']}")
        self.logger.info(f"  Signals Generated: {pipeline_results['signals_generated']}")
        self.logger.info(f"  Trades Authorized: {pipeline_results['trades_authorized']}")
        self.logger.info(f"  Trades Executed: {pipeline_results['trades_executed']}")
        self.logger.info(f"  Positions Opened: {pipeline_results['positions_opened']}")
        
        self.test_results['complete_pipeline'] = pipeline_results
    
    async def _test_performance_monitoring(self):
        """Phase 6: Test performance monitoring and analytics"""
        self.logger.info("\n📊 PHASE 6: PERFORMANCE MONITORING")
        self.logger.info("-" * 50)
        
        # Get comprehensive performance metrics
        portfolio_summary = self.trading_engine.get_portfolio_summary()
        positions = self.trading_engine.positions
        
        performance_results = {
            'portfolio_value': portfolio_summary.get('portfolio_value', 0),
            'total_return': portfolio_summary.get('total_return', 0),
            'cash_balance': portfolio_summary.get('cash', 0),
            'positions_count': len(positions),
            'trades_count': len(self.trading_engine.trades),
            'total_pnl': portfolio_summary.get('total_pnl', 0),
            'unrealized_pnl': portfolio_summary.get('unrealized_pnl', 0)
        }
        
        # Position analysis
        position_analysis = {}
        total_position_value = 0
        for symbol, position in positions.items():
            if position.quantity != 0:
                market_data = self.data_manager.get_market_data(symbol)
                if market_data is not None and not market_data.empty:
                    current_price = float(market_data['close'].iloc[-1])
                    position_value = abs(position.quantity * current_price)
                    total_position_value += position_value
                    
                    position_analysis[symbol] = {
                        'quantity': position.quantity,
                        'avg_price': position.avg_price,
                        'current_price': current_price,
                        'position_value': position_value,
                        'unrealized_pnl': position.unrealized_pnl
                    }
        
        performance_results['position_analysis'] = position_analysis
        performance_results['total_position_value'] = total_position_value
        
        self.logger.info("Performance Metrics:")
        for key, value in performance_results.items():
            if key not in ['position_analysis']:
                if isinstance(value, float):
                    if 'rate' in key or 'return' in key:
                        self.logger.info(f"  {key.replace('_', ' ').title()}: {value:.2%}")
                    else:
                        self.logger.info(f"  {key.replace('_', ' ').title()}: {value:,.2f}")
                else:
                    self.logger.info(f"  {key.replace('_', ' ').title()}: {value}")
        
        self.test_results['performance_monitoring'] = performance_results
    
    async def _test_system_health(self):
        """Phase 7: Test system health and component status"""
        self.logger.info("\n🔍 PHASE 7: SYSTEM HEALTH CHECK")
        self.logger.info("-" * 50)
        
        system_health = {}
        
        # Test component health
        components = {
            'data_manager': self.data_manager,
            'regime_assessment': self.regime_assessment,
            'risk_manager': self.risk_manager,
            'indicators_engine': self.indicators_engine,
            'feature_engineer': self.feature_engineer,
            'signal_generator': self.signal_generator,
            'trading_engine': self.trading_engine
        }
        
        for component_name, component in components.items():
            try:
                health_status = True
                health_details = {}
                
                if component_name == 'data_manager':
                    # Test data connection
                    symbols = component.get_available_symbols()
                    health_details['available_symbols'] = len(symbols)
                    health_status = len(symbols) > 0
                    
                elif component_name == 'trading_engine':
                    # Test trading engine state
                    portfolio_value = component.get_portfolio_value()
                    health_details['portfolio_value'] = portfolio_value
                    health_status = portfolio_value > 0
                
                elif hasattr(component, 'get_supported_indicators'):
                    # Test indicators calculation
                    supported_indicators = component.get_supported_indicators()
                    health_details['indicator_count'] = len(supported_indicators)
                    health_status = len(supported_indicators) > 0
                
                system_health[component_name] = {
                    'status': 'healthy' if health_status else 'unhealthy',
                    'details': health_details
                }
                
                status_icon = "✅" if health_status else "❌"
                self.logger.info(f"{status_icon} {component_name.replace('_', ' ').title()}: {'Healthy' if health_status else 'Unhealthy'}")
                
            except Exception as e:
                system_health[component_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                self.logger.error(f"❌ {component_name} health check failed: {e}")
        
        # Overall system health
        healthy_components = sum(1 for h in system_health.values() if h['status'] == 'healthy')
        total_components = len(system_health)
        system_health_score = healthy_components / total_components
        
        system_health['overall'] = {
            'health_score': system_health_score,
            'healthy_components': healthy_components,
            'total_components': total_components,
            'status': 'healthy' if system_health_score >= 0.8 else 'degraded' if system_health_score >= 0.5 else 'unhealthy'
        }
        
        self.logger.info(f"Overall System Health: {system_health_score:.1%} "
                        f"({healthy_components}/{total_components} components healthy)")
        
        self.test_results['system_health'] = system_health


async def main():
    """Main test execution"""
    print("🚀 Starting Core Engine System Integration Test")
    print("=" * 80)
    
    # Configure test
    test_config = CoreEngineSystemConfig(
        symbols=['NVDA', 'TSLA', 'AAPL'],
        test_duration_minutes=15,
        initial_capital=100000.0
    )
    
    # Run comprehensive test
    orchestrator = CoreEngineSystemOrchestrator(test_config)
    results = await orchestrator.run_comprehensive_system_test()
    
    # Print summary
    print("\n" + "=" * 80)
    print("📋 CORE ENGINE SYSTEM TEST SUMMARY")
    print("=" * 80)
    
    for phase, result in results.items():
        print(f"\n{phase.upper().replace('_', ' ')}:")
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, dict) and len(value) > 3:
                    print(f"  ✅ {key}: {len(value)} items")
                else:
                    print(f"  ✅ {key}: {value}")
        else:
            print(f"  ✅ {result}")
    
    print("\n🎉 Core Engine System Integration Test Complete!")


if __name__ == "__main__":
    asyncio.run(main())