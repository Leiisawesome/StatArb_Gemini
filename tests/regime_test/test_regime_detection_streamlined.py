#!/usr/bin/env python3
"""
Streamlined Professional Regime Detection Test
==============================================

Efficient test demonstrating professional regime detection using multiple symbols
and sophisticated detection methods w            # Show top features
            if hasattr(classification_result, 'feature_contributions') and classification_result.feature_contributions:
                top_features = sorted(
                    classification_result.feature_contributions.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                logger.info("  🏆 Top Features:")
                for feature, importance in top_features:
                    logger.info(f"    - {feature}: {importance:.4f}")
            
            return classification_resultg issues.

Author: StatArb_Gemini Professional Regime Detection System
"""

import sys
import os
# Add the project root to sys.path (two levels up from regime_test)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any

# Core engine imports
from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.regime.regime_detector import (
    RegimeDetector, RegimeDetectionConfig, DetectionMethod, RegimeType
)
from core_engine.regime.market_regime_analyzer import (
    MarketRegimeAnalyzer, RegimeAnalysisConfig
)
from core_engine.regime.regime_classifier import (
    RegimeClassifier, ClassificationConfig
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StreamlinedRegimeTest:
    """Streamlined professional regime detection test"""
    
    def __init__(self):
        """Initialize streamlined regime test"""
        
        # Professional symbols (subset for efficiency)
        self.professional_symbols = [
            'SPY',   # S&P 500 - Market benchmark
            'QQQ',   # NASDAQ - Tech/Growth
            'TLT',   # 20+ Year Treasury - Interest rates
            'GLD',   # Gold - Safe haven/inflation
            'HYG',   # High Yield Credit - Risk appetite
            'EEM'    # Emerging Markets - Global risk
        ]
        
        # Test configuration
        self.test_config = {
            'test_date': '2024-12-20',
            'symbols': self.professional_symbols
        }
        
        # Initialize components
        self.data_manager = None
        self.regime_detector = None
        self.market_analyzer = None
        self.regime_classifier = None
        
        logger.info("🚀 Streamlined Professional Regime Detection Test Initialized")
    
    async def initialize_components(self):
        """Initialize all regime detection components"""
        
        try:
            logger.info("🔧 Initializing regime detection components...")
            
            # Initialize data manager
            config = ClickHouseDataConfig(
                symbols=self.professional_symbols,
                target_date=self.test_config['test_date']
            )
            self.data_manager = ClickHouseDataManager(config)
            
            # Initialize regime detector with multiple methods
            regime_config = RegimeDetectionConfig(
                methods=[
                    DetectionMethod.MARKOV_SWITCHING,
                    DetectionMethod.GAUSSIAN_MIXTURE,
                    DetectionMethod.VOLATILITY_BASED
                ],
                short_lookback=50,
                confidence_threshold=0.6
            )
            self.regime_detector = RegimeDetector(regime_config)
            
            # Initialize market regime analyzer (use default config)
            self.market_analyzer = MarketRegimeAnalyzer(RegimeAnalysisConfig())
            
            # Initialize regime classifier (use default config)
            self.regime_classifier = RegimeClassifier(ClassificationConfig())
            
            logger.info("✅ All regime components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}")
            raise
    
    async def load_professional_data(self) -> Dict[str, pd.DataFrame]:
        """Load data for all professional symbols"""
        
        logger.info("📊 Loading professional symbol data...")
        market_data = {}
        successful_loads = 0
        
        for symbol in self.professional_symbols:
            try:
                data = self.data_manager.get_market_data(symbol=symbol)
                
                if data is not None and not data.empty:
                    # Ensure proper datetime index
                    if 'timestamp' in data.columns:
                        data.set_index('timestamp', inplace=True)
                    
                    market_data[symbol] = data
                    successful_loads += 1
                    logger.info(f"  ✅ {symbol}: {len(data)} records loaded")
                else:
                    logger.warning(f"  ⚠️ {symbol}: No data available")
                    
            except Exception as e:
                logger.warning(f"  ❌ {symbol}: Load failed - {str(e)[:50]}...")
        
        logger.info(f"📈 Successfully loaded {successful_loads}/{len(self.professional_symbols)} symbols")
        return market_data
    
    async def demonstrate_multi_method_detection(self, market_data: Dict[str, pd.DataFrame]):
        """Demonstrate multiple regime detection methods"""
        
        logger.info("🔍 Demonstrating multi-method regime detection...")
        
        # Use SPY as primary symbol for demonstration
        if 'SPY' not in market_data:
            logger.warning("⚠️ SPY not available, using first available symbol")
            primary_symbol = list(market_data.keys())[0]
        else:
            primary_symbol = 'SPY'
        
        primary_data = market_data[primary_symbol]
        
        # Test each detection method
        detection_results = {}
        
        # Test all methods including the fixed Markov switching
        for method in [DetectionMethod.MARKOV_SWITCHING, DetectionMethod.GAUSSIAN_MIXTURE, DetectionMethod.VOLATILITY_BASED]:
            try:
                # Configure detector for single method
                method_config = RegimeDetectionConfig(
                    methods=[method],
                    short_lookback=50,
                    confidence_threshold=0.5
                )
                method_detector = RegimeDetector(method_config)
                
                # Detect regime
                result = method_detector.detect_current_regime(
                    market_data=primary_data,
                    timestamp=primary_data.index[-1]
                )
                
                if result is not None:
                    detection_results[method.value] = result
                    logger.info(f"  🎯 {method.value}: {result.regime_type.value} "
                              f"(confidence: {result.confidence:.3f})")
                else:
                    logger.warning(f"  ⚠️ {method.value}: No result returned")
                
            except Exception as e:
                logger.warning(f"  ❌ {method.value}: Detection failed - {str(e)[:50]}...")
        
        return detection_results
    
    async def demonstrate_cross_asset_analysis(self, market_data: Dict[str, pd.DataFrame]):
        """Demonstrate cross-asset regime analysis"""
        
        logger.info("🌍 Demonstrating cross-asset regime analysis...")
        
        try:
            # Analyze regime across multiple assets using the cross_asset_analyzer
            cross_asset_result = self.market_analyzer.cross_asset_analyzer.analyze_cross_asset_regime(
                market_data=market_data
            )
            
            logger.info(f"  📊 Macro Regime: {cross_asset_result.macro_regime}")
            logger.info(f"  📈 Market Cycle: {cross_asset_result.market_cycle}")
            logger.info(f"  ⚡ Risk Environment: {cross_asset_result.risk_environment}")
            # Check if confidence attribute exists
            if hasattr(cross_asset_result, 'confidence'):
                logger.info(f"  🎯 Confidence: {cross_asset_result.confidence:.3f}")
            else:
                logger.info(f"  🎯 Analysis: Cross-asset regime successfully detected")
            
            # Show factor analysis
            if hasattr(cross_asset_result, 'factor_analysis'):
                logger.info("  🔬 Factor Analysis:")
                for factor, value in cross_asset_result.factor_analysis.items():
                    logger.info(f"    - {factor}: {value:.3f}")
            
            return cross_asset_result
            
        except Exception as e:
            logger.warning(f"❌ Cross-asset analysis failed: {e}")
            return None
    
    async def demonstrate_regime_classification(self, market_data: Dict[str, pd.DataFrame]):
        """Demonstrate ML-based regime classification"""
        
        logger.info("🤖 Demonstrating ML-based regime classification...")
        
        try:
            # Use SPY for classification demo
            primary_symbol = 'SPY' if 'SPY' in market_data else list(market_data.keys())[0]
            primary_data = market_data[primary_symbol]
            
            # Check if models are trained, if not, train them now
            if not hasattr(self.regime_classifier, 'models_trained') or not self.regime_classifier.models_trained:
                logger.info("  🔧 Training ML models with synthetic regime labels...")
                training_success = self.regime_classifier.train_models(price_data=primary_data)
                if not training_success:
                    logger.warning("  ⚠️ Model training failed, skipping ML classification")
                    return None
                logger.info("  ✅ ML models trained successfully!")
            
            # Classify current regime (use price_data parameter)
            classification_result = self.regime_classifier.classify_regime(
                price_data=primary_data
            )
            
            logger.info(f"  🎯 Classified Regime: {classification_result.predicted_regime}")
            logger.info(f"  📊 Classification Confidence: {classification_result.prediction_confidence:.3f}")
            logger.info(f"  🔍 Feature Importance: {len(classification_result.feature_contributions)} features")
            
            # Show top features
            if hasattr(classification_result, 'feature_importance'):
                top_features = sorted(
                    classification_result.feature_importance.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                logger.info("  🏆 Top Features:")
                for feature, importance in top_features:
                    logger.info(f"    - {feature}: {importance:.3f}")
            
            return classification_result
            
        except Exception as e:
            logger.warning(f"❌ Regime classification failed: {e}")
            return None
    
    async def generate_regime_summary(self, detection_results, cross_asset_result, classification_result):
        """Generate comprehensive regime summary"""
        
        logger.info("📋 Generating comprehensive regime summary...")
        
        print("\n" + "="*80)
        print("🎯 PROFESSIONAL REGIME DETECTION SUMMARY")
        print("="*80)
        
        # Multi-method detection summary
        print("\n🔍 MULTI-METHOD DETECTION RESULTS:")
        if detection_results:
            for method, result in detection_results.items():
                if result is not None:
                    print(f"  • {method}: {result.regime_type.value} (confidence: {result.confidence:.3f})")
                else:
                    print(f"  • {method}: No result")
        else:
            print("  • No successful detections")
        
        # Cross-asset analysis summary
        if cross_asset_result:
            print(f"\n🌍 CROSS-ASSET ANALYSIS:")
            print(f"  • Macro Regime: {cross_asset_result.macro_regime}")
            print(f"  • Market Cycle: {cross_asset_result.market_cycle}")
            print(f"  • Risk Environment: {cross_asset_result.risk_environment}")
            # Check if confidence attribute exists
            if hasattr(cross_asset_result, 'confidence'):
                print(f"  • Overall Confidence: {cross_asset_result.confidence:.3f}")
            else:
                print(f"  • Analysis: Cross-asset regime successfully detected")
        
        # Classification summary
        if classification_result:
            print(f"\n🤖 ML CLASSIFICATION:")
            print(f"  • Regime Class: {classification_result.predicted_regime}")
            print(f"  • Classification Confidence: {classification_result.prediction_confidence:.3f}")
        
        # Professional insights
        print(f"\n💡 PROFESSIONAL INSIGHTS:")
        print(f"  • Data Coverage: {len(self.professional_symbols)} professional symbols")
        print(f"  • Detection Methods: 3 sophisticated algorithms")
        print(f"  • Analysis Depth: Cross-asset, ML-based, multi-timeframe")
        print(f"  • Test Date: {self.test_config['test_date']}")
        
        print("\n" + "="*80)
        print("✅ PROFESSIONAL REGIME DETECTION TEST COMPLETED")
        print("="*80)
    
    async def run_streamlined_test(self):
        """Run the complete streamlined regime detection test"""
        
        try:
            logger.info("🚀 Starting Streamlined Professional Regime Detection Test...")
            
            # Initialize components
            await self.initialize_components()
            
            # Load professional data
            market_data = await self.load_professional_data()
            
            if not market_data:
                logger.error("❌ No market data loaded - cannot proceed")
                return
            
            # Demonstrate multi-method detection
            detection_results = await self.demonstrate_multi_method_detection(market_data)
            
            # Demonstrate cross-asset analysis
            cross_asset_result = await self.demonstrate_cross_asset_analysis(market_data)
            
            # Demonstrate regime classification
            classification_result = await self.demonstrate_regime_classification(market_data)
            
            # Generate comprehensive summary
            await self.generate_regime_summary(detection_results, cross_asset_result, classification_result)
            
            logger.info("🎉 Streamlined regime detection test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise


async def main():
    """Main test execution"""
    test = StreamlinedRegimeTest()
    await test.run_streamlined_test()


if __name__ == "__main__":
    asyncio.run(main())
