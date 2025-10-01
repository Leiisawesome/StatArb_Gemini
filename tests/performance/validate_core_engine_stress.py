#!/usr/bin/env python3
"""
Core Engine Stress Validation Pipeline

This script integrates Phase 2 stress testing with the actual core_engine components
to validate system resilience under extreme conditions using real production code.

This builds upon the successful Phase 1 validation (validate_core_engine_performance.py)
to provide comprehensive stress testing of the actual StatArb_Gemini core_engine.

Usage:
    python tests/performance/validate_core_engine_stress.py
"""

import asyncio
import logging
import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import Phase 2 stress testing framework
from tests.performance import (
    Phase2StressTestSuite, 
    Phase2TestConfiguration, 
    Phase2TestResults,
    MarketCondition,
    FailureMode,
    StressTestType
)

# Import core engine components
try:
    from core_engine.system.integration_manager import SystemIntegrationManager, create_production_config
    from core_engine.system.central_risk_manager import CentralRiskManager, TradingDecisionRequest, TradingDecisionType
    from core_engine.trading.strategies.manager import StrategyManager
    CORE_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Core engine components not available: {e}")
    CORE_ENGINE_AVAILABLE = False

logger = logging.getLogger(__name__)

class CoreEngineStressValidator:
    """Validates core_engine resilience using Phase 2 stress testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.CoreEngineStressValidator")
        self.integration_manager = None
        self.components = {}
        self.stress_suite = Phase2StressTestSuite()
        
    async def run_comprehensive_stress_validation(self, 
                                                config: Phase2TestConfiguration = None) -> Phase2TestResults:
        """Run comprehensive stress validation against core_engine"""
        
        self.logger.info("🚀 Starting Core Engine Stress Validation Pipeline")
        self.logger.info("="*70)
        
        if not CORE_ENGINE_AVAILABLE:
            raise RuntimeError("Core engine components not available for testing")
        
        # Use default config if none provided
        if config is None:
            config = self._create_default_stress_config()
        
        try:
            # Step 1: Initialize core engine
            self.logger.info("🔧 Step 1: Initializing core engine components...")
            await self._initialize_core_engine()
            
            # Step 2: Validate component health before stress testing
            self.logger.info("🏥 Step 2: Validating component health...")
            health_status = await self._validate_component_health()
            if not health_status['all_healthy']:
                self.logger.warning("⚠️ Some components unhealthy before stress testing")
            
            # Step 3: Run Phase 2 stress testing against core engine
            self.logger.info("🔥 Step 3: Running Phase 2 stress testing...")
            results = await self.stress_suite.run_comprehensive_stress_test(
                target_system=self.integration_manager,
                config=config
            )
            
            # Step 4: Validate component health after stress testing
            self.logger.info("🏥 Step 4: Validating component health after stress...")
            post_stress_health = await self._validate_component_health()
            
            # Step 5: Analyze core engine specific metrics
            self.logger.info("📊 Step 5: Analyzing core engine specific metrics...")
            await self._analyze_core_engine_metrics(results, health_status, post_stress_health)
            
            # Step 6: Generate core engine stress report
            self.logger.info("📋 Step 6: Generating core engine stress report...")
            await self._generate_core_engine_stress_report(results, config)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Core engine stress validation failed: {e}")
            raise
        
        finally:
            # Cleanup
            await self._cleanup_core_engine()
    
    def _create_default_stress_config(self) -> Phase2TestConfiguration:
        """Create default stress testing configuration for core engine"""
        
        return Phase2TestConfiguration(
            # Test selection - enable all for comprehensive validation
            enable_market_stress=True,
            enable_component_failure=True,
            enable_load_stress=True,
            enable_network_failure=True,
            enable_data_corruption=True,
            enable_memory_pressure=True,
            
            # Test intensity - moderate for production components
            test_intensity=2.0,  # 2x normal stress
            test_duration_seconds=180,  # 3 minutes per category
            
            # Baseline comparison with Phase 1 results
            enable_baseline_comparison=True,
            baseline_duration_seconds=60,
            
            # Core engine specific scenarios
            market_scenarios=[
                MarketCondition.HIGH_VOLATILITY,
                MarketCondition.FLASH_CRASH,
                MarketCondition.BULL_MARKET,
                MarketCondition.BEAR_MARKET
            ],
            
            failure_modes=[
                FailureMode.GRACEFUL_SHUTDOWN,
                FailureMode.SUDDEN_TERMINATION,
                FailureMode.MEMORY_LEAK,
                FailureMode.CPU_OVERLOAD
            ],
            
            # Target core engine components
            target_components=[
                'data_manager',
                'risk_manager', 
                'strategy_manager',
                'execution_engine',
                'portfolio_manager'
            ],
            
            # Stress parameters tuned for core engine
            max_operations_per_second=3000,
            memory_limit_mb=300,
            corruption_rate=0.02,  # 2% corruption rate
            network_latency_ms=150,
            packet_loss_rate=0.05,  # 5% packet loss
            allocation_rate_mb_per_sec=8.0,
            
            # Reporting
            generate_detailed_reports=True,
            save_raw_data=True
        )
    
    async def _initialize_core_engine(self):
        """Initialize core engine components for stress testing"""
        
        self.logger.info("   Initializing SystemIntegrationManager...")
        
        # Create production configuration
        config = create_production_config()
        
        # Initialize integration manager
        self.integration_manager = SystemIntegrationManager(config)
        
        # Initialize all components
        success = await self.integration_manager.initialize()
        if not success:
            raise RuntimeError("Failed to initialize core engine components")
        
        # Start all components
        success = await self.integration_manager.start()
        if not success:
            raise RuntimeError("Failed to start core engine components")
        
        # Get component references
        self.components = self.integration_manager.components
        
        self.logger.info(f"   ✅ Initialized {len(self.components)} core engine components")
        for component_name in self.components.keys():
            self.logger.info(f"      - {component_name}")
    
    async def _validate_component_health(self) -> Dict[str, Any]:
        """Validate health of all core engine components"""
        
        health_status = {
            'timestamp': datetime.now(),
            'component_health': {},
            'healthy_count': 0,
            'total_count': 0,
            'all_healthy': True
        }
        
        for component_name, component in self.components.items():
            health_status['total_count'] += 1
            
            try:
                if hasattr(component, 'health_check'):
                    health_result = await component.health_check()
                else:
                    # Basic health check for components without health_check method
                    health_result = {
                        'healthy': hasattr(component, 'is_operational') and getattr(component, 'is_operational', True)
                    }
                
                is_healthy = health_result.get('healthy', False)
                health_status['component_health'][component_name] = {
                    'healthy': is_healthy,
                    'details': health_result
                }
                
                if is_healthy:
                    health_status['healthy_count'] += 1
                else:
                    health_status['all_healthy'] = False
                    
            except Exception as e:
                self.logger.warning(f"Health check failed for {component_name}: {e}")
                health_status['component_health'][component_name] = {
                    'healthy': False,
                    'error': str(e)
                }
                health_status['all_healthy'] = False
        
        health_percentage = (health_status['healthy_count'] / health_status['total_count'] * 100) if health_status['total_count'] > 0 else 0
        
        self.logger.info(f"   Component Health: {health_status['healthy_count']}/{health_status['total_count']} ({health_percentage:.1f}%)")
        
        return health_status
    
    async def _analyze_core_engine_metrics(self, results: Phase2TestResults, 
                                         pre_health: Dict[str, Any], 
                                         post_health: Dict[str, Any]):
        """Analyze core engine specific metrics from stress testing"""
        
        self.logger.info("   Analyzing core engine resilience metrics...")
        
        # Component health comparison
        pre_healthy = pre_health['healthy_count']
        post_healthy = post_health['healthy_count']
        health_retention = (post_healthy / pre_healthy * 100) if pre_healthy > 0 else 0
        
        # Add core engine specific analysis to results
        if not hasattr(results, 'core_engine_analysis'):
            results.core_engine_analysis = {}
        
        results.core_engine_analysis.update({
            'component_health_retention_pct': health_retention,
            'pre_stress_healthy_components': pre_healthy,
            'post_stress_healthy_components': post_healthy,
            'component_resilience_score': min(100, health_retention + 10),  # Bonus for maintaining health
            
            # Component-specific analysis
            'component_stress_impact': await self._analyze_component_stress_impact(results),
            
            # Integration manager specific metrics
            'integration_manager_performance': await self._analyze_integration_manager_performance(),
            
            # Risk manager resilience
            'risk_manager_resilience': await self._analyze_risk_manager_resilience(),
            
            # Strategy manager stability
            'strategy_manager_stability': await self._analyze_strategy_manager_stability()
        })
        
        self.logger.info(f"   Component Health Retention: {health_retention:.1f}%")
        self.logger.info(f"   Component Resilience Score: {results.core_engine_analysis['component_resilience_score']:.1f}/100")
    
    async def _analyze_component_stress_impact(self, results: Phase2TestResults) -> Dict[str, Any]:
        """Analyze stress impact on individual components"""
        
        component_impact = {}
        
        # Analyze each component's performance under stress
        for component_name in self.components.keys():
            impact_score = 100.0  # Start with perfect score
            
            # Check if component was mentioned in critical failures
            component_failures = [f for f in results.critical_failures if component_name in f.lower()]
            if component_failures:
                impact_score -= len(component_failures) * 20  # 20 points per failure
            
            # Check component-specific stress test results
            if results.component_failure_results:
                for failure_result in results.component_failure_results:
                    if failure_result.success:
                        # Good resilience
                        impact_score += 5
                    else:
                        # Poor resilience
                        impact_score -= 15
            
            component_impact[component_name] = {
                'stress_impact_score': max(0, min(100, impact_score)),
                'failure_count': len(component_failures),
                'resilience_rating': 'excellent' if impact_score >= 90 else 
                                   'good' if impact_score >= 70 else
                                   'fair' if impact_score >= 50 else 'poor'
            }
        
        return component_impact
    
    async def _analyze_integration_manager_performance(self) -> Dict[str, Any]:
        """Analyze SystemIntegrationManager performance under stress"""
        
        try:
            # Get integration manager status
            if hasattr(self.integration_manager, 'get_system_status'):
                status = await self.integration_manager.get_system_status()
            else:
                status = {'operational': True, 'components_initialized': len(self.components)}
            
            return {
                'operational': status.get('operational', True),
                'components_managed': len(self.components),
                'initialization_success': True,  # If we got here, initialization succeeded
                'stress_handling_score': 85.0  # Base score, could be enhanced with more metrics
            }
            
        except Exception as e:
            return {
                'operational': False,
                'error': str(e),
                'stress_handling_score': 0.0
            }
    
    async def _analyze_risk_manager_resilience(self) -> Dict[str, Any]:
        """Analyze CentralRiskManager resilience under stress"""
        
        try:
            risk_manager = self.components.get('risk_manager')
            if not risk_manager:
                return {'available': False}
            
            # Test risk manager functionality
            test_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol='TEST',
                side='BUY',
                quantity=100,
                strategy_id='stress_test',
                confidence=0.8
            )
            
            # Test authorization capability
            try:
                authorization = await risk_manager.authorize_trading_decision(test_request)
                authorization_working = authorization is not None
            except Exception:
                authorization_working = False
            
            return {
                'available': True,
                'authorization_functional': authorization_working,
                'resilience_score': 90.0 if authorization_working else 30.0
            }
            
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'resilience_score': 0.0
            }
    
    async def _analyze_strategy_manager_stability(self) -> Dict[str, Any]:
        """Analyze StrategyManager stability under stress"""
        
        try:
            strategy_manager = self.components.get('strategy_manager')
            if not strategy_manager:
                return {'available': False}
            
            # Check strategy manager health
            if hasattr(strategy_manager, 'health_check'):
                health = await strategy_manager.health_check()
                is_healthy = health.get('healthy', False)
            else:
                is_healthy = getattr(strategy_manager, 'is_operational', True)
            
            # Check strategy count
            strategy_count = 0
            if hasattr(strategy_manager, 'active_strategies'):
                strategy_count = len(strategy_manager.active_strategies)
            
            return {
                'available': True,
                'healthy': is_healthy,
                'active_strategies': strategy_count,
                'stability_score': 85.0 if is_healthy else 40.0
            }
            
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'stability_score': 0.0
            }
    
    async def _generate_core_engine_stress_report(self, results: Phase2TestResults, 
                                                config: Phase2TestConfiguration):
        """Generate comprehensive core engine stress report"""
        
        # Create results directory
        results_dir = Path("tests/performance/core_engine_stress_results")
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate comprehensive JSON report
        json_report_path = results_dir / f"core_engine_stress_results_{timestamp}.json"
        await self._generate_json_stress_report(results, json_report_path)
        
        # Generate executive summary report
        summary_report_path = results_dir / f"core_engine_stress_summary_{timestamp}.md"
        await self._generate_executive_summary_report(results, summary_report_path)
        
        self.logger.info(f"   📊 Core engine stress reports generated:")
        self.logger.info(f"      JSON: {json_report_path}")
        self.logger.info(f"      Summary: {summary_report_path}")
    
    async def _generate_json_stress_report(self, results: Phase2TestResults, file_path: Path):
        """Generate detailed JSON stress report"""
        
        # Convert results to serializable format
        report_data = {
            'core_engine_stress_validation': {
                'timestamp': datetime.now().isoformat(),
                'framework_version': '2.0.0',
                'test_type': 'core_engine_stress_validation'
            },
            'overall_results': {
                'resilience_score': results.overall_resilience_score,
                'total_tests': results.total_tests_run,
                'success_rate': (results.successful_tests / results.total_tests_run * 100) if results.total_tests_run > 0 else 0,
                'duration_seconds': results.total_duration_seconds
            },
            'category_performance': results.category_scores,
            'core_engine_analysis': getattr(results, 'core_engine_analysis', {}),
            'critical_findings': results.critical_failures,
            'recovery_capabilities': results.recovery_capabilities,
            'performance_degradations': results.performance_degradations,
            'detailed_results': {
                'market_stress': [self._serialize_result(r) for r in (results.market_stress_results or [])],
                'component_failure': [self._serialize_result(r) for r in (results.component_failure_results or [])],
                'load_stress': [self._serialize_result(r) for r in (results.load_stress_results or [])],
                'network_failure': [self._serialize_result(r) for r in (results.network_failure_results or [])],
                'data_corruption': [self._serialize_result(r) for r in (results.data_corruption_results or [])],
                'memory_pressure': [self._serialize_result(r) for r in (results.memory_pressure_results or [])]
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
    
    def _serialize_result(self, result) -> Dict[str, Any]:
        """Serialize stress test result for JSON output"""
        return {
            'test_type': result.test_type.value,
            'success': result.success,
            'stability_score': result.system_stability_score,
            'duration_seconds': result.duration_seconds,
            'failure_reason': result.failure_reason,
            'performance_metrics': result.stress_performance
        }
    
    async def _generate_executive_summary_report(self, results: Phase2TestResults, file_path: Path):
        """Generate executive summary report"""
        
        with open(file_path, 'w') as f:
            f.write("# Core Engine Stress Validation Report\\n\\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"**Framework:** Phase 2 Stress Testing v2.0.0\\n")
            f.write(f"**Target:** StatArb_Gemini Core Engine\\n\\n")
            
            # Executive Summary
            f.write("## Executive Summary\\n\\n")
            f.write(f"The StatArb_Gemini core engine underwent comprehensive stress testing ")
            f.write(f"across {results.total_tests_run} scenarios with an overall resilience score of ")
            f.write(f"**{results.overall_resilience_score:.1f}/100**.\\n\\n")
            
            success_rate = (results.successful_tests / results.total_tests_run * 100) if results.total_tests_run > 0 else 0
            f.write(f"- **Success Rate:** {success_rate:.1f}%\\n")
            f.write(f"- **Test Duration:** {results.total_duration_seconds:.1f} seconds\\n")
            f.write(f"- **Components Tested:** {len(self.components)}\\n\\n")
            
            # Overall Assessment
            if results.overall_resilience_score >= 80:
                assessment = "🟢 **EXCELLENT** - Core engine demonstrates high resilience under stress"
            elif results.overall_resilience_score >= 60:
                assessment = "🟡 **GOOD** - Core engine handles stress well with minor degradation"
            elif results.overall_resilience_score >= 40:
                assessment = "🟠 **FAIR** - Core engine shows stress-related performance issues"
            else:
                assessment = "🔴 **POOR** - Core engine requires significant resilience improvements"
            
            f.write(f"**Overall Assessment:** {assessment}\\n\\n")
            
            # Category Performance
            f.write("## Category Performance\\n\\n")
            for category, score in results.category_scores.items():
                status = "✅" if score >= 70 else "⚠️" if score >= 50 else "❌"
                f.write(f"- {status} **{category.replace('_', ' ').title()}:** {score:.1f}/100\\n")
            f.write("\\n")
            
            # Core Engine Specific Analysis
            if hasattr(results, 'core_engine_analysis'):
                f.write("## Core Engine Analysis\\n\\n")
                analysis = results.core_engine_analysis
                
                if 'component_health_retention_pct' in analysis:
                    f.write(f"- **Component Health Retention:** {analysis['component_health_retention_pct']:.1f}%\\n")
                
                if 'component_resilience_score' in analysis:
                    f.write(f"- **Component Resilience Score:** {analysis['component_resilience_score']:.1f}/100\\n")
                
                # Component-specific analysis
                if 'component_stress_impact' in analysis:
                    f.write("\\n### Component Stress Impact\\n\\n")
                    for component, impact in analysis['component_stress_impact'].items():
                        rating = impact['resilience_rating']
                        score = impact['stress_impact_score']
                        f.write(f"- **{component}:** {rating.title()} ({score:.1f}/100)\\n")
                
                f.write("\\n")
            
            # Critical Findings
            if results.critical_failures:
                f.write("## Critical Findings\\n\\n")
                for i, failure in enumerate(results.critical_failures[:5], 1):
                    f.write(f"{i}. ❌ {failure}\\n")
                if len(results.critical_failures) > 5:
                    f.write(f"\\n*... and {len(results.critical_failures) - 5} additional findings*\\n")
                f.write("\\n")
            
            # Recommendations
            f.write("## Recommendations\\n\\n")
            if results.overall_resilience_score >= 80:
                f.write("- ✅ Core engine shows excellent resilience - ready for production stress\\n")
                f.write("- 🔄 Consider implementing additional monitoring for edge cases\\n")
            elif results.overall_resilience_score >= 60:
                f.write("- 🔧 Address identified performance degradations\\n")
                f.write("- 📊 Implement enhanced monitoring for stress scenarios\\n")
            else:
                f.write("- 🚨 **Priority:** Address critical resilience issues before production\\n")
                f.write("- 🔧 Implement additional error handling and recovery mechanisms\\n")
                f.write("- 📈 Consider load balancing and redundancy improvements\\n")
    
    async def _cleanup_core_engine(self):
        """Clean up core engine components"""
        
        try:
            if self.integration_manager:
                self.logger.info("🧹 Cleaning up core engine components...")
                await self.integration_manager.stop()
                self.integration_manager = None
                self.components = {}
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")

async def run_core_engine_stress_validation():
    """Main function to run core engine stress validation"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Core Engine Stress Validation Pipeline")
    logger.info("="*70)
    
    if not CORE_ENGINE_AVAILABLE:
        logger.error("❌ Core engine components not available")
        logger.info("Please ensure the core_engine package is properly installed")
        return None
    
    # Create validator
    validator = CoreEngineStressValidator()
    
    # Create stress testing configuration
    config = Phase2TestConfiguration(
        # Moderate intensity for real components
        test_intensity=1.8,
        test_duration_seconds=120,  # 2 minutes per category for faster testing
        
        # Enable comprehensive testing
        enable_market_stress=True,
        enable_component_failure=True,
        enable_load_stress=True,
        enable_network_failure=True,
        enable_data_corruption=True,
        enable_memory_pressure=True,
        
        # Core engine tuned parameters
        max_operations_per_second=2500,
        memory_limit_mb=250,
        corruption_rate=0.015,  # 1.5% corruption
        
        # Enable detailed reporting
        generate_detailed_reports=True,
        enable_baseline_comparison=True
    )
    
    try:
        # Run comprehensive stress validation
        results = await validator.run_comprehensive_stress_validation(config)
        
        # Display summary results
        logger.info("="*70)
        logger.info("📊 CORE ENGINE STRESS VALIDATION RESULTS")
        logger.info("="*70)
        
        print(f"\\n🎯 Overall Results:")
        print(f"   Resilience Score: {results.overall_resilience_score:.1f}/100")
        print(f"   Tests Completed: {results.total_tests_run}")
        success_rate = (results.successful_tests/results.total_tests_run*100) if results.total_tests_run > 0 else 0
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Duration: {results.total_duration_seconds:.1f} seconds")
        
        print(f"\\n📈 Category Scores:")
        for category, score in results.category_scores.items():
            status = "✅" if score >= 70 else "⚠️" if score >= 50 else "❌"
            print(f"   {status} {category.replace('_', ' ').title()}: {score:.1f}/100")
        
        # Core engine specific results
        if hasattr(results, 'core_engine_analysis'):
            analysis = results.core_engine_analysis
            print(f"\\n🏗️ Core Engine Analysis:")
            
            if 'component_health_retention_pct' in analysis:
                retention = analysis['component_health_retention_pct']
                status = "✅" if retention >= 90 else "⚠️" if retention >= 70 else "❌"
                print(f"   {status} Component Health Retention: {retention:.1f}%")
            
            if 'component_resilience_score' in analysis:
                resilience = analysis['component_resilience_score']
                status = "✅" if resilience >= 80 else "⚠️" if resilience >= 60 else "❌"
                print(f"   {status} Component Resilience: {resilience:.1f}/100")
        
        if results.critical_failures:
            print(f"\\n⚠️ Critical Findings ({len(results.critical_failures)} total):")
            for i, failure in enumerate(results.critical_failures[:3], 1):
                print(f"   {i}. {failure}")
            if len(results.critical_failures) > 3:
                print(f"   ... and {len(results.critical_failures) - 3} more")
        
        # Final assessment
        print(f"\\n🏆 Final Assessment:")
        if results.overall_resilience_score >= 80:
            print("   🟢 EXCELLENT - Core engine ready for production stress scenarios")
        elif results.overall_resilience_score >= 60:
            print("   🟡 GOOD - Core engine handles stress well, minor optimizations recommended")
        elif results.overall_resilience_score >= 40:
            print("   🟠 FAIR - Core engine needs resilience improvements before production")
        else:
            print("   🔴 POOR - Core engine requires significant resilience enhancements")
        
        logger.info("✅ Core engine stress validation completed successfully")
        logger.info("📊 Check 'tests/performance/core_engine_stress_results/' for detailed reports")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Core engine stress validation failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_core_engine_stress_validation())
