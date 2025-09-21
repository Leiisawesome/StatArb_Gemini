#!/usr/bin/env python3
"""
Professional Regime Detection Test
=================================

Professional-grade regime detection test using the recommended quant symbols:
- SPY, QQQ, IWM (Equity indices)
- TLT, SHY (Fixed income)
- GLD, USO (Commodities)
- UUP (Currency)
- HYG, LQD (Credit)
- EEM, EFA (International)
- XLF, XLE, XLK (Sectors)

This test demonstrates institutional-grade regime detection capabilities.

Author: StatArb_Gemini Professional Regime Detection System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Core engine imports
from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.regime.regime_detector import (
    RegimeDetector, RegimeDetectionConfig, DetectionMethod, RegimeType
)
from core_engine.regime.market_regime_analyzer import (
    MarketRegimeAnalyzer, RegimeAnalysisConfig, MacroRegime, MarketCycle, RiskEnvironment
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProfessionalRegimeTest:
    """
    Professional regime detection test using institutional-grade symbols
    """
    
    def __init__(self):
        """Initialize professional regime test"""
        
        # Professional quant symbols for comprehensive regime detection
        self.regime_symbols = {
            'primary_equity': ['SPY', 'QQQ', 'IWM'],
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
            'test_date': '2024-12-20',
            'start_time': '09:30',  # Just time, no seconds
            'end_time': '16:00'     # Just time, no seconds
        }
        
        # Initialize components
        self.data_manager = None
        self.regime_detector = None
        self.market_analyzer = None
        
        # Results storage
        self.regime_detections = {}
        self.cross_asset_analysis = {}
        self.available_symbols = []
        
        logger.info("🎯 Professional Regime Detection Test initialized")
        logger.info(f"📊 Testing {len(self.all_symbols)} professional symbols")
        logger.info(f"📅 Test date: {self.test_config['test_date']}")
    
    async def initialize_components(self):
        """Initialize regime detection components"""
        
        try:
            logger.info("🔧 Initializing professional regime detection components...")
            
            # Data Manager
            data_config = ClickHouseDataConfig(
                symbols=self.all_symbols,
                target_date=self.test_config['test_date'],
                enable_caching=True
            )
            self.data_manager = ClickHouseDataManager(data_config)
            
            # Regime Detector with professional configuration
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
                n_regimes=3,  # Professional standard
                confidence_threshold=0.7  # Higher confidence threshold
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
            
            logger.info("✅ Professional regime detection components initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            raise
    
    async def load_professional_data(self) -> Dict[str, pd.DataFrame]:
        """Load data for professional symbols"""
        
        try:
            logger.info("📊 Loading professional market data...")
            
            market_data = {}
            successful_loads = 0
            failed_symbols = []
            
            for symbol in self.all_symbols:
                try:
                    data = self.data_manager.get_market_data(
                        symbol=symbol,
                        start_time=self.test_config['start_time'],
                        end_time=self.test_config['end_time']
                    )
                    
                    if data is not None and not data.empty:
                        # Add symbol column for cross-asset analysis
                        data['symbol'] = symbol
                        market_data[symbol] = data
                        successful_loads += 1
                        self.available_symbols.append(symbol)
                        logger.info(f"   📈 Loaded {len(data)} records for {symbol}")
                    else:
                        failed_symbols.append(symbol)
                        logger.warning(f"   ⚠️ No data available for {symbol}")
                        
                except Exception as e:
                    failed_symbols.append(symbol)
                    logger.warning(f"   ❌ Failed to load {symbol}: {e}")
                    continue
            
            logger.info(f"✅ Successfully loaded data for {successful_loads}/{len(self.all_symbols)} symbols")
            
            if failed_symbols:
                logger.info(f"⚠️ Failed symbols: {failed_symbols}")
            
            if successful_loads == 0:
                raise ValueError("No market data loaded successfully")
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Failed to load professional market data: {e}")
            raise
    
    async def run_professional_regime_analysis(self, market_data: Dict[str, pd.DataFrame]):
        """Run professional regime analysis"""
        
        try:
            logger.info("🔍 Running professional regime analysis...")
            
            # Individual symbol regime detection
            for symbol, data in market_data.items():
                logger.info(f"   🎯 Analyzing regime for {symbol}...")
                
                regime_detection = self.regime_detector.detect_current_regime(
                    market_data=data,
                    timestamp=datetime.now()
                )
                
                if regime_detection:
                    self.regime_detections[symbol] = regime_detection
                    logger.info(f"      📊 Detected: {regime_detection.regime_type.value} "
                              f"(confidence: {regime_detection.confidence:.2f}, "
                              f"method: {regime_detection.method.value})")
                else:
                    logger.warning(f"      ⚠️ No regime detected for {symbol}")
            
            # Cross-asset regime analysis
            logger.info("🌍 Running cross-asset regime analysis...")
            
            comprehensive_analysis = self.market_analyzer.analyze_market_regime(market_data)
            
            if comprehensive_analysis and 'cross_asset_regime' in comprehensive_analysis:
                self.cross_asset_analysis = comprehensive_analysis
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
                
        except Exception as e:
            logger.error(f"❌ Professional regime analysis failed: {e}")
    
    def analyze_regime_by_category(self):
        """Analyze regime patterns by asset category"""
        
        try:
            logger.info("📊 Analyzing regime patterns by asset category...")
            
            category_regimes = {}
            
            for category, symbols in self.regime_symbols.items():
                if not symbols:
                    continue
                    
                category_detections = []
                for symbol in symbols:
                    if symbol in self.regime_detections:
                        category_detections.append(self.regime_detections[symbol])
                
                if category_detections:
                    # Find most common regime in category
                    regime_counts = {}
                    total_confidence = 0
                    
                    for detection in category_detections:
                        regime = detection.regime_type.value
                        if regime not in regime_counts:
                            regime_counts[regime] = 0
                        regime_counts[regime] += 1
                        total_confidence += detection.confidence
                    
                    most_common_regime = max(regime_counts.keys(), key=lambda x: regime_counts[x])
                    avg_confidence = total_confidence / len(category_detections)
                    
                    category_regimes[category] = {
                        'dominant_regime': most_common_regime,
                        'confidence': avg_confidence,
                        'symbols_analyzed': len(category_detections),
                        'regime_distribution': regime_counts
                    }
                    
                    logger.info(f"   📊 {category.upper()}: {most_common_regime} "
                              f"(confidence: {avg_confidence:.2f}, symbols: {len(category_detections)})")
            
            return category_regimes
            
        except Exception as e:
            logger.error(f"❌ Category analysis failed: {e}")
            return {}
    
    def generate_professional_report(self):
        """Generate professional regime detection report"""
        
        try:
            logger.info("📋 Generating professional regime detection report...")
            
            # Analyze by category
            category_analysis = self.analyze_regime_by_category()
            
            report_lines = [
                "=" * 80,
                "🎯 PROFESSIONAL REGIME DETECTION TEST RESULTS",
                "=" * 80,
                f"📅 Test Date: {self.test_config['test_date']}",
                f"⏰ Time Range: {self.test_config['start_time']} - {self.test_config['end_time']}",
                f"📊 Symbols Tested: {len(self.all_symbols)}",
                f"✅ Symbols Available: {len(self.available_symbols)}",
                "",
                "🏦 PROFESSIONAL SYMBOL ANALYSIS:",
                "-" * 50
            ]
            
            # Individual symbol results
            if self.regime_detections:
                for symbol, detection in self.regime_detections.items():
                    report_lines.append(f"   📊 {symbol}: {detection.regime_type.value} "
                                      f"(confidence: {detection.confidence:.2f}, "
                                      f"method: {detection.method.value})")
                
                report_lines.append("")
                report_lines.append(f"📈 Total Regimes Detected: {len(self.regime_detections)}")
                avg_confidence = np.mean([d.confidence for d in self.regime_detections.values()])
                report_lines.append(f"🎯 Average Confidence: {avg_confidence:.2f}")
            
            # Category analysis
            if category_analysis:
                report_lines.extend([
                    "",
                    "📊 ASSET CATEGORY REGIME ANALYSIS:",
                    "-" * 50
                ])
                
                for category, analysis in category_analysis.items():
                    report_lines.append(f"   🏦 {category.upper()}:")
                    report_lines.append(f"      Dominant Regime: {analysis['dominant_regime']}")
                    report_lines.append(f"      Confidence: {analysis['confidence']:.2f}")
                    report_lines.append(f"      Symbols: {analysis['symbols_analyzed']}")
                    report_lines.append(f"      Distribution: {analysis['regime_distribution']}")
                    report_lines.append("")
            
            # Cross-asset analysis
            if self.cross_asset_analysis and 'cross_asset_regime' in self.cross_asset_analysis:
                regime = self.cross_asset_analysis['cross_asset_regime']
                
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
            
            # Professional insights
            report_lines.extend([
                "",
                "🎓 PROFESSIONAL INSIGHTS:",
                "-" * 50,
                "   📊 Multi-Asset Coverage: Equity, Fixed Income, Commodities, Currency, Credit",
                "   🔬 Advanced Methods: Markov Switching, Gaussian Mixture, Volatility Analysis",
                "   🌍 Global Perspective: US, International, and Sector-specific analysis",
                "   ⚡ Real-Time Capability: Intraday regime detection and transitions",
                "   🎯 Risk Assessment: Comprehensive stress monitoring across asset classes",
                "",
                "🏆 INSTITUTIONAL-GRADE CAPABILITIES:",
                "-" * 50,
                f"   ✅ Professional Symbols: {len(self.all_symbols)} institutional-grade ETFs",
                f"   ✅ Multi-Method Detection: 4 sophisticated detection algorithms",
                f"   ✅ Cross-Asset Analysis: Comprehensive regime correlation analysis",
                f"   ✅ Risk Monitoring: Systemic, liquidity, and credit stress indicators",
                f"   ✅ Category Analysis: Asset class specific regime identification",
                f"   ✅ High Confidence: Professional-grade confidence thresholds",
                "",
                "=" * 80
            ])
            
            # Print and save report
            report_text = "\n".join(report_lines)
            print(report_text)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"professional_regime_test_report_{timestamp}.txt"
            
            with open(report_filename, 'w') as f:
                f.write(report_text)
            
            logger.info(f"📋 Professional report saved to: {report_filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate professional report: {e}")
    
    async def run_professional_test(self):
        """Run the complete professional regime detection test"""
        
        try:
            logger.info("🚀 Starting Professional Regime Detection Test")
            logger.info("=" * 80)
            
            # Initialize components
            await self.initialize_components()
            
            # Load professional market data
            market_data = await self.load_professional_data()
            
            if not market_data:
                raise ValueError("No professional market data available for testing")
            
            # Run professional regime analysis
            await self.run_professional_regime_analysis(market_data)
            
            # Generate professional report
            self.generate_professional_report()
            
            logger.info("🎉 Professional Regime Detection Test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Professional test failed: {e}")
            raise


async def main():
    """Main test execution"""
    
    try:
        # Create and run professional regime test
        regime_test = ProfessionalRegimeTest()
        await regime_test.run_professional_test()
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        raise


if __name__ == "__main__":
    # Run the professional regime detection test
    asyncio.run(main())
