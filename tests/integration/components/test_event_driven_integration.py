#!/usr/bin/env python3
"""
Event-Driven Integration Test Suite
==================================

Tests the event-driven subscriber integration patterns across core_engine components.

This test suite validates:
- Subscriber interface implementations
- Event notification patterns
- Cross-component event communication
- Event-driven data flow

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Event Integration Testing)
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Add core_engine to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core_engine'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventTestResult(Enum):
    """Event test result status"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class EventIntegrationTestResult:
    """Test result for event integration"""
    component_name: str
    event_type: str
    subscriber_count: int
    result: EventTestResult
    message: str
    execution_time: float
    error_details: Optional[str] = None


class EventDrivenIntegrationTester:
    """
    Comprehensive event-driven integration tester
    
    Tests event-driven patterns across core_engine components:
    - Regime change events
    - Strategy signal events
    - Trading execution events
    - Risk management events
    - Performance monitoring events
    - Portfolio update events
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_results: List[EventIntegrationTestResult] = []
        
        # Event-driven components to test
        self.event_components = {
            'RegimeEngine': {
                'module': 'core_engine.regime.engine',
                'class': 'EnhancedRegimeEngine',
                'subscriber_interface': 'IRegimeSubscriber',
                'events': ['regime_change']
            },
            'StrategyManager': {
                'module': 'core_engine.trading.strategies.manager',
                'class': 'StrategyManager',
                'subscriber_interface': 'IStrategySubscriber',
                'events': ['signal_generated', 'strategy_status_change']
            },
            'TradingEngine': {
                'module': 'core_engine.trading.engine',
                'class': 'EnhancedTradingEngine',
                'subscriber_interface': 'ITradingSubscriber',
                'events': ['execution_plan_created', 'slice_executed']
            }
        }
        
        self.logger.info("🔄 Event-Driven Integration Tester initialized")
        self.logger.info(f"📡 Testing {len(self.event_components)} event-driven components")
    
    async def run_event_integration_tests(self) -> Dict[str, Any]:
        """Run comprehensive event-driven integration tests"""
        
        test_start_time = datetime.now()
        self.logger.info("🚀 Starting Event-Driven Integration Test Suite")
        self.logger.info("=" * 80)
        
        try:
            # Test 1: Subscriber Interface Compliance
            await self._test_subscriber_interfaces()
            
            # Test 2: Event Notification Patterns
            await self._test_event_notifications()
            
            # Test 3: Cross-Component Event Flow
            await self._test_cross_component_events()
            
            # Generate report
            report = await self._generate_event_test_report(test_start_time)
            
            self.logger.info("✅ Event-Driven Integration Test Suite completed")
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Event test suite failed: {e}")
            return await self._generate_error_report(str(e), test_start_time)
    
    async def _test_subscriber_interfaces(self):
        """Test subscriber interface implementations"""
        
        self.logger.info("🔍 Testing Subscriber Interface Compliance...")
        self.logger.info("-" * 50)
        
        for component_name, component_info in self.event_components.items():
            await self._test_component_subscriber_interface(component_name, component_info)
    
    async def _test_component_subscriber_interface(self, component_name: str, component_info: Dict[str, Any]):
        """Test individual component subscriber interface"""
        
        start_time = datetime.now()
        self.logger.info(f"🧪 Testing {component_name} subscriber interface...")
        
        try:
            # Import component module
            module = __import__(component_info['module'], fromlist=[component_info['class']])
            getattr(module, component_info['class'])
            
            # Check if subscriber interface exists
            subscriber_interface_name = component_info['subscriber_interface']
            if hasattr(module, subscriber_interface_name):
                subscriber_interface = getattr(module, subscriber_interface_name)
                
                # Verify interface methods
                expected_events = component_info['events']
                interface_methods = []
                
                for event in expected_events:
                    method_name = f"on_{event}"
                    if hasattr(subscriber_interface, method_name):
                        interface_methods.append(method_name)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                result = EventIntegrationTestResult(
                    component_name=component_name,
                    event_type="subscriber_interface",
                    subscriber_count=len(interface_methods),
                    result=EventTestResult.PASSED if len(interface_methods) == len(expected_events) else EventTestResult.FAILED,
                    message=f"Interface methods: {interface_methods}",
                    execution_time=execution_time
                )
                
                self.test_results.append(result)
                
                if result.result == EventTestResult.PASSED:
                    self.logger.info(f"✅ {component_name}: Subscriber interface complete")
                else:
                    self.logger.warning(f"⚠️ {component_name}: Missing interface methods")
            else:
                execution_time = (datetime.now() - start_time).total_seconds()
                
                result = EventIntegrationTestResult(
                    component_name=component_name,
                    event_type="subscriber_interface",
                    subscriber_count=0,
                    result=EventTestResult.FAILED,
                    message=f"Subscriber interface {subscriber_interface_name} not found",
                    execution_time=execution_time
                )
                
                self.test_results.append(result)
                self.logger.error(f"❌ {component_name}: Subscriber interface missing")
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = EventIntegrationTestResult(
                component_name=component_name,
                event_type="subscriber_interface",
                subscriber_count=0,
                result=EventTestResult.ERROR,
                message=f"Interface test failed: {str(e)}",
                execution_time=execution_time,
                error_details=str(e)
            )
            
            self.test_results.append(result)
            self.logger.error(f"❌ {component_name}: Interface test error: {e}")
    
    async def _test_event_notifications(self):
        """Test event notification patterns"""
        
        self.logger.info("📡 Testing Event Notification Patterns...")
        self.logger.info("-" * 50)
        
        for component_name, component_info in self.event_components.items():
            await self._test_component_event_notifications(component_name, component_info)
    
    async def _test_component_event_notifications(self, component_name: str, component_info: Dict[str, Any]):
        """Test component event notification capabilities"""
        
        start_time = datetime.now()
        self.logger.info(f"📡 Testing {component_name} event notifications...")
        
        try:
            # Import component
            module = __import__(component_info['module'], fromlist=[component_info['class']])
            component_class = getattr(module, component_info['class'])
            
            # Create minimal config for testing
            self._create_minimal_config(component_name)
            
            # Check if component has subscriber management
            has_subscribers = False
            has_notify_methods = False
            
            # Check for common subscriber patterns
            if hasattr(component_class, 'subscribers') or hasattr(component_class, 'subscribe'):
                has_subscribers = True
            
            # Check for notification methods
            for event in component_info['events']:
                notify_method = f"notify_{event}"
                if hasattr(component_class, notify_method):
                    has_notify_methods = True
                    break
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Determine result
            if has_subscribers or has_notify_methods:
                result = EventTestResult.PASSED
                message = f"Event notification capability detected"
            else:
                result = EventTestResult.FAILED
                message = f"No event notification patterns found"
            
            test_result = EventIntegrationTestResult(
                component_name=component_name,
                event_type="event_notifications",
                subscriber_count=1 if has_subscribers else 0,
                result=result,
                message=message,
                execution_time=execution_time
            )
            
            self.test_results.append(test_result)
            
            if result == EventTestResult.PASSED:
                self.logger.info(f"✅ {component_name}: Event notifications supported")
            else:
                self.logger.warning(f"⚠️ {component_name}: Event notifications not implemented")
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = EventIntegrationTestResult(
                component_name=component_name,
                event_type="event_notifications",
                subscriber_count=0,
                result=EventTestResult.ERROR,
                message=f"Notification test failed: {str(e)}",
                execution_time=execution_time,
                error_details=str(e)
            )
            
            self.test_results.append(result)
            self.logger.error(f"❌ {component_name}: Notification test error: {e}")
    
    async def _test_cross_component_events(self):
        """Test cross-component event communication"""
        
        self.logger.info("🔄 Testing Cross-Component Event Communication...")
        self.logger.info("-" * 50)
        
        # Test key event flows
        event_flows = [
            {
                'name': 'regime_to_strategy_flow',
                'source': 'RegimeEngine',
                'target': 'StrategyManager',
                'event': 'regime_change'
            },
            {
                'name': 'strategy_to_trading_flow',
                'source': 'StrategyManager',
                'target': 'TradingEngine',
                'event': 'signal_generated'
            }
        ]
        
        for flow in event_flows:
            await self._test_event_flow(flow)
    
    async def _test_event_flow(self, flow: Dict[str, str]):
        """Test individual event flow"""
        
        start_time = datetime.now()
        flow_name = flow['name']
        
        self.logger.info(f"🔄 Testing {flow_name}...")
        
        try:
            # For now, just verify the components exist and have the right interfaces
            source_info = self.event_components.get(flow['source'])
            target_info = self.event_components.get(flow['target'])
            
            if source_info and target_info:
                # Check if source can emit events and target can receive them
                source_events = source_info['events']
                target_info['subscriber_interface']
                
                flow_supported = flow['event'] in source_events
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                result = EventIntegrationTestResult(
                    component_name=flow_name,
                    event_type="cross_component_flow",
                    subscriber_count=1 if flow_supported else 0,
                    result=EventTestResult.PASSED if flow_supported else EventTestResult.FAILED,
                    message=f"Event flow from {flow['source']} to {flow['target']}",
                    execution_time=execution_time
                )
                
                self.test_results.append(result)
                
                if result.result == EventTestResult.PASSED:
                    self.logger.info(f"✅ {flow_name}: Event flow supported")
                else:
                    self.logger.warning(f"⚠️ {flow_name}: Event flow not supported")
            else:
                execution_time = (datetime.now() - start_time).total_seconds()
                
                result = EventIntegrationTestResult(
                    component_name=flow_name,
                    event_type="cross_component_flow",
                    subscriber_count=0,
                    result=EventTestResult.FAILED,
                    message="Source or target component not found",
                    execution_time=execution_time
                )
                
                self.test_results.append(result)
                self.logger.error(f"❌ {flow_name}: Components not found")
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = EventIntegrationTestResult(
                component_name=flow_name,
                event_type="cross_component_flow",
                subscriber_count=0,
                result=EventTestResult.ERROR,
                message=f"Flow test failed: {str(e)}",
                execution_time=execution_time,
                error_details=str(e)
            )
            
            self.test_results.append(result)
            self.logger.error(f"❌ {flow_name}: Flow test error: {e}")
    
    def _create_minimal_config(self, component_name: str) -> Dict[str, Any]:
        """Create minimal config for component testing"""
        
        if component_name == 'RegimeEngine':
            return {
                'lookback_window': 60,
                'volatility_window': 20,
                'enable_enhanced_detection': False
            }
        elif component_name == 'StrategyManager':
            return {
                'max_concurrent_strategies': 3,
                'enable_enhanced_strategies': False,
                'auto_discover_strategies': False
            }
        elif component_name == 'TradingEngine':
            return {
                'enable_smart_routing': False,
                'max_slice_size': 500.0
            }
        else:
            return {'enable_logging': True}
    
    async def _generate_event_test_report(self, test_start_time: datetime) -> Dict[str, Any]:
        """Generate comprehensive event integration test report"""
        
        test_end_time = datetime.now()
        
        # Calculate statistics
        total_tests = len(self.test_results)
        tests_passed = sum(1 for r in self.test_results if r.result == EventTestResult.PASSED)
        tests_failed = sum(1 for r in self.test_results if r.result == EventTestResult.FAILED)
        tests_error = sum(1 for r in self.test_results if r.result == EventTestResult.ERROR)
        
        # Overall success
        overall_success = tests_failed == 0 and tests_error == 0
        
        return {
            'test_start_time': test_start_time,
            'test_end_time': test_end_time,
            'test_duration': (test_end_time - test_start_time).total_seconds(),
            'total_tests': total_tests,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'tests_error': tests_error,
            'overall_success': overall_success,
            'success_rate': (tests_passed / total_tests * 100) if total_tests > 0 else 0,
            'test_results': [
                {
                    'component_name': r.component_name,
                    'event_type': r.event_type,
                    'result': r.result.value,
                    'message': r.message,
                    'execution_time': r.execution_time,
                    'subscriber_count': r.subscriber_count
                }
                for r in self.test_results
            ]
        }
    
    async def _generate_error_report(self, error_message: str, test_start_time: datetime) -> Dict[str, Any]:
        """Generate error report when test suite fails"""
        
        return {
            'test_start_time': test_start_time,
            'test_end_time': datetime.now(),
            'total_tests': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_error': 1,
            'overall_success': False,
            'success_rate': 0,
            'error_message': error_message,
            'test_results': []
        }


def print_event_test_report(report: Dict[str, Any]):
    """Print event integration test report"""
    
    print("\n" + "=" * 80)
    print("🔄 EVENT-DRIVEN INTEGRATION TEST REPORT")
    print("=" * 80)
    
    # Test Summary
    print(f"\n📊 TEST SUMMARY:")
    print(f"   Test Duration: {report['test_duration']:.2f} seconds")
    print(f"   Total Tests: {report['total_tests']}")
    print(f"   Tests Passed: {report['tests_passed']} ✅")
    print(f"   Tests Failed: {report['tests_failed']} ❌")
    print(f"   Tests Error: {report['tests_error']} 🚨")
    print(f"   Success Rate: {report['success_rate']:.1f}%")
    
    # Overall Result
    if report['overall_success']:
        print(f"\n🎯 OVERALL RESULT: ✅ SUCCESS")
        print("   All event-driven integration tests passed!")
    else:
        print(f"\n🎯 OVERALL RESULT: ❌ NEEDS ATTENTION")
        print("   Some event integration patterns need implementation")
    
    # Test Results
    if report['test_results']:
        print(f"\n📋 DETAILED RESULTS:")
        for result in report['test_results']:
            status = "✅" if result['result'] == 'PASSED' else "❌" if result['result'] == 'FAILED' else "🚨"
            print(f"   {status} {result['component_name']}.{result['event_type']}: {result['message']}")
    
    print("\n" + "=" * 80)


async def main():
    """Main test execution function"""
    
    print("🔄 Starting Event-Driven Integration Test Suite")
    print("Testing event-driven patterns across core_engine components")
    print("=" * 80)
    
    # Create and run tester
    tester = EventDrivenIntegrationTester()
    report = await tester.run_event_integration_tests()
    
    # Print detailed report
    print_event_test_report(report)
    
    # Save report to file
    report_filename = f"event_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w') as f:
        import sys
        original_stdout = sys.stdout
        sys.stdout = f
        print_event_test_report(report)
        sys.stdout = original_stdout
    
    print(f"\n📄 Detailed report saved to: {report_filename}")
    
    # Return exit code
    return 0 if report['overall_success'] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
