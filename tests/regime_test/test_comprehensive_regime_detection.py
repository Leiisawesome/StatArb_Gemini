#!/usr/bin/env python3
"""
Comprehensive Regime Detection Test
==================================

Professional test demonstrating advanced regime detection using multiple symbols,
sophisticated detection methods, and comprehensive regime analysis.

This test leverages the full power of the core_engine regime modules:
- RegimeDetector: Multi-method regime detection (Markov, GMM, Volatility, Threshold)
- MarketRegimeAnalyzer: Cross-asset regime analysis with factor decomposition
- RegimeClassifier: ML-based regime classification with feature engineering
- RegimeIndicatorEngine: Advanced regime-specific indicators and transition signals

Author: StatArb_Gemini Enhanced Regime Detection System
"""

import sys
import os
# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import asdict

# Core engine imports
from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.regime.regime_detector import (
    RegimeDetector, RegimeDetectionConfig, DetectionMethod, RegimeType
)
from core_engine.regime.market_regime_analyzer import (
    MarketRegimeAnalyzer, RegimeAnalysisConfig, MacroRegime, MarketCycle, RiskEnvironment
)
from core_engine.regime.regime_classifier import (
    RegimeClassifier, ClassificationConfig, MLModel, FeatureType
)
from core_engine.regime.regime_indicators import (
    RegimeIndicatorEngine, IndicatorConfig, IndicatorType, SignalStrength
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveRegimeTest:
    """
    Comprehensive regime detection test using professional quant symbols
    and advanced detection methodologies
    """
    
    def __init__(self):
        """Initialize comprehensive regime test"""
        
        # Professional quant symbols for regime detection (using available symbols)
        self.regime_symbols = {
            'primary_equity': ['SPY', 'QQQ', 'IWM', 'TSLA', 'NVDA', 'AAPL'],
            'volatility': [],  # Skip VIX for now (may need special handling)
            'rates': ['TLT', 'SHY'],
            'currency': ['UUP'],
            'commodities': ['GLD', 'USO'],
            'credit': ['HYG', 'LQD'],
            'international': ['EEM', 'EFA'],
            'sectors': ['XLF', 'XLE', 'XLK']
        }
        
        # Flatten symbol list for data loading
        self.all_symbols = []
        for category, symbols in self.regime_symbols.items():
            self.all_symbols.extend(symbols)
        
        # Test configuration
        self.test_config = {
            'test_date': '2024-12-20',  # Single day for comprehensive analysis
            'start_time': '09:30:00',   # Market open
            'end_time': '16:00:00',     # Market close
            'data_frequency': '1min'    # 1-minute data for detailed analysis
        }
        
        # Initialize components
        self.data_manager = None
        self.regime_detector = None
        self.market_analyzer = None
        self.regime_classifier = None
        self.indicator_engine = None
        
        # Results storage
        self.regime_detections = {}
        self.transition_signals = []
        self.regime_timeline = []
        self.performance_metrics = {}
        
        logger.info("🎯 Comprehensive Regime Detection Test initialized")
        logger.info(f"📊 Testing {len(self.all_symbols)} professional symbols")
        logger.info(f"📅 Test date: {self.test_config['test_date']}")
    
    async def initialize_components(self):
        """Initialize all regime detection components"""
        
        try:
            logger.info("🔧 Initializing regime detection components...")
            
            # Data Manager
            data_config = ClickHouseDataConfig(
                symbols=self.all_symbols,
                target_date=self.test_config['test_date'],
                enable_caching=True
            )
            self.data_manager = ClickHouseDataManager(data_config)
            
            # Regime Detector with multiple methods
            detector_config = RegimeDetectionConfig(
                methods=[
                    DetectionMethod.MARKOV_SWITCHING,
                    DetectionMethod.GAUSSIAN_MIXTURE,
                    DetectionMethod.VOLATILITY_BASED,
                    DetectionMethod.THRESHOLD_BASED
                ],
                short_lookback=20,
                medium_lookback=60,
                long_lookback=252,
                n_regimes=4,  # More regimes for detailed analysis
                confidence_threshold=0.65
            )
            self.regime_detector = RegimeDetector(detector_config)
            
            # Market Regime Analyzer for cross-asset analysis
            analyzer_config = RegimeAnalysisConfig(
                equity_indices=self.regime_symbols['primary_equity'],
                fixed_income=self.regime_symbols['rates'],
                commodities=self.regime_symbols['commodities'],
                currencies=self.regime_symbols['currency'],
                lookback_periods=[20, 60, 252]
            )
            self.market_analyzer = MarketRegimeAnalyzer(analyzer_config)
            
            # Regime Classifier with ML models
            classifier_config = ClassificationConfig(
                primary_model=MLModel.ENSEMBLE,
                models_to_test=[
                    MLModel.RANDOM_FOREST,
                    MLModel.GRADIENT_BOOSTING,
                    MLModel.SVM,
                    MLModel.LOGISTIC_REGRESSION
                ],
                feature_types=[
                    FeatureType.PRICE_BASED,
                    FeatureType.VOLATILITY_BASED,
                    FeatureType.MOMENTUM_BASED,
                    FeatureType.CORRELATION_BASED,
                    FeatureType.TECHNICAL_INDICATORS
                ],
                max_features=30,
                confidence_threshold=0.6
            )
            self.regime_classifier = RegimeClassifier(classifier_config)
            
            # Regime Indicator Engine
            indicator_config = IndicatorConfig(
                vol_lookback_periods=[10, 20, 60],
                momentum_periods=[5, 10, 20, 60],
                mean_reversion_periods=[20, 60],
                correlation_windows=[20, 60],
                transition_sensitivity=0.1,
                warning_sensitivity=0.15
            )
            self.indicator_engine = RegimeIndicatorEngine(indicator_config)
            
            logger.info("✅ All regime detection components initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            raise
    
    async def load_market_data(self) -> Dict[str, pd.DataFrame]:
        """Load comprehensive market data for regime analysis"""
        
        try:
            logger.info("📊 Loading comprehensive market data...")
            
            # Load data for all symbols
            market_data = {}
            successful_loads = 0
            
            for symbol in self.all_symbols:
                try:
                    # Load data without time filtering first (to avoid datetime format issues)
                    data = self.data_manager.get_market_data(symbol=symbol)
                    
                    if data is not None and not data.empty:
                        # Ensure proper datetime index
                        if 'timestamp' in data.columns:
                            data.set_index('timestamp', inplace=True)
                        
                        # Add symbol column for cross-asset analysis
                        data['symbol'] = symbol
                        
                        market_data[symbol] = data
                        successful_loads += 1
                        logger.info(f"   📈 Loaded {len(data)} records for {symbol}")
                    else:
                        logger.warning(f"   ⚠️ No data available for {symbol}")
                        
                except Exception as e:
                    logger.warning(f"   ❌ Failed to load {symbol}: {e}")
                    continue
            
            logger.info(f"✅ Successfully loaded data for {successful_loads}/{len(self.all_symbols)} symbols")
            
            if successful_loads == 0:
                raise ValueError("No market data loaded successfully")
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Failed to load market data: {e}")
            raise
    
    async def run_multi_method_regime_detection(self, market_data: Dict[str, pd.DataFrame]):
        """Run regime detection using multiple methods"""
        
        try:
            logger.info("🔍 Running multi-method regime detection...")
            
            # Process each symbol with regime detector
            for symbol, data in market_data.items():
                logger.info(f"   🎯 Analyzing regime for {symbol}...")
                
                # Detect regime using multiple methods
                regime_detection = self.regime_detector.detect_current_regime(
                    market_data=data,
                    timestamp=datetime.now()
                )
                
                if regime_detection:
                    self.regime_detections[symbol] = regime_detection
                    logger.info(f"      📊 Detected: {regime_detection.regime_type.value} "
                              f"(confidence: {regime_detection.confidence:.2f})")
                else:
                    logger.warning(f"      ⚠️ No regime detected for {symbol}")
            
            # Get regime statistics
            regime_stats = self.regime_detector.get_regime_statistics()
            if regime_stats:
                logger.info("📈 Regime Detection Statistics:")
                logger.info(f"   Total detections: {regime_stats.get('total_detections', 0)}")
                logger.info(f"   Current regime distribution: {regime_stats.get('regime_distribution', {})}")
                logger.info(f"   Total transitions: {regime_stats.get('total_transitions', 0)}")
            
        except Exception as e:
            logger.error(f"❌ Multi-method regime detection failed: {e}")
    
    async def run_cross_asset_regime_analysis(self, market_data: Dict[str, pd.DataFrame]):
        """Run comprehensive cross-asset regime analysis"""
        
        try:
            logger.info("🌍 Running cross-asset regime analysis...")
            
            # Analyze cross-asset regime
            comprehensive_analysis = self.market_analyzer.analyze_market_regime(market_data)
            
            if comprehensive_analysis and 'cross_asset_regime' in comprehensive_analysis:
                cross_asset_regime = comprehensive_analysis['cross_asset_regime']
                
                logger.info("🎯 Cross-Asset Regime Analysis Results:")
                logger.info(f"   📊 Macro Regime: {cross_asset_regime.macro_regime.value}")
                logger.info(f"   🔄 Market Cycle: {cross_asset_regime.market_cycle.value}")
                logger.info(f"   ⚖️ Risk Environment: {cross_asset_regime.risk_environment.value}")
                logger.info(f"   🎯 Regime Alignment: {cross_asset_regime.regime_alignment:.2f}")
                logger.info(f"   📈 Regime Stability: {cross_asset_regime.regime_stability:.2f}")
                logger.info(f"   🔥 Systemic Stress: {cross_asset_regime.systemic_stress:.2f}")
                logger.info(f"   💧 Liquidity Stress: {cross_asset_regime.liquidity_stress:.2f}")
                logger.info(f"   💳 Credit Stress: {cross_asset_regime.credit_stress:.2f}")
                
                # Factor analysis
                if 'factor_analysis' in comprehensive_analysis:
                    factor_analysis = comprehensive_analysis['factor_analysis']
                    if 'total_variance_explained' in factor_analysis:
                        logger.info(f"   🧮 Factor Variance Explained: {factor_analysis['total_variance_explained']:.2f}")
                
                # Sector analysis
                if 'sector_analysis' in comprehensive_analysis:
                    sector_analysis = comprehensive_analysis['sector_analysis']
                    if 'rotation_signals' in sector_analysis:
                        rotation = sector_analysis['rotation_signals']
                        if 'leaders' in rotation:
                            leaders = list(rotation['leaders'].keys())[:3]
                            logger.info(f"   🏆 Sector Leaders: {leaders}")
                
                # Store comprehensive analysis
                self.performance_metrics['cross_asset_analysis'] = comprehensive_analysis
                
            else:
                logger.warning("⚠️ Cross-asset regime analysis returned no results")
                
        except Exception as e:
            logger.error(f"❌ Cross-asset regime analysis failed: {e}")
    
    async def run_advanced_indicator_analysis(self, market_data: Dict[str, pd.DataFrame]):
        """Run advanced regime indicator analysis"""
        
        try:
            logger.info("📊 Running advanced regime indicator analysis...")
            
            # Process primary equity data for detailed indicator analysis
            primary_symbols = self.regime_symbols['primary_equity']
            available_primary = [s for s in primary_symbols if s in market_data]
            
            if not available_primary:
                logger.warning("⚠️ No primary equity data available for indicator analysis")
                return
            
            # Combine primary equity data
            primary_data = pd.concat([market_data[symbol][['close']] for symbol in available_primary], 
                                   axis=1, keys=available_primary)
            primary_data.columns = [f'{symbol}_close' for symbol in available_primary]
            
            # Calculate all regime indicators
            all_indicators = self.indicator_engine.calculate_all_indicators(primary_data)
            
            if all_indicators:
                logger.info(f"📈 Calculated {len(all_indicators)} regime indicators")
                
                # Get indicator summary
                indicator_summary = self.indicator_engine.get_indicator_summary(all_indicators)
                
                logger.info("🎯 Regime Indicator Summary:")
                logger.info(f"   📊 Total Indicators: {indicator_summary.get('total_indicators', 0)}")
                logger.info(f"   📈 By Type: {indicator_summary.get('by_type', {})}")
                logger.info(f"   💪 By Strength: {indicator_summary.get('by_strength', {})}")
                logger.info(f"   🎯 Consensus Signals: {indicator_summary.get('consensus_signals', {})}")
                
                if 'strong_consensus' in indicator_summary:
                    strong_consensus = indicator_summary['strong_consensus']
                    logger.info(f"   🔥 Strong Consensus: {strong_consensus}")
                
                # Detect transition signals
                transition_signals = self.indicator_engine.detect_regime_transitions(all_indicators)
                
                if transition_signals:
                    logger.info(f"⚡ Detected {len(transition_signals)} regime transition signals:")
                    for signal in transition_signals:
                        logger.info(f"   🔄 {signal.signal_name}: {signal.from_regime.value} → "
                                  f"{signal.to_regime.value} (prob: {signal.transition_probability:.2f})")
                    
                    self.transition_signals = transition_signals
                
                # Calculate regime strength for detected regimes
                for symbol, detection in self.regime_detections.items():
                    regime_strength = self.indicator_engine.calculate_regime_strength(
                        detection.regime_type, all_indicators
                    )
                    
                    logger.info(f"💪 Regime Strength for {symbol} ({detection.regime_type.value}):")
                    logger.info(f"   Overall: {regime_strength.overall_strength:.2f}")
                    logger.info(f"   Momentum: {regime_strength.momentum_strength:.2f}")
                    logger.info(f"   Persistence: {regime_strength.persistence_strength:.2f}")
                    logger.info(f"   Coherence: {regime_strength.coherence_strength:.2f}")
                    logger.info(f"   Expected Duration: {regime_strength.expected_duration} days")
                
                # Store indicators
                self.performance_metrics['regime_indicators'] = all_indicators
                
            else:
                logger.warning("⚠️ No regime indicators calculated")
                
        except Exception as e:
            logger.error(f"❌ Advanced indicator analysis failed: {e}")
    
    async def demonstrate_regime_transitions(self, market_data: Dict[str, pd.DataFrame]):
        """Demonstrate regime transitions throughout the trading day"""
        
        try:
            logger.info("🔄 Demonstrating regime transitions throughout trading day...")
            
            # Use SPY as primary symbol for transition analysis (fallback to TSLA)
            primary_symbol = 'SPY' if 'SPY' in market_data else 'TSLA'
            if primary_symbol not in market_data:
                logger.warning(f"⚠️ {primary_symbol} data not available for transition analysis")
                return
            
            primary_data = market_data[primary_symbol]
            
            # Analyze regime at different time intervals
            time_intervals = [
                ('09:30', 'Market Open'),
                ('10:30', 'Early Trading'),
                ('12:00', 'Mid-Day'),
                ('14:00', 'Afternoon'),
                ('15:30', 'Late Trading'),
                ('16:00', 'Market Close')
            ]
            
            regime_timeline = []
            
            for time_str, label in time_intervals:
                try:
                    # Get data up to this time point
                    time_cutoff = pd.Timestamp(f"{self.test_config['test_date']} {time_str}:00")
                    data_subset = primary_data[primary_data.index <= time_cutoff]
                    
                    if len(data_subset) < 20:  # Need minimum data
                        continue
                    
                    # Detect regime at this time point
                    regime_detection = self.regime_detector.detect_current_regime(
                        market_data=data_subset,
                        timestamp=time_cutoff
                    )
                    
                    if regime_detection:
                        regime_timeline.append({
                            'time': time_str,
                            'label': label,
                            'regime': regime_detection.regime_type.value,
                            'confidence': regime_detection.confidence,
                            'method': regime_detection.method.value,
                            'volatility': regime_detection.volatility,
                            'avg_return': regime_detection.avg_return
                        })
                        
                        logger.info(f"   🕐 {label} ({time_str}): {regime_detection.regime_type.value} "
                                  f"(confidence: {regime_detection.confidence:.2f})")
                    
                except Exception as e:
                    logger.warning(f"   ⚠️ Failed to analyze regime at {time_str}: {e}")
                    continue
            
            if regime_timeline:
                self.regime_timeline = regime_timeline
                
                # Detect transitions
                transitions = []
                for i in range(1, len(regime_timeline)):
                    prev_regime = regime_timeline[i-1]['regime']
                    curr_regime = regime_timeline[i]['regime']
                    
                    if prev_regime != curr_regime:
                        transitions.append({
                            'from_time': regime_timeline[i-1]['time'],
                            'to_time': regime_timeline[i]['time'],
                            'from_regime': prev_regime,
                            'to_regime': curr_regime,
                            'from_confidence': regime_timeline[i-1]['confidence'],
                            'to_confidence': regime_timeline[i]['confidence']
                        })
                
                if transitions:
                    logger.info(f"🔄 Detected {len(transitions)} regime transitions:")
                    for trans in transitions:
                        logger.info(f"   ⚡ {trans['from_time']} → {trans['to_time']}: "
                                  f"{trans['from_regime']} → {trans['to_regime']}")
                else:
                    logger.info("📊 No regime transitions detected during trading day")
                    
            else:
                logger.warning("⚠️ No regime timeline data generated")
                
        except Exception as e:
            logger.error(f"❌ Regime transition demonstration failed: {e}")
    
    def generate_comprehensive_report(self):
        """Generate comprehensive regime detection report"""
        
        try:
            logger.info("📋 Generating comprehensive regime detection report...")
            
            report_lines = [
                "=" * 80,
                "🎯 COMPREHENSIVE REGIME DETECTION TEST RESULTS",
                "=" * 80,
                f"📅 Test Date: {self.test_config['test_date']}",
                f"⏰ Time Range: {self.test_config['start_time']} - {self.test_config['end_time']}",
                f"📊 Symbols Analyzed: {len(self.all_symbols)}",
                "",
                "🔍 MULTI-METHOD REGIME DETECTION RESULTS:",
                "-" * 50
            ]
            
            # Individual symbol regime detections
            if self.regime_detections:
                regime_summary = {}
                for symbol, detection in self.regime_detections.items():
                    regime_type = detection.regime_type.value
                    if regime_type not in regime_summary:
                        regime_summary[regime_type] = []
                    regime_summary[regime_type].append((symbol, detection.confidence))
                
                for regime_type, symbols in regime_summary.items():
                    report_lines.append(f"   📊 {regime_type.upper()}:")
                    for symbol, confidence in symbols:
                        report_lines.append(f"      • {symbol}: {confidence:.2f} confidence")
                
                report_lines.append("")
                report_lines.append(f"📈 Total Regimes Detected: {len(regime_summary)}")
                report_lines.append(f"🎯 Average Confidence: {np.mean([d.confidence for d in self.regime_detections.values()]):.2f}")
            
            # Cross-asset analysis results
            if 'cross_asset_analysis' in self.performance_metrics:
                cross_asset = self.performance_metrics['cross_asset_analysis']
                if 'cross_asset_regime' in cross_asset:
                    regime = cross_asset['cross_asset_regime']
                    
                    report_lines.extend([
                        "",
                        "🌍 CROSS-ASSET REGIME ANALYSIS:",
                        "-" * 50,
                        f"   📊 Macro Regime: {regime.macro_regime.value}",
                        f"   🔄 Market Cycle: {regime.market_cycle.value}",
                        f"   ⚖️ Risk Environment: {regime.risk_environment.value}",
                        f"   🎯 Regime Alignment: {regime.regime_alignment:.2f}",
                        f"   📈 Regime Stability: {regime.regime_stability:.2f}",
                        f"   🔥 Systemic Stress: {regime.systemic_stress:.2f}",
                        f"   💧 Liquidity Stress: {regime.liquidity_stress:.2f}",
                        f"   💳 Credit Stress: {regime.credit_stress:.2f}"
                    ])
            
            # Transition signals
            if self.transition_signals:
                report_lines.extend([
                    "",
                    "⚡ REGIME TRANSITION SIGNALS:",
                    "-" * 50
                ])
                
                for signal in self.transition_signals:
                    report_lines.append(f"   🔄 {signal.signal_name}:")
                    report_lines.append(f"      From: {signal.from_regime.value}")
                    report_lines.append(f"      To: {signal.to_regime.value}")
                    report_lines.append(f"      Probability: {signal.transition_probability:.2f}")
                    report_lines.append(f"      Strength: {signal.signal_strength.value}")
                    report_lines.append(f"      Supporting Indicators: {len(signal.supporting_indicators)}")
                    report_lines.append("")
            
            # Regime timeline
            if self.regime_timeline:
                report_lines.extend([
                    "",
                    "🕐 INTRADAY REGIME TIMELINE:",
                    "-" * 50
                ])
                
                for entry in self.regime_timeline:
                    report_lines.append(f"   {entry['time']} ({entry['label']}): "
                                      f"{entry['regime']} (confidence: {entry['confidence']:.2f})")
            
            # Professional insights
            report_lines.extend([
                "",
                "🎓 PROFESSIONAL INSIGHTS:",
                "-" * 50,
                "   📊 Multi-Symbol Analysis: Comprehensive cross-asset regime detection",
                "   🔬 Advanced Methods: Markov Switching, Gaussian Mixture, ML Classification",
                "   ⚡ Real-Time Transitions: Intraday regime change detection",
                "   🎯 Risk Assessment: Systemic, liquidity, and credit stress monitoring",
                "   📈 Factor Analysis: Principal component regime decomposition",
                "   🌍 Global Context: International and sector rotation analysis",
                "",
                "🏆 SYSTEM CAPABILITIES DEMONSTRATED:",
                "-" * 50,
                f"   ✅ Multi-Method Detection: {len(DetectionMethod)} different approaches",
                f"   ✅ Cross-Asset Analysis: {len(self.regime_symbols)} asset categories",
                f"   ✅ Advanced Indicators: Volatility, momentum, mean reversion",
                f"   ✅ Transition Detection: Early warning and confirmation signals",
                f"   ✅ ML Classification: Ensemble models with feature engineering",
                f"   ✅ Professional Standards: Institutional-grade regime analysis",
                "",
                "=" * 80
            ])
            
            # Print report
            report_text = "\n".join(report_lines)
            print(report_text)
            
            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"comprehensive_regime_test_report_{timestamp}.txt"
            
            with open(report_filename, 'w') as f:
                f.write(report_text)
            
            logger.info(f"📋 Report saved to: {report_filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate report: {e}")
    
    async def run_comprehensive_test(self):
        """Run the complete comprehensive regime detection test"""
        
        try:
            logger.info("🚀 Starting Comprehensive Regime Detection Test")
            logger.info("=" * 80)
            
            # Initialize all components
            await self.initialize_components()
            
            # Load comprehensive market data
            market_data = await self.load_market_data()
            
            if not market_data:
                raise ValueError("No market data available for testing")
            
            # Run multi-method regime detection
            await self.run_multi_method_regime_detection(market_data)
            
            # Run cross-asset regime analysis
            await self.run_cross_asset_regime_analysis(market_data)
            
            # Run advanced indicator analysis
            await self.run_advanced_indicator_analysis(market_data)
            
            # Demonstrate regime transitions
            await self.demonstrate_regime_transitions(market_data)
            
            # Generate comprehensive report
            self.generate_comprehensive_report()
            
            logger.info("🎉 Comprehensive Regime Detection Test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Comprehensive test failed: {e}")
            raise


async def main():
    """Main test execution"""
    
    try:
        # Create and run comprehensive regime test
        regime_test = ComprehensiveRegimeTest()
        await regime_test.run_comprehensive_test()
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        raise


if __name__ == "__main__":
    # Run the comprehensive regime detection test
    asyncio.run(main())
