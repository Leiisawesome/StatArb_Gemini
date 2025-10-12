#!/usr/bin/env python3
"""
Phase 2: Comprehensive Stress Testing Suite

This module integrates all Phase 2 stress testing components into a unified
testing suite that can be run against the StatArb_Gemini core_engine to
validate system resilience under extreme conditions.

Components Integrated:
- Market Stress Testing (bull/bear/sideways scenarios)
- Component Failure Testing (graceful/sudden failures)
- Load Stress Testing (high-volume operations)
- Network Failure Testing (connectivity/latency issues)
- Data Corruption Testing (integrity/validation)
- Memory Pressure Testing (resource exhaustion)

Author: StatArb_Gemini Performance Testing Team
Version: 2.0.0 (Phase 2 - Complete Stress Testing Suite)
"""

import asyncio
import logging
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# Import Phase 1 framework
from .performance_test_suite import PerformanceTestSuite

# Import Phase 2 stress testing modules
from .stress_testing import (
    StressTestSuite, StressTestConfiguration, StressTestResult, StressTestType,
    MarketCondition, FailureMode
)
from .network_failure_testing import NetworkFailureTester
from .data_corruption_testing import DataCorruptionTester
from .memory_pressure_testing import MemoryPressureTester, ResourceExhaustionTester

logger = logging.getLogger(__name__)

# ============================================================================
# PHASE 2 COMPREHENSIVE TEST CONFIGURATION
# ============================================================================

@dataclass
class Phase2TestConfiguration:
    """Configuration for comprehensive Phase 2 stress testing"""
    
    # Test selection
    enable_market_stress: bool = True
    enable_component_failure: bool = True
    enable_load_stress: bool = True
    enable_network_failure: bool = True
    enable_data_corruption: bool = True
    enable_memory_pressure: bool = True
    
    # Test intensity (1.0 = normal, 2.0 = high, 5.0 = extreme)
    test_intensity: float = 2.0
    
    # Test duration
    test_duration_seconds: int = 300  # 5 minutes default
    
    # Baseline comparison
    enable_baseline_comparison: bool = True
    baseline_duration_seconds: int = 60
    
    # Reporting
    generate_detailed_reports: bool = True
    save_raw_data: bool = True
    
    # Market stress specific
    market_scenarios: List[MarketCondition] = None
    
    # Component failure specific
    failure_modes: List[FailureMode] = None
    target_components: List[str] = None
    
    # Load stress specific
    max_operations_per_second: int = 5000
    
    # Network failure specific
    network_latency_ms: int = 200
    packet_loss_rate: float = 0.1
    
    # Data corruption specific
    corruption_rate: float = 0.05
    corruption_types: List[str] = None
    
    # Memory pressure specific
    memory_limit_mb: int = 512
    allocation_rate_mb_per_sec: float = 10.0
    
    def __post_init__(self):
        """Set default values for list fields"""
        if self.market_scenarios is None:
            self.market_scenarios = [
                MarketCondition.HIGH_VOLATILITY,
                MarketCondition.FLASH_CRASH,
                MarketCondition.BULL_MARKET
            ]
        
        if self.failure_modes is None:
            self.failure_modes = [
                FailureMode.GRACEFUL_SHUTDOWN,
                FailureMode.SUDDEN_TERMINATION,
                FailureMode.MEMORY_LEAK
            ]
        
        if self.corruption_types is None:
            self.corruption_types = ['nan', 'inf', 'null', 'out_of_range']

