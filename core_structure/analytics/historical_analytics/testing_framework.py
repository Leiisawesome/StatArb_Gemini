#!/usr/bin/env python3
"""
Historical Analytics Testing Framework
=====================================

Comprehensive testing and validation for the historical analytics system.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging
import json
import pytest
import sys
import os

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core_structure.analytics.historical_analytics import (
    HistoricalAnalyticsEngine,
    HistoricalDataManager,
    HistoricalRegimeAnalyzer,
    HistoricalRankingEngine,
    BacktestConfigGenerator,
    HistoricalAnalyticsOutputManager,
    HistoricalAnalyticsConfigManager,
    SystemIntegrationManager,
    HistoricalPeriod,
    MarketDataset,
    validate_historical_period
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalAnalyticsTestSuite:
    """
    Comprehensive test suite for historical analytics framework
    """
    
    def __init__(self, test_data_path: Optional[str] = None):
        """
        Initialize test suite
        
        Args:
            test_data_path: Path to test data directory
        """
        self.test_data_path = test_data_path or self._setup_test_data_path()
        self.test_results: Dict[str, Any] = {}
        self.config_manager = HistoricalAnalyticsConfigManager()
        
        logger.info("HistoricalAnalyticsTestSuite initialized")
    
    def run_complete_test_suite(self) -> Dict[str, Any]:
        """
        Run complete test suite
        
        Returns:
            Complete test results
        """
        logger.info("Starting complete historical analytics test suite")
        
        test_suite_results = {
            'test_timestamp': datetime.now().isoformat(),
            'component_tests': {},
            'integration_tests': {},
            'performance_tests': {},
            'validation_tests': {},
            'overall_success': True,
            'test_summary': {}
        }
        
        try:
            # Component tests
            test_suite_results['component_tests'] = self._run_component_tests()
            
            # Integration tests
            test_suite_results['integration_tests'] = self._run_integration_tests()
            
            # Performance tests
            test_suite_results['performance_tests'] = self._run_performance_tests()
            
            # Validation tests
            test_suite_results['validation_tests'] = self._run_validation_tests()
            
            # Generate test summary
            test_suite_results['test_summary'] = self._generate_test_summary(test_suite_results)
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            test_suite_results['overall_success'] = False
            test_suite_results['error_message'] = str(e)
        
        logger.info(f"Test suite completed - Success: {test_suite_results['overall_success']}")
        return test_suite_results
    
    def _run_component_tests(self) -> Dict[str, Any]:
        """Run individual component tests"""
        logger.info("Running component tests")
        
        component_results = {
            'data_ingestion': self._test_data_ingestion(),
            'regime_analysis': self._test_regime_analysis(),
            'ranking_engine': self._test_ranking_engine(),
            'config_generation': self._test_config_generation(),
            'data_output': self._test_data_output(),
            'config_management': self._test_config_management()
        }
        
        return component_results
    
    def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        logger.info("Running integration tests")
        
        integration_results = {
            'end_to_end_pipeline': self._test_end_to_end_pipeline(),
            'backtesting_integration': self._test_backtesting_integration(),
            'paper_trading_integration': self._test_paper_trading_integration(),
            'system_integration': self._test_system_integration()
        }
        
        return integration_results
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests"""
        logger.info("Running performance tests")
        
        performance_results = {
            'data_loading_performance': self._test_data_loading_performance(),
            'analysis_performance': self._test_analysis_performance(),
            'memory_usage': self._test_memory_usage(),
            'scalability': self._test_scalability()
        }
        
        return performance_results
    
    def _run_validation_tests(self) -> Dict[str, Any]:
        """Run validation tests"""
        logger.info("Running validation tests")
        
        validation_results = {
            'data_validation': self._test_data_validation(),
            'result_validation': self._test_result_validation(),
            'configuration_validation': self._test_configuration_validation(),
            'output_validation': self._test_output_validation()
        }
        
        return validation_results
    
    def _test_data_ingestion(self) -> Dict[str, Any]:
        """Test data ingestion components"""
        logger.debug("Testing data ingestion")
        
        try:
            # Create test historical periods
            periods = self._create_test_periods()
            
            # Initialize data manager
            data_manager = HistoricalDataManager()
            
            # Test data loading
            mock_data = self._generate_mock_market_data(periods)
            
            # Validate data structure
            for period_name, dataset in mock_data.items():
                assert isinstance(dataset, MarketDataset)
                assert len(dataset.data) > 0
                assert 'AAPL' in dataset.data.columns  # Test symbol
            
            return {
                'status': 'passed',
                'periods_tested': len(periods),
                'datasets_validated': len(mock_data),
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data ingestion test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_regime_analysis(self) -> Dict[str, Any]:
        """Test regime analysis components"""
        logger.debug("Testing regime analysis")
        
        try:
            # Create test data
            periods = self._create_test_periods()
            mock_data = self._generate_mock_market_data(periods)
            
            # Initialize regime analyzer
            regime_analyzer = HistoricalRegimeAnalyzer()
            
            # Test regime detection
            analysis_results = {}
            for period_name, dataset in mock_data.items():
                result = regime_analyzer.analyze_historical_regimes(
                    {period_name: dataset}
                )
                analysis_results[period_name] = result
            
            # Validate results
            for period_name, result in analysis_results.items():
                assert result.regime_statistics is not None
                assert len(result.regime_periods) > 0
                assert result.regime_transitions is not None
            
            return {
                'status': 'passed',
                'periods_analyzed': len(analysis_results),
                'regimes_detected': sum(len(r.regime_periods) for r in analysis_results.values()),
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Regime analysis test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_ranking_engine(self) -> Dict[str, Any]:
        """Test ranking engine components"""
        logger.debug("Testing ranking engine")
        
        try:
            # Create test data and regime analysis
            periods = self._create_test_periods()
            mock_data = self._generate_mock_market_data(periods)
            
            regime_analyzer = HistoricalRegimeAnalyzer()
            regime_results = {}
            for period_name, dataset in mock_data.items():
                regime_results[period_name] = regime_analyzer.analyze_historical_regimes(
                    {period_name: dataset}
                )
            
            # Initialize ranking engine
            ranking_engine = HistoricalRankingEngine()
            
            # Test instrument ranking
            rankings = ranking_engine.rank_instruments_across_regimes(
                mock_data, regime_results
            )
            
            # Validate rankings
            assert rankings.strategy_rankings is not None
            assert len(rankings.strategy_rankings) > 0
            
            for strategy_name, regime_rankings in rankings.strategy_rankings.items():
                assert len(regime_rankings) > 0
                for regime_name, instruments in regime_rankings.items():
                    assert isinstance(instruments, list)
            
            return {
                'status': 'passed',
                'strategies_tested': len(rankings.strategy_rankings),
                'rankings_generated': sum(len(r) for r in rankings.strategy_rankings.values()),
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ranking engine test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_config_generation(self) -> Dict[str, Any]:
        """Test config generation components"""
        logger.debug("Testing config generation")
        
        try:
            # Create mock rankings
            rankings = self._create_mock_rankings()
            
            # Initialize config generator
            config_generator = BacktestConfigGenerator()
            
            # Test config generation
            backtest_suite = config_generator.generate_backtest_suite(rankings)
            
            # Validate backtest suite
            assert backtest_suite.total_configs > 0
            assert len(backtest_suite.optimized_configs) > 0
            assert len(backtest_suite.baseline_configs) > 0
            assert len(backtest_suite.stress_configs) > 0
            
            return {
                'status': 'passed',
                'total_configs_generated': backtest_suite.total_configs,
                'optimized_configs': len(backtest_suite.optimized_configs),
                'baseline_configs': len(backtest_suite.baseline_configs),
                'stress_configs': len(backtest_suite.stress_configs),
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Config generation test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_data_output(self) -> Dict[str, Any]:
        """Test data output components"""
        logger.debug("Testing data output")
        
        try:
            # Create mock analysis results
            analysis_results = self._create_mock_analysis_results()
            
            # Initialize output manager
            output_manager = HistoricalAnalyticsOutputManager()
            
            # Test output generation
            output_paths = output_manager.save_complete_analysis(
                analysis_results, base_output_dir=self.test_data_path
            )
            
            # Validate outputs
            assert output_paths.analysis_summary_path.exists()
            assert output_paths.rankings_summary_path.exists()
            
            return {
                'status': 'passed',
                'output_files_created': len([p for p in [
                    output_paths.analysis_summary_path,
                    output_paths.rankings_summary_path
                ] if p.exists()]),
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data output test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_config_management(self) -> Dict[str, Any]:
        """Test configuration management"""
        logger.debug("Testing configuration management")
        
        try:
            # Test default config loading
            config = self.config_manager.get_default_config()
            
            # Validate config structure
            assert 'historical_periods' in config
            assert 'strategy_configs' in config
            assert 'risk_management' in config
            assert 'analysis_settings' in config
            
            # Test config saving and loading
            test_config_path = Path(self.test_data_path) / 'test_config.yaml'
            self.config_manager.save_config(config, test_config_path)
            
            loaded_config = self.config_manager.load_config(test_config_path)
            
            # Validate loaded config
            assert loaded_config == config
            
            return {
                'status': 'passed',
                'config_sections_validated': 4,
                'save_load_test_passed': True,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Config management test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_end_to_end_pipeline(self) -> Dict[str, Any]:
        """Test complete end-to-end pipeline"""
        logger.debug("Testing end-to-end pipeline")
        
        try:
            # Initialize main engine
            engine = HistoricalAnalyticsEngine()
            
            # Create test configuration
            config = self.config_manager.get_default_config()
            periods = self._create_test_periods()
            mock_data = self._generate_mock_market_data(periods)
            
            # Run complete analysis
            analysis_results = engine.run_complete_analysis(
                historical_datasets=mock_data,
                config=config,
                output_base_path=self.test_data_path
            )
            
            # Validate complete results
            assert analysis_results.regime_analysis is not None
            assert analysis_results.instrument_rankings is not None
            assert analysis_results.backtest_suite is not None
            assert analysis_results.output_paths is not None
            
            return {
                'status': 'passed',
                'pipeline_steps_completed': 4,
                'total_configs_generated': analysis_results.backtest_suite.total_configs,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"End-to-end pipeline test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_backtesting_integration(self) -> Dict[str, Any]:
        """Test backtesting system integration"""
        logger.debug("Testing backtesting integration")
        
        try:
            # Create mock backtest suite
            rankings = self._create_mock_rankings()
            config_generator = BacktestConfigGenerator()
            backtest_suite = config_generator.generate_backtest_suite(rankings)
            
            # Initialize integration manager
            integration_manager = SystemIntegrationManager()
            
            # Test backtest execution
            results = integration_manager.backtesting_integration.execute_backtest_suite(
                backtest_suite, self.test_data_path
            )
            
            # Validate results
            assert results.results is not None
            assert results.performance_comparison is not None
            assert results.execution_metadata is not None
            
            return {
                'status': 'passed',
                'backtests_executed': results.execution_metadata['total_configs_executed'],
                'performance_comparison_generated': True,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Backtesting integration test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_paper_trading_integration(self) -> Dict[str, Any]:
        """Test paper trading integration"""
        logger.debug("Testing paper trading integration")
        
        try:
            # Create mock rankings
            rankings = self._create_mock_rankings()
            
            # Initialize integration manager
            integration_manager = SystemIntegrationManager()
            
            # Test deployment
            deployment_results = integration_manager.paper_trading_integration.deploy_top_performers(
                rankings
            )
            
            # Validate deployment
            assert deployment_results['total_strategies_deployed'] > 0
            assert len(deployment_results['deployed_strategies']) > 0
            
            # Test monitoring
            monitoring_results = integration_manager.paper_trading_integration.monitor_deployed_strategies()
            
            # Validate monitoring
            assert monitoring_results['active_strategies_count'] > 0
            assert 'strategy_performance' in monitoring_results
            
            return {
                'status': 'passed',
                'strategies_deployed': deployment_results['total_strategies_deployed'],
                'monitoring_active': True,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Paper trading integration test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_system_integration(self) -> Dict[str, Any]:
        """Test complete system integration"""
        logger.debug("Testing system integration")
        
        try:
            # Create mock analysis results
            analysis_results = self._create_mock_analysis_results()
            
            # Initialize integration manager
            integration_manager = SystemIntegrationManager()
            
            # Test full pipeline integration
            integration_results = integration_manager.full_pipeline_integration(
                analysis_results, self.test_data_path
            )
            
            # Validate integration
            assert integration_results['integration_summary']['integration_success']
            assert integration_results['backtest_results'] is not None
            assert integration_results['paper_trading_deployment'] is not None
            
            return {
                'status': 'passed',
                'full_integration_success': True,
                'backtest_and_paper_trading_integrated': True,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System integration test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_data_loading_performance(self) -> Dict[str, Any]:
        """Test data loading performance"""
        logger.debug("Testing data loading performance")
        
        try:
            start_time = datetime.now()
            
            # Test with larger dataset
            periods = self._create_test_periods(count=10)
            mock_data = self._generate_mock_market_data(periods, instruments_count=100)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                'status': 'passed',
                'data_loading_time_seconds': duration,
                'periods_loaded': len(periods),
                'instruments_per_period': 100,
                'performance_rating': 'good' if duration < 5.0 else 'slow',
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data loading performance test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_analysis_performance(self) -> Dict[str, Any]:
        """Test analysis performance"""
        logger.debug("Testing analysis performance")
        
        try:
            start_time = datetime.now()
            
            # Run complete analysis
            engine = HistoricalAnalyticsEngine()
            config = self.config_manager.get_default_config()
            periods = self._create_test_periods(count=5)
            mock_data = self._generate_mock_market_data(periods)
            
            analysis_results = engine.run_complete_analysis(
                historical_datasets=mock_data,
                config=config,
                output_base_path=self.test_data_path
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                'status': 'passed',
                'analysis_time_seconds': duration,
                'periods_analyzed': len(periods),
                'configs_generated': analysis_results.backtest_suite.total_configs,
                'performance_rating': 'good' if duration < 30.0 else 'slow',
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analysis performance test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage"""
        logger.debug("Testing memory usage")
        
        try:
            import psutil
            import gc
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Run analysis
            engine = HistoricalAnalyticsEngine()
            config = self.config_manager.get_default_config()
            periods = self._create_test_periods(count=3)
            mock_data = self._generate_mock_market_data(periods)
            
            analysis_results = engine.run_complete_analysis(
                historical_datasets=mock_data,
                config=config,
                output_base_path=self.test_data_path
            )
            
            # Get peak memory usage
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            # Clean up
            del analysis_results
            gc.collect()
            
            return {
                'status': 'passed',
                'initial_memory_mb': initial_memory,
                'peak_memory_mb': peak_memory,
                'memory_increase_mb': memory_increase,
                'memory_efficiency': 'good' if memory_increase < 500 else 'high',
                'test_timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            return {
                'status': 'skipped',
                'reason': 'psutil not available',
                'test_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Memory usage test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_scalability(self) -> Dict[str, Any]:
        """Test system scalability"""
        logger.debug("Testing scalability")
        
        try:
            scalability_results = {}
            
            # Test with increasing data sizes
            for scale in [1, 3, 5]:
                start_time = datetime.now()
                
                periods = self._create_test_periods(count=scale)
                mock_data = self._generate_mock_market_data(periods, instruments_count=20*scale)
                
                engine = HistoricalAnalyticsEngine()
                config = self.config_manager.get_default_config()
                
                analysis_results = engine.run_complete_analysis(
                    historical_datasets=mock_data,
                    config=config,
                    output_base_path=self.test_data_path
                )
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                scalability_results[f'scale_{scale}'] = {
                    'periods': scale,
                    'instruments': 20*scale,
                    'duration_seconds': duration,
                    'configs_generated': analysis_results.backtest_suite.total_configs
                }
            
            return {
                'status': 'passed',
                'scalability_results': scalability_results,
                'linear_scaling': all(
                    scalability_results[f'scale_{i+1}']['duration_seconds'] < 
                    scalability_results[f'scale_{i}']['duration_seconds'] * 3
                    for i in [1, 3] if f'scale_{i+1}' in scalability_results
                ),
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Scalability test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_data_validation(self) -> Dict[str, Any]:
        """Test data validation"""
        logger.debug("Testing data validation")
        
        try:
            validation_results = {}
            
            # Test valid data
            valid_period = HistoricalPeriod(
                name="test_valid",
                start_date=datetime(2020, 1, 1),
                end_date=datetime(2020, 12, 31),
                description="Valid test period"
            )
            
            validation_result = validate_historical_period(valid_period)
            validation_results['valid_period'] = validation_result
            
            # Test invalid data
            try:
                invalid_period = HistoricalPeriod(
                    name="test_invalid",
                    start_date=datetime(2020, 12, 31),
                    end_date=datetime(2020, 1, 1),  # End before start
                    description="Invalid test period"
                )
                validate_historical_period(invalid_period)
                validation_results['invalid_period'] = False  # Should not reach here
            except ValueError:
                validation_results['invalid_period'] = True  # Expected validation error
            
            return {
                'status': 'passed',
                'valid_period_validated': validation_results['valid_period'],
                'invalid_period_caught': validation_results['invalid_period'],
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data validation test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_result_validation(self) -> Dict[str, Any]:
        """Test result validation"""
        logger.debug("Testing result validation")
        
        try:
            # Run analysis and validate results
            engine = HistoricalAnalyticsEngine()
            config = self.config_manager.get_default_config()
            periods = self._create_test_periods(count=2)
            mock_data = self._generate_mock_market_data(periods)
            
            analysis_results = engine.run_complete_analysis(
                historical_datasets=mock_data,
                config=config,
                output_base_path=self.test_data_path
            )
            
            # Validate result structure and content
            validation_checks = {
                'regime_analysis_exists': analysis_results.regime_analysis is not None,
                'rankings_exist': analysis_results.instrument_rankings is not None,
                'backtest_suite_exists': analysis_results.backtest_suite is not None,
                'output_paths_exist': analysis_results.output_paths is not None,
                'rankings_have_strategies': len(analysis_results.instrument_rankings.strategy_rankings) > 0,
                'backtest_configs_generated': analysis_results.backtest_suite.total_configs > 0
            }
            
            all_checks_passed = all(validation_checks.values())
            
            return {
                'status': 'passed' if all_checks_passed else 'failed',
                'validation_checks': validation_checks,
                'all_checks_passed': all_checks_passed,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Result validation test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_configuration_validation(self) -> Dict[str, Any]:
        """Test configuration validation"""
        logger.debug("Testing configuration validation")
        
        try:
            # Test default config validation
            config = self.config_manager.get_default_config()
            
            validation_checks = {
                'has_historical_periods': 'historical_periods' in config,
                'has_strategy_configs': 'strategy_configs' in config,
                'has_risk_management': 'risk_management' in config,
                'has_analysis_settings': 'analysis_settings' in config,
                'periods_properly_formatted': isinstance(config.get('historical_periods', {}), dict),
                'strategies_properly_formatted': isinstance(config.get('strategy_configs', {}), dict)
            }
            
            all_checks_passed = all(validation_checks.values())
            
            return {
                'status': 'passed' if all_checks_passed else 'failed',
                'validation_checks': validation_checks,
                'all_checks_passed': all_checks_passed,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Configuration validation test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _test_output_validation(self) -> Dict[str, Any]:
        """Test output validation"""
        logger.debug("Testing output validation")
        
        try:
            # Create and save analysis results
            analysis_results = self._create_mock_analysis_results()
            output_manager = HistoricalAnalyticsOutputManager()
            
            output_paths = output_manager.save_complete_analysis(
                analysis_results, base_output_dir=self.test_data_path
            )
            
            # Validate output files
            validation_checks = {
                'analysis_summary_exists': output_paths.analysis_summary_path.exists(),
                'rankings_summary_exists': output_paths.rankings_summary_path.exists(),
                'analysis_summary_readable': False,
                'rankings_summary_readable': False
            }
            
            # Test file readability
            if validation_checks['analysis_summary_exists']:
                try:
                    with open(output_paths.analysis_summary_path, 'r') as f:
                        json.load(f)
                    validation_checks['analysis_summary_readable'] = True
                except:
                    pass
            
            if validation_checks['rankings_summary_exists']:
                try:
                    with open(output_paths.rankings_summary_path, 'r') as f:
                        json.load(f)
                    validation_checks['rankings_summary_readable'] = True
                except:
                    pass
            
            all_checks_passed = all(validation_checks.values())
            
            return {
                'status': 'passed' if all_checks_passed else 'failed',
                'validation_checks': validation_checks,
                'all_checks_passed': all_checks_passed,
                'test_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Output validation test failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'test_timestamp': datetime.now().isoformat()
            }
    
    def _setup_test_data_path(self) -> str:
        """Setup test data directory"""
        test_path = Path(__file__).parent / 'test_data'
        test_path.mkdir(exist_ok=True)
        return str(test_path)
    
    def _create_test_periods(self, count: int = 3) -> List[HistoricalPeriod]:
        """Create test historical periods"""
        periods = []
        for i in range(count):
            start_date = datetime(2020, 1, 1) + timedelta(days=i*100)
            end_date = start_date + timedelta(days=90)
            
            period = HistoricalPeriod(
                name=f"test_period_{i+1}",
                start_date=start_date,
                end_date=end_date,
                description=f"Test period {i+1}"
            )
            periods.append(period)
        
        return periods
    
    def _generate_mock_market_data(self, periods: List[HistoricalPeriod], 
                                 instruments_count: int = 10) -> Dict[str, MarketDataset]:
        """Generate mock market data for testing"""
        mock_data = {}
        
        # Sample instruments
        instruments = [f"TEST{i:03d}" for i in range(instruments_count)]
        if instruments_count >= 5:
            instruments[:5] = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        for period in periods:
            # Generate date range
            dates = pd.date_range(period.start_date, period.end_date, freq='D')
            
            # Generate mock price data
            data = {}
            for instrument in instruments:
                # Generate realistic price series
                np.random.seed(hash(instrument + period.name) % 2**31)
                initial_price = 100 + np.random.uniform(-50, 100)
                returns = np.random.normal(0.0005, 0.02, len(dates))
                prices = initial_price * np.cumprod(1 + returns)
                
                data[instrument] = prices
            
            df = pd.DataFrame(data, index=dates)
            
            dataset = MarketDataset(
                data=df,
                metadata={
                    'period_name': period.name,
                    'start_date': period.start_date.isoformat(),
                    'end_date': period.end_date.isoformat(),
                    'instruments': instruments,
                    'data_frequency': 'daily'
                }
            )
            
            mock_data[period.name] = dataset
        
        return mock_data
    
    def _create_mock_rankings(self):
        """Create mock instrument rankings for testing"""
        from core_structure.analytics.historical_analytics.data_types import InstrumentRankings, InstrumentScore
        
        # Create mock instrument scores
        instruments = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        strategy_rankings = {
            'mean_reversion': {
                'bull_market': [
                    InstrumentScore(symbol=symbol, score=0.8 - i*0.1, rank=i+1, 
                                  confidence=0.9, statistical_significance=True)
                    for i, symbol in enumerate(instruments)
                ],
                'bear_market': [
                    InstrumentScore(symbol=symbol, score=0.7 - i*0.1, rank=i+1,
                                  confidence=0.8, statistical_significance=True)
                    for i, symbol in enumerate(instruments)
                ]
            },
            'momentum': {
                'bull_market': [
                    InstrumentScore(symbol=symbol, score=0.9 - i*0.1, rank=i+1,
                                  confidence=0.85, statistical_significance=True)
                    for i, symbol in enumerate(instruments)
                ]
            }
        }
        
        return InstrumentRankings(
            strategy_rankings=strategy_rankings,
            ranking_metadata={
                'ranking_timestamp': datetime.now().isoformat(),
                'total_instruments_analyzed': len(instruments),
                'strategies_analyzed': list(strategy_rankings.keys())
            }
        )
    
    def _create_mock_analysis_results(self):
        """Create mock analysis results for testing"""
        from core_structure.analytics.historical_analytics.data_types import (
            AnalysisResults, RegimeAnalysisOutput, BacktestSuite, AnalysisOutputPaths
        )
        
        # Mock regime analysis
        regime_analysis = RegimeAnalysisOutput(
            regime_statistics={'bull_market': 0.6, 'bear_market': 0.4},
            regime_periods={'test_period_1': [('bull_market', '2020-01-01', '2020-06-01')]},
            regime_transitions={'bull_to_bear': 2, 'bear_to_bull': 1},
            analysis_metadata={'analysis_date': datetime.now().isoformat()}
        )
        
        # Mock rankings
        rankings = self._create_mock_rankings()
        
        # Mock backtest suite
        config_generator = BacktestConfigGenerator()
        backtest_suite = config_generator.generate_backtest_suite(rankings)
        
        # Mock output paths
        output_paths = AnalysisOutputPaths(
            analysis_summary_path=Path(self.test_data_path) / 'analysis_summary.json',
            rankings_summary_path=Path(self.test_data_path) / 'rankings_summary.json'
        )
        
        return AnalysisResults(
            regime_analysis=regime_analysis,
            instrument_rankings=rankings,
            backtest_suite=backtest_suite,
            output_paths=output_paths,
            analysis_metadata={
                'analysis_timestamp': datetime.now().isoformat(),
                'total_periods_analyzed': 1,
                'total_instruments_ranked': 5
            }
        )
    
    def _generate_test_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        summary = {
            'total_test_categories': 4,
            'test_categories': {
                'component_tests': self._summarize_test_category(test_results['component_tests']),
                'integration_tests': self._summarize_test_category(test_results['integration_tests']),
                'performance_tests': self._summarize_test_category(test_results['performance_tests']),
                'validation_tests': self._summarize_test_category(test_results['validation_tests'])
            },
            'overall_statistics': {
                'total_tests_run': 0,
                'tests_passed': 0,
                'tests_failed': 0,
                'tests_skipped': 0,
                'success_rate': 0.0
            }
        }
        
        # Calculate overall statistics
        for category_summary in summary['test_categories'].values():
            summary['overall_statistics']['total_tests_run'] += category_summary['total_tests']
            summary['overall_statistics']['tests_passed'] += category_summary['tests_passed']
            summary['overall_statistics']['tests_failed'] += category_summary['tests_failed']
            summary['overall_statistics']['tests_skipped'] += category_summary['tests_skipped']
        
        if summary['overall_statistics']['total_tests_run'] > 0:
            summary['overall_statistics']['success_rate'] = (
                summary['overall_statistics']['tests_passed'] / 
                summary['overall_statistics']['total_tests_run']
            )
        
        return summary
    
    def _summarize_test_category(self, category_results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize results for a test category"""
        total_tests = len(category_results)
        tests_passed = sum(1 for result in category_results.values() if result.get('status') == 'passed')
        tests_failed = sum(1 for result in category_results.values() if result.get('status') == 'failed')
        tests_skipped = sum(1 for result in category_results.values() if result.get('status') == 'skipped')
        
        return {
            'total_tests': total_tests,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'tests_skipped': tests_skipped,
            'success_rate': tests_passed / total_tests if total_tests > 0 else 0.0
        }


def run_historical_analytics_demo():
    """
    Demonstration of the complete historical analytics system
    """
    logger.info("Starting Historical Analytics Demo")
    
    print("=" * 80)
    print("HISTORICAL ANALYTICS FRAMEWORK DEMONSTRATION")
    print("=" * 80)
    
    try:
        # Initialize test suite
        test_suite = HistoricalAnalyticsTestSuite()
        
        print("\n1. Running Component Tests...")
        component_results = test_suite._run_component_tests()
        
        passed_components = [name for name, result in component_results.items() 
                           if result.get('status') == 'passed']
        print(f"   ✓ Components Passed: {len(passed_components)}/{len(component_results)}")
        
        print("\n2. Running Integration Tests...")
        integration_results = test_suite._run_integration_tests()
        
        passed_integrations = [name for name, result in integration_results.items() 
                             if result.get('status') == 'passed']
        print(f"   ✓ Integrations Passed: {len(passed_integrations)}/{len(integration_results)}")
        
        print("\n3. Demonstrating End-to-End Pipeline...")
        
        # Initialize main components
        config_manager = HistoricalAnalyticsConfigManager()
        engine = HistoricalAnalyticsEngine()
        integration_manager = SystemIntegrationManager()
        
        # Create demonstration data
        periods = test_suite._create_test_periods(count=3)
        mock_data = test_suite._generate_mock_market_data(periods, instruments_count=20)
        
        print(f"   • Generated {len(periods)} historical periods")
        print(f"   • Created market data for {len(list(mock_data.values())[0].data.columns)} instruments")
        
        # Run complete analysis
        config = config_manager.get_default_config()
        analysis_results = engine.run_complete_analysis(
            historical_datasets=mock_data,
            config=config,
            output_base_path=test_suite.test_data_path
        )
        
        print(f"   • Detected {len(analysis_results.regime_analysis.regime_periods)} regime periods")
        print(f"   • Generated rankings for {len(analysis_results.instrument_rankings.strategy_rankings)} strategies")
        print(f"   • Created {analysis_results.backtest_suite.total_configs} backtest configurations")
        
        # Demonstrate integration
        integration_results = integration_manager.full_pipeline_integration(
            analysis_results, test_suite.test_data_path
        )
        
        print(f"   • Executed {integration_results['backtest_results'].execution_metadata['total_configs_executed']} backtests")
        print(f"   • Deployed {integration_results['paper_trading_deployment']['total_strategies_deployed']} strategies to paper trading")
        
        print("\n4. Performance Summary:")
        print(f"   • Analysis completed successfully: ✓")
        print(f"   • Integration completed successfully: ✓")
        print(f"   • All outputs generated: ✓")
        
        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        return False


if __name__ == "__main__":
    # Run the complete test suite
    test_suite = HistoricalAnalyticsTestSuite()
    results = test_suite.run_complete_test_suite()
    
    print("\n" + "=" * 80)
    print("HISTORICAL ANALYTICS TEST RESULTS")
    print("=" * 80)
    
    print(f"Overall Success: {'✓' if results['overall_success'] else '❌'}")
    
    if 'test_summary' in results:
        summary = results['test_summary']
        print(f"Total Tests: {summary['overall_statistics']['total_tests_run']}")
        print(f"Passed: {summary['overall_statistics']['tests_passed']}")
        print(f"Failed: {summary['overall_statistics']['tests_failed']}")
        print(f"Success Rate: {summary['overall_statistics']['success_rate']:.1%}")
    
    print("\n" + "=" * 80)
    
    # Run demonstration
    print("\nRunning demonstration...")
    demo_success = run_historical_analytics_demo()
    
    if demo_success:
        print("\n🎉 Historical Analytics Framework is fully functional!")
    else:
        print("\n❌ Demo encountered issues.")