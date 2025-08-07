#!/usr/bin/env python3
"""
System Integration Framework
Phase 3: Advanced Analytics & Optimization - Batch 5
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class SystemIntegrator:
    """System integration framework for the complete trading system"""
    
    def __init__(self):
        self.integration_results = {}
        self.system_components = {}
        self.performance_metrics = {}
        
        logger.info("Initialized SystemIntegrator")
    
    def integrate_machine_learning_components(self, data: pd.DataFrame,
                                           strategy_config: Dict) -> Dict:
        """Integrate machine learning components"""
        
        try:
            logger.info("Integrating machine learning components...")
            
            # Import ML components
            from backtesting_framework.ml.model_registry import ModelRegistry
            # Feature engineering moved to core_structure/signal_generation/feature_engine.py
# from backtesting_framework.ml.feature_engineering import FeatureEngineer
            from backtesting_framework.ml.training_pipeline import TrainingPipeline
            
            # Initialize components
            model_registry = ModelRegistry()
            feature_engineer = FeatureEngineer()
            training_pipeline = TrainingPipeline()
            
            # Generate features
            features = feature_engineer.generate_features(data)
            logger.info(f"Generated {len(features.columns)} features")
            
            # Train models
            training_results = training_pipeline.train_models(features, strategy_config)
            logger.info(f"Trained {len(training_results)} models")
            
            # Register models
            for model_name, model in training_results.items():
                model_registry.register_model(model_name, model)
            
            # Store components
            self.system_components['ml'] = {
                'model_registry': model_registry,
                'feature_engineer': feature_engineer,
                'training_pipeline': training_pipeline,
                'features': features,
                'training_results': training_results
            }
            
            integration_result = {
                'ml_components': list(training_results.keys()),
                'feature_count': len(features.columns),
                'model_count': len(training_results),
                'integration_status': 'success'
            }
            
            logger.info("Machine learning components integrated successfully")
            return integration_result
            
        except Exception as e:
            logger.error(f"ML integration failed: {e}")
            return {'integration_status': 'failed', 'error': str(e)}
    
    def integrate_analytics_components(self, data: pd.DataFrame,
                                    analytics_config: Dict) -> Dict:
        """Integrate analytics components"""
        
        try:
            logger.info("Integrating analytics components...")
            
            # Import analytics components
            from backtesting_framework.analytics.statistical_analyzer import StatisticalAnalyzer
            from backtesting_framework.analytics.regime_detector import RegimeDetector
            from backtesting_framework.analytics.factor_analyzer import FactorAnalyzer
            from backtesting_framework.analytics.volatility_analyzer import VolatilityAnalyzer
            from backtesting_framework.analytics.sentiment_analyzer import SentimentAnalyzer
            
            # Initialize components
            statistical_analyzer = StatisticalAnalyzer()
            regime_detector = RegimeDetector()
            factor_analyzer = FactorAnalyzer()
            volatility_analyzer = VolatilityAnalyzer()
            sentiment_analyzer = SentimentAnalyzer()
            
            # Run analytics
            statistical_results = statistical_analyzer.analyze_data(data)
            regime_results = regime_detector.detect_regimes(data)
            factor_results = factor_analyzer.analyze_factors(data)
            volatility_results = volatility_analyzer.analyze_volatility(data)
            sentiment_results = sentiment_analyzer.analyze_sentiment(data)
            
            # Store components
            self.system_components['analytics'] = {
                'statistical_analyzer': statistical_analyzer,
                'regime_detector': regime_detector,
                'factor_analyzer': factor_analyzer,
                'volatility_analyzer': volatility_analyzer,
                'sentiment_analyzer': sentiment_analyzer,
                'statistical_results': statistical_results,
                'regime_results': regime_results,
                'factor_results': factor_results,
                'volatility_results': volatility_results,
                'sentiment_results': sentiment_results
            }
            
            integration_result = {
                'analytics_components': ['statistical', 'regime', 'factor', 'volatility', 'sentiment'],
                'regime_count': len(regime_results.get('regimes', [])),
                'factor_count': len(factor_results.get('factors', [])),
                'integration_status': 'success'
            }
            
            logger.info("Analytics components integrated successfully")
            return integration_result
            
        except Exception as e:
            logger.error(f"Analytics integration failed: {e}")
            return {'integration_status': 'failed', 'error': str(e)}
    
    def integrate_optimization_components(self, data: pd.DataFrame,
                                       optimization_config: Dict) -> Dict:
        """Integrate optimization components"""
        
        try:
            logger.info("Integrating optimization components...")
            
            # Import optimization components
            from backtesting_framework.optimization import (
                MPTOptimizer, RiskParity, BlackLitterman, 
                DynamicAllocation, FactorOptimizer
            )
            
            # Initialize components
            mpt_optimizer = MPTOptimizer()
            risk_parity = RiskParity()
            black_litterman = BlackLitterman()
            dynamic_allocation = DynamicAllocation()
            factor_optimizer = FactorOptimizer()
            
            # Calculate returns and covariance
            returns = data.pct_change().dropna()
            expected_returns = returns.mean() * 252
            covariance_matrix = returns.cov() * 252
            
            # Run optimizations
            mpt_results = mpt_optimizer.optimize_portfolio(expected_returns, covariance_matrix)
            rp_results = risk_parity.calculate_risk_parity_weights(covariance_matrix)
            
            # Store components
            self.system_components['optimization'] = {
                'mpt_optimizer': mpt_optimizer,
                'risk_parity': risk_parity,
                'black_litterman': black_litterman,
                'dynamic_allocation': dynamic_allocation,
                'factor_optimizer': factor_optimizer,
                'mpt_results': mpt_results,
                'rp_results': rp_results,
                'expected_returns': expected_returns,
                'covariance_matrix': covariance_matrix
            }
            
            integration_result = {
                'optimization_components': ['mpt', 'risk_parity', 'black_litterman', 'dynamic_allocation', 'factor_optimizer'],
                'mpt_portfolios': len(mpt_results.get('optimal_portfolios', {})),
                'rp_portfolio': rp_results.get('portfolio_volatility', 0),
                'integration_status': 'success'
            }
            
            logger.info("Optimization components integrated successfully")
            return integration_result
            
        except Exception as e:
            logger.error(f"Optimization integration failed: {e}")
            return {'integration_status': 'failed', 'error': str(e)}
    
    def integrate_backtesting_components(self, data: pd.DataFrame,
                                      backtesting_config: Dict) -> Dict:
        """Integrate enhanced backtesting components"""
        
        try:
            logger.info("Integrating enhanced backtesting components...")
            
            # Import backtesting components
            from backtesting_framework.enhanced_backtesting import (
                WalkForwardAnalyzer, MonteCarloSimulator, StressTester,
                ScenarioAnalyzer, PerformanceAttribution
            )
            
            # Initialize components
            walk_forward = WalkForwardAnalyzer()
            monte_carlo = MonteCarloSimulator()
            stress_tester = StressTester()
            scenario_analyzer = ScenarioAnalyzer()
            performance_attribution = PerformanceAttribution()
            
            # Run backtesting analyses
            def mock_strategy(data, params):
                return params
            
            wf_results = walk_forward.run_walk_forward_analysis(
                data, mock_strategy, {'param1': 0.1}, train_window=252, test_window=63
            )
            
            returns_series = data.pct_change().dropna().iloc[:, 0]
            mc_results = monte_carlo.run_monte_carlo_simulation(returns_series, n_simulations=50)
            
            # Store components
            self.system_components['backtesting'] = {
                'walk_forward': walk_forward,
                'monte_carlo': monte_carlo,
                'stress_tester': stress_tester,
                'scenario_analyzer': scenario_analyzer,
                'performance_attribution': performance_attribution,
                'wf_results': wf_results,
                'mc_results': mc_results
            }
            
            integration_result = {
                'backtesting_components': ['walk_forward', 'monte_carlo', 'stress_tester', 'scenario_analyzer', 'performance_attribution'],
                'wf_periods': wf_results.get('n_periods', 0),
                'mc_simulations': mc_results.get('simulation_parameters', {}).get('n_simulations', 0),
                'integration_status': 'success'
            }
            
            logger.info("Enhanced backtesting components integrated successfully")
            return integration_result
            
        except Exception as e:
            logger.error(f"Backtesting integration failed: {e}")
            return {'integration_status': 'failed', 'error': str(e)}
    
    def run_full_system_integration(self, data: pd.DataFrame,
                                  config: Dict) -> Dict:
        """Run full system integration"""
        
        try:
            logger.info("Starting full system integration...")
            
            integration_results = {}
            
            # Integrate all components
            ml_result = self.integrate_machine_learning_components(data, config.get('ml', {}))
            analytics_result = self.integrate_analytics_components(data, config.get('analytics', {}))
            optimization_result = self.integrate_optimization_components(data, config.get('optimization', {}))
            backtesting_result = self.integrate_backtesting_components(data, config.get('backtesting', {}))
            
            integration_results = {
                'ml_integration': ml_result,
                'analytics_integration': analytics_result,
                'optimization_integration': optimization_result,
                'backtesting_integration': backtesting_result,
                'integration_date': datetime.now().isoformat()
            }
            
            # Calculate overall integration success
            success_count = sum(1 for result in integration_results.values() 
                              if isinstance(result, dict) and result.get('integration_status') == 'success')
            total_components = len([k for k in integration_results.keys() if k.endswith('_integration')])
            
            overall_status = 'success' if success_count == total_components else 'partial'
            
            integration_results['overall_status'] = overall_status
            integration_results['success_rate'] = success_count / total_components if total_components > 0 else 0
            
            # Store results
            integration_id = f"system_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.integration_results[integration_id] = integration_results
            
            logger.info(f"Full system integration completed: {overall_status} ({success_count}/{total_components} components)")
            return integration_results
            
        except Exception as e:
            logger.error(f"Full system integration failed: {e}")
            return {'overall_status': 'failed', 'error': str(e)}
    
    def get_system_summary(self) -> Dict:
        """Get system integration summary"""
        return {
            'total_integrations': len(self.integration_results),
            'component_count': len(self.system_components),
            'available_integrations': list(self.integration_results.keys()),
            'component_types': list(self.system_components.keys())
        }
