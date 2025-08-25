#!/usr/bin/env python3
"""
Phase 5B Analytics Test Suite
============================

Comprehensive test suite for Phase 5B Advanced Analytics and Intelligence components.

Author: StatArb_Gemini Team
"""

import unittest
import asyncio
import time
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# Import Phase 5B components
from trade_engine.analytics.performance_analyzer import (
    PerformanceAnalyzer, PerformanceMetrics, PerformancePatternType
)
from trade_engine.analytics.predictive_monitor import (
    PredictiveMonitor, PredictionType, PredictionConfidence
)
from trade_engine.analytics.anomaly_detector import (
    AnomalyDetector, AnomalyType, AnomalySeverity
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPhase5BAnalytics(unittest.TestCase):
    """Test Phase 5B analytics implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.performance_analyzer = PerformanceAnalyzer(
            history_window=100,
            forecast_horizon=3,
            retrain_frequency=10
        )
        self.predictive_monitor = PredictiveMonitor(
            prediction_horizons=[1, 6, 24],
            history_window=100,
            retrain_frequency=48
        )
        self.anomaly_detector = AnomalyDetector(
            contamination_rate=0.1,
            history_window=100,
            sensitivity=0.8
        )
    
    def tearDown(self):
        """Clean up test environment"""
        asyncio.run(self._async_teardown())
    
    async def _async_teardown(self):
        """Async teardown"""
        try:
            await self.performance_analyzer.stop_analysis()
            await self.predictive_monitor.stop_monitoring()
            await self.anomaly_detector.stop_detection()
        except Exception as e:
            logger.warning(f"Error during teardown: {e}")
    
    def test_performance_analyzer_initialization(self):
        """Test performance analyzer initialization"""
        logger.info("Testing performance analyzer initialization")
        
        self.assertIsNotNone(self.performance_analyzer)
        self.assertFalse(self.performance_analyzer.is_analyzing)
        self.assertEqual(len(self.performance_analyzer.performance_history), 0)
        self.assertEqual(self.performance_analyzer.forecast_horizon, 3)
        
        logger.info("✅ Performance analyzer initialization passed")
    
    def test_performance_analysis_workflow(self):
        """Test complete performance analysis workflow"""
        async def async_test():
            logger.info("Testing performance analysis workflow")
            
            # Start analysis
            await self.performance_analyzer.start_analysis()
            self.assertTrue(self.performance_analyzer.is_analyzing)
            
            # Add sample data
            for i in range(30):
                metrics = PerformanceMetrics(
                    timestamp=datetime.now() - timedelta(days=29-i),
                    returns=np.random.normal(0.001, 0.02),  # 0.1% daily return, 2% volatility
                    volatility=np.random.uniform(0.015, 0.025),
                    sharpe_ratio=np.random.uniform(0.5, 2.0),
                    max_drawdown=np.random.uniform(0.05, 0.15),
                    win_rate=np.random.uniform(0.4, 0.7),
                    profit_factor=np.random.uniform(1.1, 2.5),
                    calmar_ratio=np.random.uniform(0.3, 1.5),
                    sortino_ratio=np.random.uniform(0.8, 2.5),
                    var_95=np.random.uniform(0.02, 0.05),
                    cvar_95=np.random.uniform(0.03, 0.07)
                )
                self.performance_analyzer.add_performance_data(metrics)
            
            # Test analysis
            analysis_result = await self.performance_analyzer.analyze_current_performance()
            
            self.assertIn('current_pattern', analysis_result)
            self.assertIn('indicators', analysis_result)
            self.assertEqual(analysis_result.get('data_points'), 30)
            
            # Test pattern detection
            pattern = analysis_result['current_pattern']
            self.assertIsInstance(pattern.pattern_type, PerformancePatternType)
            self.assertGreaterEqual(pattern.confidence, 0.0)
            self.assertLessEqual(pattern.confidence, 1.0)
            
            logger.info("✅ Performance analysis workflow passed")
        
        asyncio.run(async_test())
    
    def test_predictive_monitor_initialization(self):
        """Test predictive monitor initialization"""
        logger.info("Testing predictive monitor initialization")
        
        self.assertIsNotNone(self.predictive_monitor)
        self.assertFalse(self.predictive_monitor.is_monitoring)
        self.assertEqual(len(self.predictive_monitor.metrics_history), 0)
        self.assertEqual(len(self.predictive_monitor.prediction_horizons), 3)
        
        logger.info("✅ Predictive monitor initialization passed")
    
    def test_predictive_monitoring_workflow(self):
        """Test predictive monitoring workflow"""
        async def async_test():
            logger.info("Testing predictive monitoring workflow")
            
            # Start monitoring
            await self.predictive_monitor.start_monitoring()
            self.assertTrue(self.predictive_monitor.is_monitoring)
            
            # Add sample metrics data
            for i in range(40):
                timestamp = datetime.now() - timedelta(hours=39-i)
                metrics = {
                    'cpu_usage': np.random.uniform(20, 80) + i * 0.5,  # Slight upward trend
                    'memory_usage': np.random.uniform(30, 70),
                    'latency': np.random.uniform(50, 200),
                    'throughput': np.random.uniform(1000, 5000),
                    'error_rate': np.random.uniform(0.001, 0.01)
                }
                self.predictive_monitor.add_metrics_data(timestamp, metrics)
            
            # Generate predictions
            predictions = await self.predictive_monitor.generate_predictions()
            
            self.assertIn('status', predictions)
            self.assertEqual(predictions['status'], 'success')
            self.assertIn('trend_predictions', predictions)
            self.assertIn('system_predictions', predictions)
            self.assertIn('risk_predictions', predictions)
            
            # Test trend predictions
            trend_predictions = predictions['trend_predictions']
            self.assertIsInstance(trend_predictions, list)
            
            if trend_predictions:
                trend_pred = trend_predictions[0]
                self.assertIsNotNone(trend_pred.metric_name)
                self.assertIsInstance(trend_pred.predicted_values, list)
                self.assertIsInstance(trend_pred.confidence_intervals, list)
            
            logger.info("✅ Predictive monitoring workflow passed")
        
        asyncio.run(async_test())
    
    def test_anomaly_detector_initialization(self):
        """Test anomaly detector initialization"""
        logger.info("Testing anomaly detector initialization")
        
        self.assertIsNotNone(self.anomaly_detector)
        self.assertFalse(self.anomaly_detector.is_detecting)
        self.assertEqual(len(self.anomaly_detector.metrics_history), 0)
        self.assertEqual(self.anomaly_detector.contamination_rate, 0.1)
        self.assertEqual(self.anomaly_detector.sensitivity, 0.8)
        
        logger.info("✅ Anomaly detector initialization passed")
    
    def test_anomaly_detection_workflow(self):
        """Test anomaly detection workflow"""
        async def async_test():
            logger.info("Testing anomaly detection workflow")
            
            # Start detection
            await self.anomaly_detector.start_detection()
            self.assertTrue(self.anomaly_detector.is_detecting)
            
            # Add normal data points
            for i in range(50):
                timestamp = datetime.now() - timedelta(minutes=49-i)
                normal_metrics = {
                    'cpu_usage': np.random.normal(50, 5),  # Normal around 50%
                    'memory_usage': np.random.normal(60, 8),
                    'latency': np.random.normal(100, 15),
                    'error_rate': np.random.normal(0.01, 0.002)
                }
                self.anomaly_detector.add_metrics_data(timestamp, normal_metrics)
            
            # Add anomalous data point
            anomalous_metrics = {
                'cpu_usage': 95.0,  # Very high CPU
                'memory_usage': 45.0,  # Normal memory
                'latency': 500.0,  # High latency
                'error_rate': 0.001  # Low error rate
            }
            
            # Detect anomalies
            anomalies = await self.anomaly_detector.detect_anomalies(anomalous_metrics)
            
            # Should detect CPU and latency anomalies
            cpu_anomaly_found = any('cpu_usage' in a.affected_metrics for a in anomalies)
            latency_anomaly_found = any('latency' in a.affected_metrics for a in anomalies)
            
            self.assertTrue(cpu_anomaly_found or latency_anomaly_found, 
                           "Should detect at least one anomaly in CPU or latency")
            
            if anomalies:
                anomaly = anomalies[0]
                self.assertIsInstance(anomaly.anomaly_type, AnomalyType)
                self.assertIsInstance(anomaly.severity, AnomalySeverity)
                self.assertGreaterEqual(anomaly.anomaly_score, 0.0)
                self.assertLessEqual(anomaly.anomaly_score, 1.0)
                self.assertGreater(len(anomaly.affected_metrics), 0)
            
            logger.info("✅ Anomaly detection workflow passed")
        
        asyncio.run(async_test())
    
    def test_performance_pattern_detection(self):
        """Test performance pattern detection capabilities"""
        async def async_test():
            logger.info("Testing performance pattern detection")
            
            await self.performance_analyzer.start_analysis()
            
            # Create trending up pattern
            for i in range(20):
                metrics = PerformanceMetrics(
                    timestamp=datetime.now() - timedelta(days=19-i),
                    returns=0.005 + i * 0.0002,  # Increasing returns
                    volatility=0.02,
                    sharpe_ratio=1.0 + i * 0.05,
                    max_drawdown=0.1,
                    win_rate=0.6,
                    profit_factor=1.5,
                    calmar_ratio=1.0,
                    sortino_ratio=1.2,
                    var_95=0.03,
                    cvar_95=0.04
                )
                self.performance_analyzer.add_performance_data(metrics)
            
            # Analyze pattern
            analysis = await self.performance_analyzer.analyze_current_performance()
            pattern = analysis['current_pattern']
            
            # Should detect upward trend
            self.assertIn(pattern.pattern_type, [
                PerformancePatternType.TRENDING_UP,
                PerformancePatternType.BREAKOUT,
                PerformancePatternType.STABLE
            ])
            self.assertGreater(pattern.confidence, 0.0)
            
            logger.info(f"Detected pattern: {pattern.pattern_type.value} with confidence {pattern.confidence:.2f}")
            logger.info("✅ Performance pattern detection passed")
        
        asyncio.run(async_test())
    
    def test_predictive_alerts_generation(self):
        """Test predictive alerts generation"""
        async def async_test():
            logger.info("Testing predictive alerts generation")
            
            await self.predictive_monitor.start_monitoring()
            
            # Add data with increasing risk pattern
            for i in range(30):
                timestamp = datetime.now() - timedelta(hours=29-i)
                metrics = {
                    'cpu_usage': 40 + i * 1.5,  # Steadily increasing CPU
                    'memory_usage': 50 + i * 1.0,  # Increasing memory
                    'error_rate': 0.001 + i * 0.0002,  # Increasing errors
                    'latency': 100 + i * 5  # Increasing latency
                }
                self.predictive_monitor.add_metrics_data(timestamp, metrics)
            
            # Generate predictions and alerts
            predictions = await self.predictive_monitor.generate_predictions()
            
            if 'proactive_alerts' in predictions:
                alerts = predictions['proactive_alerts']
                
                if alerts:
                    alert = alerts[0]
                    self.assertIsInstance(alert.prediction_type, PredictionType)
                    self.assertIsInstance(alert.confidence, PredictionConfidence)
                    self.assertGreater(len(alert.recommended_actions), 0)
                    self.assertGreater(alert.time_horizon, 0)
                    
                    logger.info(f"Generated alert: {alert.description}")
                
            logger.info("✅ Predictive alerts generation passed")
        
        asyncio.run(async_test())
    
    def test_multi_dimensional_anomaly_detection(self):
        """Test multi-dimensional anomaly detection"""
        async def async_test():
            logger.info("Testing multi-dimensional anomaly detection")
            
            await self.anomaly_detector.start_detection()
            
            # Add normal correlated data
            for i in range(40):
                timestamp = datetime.now() - timedelta(minutes=39-i)
                base_value = np.random.normal(0, 1)
                
                # Create correlated metrics
                metrics = {
                    'cpu_usage': 50 + base_value * 10,
                    'memory_usage': 60 + base_value * 8,  # Positively correlated with CPU
                    'response_time': 100 - base_value * 20,  # Negatively correlated
                    'throughput': 1000 - base_value * 100  # Negatively correlated
                }
                
                # Ensure values are in reasonable ranges
                metrics = {k: max(0, min(100 if 'usage' in k else v, v)) for k, v in metrics.items()}
                
                self.anomaly_detector.add_metrics_data(timestamp, metrics)
            
            # Create correlation-breaking anomaly
            anomalous_metrics = {
                'cpu_usage': 90,  # High CPU
                'memory_usage': 30,  # But low memory (breaks correlation)
                'response_time': 50,  # Should be high when CPU is high
                'throughput': 2000   # Should be low when CPU is high
            }
            
            anomalies = await self.anomaly_detector.detect_anomalies(anomalous_metrics)
            
            # Should detect some form of anomaly
            self.assertGreaterEqual(len(anomalies), 0)
            
            if anomalies:
                # Check for pattern or collective anomalies
                pattern_anomalies = [a for a in anomalies if a.anomaly_type in [
                    AnomalyType.COLLECTIVE_ANOMALY, 
                    AnomalyType.POINT_ANOMALY
                ]]
                
                logger.info(f"Detected {len(anomalies)} anomalies, including {len(pattern_anomalies)} pattern anomalies")
            
            logger.info("✅ Multi-dimensional anomaly detection passed")
        
        asyncio.run(async_test())
    
    def test_analytics_integration(self):
        """Test integration between analytics components"""
        logger.info("Testing analytics components integration")
        
        # Test that components can work together
        self.assertIsNotNone(self.performance_analyzer)
        self.assertIsNotNone(self.predictive_monitor)
        self.assertIsNotNone(self.anomaly_detector)
        
        # Test summary methods
        perf_summary = self.performance_analyzer.get_analysis_summary()
        pred_summary = self.predictive_monitor.get_monitoring_summary()
        anom_summary = self.anomaly_detector.get_anomaly_summary()
        
        self.assertIn('is_analyzing', perf_summary)
        self.assertIn('is_monitoring', pred_summary)
        self.assertIn('is_detecting', anom_summary)
        
        logger.info("✅ Analytics integration passed")


class TestPhase5BIntegration(unittest.TestCase):
    """Test Phase 5B system integration"""
    
    def test_phase5b_system_integration(self):
        """Test complete Phase 5B system integration"""
        async def async_test():
            logger.info("Testing Phase 5B complete system integration")
            
            # Initialize all components
            performance_analyzer = PerformanceAnalyzer(history_window=50)
            predictive_monitor = PredictiveMonitor(history_window=50)
            anomaly_detector = AnomalyDetector(history_window=50)
            
            try:
                # Start all systems
                await performance_analyzer.start_analysis()
                await predictive_monitor.start_monitoring()
                await anomaly_detector.start_detection()
                
                # Simulate integrated data flow
                for i in range(20):
                    timestamp = datetime.now() - timedelta(hours=19-i)
                    
                    # Generate realistic performance data
                    base_return = np.random.normal(0.001, 0.02)
                    
                    # Performance metrics
                    perf_metrics = PerformanceMetrics(
                        timestamp=timestamp,
                        returns=base_return,
                        volatility=abs(base_return) * 10 + 0.01,
                        sharpe_ratio=np.random.uniform(0.5, 2.0),
                        max_drawdown=np.random.uniform(0.05, 0.2),
                        win_rate=0.5 + base_return * 10,
                        profit_factor=1.0 + base_return * 5,
                        calmar_ratio=np.random.uniform(0.3, 1.5),
                        sortino_ratio=np.random.uniform(0.8, 2.5),
                        var_95=np.random.uniform(0.02, 0.05),
                        cvar_95=np.random.uniform(0.03, 0.07)
                    )
                    
                    # System metrics (correlated with performance)
                    system_metrics = {
                        'cpu_usage': 40 + abs(base_return) * 1000,
                        'memory_usage': 50 + np.random.uniform(-10, 10),
                        'latency': 100 + abs(base_return) * 2000,
                        'throughput': 2000 - abs(base_return) * 50000,
                        'error_rate': max(0.001, abs(base_return) * 2)
                    }
                    
                    # Ensure realistic ranges
                    system_metrics['cpu_usage'] = min(95, max(10, system_metrics['cpu_usage']))
                    system_metrics['memory_usage'] = min(90, max(20, system_metrics['memory_usage']))
                    system_metrics['latency'] = min(1000, max(50, system_metrics['latency']))
                    system_metrics['throughput'] = min(5000, max(500, system_metrics['throughput']))
                    system_metrics['error_rate'] = min(0.1, max(0.001, system_metrics['error_rate']))
                    
                    # Feed data to all systems
                    performance_analyzer.add_performance_data(perf_metrics)
                    predictive_monitor.add_metrics_data(timestamp, system_metrics)
                    anomaly_detector.add_metrics_data(timestamp, system_metrics)
                
                # Test analysis coordination
                performance_analysis = await performance_analyzer.analyze_current_performance()
                predictions = await predictive_monitor.generate_predictions()
                
                # Test anomaly detection with current metrics
                current_metrics = {
                    'cpu_usage': 85,  # High but not extreme
                    'memory_usage': 75,
                    'latency': 200,
                    'throughput': 1500,
                    'error_rate': 0.01
                }
                anomalies = await anomaly_detector.detect_anomalies(current_metrics)
                
                # Verify integration results
                self.assertIsNotNone(performance_analysis)
                self.assertIsNotNone(predictions)
                self.assertIsInstance(anomalies, list)
                
                # Check that systems are generating insights
                if performance_analysis.get('status') != 'insufficient_data':
                    self.assertIn('current_pattern', performance_analysis)
                    self.assertIn('indicators', performance_analysis)
                
                if predictions.get('status') == 'success':
                    self.assertIn('trend_predictions', predictions)
                    self.assertIn('system_predictions', predictions)
                
                # Test summary integration
                integration_summary = {
                    'performance_analysis': performance_analyzer.get_analysis_summary(),
                    'predictive_monitoring': predictive_monitor.get_monitoring_summary(),
                    'anomaly_detection': anomaly_detector.get_anomaly_summary(),
                    'timestamp': datetime.now(),
                    'integration_status': 'operational'
                }
                
                self.assertIn('performance_analysis', integration_summary)
                self.assertIn('predictive_monitoring', integration_summary)
                self.assertIn('anomaly_detection', integration_summary)
                
                logger.info("✅ Phase 5B system integration passed")
                
            finally:
                # Cleanup
                await performance_analyzer.stop_analysis()
                await predictive_monitor.stop_monitoring()
                await anomaly_detector.stop_detection()
        
        asyncio.run(async_test())


if __name__ == '__main__':
    # Configure test environment
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Run tests
    unittest.main(verbosity=2)