@dataclass
class Phase2TestResults:
    """Comprehensive results from Phase 2 stress testing"""
    
    # Test metadata
    test_start_time: datetime
    test_end_time: datetime
    total_duration_seconds: float
    configuration: Phase2TestConfiguration
    
    # Individual test results
    market_stress_results: List[StressTestResult] = None
    component_failure_results: List[StressTestResult] = None
    load_stress_results: List[StressTestResult] = None
    network_failure_results: List[StressTestResult] = None
    data_corruption_results: List[StressTestResult] = None
    memory_pressure_results: List[StressTestResult] = None
    
    # Baseline performance (Phase 1)
    baseline_performance: Dict[str, Any] = None
    
    # Overall scores
    overall_resilience_score: float = 0.0
    category_scores: Dict[str, float] = None
    
    # Summary statistics
    total_tests_run: int = 0
    successful_tests: int = 0
    failed_tests: int = 0
    
    # Critical findings
    critical_failures: List[str] = None
    performance_degradations: Dict[str, float] = None
    recovery_capabilities: Dict[str, float] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.market_stress_results is None:
            self.market_stress_results = []
        if self.component_failure_results is None:
            self.component_failure_results = []
        if self.load_stress_results is None:
            self.load_stress_results = []
        if self.network_failure_results is None:
            self.network_failure_results = []
        if self.data_corruption_results is None:
            self.data_corruption_results = []
        if self.memory_pressure_results is None:
            self.memory_pressure_results = []
        if self.category_scores is None:
            self.category_scores = {}
        if self.critical_failures is None:
            self.critical_failures = []
        if self.performance_degradations is None:
            self.performance_degradations = {}
        if self.recovery_capabilities is None:
            self.recovery_capabilities = {}

# ============================================================================
# PHASE 2 COMPREHENSIVE STRESS TEST SUITE
# ============================================================================

