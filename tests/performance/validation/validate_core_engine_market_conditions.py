#!/usr/bin/env python3
"""
Phase 3: Core Engine Market Condition Validation

This script validates the core engine's performance under various market conditions
and regimes. It integrates with the Phase 3 Market Condition Testing framework
to provide comprehensive testing across different market scenarios.

Usage:
    python validate_core_engine_market_conditions.py

Features:
- Market regime testing (bull, bear, sideways, volatile, crisis)
- Volatility regime testing (low, normal, high, extreme)
- Liquidity condition testing (high, normal, low, crisis)
- Correlation regime testing (normal, high, breakdown, flight-to-quality)
- Comprehensive performance analysis and reporting
"""

import asyncio
import logging
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Core engine imports
from core_engine.system.integration_manager import SystemIntegrationManager

# Phase 3 testing imports
from tests.performance.phase3_market_condition_testing import (
    Phase3MarketConditionSuite
)

# Performance testing imports


class CoreEngineMarketConditionValidator:
    """Validates core engine performance under various market conditions"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.integration_manager = None
        self.phase3_suite = Phase3MarketConditionSuite()
        self.validation_results = {}
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('phase3_market_condition_validation.log')
            ]
        )
        return logging.getLogger(self.__class__.__name__)
    
    async def initialize_core_engine(self) -> bool:
        """Initialize core engine components for testing"""
        
        self.logger.info("🔧 Initializing core engine components for market condition testing")
        
        try:
            # Import SystemConfiguration
            from core_engine.system.integration_manager import SystemConfiguration
            
            # Create minimal system configuration
            system_config = SystemConfiguration()
            
            # Initialize SystemIntegrationManager
            self.integration_manager = SystemIntegrationManager(system_config)
            
            # Initialize core components with minimal configuration
            components_config = {
                'data_manager': {
                    'type': 'clickhouse',
                    'host': 'localhost',
                    'port': 8123,
                    'database': 'market_data'
                },
                'risk_manager': {
                    'max_position_size': 0.10,
                    'max_daily_var': 0.05,
                    'enable_regime_adjustment': True
                },
                'regime_engine': {
                    'enable_ml_prediction': True,
                    'lookback_periods': [20, 60, 252],
                    'volatility_threshold': 0.02
                },
                'strategy_manager': {
                    'max_strategies': 5,
                    'enable_multi_strategy': True
                },
                'execution_engine': {
                    'enable_smart_routing': True,
                    'max_market_impact': 0.05
                },
                'portfolio_manager': {
                    'initial_capital': 1000000,
                    'enable_rebalancing': True
                }
            }
            
            # Initialize the integration manager
            success = await self.integration_manager.initialize()
            
            if success:
                self.logger.info("✅ Core engine components initialized successfully")
                return True
            else:
                self.logger.error("❌ Failed to initialize core engine components")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Core engine initialization failed: {e}")
            return False
    
    async def run_market_condition_validation(self) -> dict:
        """Run comprehensive market condition validation"""
        
        self.logger.info("🚀 Starting Phase 3: Market Condition Validation")
        validation_start_time = time.time()
        
        try:
            # Initialize core engine
            if not await self.initialize_core_engine():
                return {
                    'status': 'failed',
                    'error': 'Failed to initialize core engine',
                    'results': {}
                }
            
            # Run Phase 3 market condition tests
            self.logger.info("📊 Running comprehensive market condition tests")
            phase3_results = await self.phase3_suite.run_phase3_tests(self.integration_manager)
            
            # Analyze and validate results
            validation_analysis = await self._analyze_validation_results(phase3_results)
            
            # Generate comprehensive report
            validation_report = await self._generate_validation_report(
                phase3_results, validation_analysis
            )
            
            validation_duration = time.time() - validation_start_time
            
            # Compile final validation results
            final_results = {
                'validation_timestamp': datetime.now().isoformat(),
                'validation_duration_seconds': validation_duration,
                'phase3_results': phase3_results,
                'validation_analysis': validation_analysis,
                'validation_report': validation_report,
                'status': 'completed',
                'summary': self._generate_executive_summary(phase3_results, validation_analysis)
            }
            
            # Save results
            await self._save_validation_results(final_results)
            
            self.logger.info(f"✅ Phase 3 validation completed in {validation_duration:.2f}s")
            return final_results
            
        except Exception as e:
            validation_duration = time.time() - validation_start_time
            self.logger.error(f"❌ Market condition validation failed: {e}")
            
            return {
                'validation_timestamp': datetime.now().isoformat(),
                'validation_duration_seconds': validation_duration,
                'status': 'failed',
                'error': str(e),
                'results': {}
            }
    
    async def _analyze_validation_results(self, phase3_results: dict) -> dict:
        """Analyze Phase 3 validation results"""
        
        self.logger.info("🔍 Analyzing market condition validation results")
        
        try:
            analysis = {
                'overall_assessment': {},
                'regime_performance': {},
                'component_performance': {},
                'risk_assessment': {},
                'recommendations': []
            }
            
            # Extract condition results
            condition_results = phase3_results.get('condition_results', [])
            
            if not condition_results:
                return {
                    'status': 'no_results',
                    'message': 'No market condition test results available'
                }
            
            # Overall assessment
            total_conditions = len(condition_results)
            successful_conditions = len([r for r in condition_results if not r.errors_encountered])
            
            # Calculate average scores across all conditions
            avg_scores = {
                'regime_detection': sum(r.regime_detection_accuracy for r in condition_results) / total_conditions,
                'risk_management': sum(r.risk_management_effectiveness for r in condition_results) / total_conditions,
                'execution_quality': sum(r.execution_quality_score for r in condition_results) / total_conditions,
                'strategy_adaptation': sum(r.strategy_adaptation_score for r in condition_results) / total_conditions,
                'system_stability': sum(r.system_stability_score for r in condition_results) / total_conditions
            }
            
            overall_score = sum(avg_scores.values()) / len(avg_scores)
            
            analysis['overall_assessment'] = {
                'total_conditions_tested': total_conditions,
                'successful_conditions': successful_conditions,
                'success_rate': successful_conditions / total_conditions,
                'overall_score': overall_score,
                'average_scores': avg_scores,
                'grade': self._calculate_grade(overall_score)
            }
            
            # Regime-specific performance analysis
            regime_performance = {}
            for result in condition_results:
                regime = result.market_regime
                if regime not in regime_performance:
                    regime_performance[regime] = {
                        'tests': 0,
                        'total_score': 0,
                        'regime_accuracy': 0,
                        'risk_effectiveness': 0,
                        'execution_quality': 0,
                        'strategy_adaptation': 0,
                        'system_stability': 0
                    }
                
                regime_perf = regime_performance[regime]
                regime_perf['tests'] += 1
                regime_perf['regime_accuracy'] += result.regime_detection_accuracy
                regime_perf['risk_effectiveness'] += result.risk_management_effectiveness
                regime_perf['execution_quality'] += result.execution_quality_score
                regime_perf['strategy_adaptation'] += result.strategy_adaptation_score
                regime_perf['system_stability'] += result.system_stability_score
                
                condition_score = (
                    result.regime_detection_accuracy +
                    result.risk_management_effectiveness +
                    result.execution_quality_score +
                    result.strategy_adaptation_score +
                    result.system_stability_score
                ) / 5.0
                
                regime_perf['total_score'] += condition_score
            
            # Calculate averages for each regime
            for regime, perf in regime_performance.items():
                test_count = perf['tests']
                regime_performance[regime] = {
                    'test_count': test_count,
                    'average_score': perf['total_score'] / test_count,
                    'regime_detection_accuracy': perf['regime_accuracy'] / test_count,
                    'risk_management_effectiveness': perf['risk_effectiveness'] / test_count,
                    'execution_quality': perf['execution_quality'] / test_count,
                    'strategy_adaptation': perf['strategy_adaptation'] / test_count,
                    'system_stability': perf['system_stability'] / test_count,
                    'grade': self._calculate_grade(perf['total_score'] / test_count)
                }
            
            analysis['regime_performance'] = regime_performance
            
            # Component performance analysis
            analysis['component_performance'] = {
                'regime_engine': {
                    'average_accuracy': avg_scores['regime_detection'],
                    'grade': self._calculate_grade(avg_scores['regime_detection']),
                    'status': 'excellent' if avg_scores['regime_detection'] >= 0.8 else 'needs_improvement'
                },
                'risk_manager': {
                    'average_effectiveness': avg_scores['risk_management'],
                    'grade': self._calculate_grade(avg_scores['risk_management']),
                    'status': 'excellent' if avg_scores['risk_management'] >= 0.8 else 'needs_improvement'
                },
                'execution_engine': {
                    'average_quality': avg_scores['execution_quality'],
                    'grade': self._calculate_grade(avg_scores['execution_quality']),
                    'status': 'excellent' if avg_scores['execution_quality'] >= 0.8 else 'needs_improvement'
                },
                'strategy_manager': {
                    'average_adaptation': avg_scores['strategy_adaptation'],
                    'grade': self._calculate_grade(avg_scores['strategy_adaptation']),
                    'status': 'excellent' if avg_scores['strategy_adaptation'] >= 0.8 else 'needs_improvement'
                },
                'system_integration': {
                    'average_stability': avg_scores['system_stability'],
                    'grade': self._calculate_grade(avg_scores['system_stability']),
                    'status': 'excellent' if avg_scores['system_stability'] >= 0.8 else 'needs_improvement'
                }
            }
            
            # Risk assessment
            analysis['risk_assessment'] = await self._assess_market_condition_risks(condition_results)
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_improvement_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Validation analysis failed: {e}")
            return {
                'status': 'analysis_failed',
                'error': str(e)
            }
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score"""
        if score >= 0.9:
            return 'A+'
        elif score >= 0.85:
            return 'A'
        elif score >= 0.8:
            return 'A-'
        elif score >= 0.75:
            return 'B+'
        elif score >= 0.7:
            return 'B'
        elif score >= 0.65:
            return 'B-'
        elif score >= 0.6:
            return 'C+'
        elif score >= 0.55:
            return 'C'
        elif score >= 0.5:
            return 'C-'
        elif score >= 0.4:
            return 'D'
        else:
            return 'F'
    
    async def _assess_market_condition_risks(self, condition_results: list) -> dict:
        """Assess risks based on market condition test results"""
        
        risk_assessment = {
            'high_risk_conditions': [],
            'medium_risk_conditions': [],
            'low_risk_conditions': [],
            'critical_failures': [],
            'risk_score': 0.0
        }
        
        for result in condition_results:
            condition_name = result.condition_name
            overall_score = (
                result.regime_detection_accuracy +
                result.risk_management_effectiveness +
                result.execution_quality_score +
                result.strategy_adaptation_score +
                result.system_stability_score
            ) / 5.0
            
            if result.errors_encountered:
                risk_assessment['critical_failures'].append({
                    'condition': condition_name,
                    'errors': result.errors_encountered
                })
            elif overall_score < 0.5:
                risk_assessment['high_risk_conditions'].append({
                    'condition': condition_name,
                    'score': overall_score,
                    'regime': result.market_regime
                })
            elif overall_score < 0.7:
                risk_assessment['medium_risk_conditions'].append({
                    'condition': condition_name,
                    'score': overall_score,
                    'regime': result.market_regime
                })
            else:
                risk_assessment['low_risk_conditions'].append({
                    'condition': condition_name,
                    'score': overall_score,
                    'regime': result.market_regime
                })
        
        # Calculate overall risk score
        total_conditions = len(condition_results)
        high_risk_count = len(risk_assessment['high_risk_conditions'])
        medium_risk_count = len(risk_assessment['medium_risk_conditions'])
        critical_count = len(risk_assessment['critical_failures'])
        
        # Risk score calculation (lower is better)
        risk_score = (
            (critical_count * 1.0) +
            (high_risk_count * 0.7) +
            (medium_risk_count * 0.3)
        ) / total_conditions if total_conditions > 0 else 0
        
        risk_assessment['risk_score'] = risk_score
        risk_assessment['risk_level'] = (
            'CRITICAL' if risk_score > 0.5 else
            'HIGH' if risk_score > 0.3 else
            'MEDIUM' if risk_score > 0.1 else
            'LOW'
        )
        
        return risk_assessment
    
    def _generate_improvement_recommendations(self, analysis: dict) -> list:
        """Generate improvement recommendations based on analysis"""
        
        recommendations = []
        
        # Overall performance recommendations
        overall_score = analysis['overall_assessment']['overall_score']
        if overall_score < 0.7:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Overall Performance',
                'recommendation': 'Comprehensive system optimization needed - overall score below acceptable threshold',
                'target_components': ['All']
            })
        
        # Component-specific recommendations
        component_perf = analysis['component_performance']
        
        for component, perf in component_perf.items():
            score_key = list(perf.keys())[0]  # Get the score key (varies by component)
            score = perf[score_key]
            
            if score < 0.6:
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'Component Performance',
                    'recommendation': f'{component.replace("_", " ").title()} requires significant improvement',
                    'target_components': [component],
                    'current_score': score
                })
            elif score < 0.8:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'Component Performance',
                    'recommendation': f'{component.replace("_", " ").title()} has room for optimization',
                    'target_components': [component],
                    'current_score': score
                })
        
        # Regime-specific recommendations
        regime_perf = analysis['regime_performance']
        worst_regimes = sorted(regime_perf.items(), key=lambda x: x[1]['average_score'])[:2]
        
        for regime, perf in worst_regimes:
            if perf['average_score'] < 0.7:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'Market Regime Performance',
                    'recommendation': f'Improve performance under {regime.replace("_", " ")} conditions',
                    'target_components': ['Strategy Manager', 'Risk Manager'],
                    'regime': regime,
                    'current_score': perf['average_score']
                })
        
        # Risk-based recommendations
        risk_assessment = analysis['risk_assessment']
        if risk_assessment['risk_level'] in ['CRITICAL', 'HIGH']:
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Risk Management',
                'recommendation': 'Address critical risk issues identified in market condition testing',
                'target_components': ['Risk Manager', 'System Integration'],
                'risk_level': risk_assessment['risk_level']
            })
        
        return recommendations
    
    async def _generate_validation_report(self, phase3_results: dict, 
                                        validation_analysis: dict) -> dict:
        """Generate comprehensive validation report"""
        
        self.logger.info("📋 Generating comprehensive validation report")
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'executive_summary': {},
            'detailed_analysis': validation_analysis,
            'performance_metrics': {},
            'risk_analysis': validation_analysis.get('risk_assessment', {}),
            'recommendations': validation_analysis.get('recommendations', []),
            'appendices': {}
        }
        
        # Executive summary
        overall_assessment = validation_analysis.get('overall_assessment', {})
        report['executive_summary'] = {
            'test_scope': 'Comprehensive market condition testing across multiple regimes',
            'total_conditions_tested': overall_assessment.get('total_conditions_tested', 0),
            'overall_grade': overall_assessment.get('grade', 'N/A'),
            'overall_score': overall_assessment.get('overall_score', 0.0),
            'success_rate': overall_assessment.get('success_rate', 0.0),
            'key_findings': self._extract_key_findings(validation_analysis),
            'critical_issues': self._extract_critical_issues(validation_analysis),
            'strengths': self._extract_strengths(validation_analysis),
            'areas_for_improvement': self._extract_improvement_areas(validation_analysis)
        }
        
        # Performance metrics summary
        if 'condition_results' in phase3_results:
            condition_results = phase3_results['condition_results']
            perf_metrics = [r.performance_metrics for r in condition_results if r.performance_metrics]
            
            if perf_metrics:
                report['performance_metrics'] = {
                    'average_latency_ms': sum(p.avg_latency_ms for p in perf_metrics) / len(perf_metrics),
                    'average_throughput': sum(p.throughput_ops_per_sec for p in perf_metrics) / len(perf_metrics),
                    'average_memory_usage_mb': sum(p.memory_usage_mb for p in perf_metrics) / len(perf_metrics),
                    'average_cpu_usage_percent': sum(p.cpu_usage_percent for p in perf_metrics) / len(perf_metrics),
                    'average_error_rate': sum(p.error_rate for p in perf_metrics) / len(perf_metrics)
                }
        
        return report
    
    def _extract_key_findings(self, analysis: dict) -> list:
        """Extract key findings from analysis"""
        findings = []
        
        overall = analysis.get('overall_assessment', {})
        if overall.get('overall_score', 0) >= 0.8:
            findings.append('Core engine demonstrates strong performance across market conditions')
        elif overall.get('overall_score', 0) >= 0.6:
            findings.append('Core engine shows acceptable performance with room for improvement')
        else:
            findings.append('Core engine performance requires significant improvement')
        
        # Component findings
        component_perf = analysis.get('component_performance', {})
        best_component = max(component_perf.items(), key=lambda x: list(x[1].values())[0]) if component_perf else None
        worst_component = min(component_perf.items(), key=lambda x: list(x[1].values())[0]) if component_perf else None
        
        if best_component:
            findings.append(f'Best performing component: {best_component[0].replace("_", " ").title()}')
        
        if worst_component:
            findings.append(f'Component needing most improvement: {worst_component[0].replace("_", " ").title()}')
        
        return findings
    
    def _extract_critical_issues(self, analysis: dict) -> list:
        """Extract critical issues from analysis"""
        issues = []
        
        risk_assessment = analysis.get('risk_assessment', {})
        
        if risk_assessment.get('critical_failures'):
            issues.append(f"{len(risk_assessment['critical_failures'])} critical test failures detected")
        
        if risk_assessment.get('risk_level') == 'CRITICAL':
            issues.append('System risk level assessed as CRITICAL')
        
        overall_score = analysis.get('overall_assessment', {}).get('overall_score', 1.0)
        if overall_score < 0.5:
            issues.append('Overall performance score below minimum acceptable threshold')
        
        return issues
    
    def _extract_strengths(self, analysis: dict) -> list:
        """Extract system strengths from analysis"""
        strengths = []
        
        component_perf = analysis.get('component_performance', {})
        for component, perf in component_perf.items():
            if perf.get('status') == 'excellent':
                strengths.append(f'Excellent {component.replace("_", " ")} performance')
        
        regime_perf = analysis.get('regime_performance', {})
        best_regimes = [regime for regime, perf in regime_perf.items() if perf['average_score'] >= 0.8]
        
        if best_regimes:
            strengths.append(f'Strong performance in {len(best_regimes)} market regimes')
        
        return strengths
    
    def _extract_improvement_areas(self, analysis: dict) -> list:
        """Extract areas for improvement from analysis"""
        areas = []
        
        component_perf = analysis.get('component_performance', {})
        for component, perf in component_perf.items():
            if perf.get('status') == 'needs_improvement':
                areas.append(f'{component.replace("_", " ").title()} optimization')
        
        regime_perf = analysis.get('regime_performance', {})
        weak_regimes = [regime for regime, perf in regime_perf.items() if perf['average_score'] < 0.7]
        
        if weak_regimes:
            areas.append(f'Performance under {", ".join(weak_regimes).replace("_", " ")} conditions')
        
        return areas
    
    def _generate_executive_summary(self, phase3_results: dict, 
                                  validation_analysis: dict) -> dict:
        """Generate executive summary"""
        
        overall = validation_analysis.get('overall_assessment', {})
        
        return {
            'validation_status': 'COMPLETED',
            'overall_grade': overall.get('grade', 'N/A'),
            'overall_score': overall.get('overall_score', 0.0),
            'conditions_tested': overall.get('total_conditions_tested', 0),
            'success_rate': overall.get('success_rate', 0.0),
            'risk_level': validation_analysis.get('risk_assessment', {}).get('risk_level', 'UNKNOWN'),
            'recommendation_count': len(validation_analysis.get('recommendations', [])),
            'next_steps': self._generate_next_steps(validation_analysis)
        }
    
    def _generate_next_steps(self, analysis: dict) -> list:
        """Generate next steps based on analysis"""
        
        next_steps = []
        
        overall_score = analysis.get('overall_assessment', {}).get('overall_score', 0.0)
        
        if overall_score >= 0.8:
            next_steps.append('Continue monitoring and maintain current performance levels')
            next_steps.append('Consider advanced optimization for edge cases')
        elif overall_score >= 0.6:
            next_steps.append('Implement medium-priority recommendations')
            next_steps.append('Focus on weakest performing components')
        else:
            next_steps.append('Address all high-priority recommendations immediately')
            next_steps.append('Conduct detailed component-level analysis')
            next_steps.append('Consider system architecture review')
        
        risk_level = analysis.get('risk_assessment', {}).get('risk_level', 'UNKNOWN')
        if risk_level in ['CRITICAL', 'HIGH']:
            next_steps.insert(0, 'Address critical risk issues before production deployment')
        
        return next_steps
    
    async def _save_validation_results(self, results: dict) -> None:
        """Save validation results to file"""
        
        try:
            # Save detailed results as JSON
            results_file = f"phase3_market_condition_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            self.logger.info(f"💾 Validation results saved to {results_file}")
            
            # Save summary report
            summary_file = f"phase3_validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(summary_file, 'w') as f:
                f.write("Phase 3: Market Condition Validation Summary\n")
                f.write("=" * 50 + "\n\n")
                
                summary = results.get('summary', {})
                f.write(f"Overall Grade: {summary.get('overall_grade', 'N/A')}\n")
                f.write(f"Overall Score: {summary.get('overall_score', 0.0):.3f}\n")
                f.write(f"Conditions Tested: {summary.get('conditions_tested', 0)}\n")
                f.write(f"Success Rate: {summary.get('success_rate', 0.0):.1%}\n")
                f.write(f"Risk Level: {summary.get('risk_level', 'UNKNOWN')}\n")
                f.write(f"Validation Duration: {results.get('validation_duration_seconds', 0):.2f}s\n\n")
                
                # Next steps
                next_steps = summary.get('next_steps', [])
                if next_steps:
                    f.write("Next Steps:\n")
                    for i, step in enumerate(next_steps, 1):
                        f.write(f"{i}. {step}\n")
            
            self.logger.info(f"📄 Summary report saved to {summary_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save validation results: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        
        try:
            if self.integration_manager:
                await self.integration_manager.stop()
            self.logger.info("🧹 Cleanup completed")
        except Exception as e:
            self.logger.error(f"❌ Cleanup failed: {e}")


async def main():
    """Main execution function"""
    
    print("🎯 Phase 3: Core Engine Market Condition Validation")
    print("=" * 60)
    
    validator = CoreEngineMarketConditionValidator()
    
    try:
        # Run comprehensive market condition validation
        results = await validator.run_market_condition_validation()
        
        # Display results summary
        print("\n📊 VALIDATION RESULTS SUMMARY")
        print("-" * 40)
        
        if results['status'] == 'completed':
            summary = results.get('summary', {})
            print(f"✅ Status: {results['status'].upper()}")
            print(f"📈 Overall Grade: {summary.get('overall_grade', 'N/A')}")
            print(f"🎯 Overall Score: {summary.get('overall_score', 0.0):.3f}")
            print(f"🧪 Conditions Tested: {summary.get('conditions_tested', 0)}")
            print(f"✅ Success Rate: {summary.get('success_rate', 0.0):.1%}")
            print(f"⚠️  Risk Level: {summary.get('risk_level', 'UNKNOWN')}")
            print(f"⏱️  Duration: {results.get('validation_duration_seconds', 0):.2f}s")
            
            # Display next steps
            next_steps = summary.get('next_steps', [])
            if next_steps:
                print(f"\n🎯 NEXT STEPS:")
                for i, step in enumerate(next_steps, 1):
                    print(f"   {i}. {step}")
        else:
            print(f"❌ Status: {results['status'].upper()}")
            if 'error' in results:
                print(f"❌ Error: {results['error']}")
        
        print(f"\n📁 Detailed results saved to validation files")
        print("🏁 Phase 3 Market Condition Validation completed")
        
        return results
        
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        return {'status': 'interrupted'}
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        return {'status': 'failed', 'error': str(e)}
        
    finally:
        await validator.cleanup()


if __name__ == "__main__":
    # Run the validation
    asyncio.run(main())
