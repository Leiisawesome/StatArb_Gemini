#!/usr/bin/env python3
"""
Module Integration Examples
===========================

Comprehensive examples demonstrating how different modules integrate
through the SystemOrchestrator in realistic trading scenarios.

Examples cover:
- Signal Generation ↔ Execution Engine Integration
- Analytics Integration with Real-time Data
- Multi-Module Workflow Orchestration
- Error Handling and Recovery
- Performance Monitoring

Author: Infrastructure Integration Team
Date: 2025-01-27
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_structure.infrastructure.system_orchestrator import (
    SystemOrchestrator,
    OrchestrationConfig,
    ModuleStatus,
    MessageType,
    SystemMessage
)

class TradingSignalGenerator:
    """Mock signal generation module"""
    
    def __init__(self, name: str):
        self.name = name
        self.signals_generated = 0
        self.last_signal_time = None
    
    async def generate_signal(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signal based on market data"""
        self.signals_generated += 1
        self.last_signal_time = datetime.now()
        
        # Mock signal generation logic
        price = market_data.get('price', 100.0)
        volume = market_data.get('volume', 1000000)
        
        # Simple momentum-based signal
        if price > 105.0 and volume > 1500000:
            signal = {
                'action': 'buy',
                'symbol': market_data.get('symbol', 'AAPL'),
                'quantity': 100,
                'price': price,
                'confidence': 0.85,
                'reason': 'Strong momentum with high volume'
            }
        elif price < 95.0:
            signal = {
                'action': 'sell',
                'symbol': market_data.get('symbol', 'AAPL'),
                'quantity': 100,
                'price': price,
                'confidence': 0.75,
                'reason': 'Price decline detected'
            }
        else:
            signal = {
                'action': 'hold',
                'symbol': market_data.get('symbol', 'AAPL'),
                'quantity': 0,
                'price': price,
                'confidence': 0.5,
                'reason': 'No clear signal'
            }
        
        return signal
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for signal generator"""
        return {
            'is_healthy': True,
            'health_score': 0.95,
            'signals_generated': self.signals_generated,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'signals_generated': self.signals_generated,
            'uptime_hours': 24.0,
            'avg_processing_time_ms': 15.0,
            'success_rate': 0.98
        }

class ExecutionEngine:
    """Mock execution engine module"""
    
    def __init__(self, name: str):
        self.name = name
        self.orders_executed = 0
        self.total_volume = 0
        self.execution_history = []
    
    async def execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading order"""
        self.orders_executed += 1
        quantity = order.get('quantity', 0)
        price = order.get('price', 0.0)
        self.total_volume += quantity * price
        
        # Mock execution logic
        execution_time = datetime.now()
        execution_id = f"EXEC_{self.orders_executed:06d}"
        
        # Simulate execution delay
        await asyncio.sleep(0.01)
        
        execution_result = {
            'execution_id': execution_id,
            'order_id': order.get('order_id', f"ORDER_{self.orders_executed:06d}"),
            'symbol': order.get('symbol'),
            'action': order.get('action'),
            'quantity': quantity,
            'price': price,
            'execution_time': execution_time.isoformat(),
            'status': 'completed',
            'slippage': 0.02,  # 2 cents slippage
            'commission': 1.0
        }
        
        self.execution_history.append(execution_result)
        return execution_result
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for execution engine"""
        return {
            'is_healthy': True,
            'health_score': 0.98,
            'orders_executed': self.orders_executed,
            'total_volume': self.total_volume
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'orders_executed': self.orders_executed,
            'total_volume': self.total_volume,
            'avg_execution_time_ms': 25.0,
            'success_rate': 0.99,
            'avg_slippage': 0.02
        }

class AnalyticsEngine:
    """Mock analytics engine module"""
    
    def __init__(self, name: str):
        self.name = name
        self.analyses_performed = 0
        self.performance_data = []
    
    async def analyze_performance(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze execution performance"""
        self.analyses_performed += 1
        
        # Mock analytics logic
        slippage = execution_data.get('slippage', 0.0)
        commission = execution_data.get('commission', 0.0)
        price = execution_data.get('price', 0.0)
        
        total_cost = slippage + commission
        cost_basis = total_cost / price if price > 0 else 0
        
        analysis_result = {
            'execution_id': execution_data.get('execution_id'),
            'total_cost': total_cost,
            'cost_basis': cost_basis,
            'slippage_impact': slippage,
            'commission_impact': commission,
            'efficiency_score': max(0, 1 - cost_basis),
            'analysis_time': datetime.now().isoformat()
        }
        
        self.performance_data.append(analysis_result)
        return analysis_result
    
    async def generate_report(self, time_period: str = "daily") -> Dict[str, Any]:
        """Generate performance report"""
        if not self.performance_data:
            return {"message": "No data available for report"}
        
        avg_efficiency = sum(d['efficiency_score'] for d in self.performance_data) / len(self.performance_data)
        avg_cost = sum(d['total_cost'] for d in self.performance_data) / len(self.performance_data)
        
        return {
            'report_type': f"{time_period}_performance",
            'analyses_performed': self.analyses_performed,
            'avg_efficiency_score': avg_efficiency,
            'avg_total_cost': avg_cost,
            'generated_at': datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for analytics engine"""
        return {
            'is_healthy': True,
            'health_score': 0.92,
            'analyses_performed': self.analyses_performed,
            'data_points': len(self.performance_data)
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'analyses_performed': self.analyses_performed,
            'avg_processing_time_ms': 45.0,
            'data_points_processed': len(self.performance_data),
            'uptime_hours': 24.0
        }

class RiskManager:
    """Mock risk management module"""
    
    def __init__(self, name: str):
        self.name = name
        self.risk_checks = 0
        self.risk_alerts = 0
    
    async def check_risk(self, order: Dict[str, Any], portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Check risk for proposed order"""
        self.risk_checks += 1
        
        # Mock risk assessment
        quantity = order.get('quantity', 0)
        price = order.get('price', 0.0)
        order_value = quantity * price
        
        current_exposure = portfolio_state.get('total_exposure', 0)
        max_exposure = portfolio_state.get('max_exposure', 100000)
        
        new_exposure = current_exposure + order_value
        risk_level = "low" if new_exposure < max_exposure * 0.8 else "medium" if new_exposure < max_exposure else "high"
        
        if risk_level == "high":
            self.risk_alerts += 1
        
        return {
            'order_id': order.get('order_id'),
            'risk_level': risk_level,
            'current_exposure': current_exposure,
            'new_exposure': new_exposure,
            'max_exposure': max_exposure,
            'approved': risk_level != "high",
            'risk_score': 0.1 if risk_level == "low" else 0.5 if risk_level == "medium" else 0.9
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for risk manager"""
        return {
            'is_healthy': True,
            'health_score': 0.97,
            'risk_checks': self.risk_checks,
            'risk_alerts': self.risk_alerts
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'risk_checks': self.risk_checks,
            'risk_alerts': self.risk_alerts,
            'avg_processing_time_ms': 10.0,
            'uptime_hours': 24.0
        }

class ModuleIntegrationExamples:
    """Examples of module integration through SystemOrchestrator"""
    
    def __init__(self):
        self.orchestrator = None
        self.signal_generator = None
        self.execution_engine = None
        self.analytics_engine = None
        self.risk_manager = None
        
        # Message handlers
        self.signal_messages = []
        self.execution_messages = []
        self.analytics_messages = []
        self.risk_messages = []
    
    async def setup_orchestrator(self):
        """Setup SystemOrchestrator with all modules"""
        print("🔧 Setting up SystemOrchestrator...")
        
        # Create orchestrator with custom config
        config = OrchestrationConfig(
            health_check_interval=5.0,
            metrics_collection_interval=10.0,
            max_message_queue_size=1000
        )
        
        self.orchestrator = SystemOrchestrator(config)
        await self.orchestrator.start()
        
        # Create module instances
        self.signal_generator = TradingSignalGenerator("signal_generator")
        self.execution_engine = ExecutionEngine("execution_engine")
        self.analytics_engine = AnalyticsEngine("analytics_engine")
        self.risk_manager = RiskManager("risk_manager")
        
        # Register modules with orchestrator
        await self._register_modules()
        await self._setup_message_handlers()
        
        print("✅ SystemOrchestrator setup complete")
    
    async def _register_modules(self):
        """Register all modules with the orchestrator"""
        # Register signal generator
        self.orchestrator.register_module(
            name="signal_generator",
            module_type="signal_generation",
            version="1.0.0",
            capabilities=["technical_analysis", "pattern_recognition", "signal_generation"],
            integration_points=["execution_engine", "risk_management", "analytics"],
            health_checker=self.signal_generator.health_check,
            metrics_collector=self.signal_generator.get_metrics
        )
        
        # Register execution engine
        self.orchestrator.register_module(
            name="execution_engine",
            module_type="execution",
            version="1.0.0",
            capabilities=["order_execution", "market_impact_analysis", "execution_optimization"],
            integration_points=["signal_generation", "risk_management", "analytics"],
            health_checker=self.execution_engine.health_check,
            metrics_collector=self.execution_engine.get_metrics
        )
        
        # Register analytics engine
        self.orchestrator.register_module(
            name="analytics_engine",
            module_type="analytics",
            version="1.0.0",
            capabilities=["performance_analysis", "reporting", "data_visualization"],
            integration_points=["signal_generation", "execution_engine", "risk_management"],
            health_checker=self.analytics_engine.health_check,
            metrics_collector=self.analytics_engine.get_metrics
        )
        
        # Register risk manager
        self.orchestrator.register_module(
            name="risk_manager",
            module_type="risk_management",
            version="1.0.0",
            capabilities=["risk_assessment", "position_monitoring", "compliance_checking"],
            integration_points=["signal_generation", "execution_engine", "analytics"],
            health_checker=self.risk_manager.health_check,
            metrics_collector=self.risk_manager.get_metrics
        )
    
    async def _setup_message_handlers(self):
        """Setup message handlers for all modules"""
        # Signal generator message handler
        async def signal_handler(message):
            self.signal_messages.append(message)
            if message.message_type == MessageType.COMMAND and message.payload.get('action') == 'generate_signal':
                market_data = message.payload.get('market_data', {})
                signal = await self.signal_generator.generate_signal(market_data)
                
                # Send signal to risk manager for approval
                await self.orchestrator.send_message(
                    source_module="signal_generator",
                    target_module="risk_manager",
                    message_type=MessageType.COMMAND,
                    payload={
                        'action': 'check_risk',
                        'signal': signal,
                        'portfolio_state': message.payload.get('portfolio_state', {})
                    }
                )
        
        # Execution engine message handler
        async def execution_handler(message):
            self.execution_messages.append(message)
            if message.message_type == MessageType.COMMAND and message.payload.get('action') == 'execute_order':
                order = message.payload.get('order', {})
                execution_result = await self.execution_engine.execute_order(order)
                
                # Send execution result to analytics
                await self.orchestrator.send_message(
                    source_module="execution_engine",
                    target_module="analytics_engine",
                    message_type=MessageType.COMMAND,
                    payload={
                        'action': 'analyze_performance',
                        'execution_data': execution_result
                    }
                )
        
        # Analytics engine message handler
        async def analytics_handler(message):
            self.analytics_messages.append(message)
            if message.message_type == MessageType.COMMAND and message.payload.get('action') == 'analyze_performance':
                execution_data = message.payload.get('execution_data', {})
                analysis_result = await self.analytics_engine.analyze_performance(execution_data)
                
                # Broadcast analysis result
                await self.orchestrator.broadcast_message(
                    source_module="analytics_engine",
                    message_type=MessageType.EVENT,
                    payload={
                        'event_type': 'performance_analysis_complete',
                        'analysis_result': analysis_result
                    }
                )
        
        # Risk manager message handler
        async def risk_handler(message):
            self.risk_messages.append(message)
            if message.message_type == MessageType.COMMAND and message.payload.get('action') == 'check_risk':
                signal = message.payload.get('signal', {})
                portfolio_state = message.payload.get('portfolio_state', {})
                risk_result = await self.risk_manager.check_risk(signal, portfolio_state)
                
                if risk_result.get('approved', False):
                    # Send approved order to execution engine
                    await self.orchestrator.send_message(
                        source_module="risk_manager",
                        target_module="execution_engine",
                        message_type=MessageType.COMMAND,
                        payload={
                            'action': 'execute_order',
                            'order': {
                                'order_id': f"ORDER_{int(time.time())}",
                                'symbol': signal.get('symbol'),
                                'action': signal.get('action'),
                                'quantity': signal.get('quantity'),
                                'price': signal.get('price')
                            }
                        }
                    )
                else:
                    # Send rejection back to signal generator
                    await self.orchestrator.send_message(
                        source_module="risk_manager",
                        target_module="signal_generator",
                        message_type=MessageType.RESPONSE,
                        payload={
                            'status': 'rejected',
                            'reason': f"Risk level too high: {risk_result.get('risk_level')}",
                            'risk_result': risk_result
                        }
                    )
        
        # Register handlers
        self.orchestrator.add_message_handler("signal_generator", signal_handler)
        self.orchestrator.add_message_handler("execution_engine", execution_handler)
        self.orchestrator.add_message_handler("analytics_engine", analytics_handler)
        self.orchestrator.add_message_handler("risk_manager", risk_handler)
    
    async def example_1_signal_to_execution_workflow(self):
        """Example 1: Complete signal generation to execution workflow"""
        print("\n" + "="*60)
        print("📈 EXAMPLE 1: Signal Generation → Execution Workflow")
        print("="*60)
        
        # Simulate market data
        market_data = {
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 2000000,
            'timestamp': datetime.now().isoformat()
        }
        
        portfolio_state = {
            'total_exposure': 50000,
            'max_exposure': 100000,
            'cash_available': 75000
        }
        
        print(f"📊 Market Data: {market_data['symbol']} @ ${market_data['price']}")
        print(f"💼 Portfolio State: ${portfolio_state['total_exposure']} exposure, ${portfolio_state['cash_available']} cash")
        
        # Trigger signal generation
        await self.orchestrator.send_message(
            source_module="trading_system",
            target_module="signal_generator",
            message_type=MessageType.COMMAND,
            payload={
                'action': 'generate_signal',
                'market_data': market_data,
                'portfolio_state': portfolio_state
            }
        )
        
        # Wait for workflow completion
        await asyncio.sleep(2.0)
        
        # Display results
        print(f"\n📋 Workflow Results:")
        print(f"   Signal Messages: {len(self.signal_messages)}")
        print(f"   Execution Messages: {len(self.execution_messages)}")
        print(f"   Analytics Messages: {len(self.analytics_messages)}")
        print(f"   Risk Messages: {len(self.risk_messages)}")
        
        if self.execution_messages:
            print(f"   ✅ Order executed successfully")
        else:
            print(f"   ❌ Order was rejected by risk management")
    
    async def example_2_multi_signal_batch_processing(self):
        """Example 2: Batch processing of multiple signals"""
        print("\n" + "="*60)
        print("🔄 EXAMPLE 2: Multi-Signal Batch Processing")
        print("="*60)
        
        # Create multiple market scenarios
        market_scenarios = [
            {'symbol': 'AAPL', 'price': 155.0, 'volume': 2500000},  # Strong buy signal
            {'symbol': 'GOOGL', 'price': 2800.0, 'volume': 800000},  # Hold signal
            {'symbol': 'TSLA', 'price': 180.0, 'volume': 3000000},   # Strong buy signal
            {'symbol': 'MSFT', 'price': 320.0, 'volume': 1200000},   # Hold signal
        ]
        
        portfolio_state = {
            'total_exposure': 30000,
            'max_exposure': 100000,
            'cash_available': 100000
        }
        
        print(f"📊 Processing {len(market_scenarios)} market scenarios...")
        
        # Process all scenarios concurrently
        tasks = []
        for i, market_data in enumerate(market_scenarios):
            task = self.orchestrator.send_message(
                source_module=f"batch_processor_{i}",
                target_module="signal_generator",
                message_type=MessageType.COMMAND,
                payload={
                    'action': 'generate_signal',
                    'market_data': market_data,
                    'portfolio_state': portfolio_state
                }
            )
            tasks.append(task)
        
        # Wait for all messages to be sent
        await asyncio.gather(*tasks)
        
        # Wait for processing
        await asyncio.sleep(3.0)
        
        # Display results
        print(f"\n📋 Batch Processing Results:")
        print(f"   Total Signals Processed: {len(self.signal_messages)}")
        print(f"   Orders Executed: {len(self.execution_messages)}")
        print(f"   Performance Analyses: {len(self.analytics_messages)}")
        print(f"   Risk Checks: {len(self.risk_messages)}")
        
        # Show system health
        system_health = self.orchestrator.get_system_health()
        print(f"   System Health: {system_health['health_percentage']:.1f}% ({system_health['system_status']})")
    
    async def example_3_real_time_monitoring_and_analytics(self):
        """Example 3: Real-time monitoring and analytics"""
        print("\n" + "="*60)
        print("📊 EXAMPLE 3: Real-time Monitoring & Analytics")
        print("="*60)
        
        # Simulate real-time market data stream
        print("📡 Starting real-time market data stream...")
        
        for i in range(5):
            # Generate market data
            market_data = {
                'symbol': 'AAPL',
                'price': 150.0 + (i * 0.5),  # Simulate price movement
                'volume': 1500000 + (i * 100000),
                'timestamp': datetime.now().isoformat()
            }
            
            portfolio_state = {
                'total_exposure': 50000 + (i * 1000),
                'max_exposure': 100000,
                'cash_available': 75000 - (i * 1000)
            }
            
            print(f"   📊 Tick {i+1}: {market_data['symbol']} @ ${market_data['price']}")
            
            # Send signal request
            await self.orchestrator.send_message(
                source_module="real_time_trader",
                target_module="signal_generator",
                message_type=MessageType.COMMAND,
                payload={
                    'action': 'generate_signal',
                    'market_data': market_data,
                    'portfolio_state': portfolio_state
                }
            )
            
            # Wait between ticks
            await asyncio.sleep(0.5)
        
        # Wait for processing
        await asyncio.sleep(2.0)
        
        # Generate analytics report
        print(f"\n📈 Generating Analytics Report...")
        await self.orchestrator.send_message(
            source_module="reporting_system",
            target_module="analytics_engine",
            message_type=MessageType.COMMAND,
            payload={
                'action': 'generate_report',
                'time_period': 'session'
            }
        )
        
        await asyncio.sleep(1.0)
        
        # Display monitoring results
        print(f"\n📋 Real-time Monitoring Results:")
        print(f"   Market Ticks Processed: 5")
        print(f"   Signals Generated: {len(self.signal_messages)}")
        print(f"   Orders Executed: {len(self.execution_messages)}")
        print(f"   Risk Checks: {len(self.risk_messages)}")
        print(f"   Analytics Events: {len(self.analytics_messages)}")
        
        # Show module metrics
        for module_name in ["signal_generator", "execution_engine", "analytics_engine", "risk_manager"]:
            module_status = self.orchestrator.get_module_status(module_name)
            if module_status:
                print(f"   {module_name}: {module_status.health_score:.2f} health score")
    
    async def example_4_error_handling_and_recovery(self):
        """Example 4: Error handling and recovery scenarios"""
        print("\n" + "="*60)
        print("⚠️ EXAMPLE 4: Error Handling & Recovery")
        print("="*60)
        
        # Simulate various error scenarios
        error_scenarios = [
            {'symbol': 'INVALID', 'price': -100, 'volume': 0},  # Invalid data
            {'symbol': 'AAPL', 'price': 150.0, 'volume': 999999999},  # Excessive volume
            {'symbol': 'AAPL', 'price': 150.0, 'volume': 1000000},  # Normal data
        ]
        
        portfolio_state = {
            'total_exposure': 50000,
            'max_exposure': 100000,
            'cash_available': 75000
        }
        
        print("🔄 Testing error handling scenarios...")
        
        for i, market_data in enumerate(error_scenarios):
            print(f"   📊 Scenario {i+1}: {market_data['symbol']} @ ${market_data['price']}")
            
            await self.orchestrator.send_message(
                source_module="error_test_system",
                target_module="signal_generator",
                message_type=MessageType.COMMAND,
                payload={
                    'action': 'generate_signal',
                    'market_data': market_data,
                    'portfolio_state': portfolio_state
                }
            )
            
            await asyncio.sleep(0.5)
        
        # Wait for processing
        await asyncio.sleep(2.0)
        
        # Display error handling results
        print(f"\n📋 Error Handling Results:")
        system_health = self.orchestrator.get_system_health()
        print(f"   System Errors: {system_health['performance_metrics']['total_errors']}")
        print(f"   System Health: {system_health['health_percentage']:.1f}%")
        print(f"   System Status: {system_health['system_status']}")
        
        # Show individual module error counts
        for module_name in ["signal_generator", "execution_engine", "analytics_engine", "risk_manager"]:
            module_status = self.orchestrator.get_module_status(module_name)
            if module_status:
                print(f"   {module_name} errors: {module_status.error_count}")
    
    async def example_5_performance_benchmarking(self):
        """Example 5: Performance benchmarking and optimization"""
        print("\n" + "="*60)
        print("⚡ EXAMPLE 5: Performance Benchmarking")
        print("="*60)
        
        # Benchmark message processing performance
        message_count = 100
        print(f"📊 Benchmarking {message_count} messages...")
        
        start_time = time.time()
        
        # Send high volume of messages
        tasks = []
        for i in range(message_count):
            market_data = {
                'symbol': 'AAPL',
                'price': 150.0 + (i % 10),
                'volume': 1000000 + (i * 1000),
                'timestamp': datetime.now().isoformat()
            }
            
            task = self.orchestrator.send_message(
                source_module=f"benchmark_{i}",
                target_module="signal_generator",
                message_type=MessageType.COMMAND,
                payload={
                    'action': 'generate_signal',
                    'market_data': market_data,
                    'portfolio_state': {'total_exposure': 50000, 'max_exposure': 100000, 'cash_available': 75000}
                }
            )
            tasks.append(task)
        
        # Wait for all messages to be sent
        await asyncio.gather(*tasks)
        
        # Wait for processing
        await asyncio.sleep(3.0)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Display performance results
        print(f"\n📋 Performance Benchmark Results:")
        print(f"   Messages Sent: {message_count}")
        print(f"   Total Processing Time: {processing_time:.2f} seconds")
        print(f"   Messages Per Second: {message_count / processing_time:.1f}")
        print(f"   Average Time Per Message: {(processing_time / message_count) * 1000:.1f} ms")
        
        # Show system performance metrics
        system_health = self.orchestrator.get_system_health()
        print(f"   System Messages Processed: {system_health['performance_metrics']['total_messages']}")
        print(f"   System Errors: {system_health['performance_metrics']['total_errors']}")
        print(f"   System Uptime: {system_health['uptime']:.1f} seconds")
    
    async def run_all_examples(self):
        """Run all integration examples"""
        print("🚀 Starting Module Integration Examples...")
        print("="*60)
        
        # Setup orchestrator
        await self.setup_orchestrator()
        
        # Run examples
        await self.example_1_signal_to_execution_workflow()
        await self.example_2_multi_signal_batch_processing()
        await self.example_3_real_time_monitoring_and_analytics()
        await self.example_4_error_handling_and_recovery()
        await self.example_5_performance_benchmarking()
        
        # Final system summary
        print("\n" + "="*60)
        print("🎯 FINAL SYSTEM SUMMARY")
        print("="*60)
        
        system_health = self.orchestrator.get_system_health()
        print(f"📊 System Health: {system_health['health_percentage']:.1f}% ({system_health['system_status']})")
        print(f"🔧 Total Modules: {system_health['total_modules']}")
        print(f"✅ Healthy Modules: {system_health['healthy_modules']}")
        print(f"📨 Total Messages: {system_health['performance_metrics']['total_messages']}")
        print(f"❌ Total Errors: {system_health['performance_metrics']['total_errors']}")
        print(f"⏱️ System Uptime: {system_health['uptime']:.1f} seconds")
        
        # Integration points summary
        integration_points = self.orchestrator.get_integration_points()
        print(f"\n🔗 Integration Points:")
        for point, modules in integration_points.items():
            print(f"   {point}: {len(modules)} modules")
        
        print("\n🎉 All examples completed successfully!")
        print("="*60)
        
        # Cleanup
        await self.orchestrator.stop()

async def main():
    """Main function to run all examples"""
    examples = ModuleIntegrationExamples()
    await examples.run_all_examples()

if __name__ == "__main__":
    asyncio.run(main()) 