class Phase2StressTestSuite:
    """Comprehensive Phase 2 stress testing suite"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.Phase2StressTestSuite")
        
        # Phase 1 components (for baseline)
        self.performance_suite = PerformanceTestSuite()
        
        # Phase 2 components
        self.stress_suite = StressTestSuite()
        self.network_tester = NetworkFailureTester()
        self.data_corruption_tester = DataCorruptionTester()
        self.memory_pressure_tester = MemoryPressureTester()
        self.resource_exhaustion_tester = ResourceExhaustionTester()
        
    async def run_comprehensive_stress_test(self, target_system: Any,
                                          config: Phase2TestConfiguration) -> Phase2TestResults:
        """Run comprehensive Phase 2 stress testing"""
        
        self.logger.info("🚀 Starting Phase 2 Comprehensive Stress Testing Suite...")
        self.logger.info(f"   Test Intensity: {config.test_intensity}x")
        self.logger.info(f"   Duration: {config.test_duration_seconds} seconds")
        
        start_time = datetime.now()
        
        results = Phase2TestResults(
            test_start_time=start_time,
            test_end_time=start_time,  # Will be updated
            total_duration_seconds=0.0,
            configuration=config
        )
        
        try:
            # Step 1: Establish baseline performance (Phase 1)
            if config.enable_baseline_comparison:
                self.logger.info("📊 Step 1: Establishing baseline performance...")
                results.baseline_performance = await self._run_baseline_tests(target_system, config)
            
            # Step 2: Market stress testing
            if config.enable_market_stress:
                self.logger.info("🌪️ Step 2: Market stress testing...")
                try:
                    results.market_stress_results = await asyncio.wait_for(
                        self._run_market_stress_tests(target_system, config),
                        timeout=config.test_duration_seconds + 30
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Market stress tests timed out")
                    results.market_stress_results = []
            
            # Step 3: Component failure testing
            if config.enable_component_failure:
                self.logger.info("💥 Step 3: Component failure testing...")
                try:
                    results.component_failure_results = await asyncio.wait_for(
                        self._run_component_failure_tests(target_system, config),
                        timeout=config.test_duration_seconds + 30
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Component failure tests timed out")
                    results.component_failure_results = []
            
            # Step 4: Load stress testing
            if config.enable_load_stress:
                self.logger.info("🔥 Step 4: Load stress testing...")
                try:
                    results.load_stress_results = await asyncio.wait_for(
                        self._run_load_stress_tests(target_system, config),
                        timeout=config.test_duration_seconds + 30
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Load stress tests timed out")
                    results.load_stress_results = []
            
            # Step 5: Network failure testing
            if config.enable_network_failure:
                self.logger.info("🌐 Step 5: Network failure testing...")
                try:
                    results.network_failure_results = await asyncio.wait_for(
                        self._run_network_failure_tests(target_system, config),
                        timeout=config.test_duration_seconds + 30
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Network failure tests timed out")
                    results.network_failure_results = []
            
            # Step 6: Data corruption testing
            if config.enable_data_corruption:
                self.logger.info("🗂️ Step 6: Data corruption testing...")
                try:
                    results.data_corruption_results = await asyncio.wait_for(
                        self._run_data_corruption_tests(target_system, config),
                        timeout=config.test_duration_seconds + 30
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Data corruption tests timed out")
                    results.data_corruption_results = []
            
            # Step 7: Memory pressure testing
            if config.enable_memory_pressure:
                self.logger.info("🧠 Step 7: Memory pressure testing...")
                try:
                    results.memory_pressure_results = await asyncio.wait_for(
                        self._run_memory_pressure_tests(target_system, config),
                        timeout=config.test_duration_seconds + 30
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Memory pressure tests timed out")
                    results.memory_pressure_results = []
            
            # Step 8: Calculate overall scores and analysis
            self.logger.info("📈 Step 8: Calculating resilience scores...")
            await self._calculate_overall_scores(results)
            
            # Step 9: Generate comprehensive reports
            if config.generate_detailed_reports:
                self.logger.info("📊 Step 9: Generating comprehensive reports...")
                await self._generate_comprehensive_reports(results)
            
        except Exception as e:
            self.logger.error(f"Comprehensive stress testing failed: {e}")
            results.critical_failures.append(f"Test suite failure: {str(e)}")
        
        finally:
            results.test_end_time = datetime.now()
            results.total_duration_seconds = (results.test_end_time - results.test_start_time).total_seconds()
        
        return results
    
    async def _run_baseline_tests(self, target_system: Any, 
                                config: Phase2TestConfiguration) -> Dict[str, Any]:
        """Run Phase 1 baseline performance tests"""
        
        self.logger.info("   Running Phase 1 baseline tests...")
        
        try:
            # Use Phase 1 performance test suite for baseline with timeout
            baseline_results = await asyncio.wait_for(
                self.performance_suite.run_comprehensive_performance_tests(
                    integration_manager=target_system
                ),
                timeout=config.baseline_duration_seconds + 30  # Add 30s buffer
            )
            
            return {
                'latency_baseline': baseline_results.get('latency_results', {}),
                'memory_baseline': baseline_results.get('memory_results', {}),
                'throughput_baseline': baseline_results.get('throughput_results', {}),
                'baseline_duration': config.baseline_duration_seconds
            }
        except asyncio.TimeoutError:
            self.logger.warning("Baseline tests timed out, using minimal baseline")
            return {
                'latency_baseline': {'mean_latency_ms': 1.0, 'p95_latency_ms': 2.0},
                'memory_baseline': {'peak_memory_mb': 100.0, 'efficiency_score': 80.0},
                'throughput_baseline': {'operations_per_second': 1000.0, 'scalability_score': 75.0},
                'baseline_duration': config.baseline_duration_seconds,
                'baseline_timeout': True
            }
    
    async def _run_market_stress_tests(self, target_system: Any,
                                     config: Phase2TestConfiguration) -> List[StressTestResult]:
        """Run market stress testing scenarios"""
        
        results = []
        
        for market_condition in config.market_scenarios:
            self.logger.info(f"   Testing market condition: {market_condition.value}")
            
            test_config = StressTestConfiguration(
                test_type=StressTestType.MARKET_STRESS,
                market_condition=market_condition,
                duration_seconds=config.test_duration_seconds // len(config.market_scenarios),
                intensity_level=config.test_intensity,
                price_volatility=0.02 * config.test_intensity,
                volume_multiplier=config.test_intensity
            )
            
            result = await self.stress_suite.market_tester.run_market_stress_test(test_config, target_system)
            results.append(result)
        
        return results
    
    async def _run_component_failure_tests(self, target_system: Any,
                                         config: Phase2TestConfiguration) -> List[StressTestResult]:
        """Run component failure testing scenarios"""
        
        results = []
        
        for failure_mode in config.failure_modes:
            self.logger.info(f"   Testing failure mode: {failure_mode.value}")
            
            test_config = StressTestConfiguration(
                test_type=StressTestType.COMPONENT_FAILURE,
                failure_mode=failure_mode,
                duration_seconds=config.test_duration_seconds // len(config.failure_modes),
                intensity_level=config.test_intensity,
                target_components=config.target_components or []
            )
            
            result = await self.stress_suite.component_tester.run_component_failure_test(test_config, target_system)
            results.append(result)
        
        return results
    
    async def _run_load_stress_tests(self, target_system: Any,
                                   config: Phase2TestConfiguration) -> List[StressTestResult]:
        """Run load stress testing scenarios"""
        
        results = []
        
        # Test multiple load levels
        load_levels = [
            int(config.max_operations_per_second * 0.5),  # 50% load
            int(config.max_operations_per_second * 0.8),  # 80% load
            config.max_operations_per_second              # 100% load
        ]
        
        for ops_per_sec in load_levels:
            self.logger.info(f"   Testing load level: {ops_per_sec} ops/sec")
            
            test_config = StressTestConfiguration(
                test_type=StressTestType.LOAD_STRESS,
                operations_per_second=ops_per_sec,
                duration_seconds=config.test_duration_seconds // len(load_levels),
                intensity_level=config.test_intensity,
                ramp_up_duration=20
            )
            
            result = await self.stress_suite.load_tester.run_load_stress_test(test_config, target_system)
            results.append(result)
        
        return results
    
    async def _run_network_failure_tests(self, target_system: Any,
                                       config: Phase2TestConfiguration) -> List[StressTestResult]:
        """Run network failure testing scenarios"""
        
        results = []
        
        # Test different network conditions
        network_conditions = [
            {'latency_ms': config.network_latency_ms, 'packet_loss': 0.0},
            {'latency_ms': 50, 'packet_loss': config.packet_loss_rate},
            {'latency_ms': config.network_latency_ms, 'packet_loss': config.packet_loss_rate}
        ]
        
        for condition in network_conditions:
            self.logger.info(f"   Testing network condition: {condition['latency_ms']}ms latency, "
                           f"{condition['packet_loss']*100:.1f}% loss")
            
            test_config = StressTestConfiguration(
                test_type=StressTestType.NETWORK_FAILURE,
                duration_seconds=config.test_duration_seconds // len(network_conditions),
                network_latency_ms=condition['latency_ms'],
                packet_loss_rate=condition['packet_loss'],
                intensity_level=config.test_intensity
            )
            
            result = await self.network_tester.run_network_failure_test(test_config, target_system)
            results.append(result)
        
        return results
    
    async def _run_data_corruption_tests(self, target_system: Any,
                                       config: Phase2TestConfiguration) -> List[StressTestResult]:
        """Run data corruption testing scenarios"""
        
        results = []
        
        # Test different corruption rates
        corruption_rates = [
            config.corruption_rate * 0.5,  # Low corruption
            config.corruption_rate,        # Medium corruption
            config.corruption_rate * 2.0   # High corruption
        ]
        
        for corruption_rate in corruption_rates:
            self.logger.info(f"   Testing corruption rate: {corruption_rate*100:.1f}%")
            
            test_config = StressTestConfiguration(
                test_type=StressTestType.DATA_CORRUPTION,
                duration_seconds=config.test_duration_seconds // len(corruption_rates),
                corruption_rate=corruption_rate,
                corruption_types=config.corruption_types,
                intensity_level=config.test_intensity
            )
            
            result = await self.data_corruption_tester.run_data_corruption_test(test_config, target_system)
            results.append(result)
        
        return results
    
    async def _run_memory_pressure_tests(self, target_system: Any,
                                       config: Phase2TestConfiguration) -> List[StressTestResult]:
        """Run memory pressure testing scenarios"""
        
        results = []
        
        # Test different memory pressure levels
        memory_limits = [
            config.memory_limit_mb,        # Target limit
            config.memory_limit_mb * 1.5,  # 150% of target
            config.memory_limit_mb * 0.7   # 70% of target (more aggressive)
        ]
        
        for memory_limit in memory_limits:
            self.logger.info(f"   Testing memory limit: {memory_limit:.0f} MB")
            
            test_config = StressTestConfiguration(
                test_type=StressTestType.MEMORY_PRESSURE,
                duration_seconds=config.test_duration_seconds // len(memory_limits),
                memory_limit_mb=memory_limit,
                allocation_rate_mb_per_sec=config.allocation_rate_mb_per_sec * config.test_intensity,
                intensity_level=config.test_intensity
            )
            
            result = await self.memory_pressure_tester.run_memory_pressure_test(test_config, target_system)
            results.append(result)
        
        return results
    
    async def _calculate_overall_scores(self, results: Phase2TestResults):
        """Calculate overall resilience scores and analysis"""
        
        # Collect all test results
        all_results = []
        all_results.extend(results.market_stress_results or [])
        all_results.extend(results.component_failure_results or [])
        all_results.extend(results.load_stress_results or [])
        all_results.extend(results.network_failure_results or [])
        all_results.extend(results.data_corruption_results or [])
        all_results.extend(results.memory_pressure_results or [])
        
        # Calculate summary statistics
        results.total_tests_run = len(all_results)
        results.successful_tests = sum(1 for r in all_results if r.success)
        results.failed_tests = results.total_tests_run - results.successful_tests
        
        # Calculate category scores
        category_results = {
            'market_stress': results.market_stress_results or [],
            'component_failure': results.component_failure_results or [],
            'load_stress': results.load_stress_results or [],
            'network_failure': results.network_failure_results or [],
            'data_corruption': results.data_corruption_results or [],
            'memory_pressure': results.memory_pressure_results or []
        }
        
        for category, category_results_list in category_results.items():
            if category_results_list:
                scores = [r.system_stability_score for r in category_results_list if r.success]
                results.category_scores[category] = sum(scores) / len(scores) if scores else 0.0
        
        # Calculate overall resilience score
        if results.category_scores:
            results.overall_resilience_score = sum(results.category_scores.values()) / len(results.category_scores)
        
        # Identify critical failures
        for result in all_results:
            if not result.success:
                results.critical_failures.append(f"{result.test_type.value}: {result.failure_reason}")
            elif result.system_stability_score < 50:  # Score below 50 is concerning
                results.critical_failures.append(f"{result.test_type.value}: Low stability score ({result.system_stability_score:.1f})")
        
        # Calculate performance degradations (compared to baseline)
        if results.baseline_performance:
            await self._calculate_performance_degradations(results)
        
        # Calculate recovery capabilities
        await self._calculate_recovery_capabilities(results)
    
    async def _calculate_performance_degradations(self, results: Phase2TestResults):
        """Calculate performance degradations compared to baseline"""
        
        baseline = results.baseline_performance
        
        # Compare with stress test performance
        for category, category_results in [
            ('market_stress', results.market_stress_results),
            ('load_stress', results.load_stress_results)
        ]:
            if category_results and baseline:
                # Calculate average degradation for this category
                degradations = []
                
                for result in category_results:
                    if result.success and result.performance_degradation:
                        for metric, degradation in result.performance_degradation.items():
                            if not np.isinf(degradation):
                                degradations.append(degradation)
                
                if degradations:
                    avg_degradation = sum(degradations) / len(degradations)
                    results.performance_degradations[category] = avg_degradation
    
    async def _calculate_recovery_capabilities(self, results: Phase2TestResults):
        """Calculate recovery capabilities across test categories"""
        
        recovery_data = {}
        
        # Component failure recovery
        if results.component_failure_results:
            recovery_times = []
            recovery_rates = []
            
            for result in results.component_failure_results:
                if result.success and result.recovery_times:
                    recovery_times.extend(result.recovery_times)
                
                if result.recovery_count > 0 and result.failure_count > 0:
                    recovery_rate = result.recovery_count / result.failure_count
                    recovery_rates.append(recovery_rate)
            
            if recovery_times:
                recovery_data['avg_recovery_time_ms'] = sum(recovery_times) / len(recovery_times)
            
            if recovery_rates:
                recovery_data['avg_recovery_rate'] = sum(recovery_rates) / len(recovery_rates)
        
        # Memory pressure recovery
        if results.memory_pressure_results:
            memory_recoveries = []
            
            for result in results.memory_pressure_results:
                if result.success:
                    recovery_pct = result.stress_performance.get('memory_recovery_percentage', 0)
                    memory_recoveries.append(recovery_pct)
            
            if memory_recoveries:
                recovery_data['avg_memory_recovery_pct'] = sum(memory_recoveries) / len(memory_recoveries)
        
        results.recovery_capabilities = recovery_data
    
    async def _generate_comprehensive_reports(self, results: Phase2TestResults):
        """Generate comprehensive test reports"""
        
        # Create results directory
        results_dir = Path("tests/performance/phase2_results")
        results_dir.mkdir(exist_ok=True)
        
        timestamp = results.test_start_time.strftime("%Y%m%d_%H%M%S")
        
        # Generate JSON report
        json_report_path = results_dir / f"phase2_comprehensive_results_{timestamp}.json"
        await self._generate_json_report(results, json_report_path)
        
        # Generate Markdown report
        md_report_path = results_dir / f"phase2_comprehensive_report_{timestamp}.md"
        await self._generate_markdown_report(results, md_report_path)
        
        # Generate CSV summary
        csv_report_path = results_dir / f"phase2_summary_{timestamp}.csv"
        await self._generate_csv_summary(results, csv_report_path)
        
        self.logger.info(f"📊 Comprehensive reports generated:")
        self.logger.info(f"   JSON: {json_report_path}")
        self.logger.info(f"   Markdown: {md_report_path}")
        self.logger.info(f"   CSV: {csv_report_path}")
    
    async def _generate_json_report(self, results: Phase2TestResults, file_path: Path):
        """Generate JSON report with all test data"""
        
        # Convert results to serializable format
        report_data = {
            'test_metadata': {
                'start_time': results.test_start_time.isoformat(),
                'end_time': results.test_end_time.isoformat(),
                'duration_seconds': results.total_duration_seconds,
                'configuration': asdict(results.configuration)
            },
            'summary': {
                'overall_resilience_score': results.overall_resilience_score,
                'total_tests_run': results.total_tests_run,
                'successful_tests': results.successful_tests,
                'failed_tests': results.failed_tests,
                'category_scores': results.category_scores
            },
            'baseline_performance': results.baseline_performance,
            'test_results': {
                'market_stress': [asdict(r) for r in (results.market_stress_results or [])],
                'component_failure': [asdict(r) for r in (results.component_failure_results or [])],
                'load_stress': [asdict(r) for r in (results.load_stress_results or [])],
                'network_failure': [asdict(r) for r in (results.network_failure_results or [])],
                'data_corruption': [asdict(r) for r in (results.data_corruption_results or [])],
                'memory_pressure': [asdict(r) for r in (results.memory_pressure_results or [])]
            },
            'analysis': {
                'critical_failures': results.critical_failures,
                'performance_degradations': results.performance_degradations,
                'recovery_capabilities': results.recovery_capabilities
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
    
    async def _generate_markdown_report(self, results: Phase2TestResults, file_path: Path):
        """Generate human-readable Markdown report"""
        
        with open(file_path, 'w') as f:
            f.write("# Phase 2 Comprehensive Stress Testing Report\\n\\n")
            f.write(f"**Generated:** {results.test_end_time.strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"**Duration:** {results.total_duration_seconds:.1f} seconds\\n\\n")
            
            # Executive Summary
            f.write("## Executive Summary\\n\\n")
            f.write(f"- **Overall Resilience Score:** {results.overall_resilience_score:.1f}/100\\n")
            f.write(f"- **Tests Run:** {results.total_tests_run}\\n")
            f.write(f"- **Success Rate:** {(results.successful_tests/results.total_tests_run*100):.1f}%\\n")
            f.write(f"- **Test Intensity:** {results.configuration.test_intensity}x\\n\\n")
            
            # Category Scores
            f.write("## Category Performance\\n\\n")
            for category, score in results.category_scores.items():
                f.write(f"- **{category.replace('_', ' ').title()}:** {score:.1f}/100\\n")
            f.write("\\n")
            
            # Critical Failures
            if results.critical_failures:
                f.write("## Critical Failures\\n\\n")
                for failure in results.critical_failures:
                    f.write(f"- ❌ {failure}\\n")
                f.write("\\n")
            
            # Recovery Capabilities
            if results.recovery_capabilities:
                f.write("## Recovery Capabilities\\n\\n")
                for metric, value in results.recovery_capabilities.items():
                    f.write(f"- **{metric.replace('_', ' ').title()}:** {value:.2f}\\n")
                f.write("\\n")
            
            # Performance Degradations
            if results.performance_degradations:
                f.write("## Performance Degradations\\n\\n")
                for category, degradation in results.performance_degradations.items():
                    f.write(f"- **{category.replace('_', ' ').title()}:** {degradation:.1f}%\\n")
                f.write("\\n")
    
    async def _generate_csv_summary(self, results: Phase2TestResults, file_path: Path):
        """Generate CSV summary for data analysis"""
        
        import csv
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Test_Category', 'Test_Type', 'Success', 'Stability_Score', 
                'Duration_Seconds', 'Failure_Reason'
            ])
            
            # Write all test results
            all_test_categories = [
                ('Market_Stress', results.market_stress_results),
                ('Component_Failure', results.component_failure_results),
                ('Load_Stress', results.load_stress_results),
                ('Network_Failure', results.network_failure_results),
                ('Data_Corruption', results.data_corruption_results),
                ('Memory_Pressure', results.memory_pressure_results)
            ]
            
            for category, test_results in all_test_categories:
                if test_results:
                    for result in test_results:
                        writer.writerow([
                            category,
                            result.test_type.value,
                            'Yes' if result.success else 'No',
                            f"{result.system_stability_score:.1f}",
                            f"{result.duration_seconds:.1f}",
                            result.failure_reason or ''
                        ])

# ============================================================================
# EXAMPLE USAGE AND MAIN RUNNER
# ============================================================================

async def run_phase2_comprehensive_test():
    """Example usage of Phase 2 comprehensive stress testing"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create mock target system
    class MockComprehensiveSystem:
        def __init__(self):
            self.is_operational = True
            self.components = {
                'data_manager': self,
                'risk_manager': self,
                'strategy_manager': self,
                'execution_engine': self
            }
            self.data_cache = {}
        
        async def process_market_data(self, data):
            await asyncio.sleep(0.001)
            return {'processed': True}
        
        async def process_operation(self, data):
            # Store in cache (potential memory usage)
            operation_id = str(len(self.data_cache))
            self.data_cache[operation_id] = data
            await asyncio.sleep(0.0005)
            return {'result': 'success'}
        
        async def process_data(self, data):
            # Validate data
            if isinstance(data, dict) and 'price' in data:
                price = data['price']
                if price <= 0 or np.isnan(price) or np.isinf(price):
                    raise ValueError("Invalid price data")
            await asyncio.sleep(0.001)
            return {'validated': True}
        
        async def health_check(self):
            return {'healthy': self.is_operational}
    
    target_system = MockComprehensiveSystem()
    
    # Configure comprehensive testing
    config = Phase2TestConfiguration(
        test_intensity=1.5,  # Moderate intensity for example
        test_duration_seconds=120,  # 2 minutes for example
        enable_baseline_comparison=True,
        generate_detailed_reports=True,
        max_operations_per_second=1000,
        memory_limit_mb=100,
        corruption_rate=0.05
    )
    
    # Run comprehensive stress testing
    suite = Phase2StressTestSuite()
    results = await suite.run_comprehensive_stress_test(target_system, config)
    
    # Print summary
    print("\\n" + "="*80)
    print("PHASE 2 COMPREHENSIVE STRESS TEST RESULTS")
    print("="*80)
    print(f"Overall Resilience Score: {results.overall_resilience_score:.1f}/100")
    print(f"Tests Run: {results.total_tests_run}")
    print(f"Success Rate: {(results.successful_tests/results.total_tests_run*100):.1f}%")
    print(f"Duration: {results.total_duration_seconds:.1f} seconds")
    
    print("\\nCategory Scores:")
    for category, score in results.category_scores.items():
        print(f"  {category.replace('_', ' ').title()}: {score:.1f}/100")
    
    if results.critical_failures:
        print("\\nCritical Failures:")
        for failure in results.critical_failures[:5]:  # Show first 5
            print(f"  ❌ {failure}")
    
    return results

if __name__ == "__main__":
    import numpy as np
    asyncio.run(run_phase2_comprehensive_test())
