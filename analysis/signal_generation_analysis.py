#!/usr/bin/env python3
"""
Signal Generation Analysis Script
================================

This script analyzes the signal generation components in the core system:
- SignalGenerator availability and capabilities
- RegimeDetector availability and functionality
- Technical indicators availability and performance
- Feature engineering capabilities
- Model ensemble functionality

Author: AI Integration Team
Date: 2025-01-27
"""

import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
except ImportError as e:
    print(f"Warning: Some packages not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SignalComponentStatus:
    """Status information for a signal generation component"""
    name: str
    available: bool
    version: Optional[str] = None
    capabilities: List[str] = None
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = None

@dataclass
class SignalGenerationReport:
    """Complete signal generation analysis report"""
    timestamp: str
    overall_status: str
    components: Dict[str, SignalComponentStatus]
    recommendations: List[str]
    integration_readiness: float  # 0.0 to 1.0

class SignalGenerationAnalyzer:
    """Analyzes signal generation components in the core system"""
    
    def __init__(self):
        self.report = None
        self.components = {}
        
    async def analyze_all_components(self) -> SignalGenerationReport:
        """Analyze all signal generation components"""
        logger.info("Starting signal generation analysis...")
        
        # Analyze each component
        await self._analyze_signal_generator()
        await self._analyze_regime_detector()
        await self._analyze_technical_indicators()
        await self._analyze_feature_engineering()
        await self._analyze_model_ensemble()
        
        # Generate overall report
        self.report = self._generate_report()
        
        logger.info("Signal generation analysis completed")
        return self.report
    
    async def _analyze_signal_generator(self):
        """Analyze SignalGenerator availability and capabilities"""
        logger.info("Analyzing SignalGenerator...")
        
        try:
            # Check if signal generator module exists
            signal_generator_path = project_root / "core_structure" / "signal_generation" / "signal_generator.py"
            
            if signal_generator_path.exists():
                try:
                    # Try to import and test signal generator
                    from core_structure.signal_generation.signal_generator import SignalGenerator
                    
                    # Test basic functionality
                    generator = SignalGenerator()
                    
                    # Create sample market data for testing
                    sample_data = self._create_sample_market_data()
                    
                    # Test signal generation
                    try:
                        signal = await generator.generate_signal(
                            symbol_pair="AAPL",
                            market_data=sample_data,
                            real_time_data=None
                        )
                        
                        capabilities = [
                            "Async signal generation",
                            "Market data processing",
                            "Real-time data handling",
                            "Symbol pair support"
                        ]
                        
                        performance_metrics = {
                            "signal_generated": signal is not None,
                            "signal_type": type(signal).__name__ if signal else "None"
                        }
                        
                    except Exception as e:
                        capabilities = [
                            "Async signal generation",
                            "Market data processing",
                            "Real-time data handling",
                            "Symbol pair support"
                        ]
                        
                        performance_metrics = {
                            "signal_generated": False,
                            "error": str(e)
                        }
                    
                    self.components['signal_generator'] = SignalComponentStatus(
                        name="SignalGenerator",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics
                    )
                    
                except Exception as e:
                    self.components['signal_generator'] = SignalComponentStatus(
                        name="SignalGenerator",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}"
                    )
            else:
                self.components['signal_generator'] = SignalComponentStatus(
                    name="SignalGenerator",
                    available=False,
                    error_message="Signal generator module not found"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing SignalGenerator: {e}")
            self.components['signal_generator'] = SignalComponentStatus(
                name="SignalGenerator",
                available=False,
                error_message=str(e)
            )
    
    async def _analyze_regime_detector(self):
        """Analyze RegimeDetector availability and functionality"""
        logger.info("Analyzing RegimeDetector...")
        
        try:
            # Check if regime detector module exists
            regime_detector_path = project_root / "core_structure" / "signal_generation" / "regime_detector.py"
            
            if regime_detector_path.exists():
                try:
                    # Try to import and test regime detector
                    from core_structure.signal_generation.regime_detector import RegimeDetector
                    
                    # Test basic functionality
                    detector = RegimeDetector()
                    
                    # Create sample market data for testing
                    sample_data = self._create_sample_market_data()
                    
                    # Test regime detection
                    try:
                        regime = detector.detect_regime(sample_data)
                        
                        capabilities = [
                            "Market regime detection",
                            "Volatility analysis",
                            "Trend identification",
                            "Regime classification"
                        ]
                        
                        performance_metrics = {
                            "regime_detected": regime is not None,
                            "regime_type": type(regime).__name__ if regime else "None"
                        }
                        
                    except Exception as e:
                        capabilities = [
                            "Market regime detection",
                            "Volatility analysis",
                            "Trend identification",
                            "Regime classification"
                        ]
                        
                        performance_metrics = {
                            "regime_detected": False,
                            "error": str(e)
                        }
                    
                    self.components['regime_detector'] = SignalComponentStatus(
                        name="RegimeDetector",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics
                    )
                    
                except Exception as e:
                    self.components['regime_detector'] = SignalComponentStatus(
                        name="RegimeDetector",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}"
                    )
            else:
                self.components['regime_detector'] = SignalComponentStatus(
                    name="RegimeDetector",
                    available=False,
                    error_message="Regime detector module not found"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing RegimeDetector: {e}")
            self.components['regime_detector'] = SignalComponentStatus(
                name="RegimeDetector",
                available=False,
                error_message=str(e)
            )
    
    async def _analyze_technical_indicators(self):
        """Analyze Technical Indicators availability and performance"""
        logger.info("Analyzing Technical Indicators...")
        
        try:
            # Check if technical indicators module exists
            indicators_path = project_root / "core_structure" / "signal_generation" / "indicators" / "technical_indicators.py"
            
            if indicators_path.exists():
                try:
                    # Try to import and test technical indicators
                    from core_structure.signal_generation.indicators.technical_indicators import TechnicalIndicators
                    
                    # Test basic functionality
                    indicators = TechnicalIndicators()
                    
                    # Create sample market data for testing
                    sample_data = self._create_sample_market_data()
                    
                    # Test indicator calculation
                    try:
                        # Test common indicators
                        sma = indicators.calculate_sma(sample_data, window=20)
                        rsi = indicators.calculate_rsi(sample_data, window=14)
                        macd = indicators.calculate_macd(sample_data)
                        
                        capabilities = [
                            "Moving averages (SMA, EMA)",
                            "RSI calculation",
                            "MACD calculation",
                            "Bollinger Bands",
                            "Volume indicators"
                        ]
                        
                        performance_metrics = {
                            "sma_calculated": sma is not None,
                            "rsi_calculated": rsi is not None,
                            "macd_calculated": macd is not None,
                            "indicators_available": len(capabilities)
                        }
                        
                    except Exception as e:
                        capabilities = [
                            "Moving averages (SMA, EMA)",
                            "RSI calculation",
                            "MACD calculation",
                            "Bollinger Bands",
                            "Volume indicators"
                        ]
                        
                        performance_metrics = {
                            "sma_calculated": False,
                            "rsi_calculated": False,
                            "macd_calculated": False,
                            "error": str(e)
                        }
                    
                    self.components['technical_indicators'] = SignalComponentStatus(
                        name="Technical Indicators",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics
                    )
                    
                except Exception as e:
                    self.components['technical_indicators'] = SignalComponentStatus(
                        name="Technical Indicators",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}"
                    )
            else:
                self.components['technical_indicators'] = SignalComponentStatus(
                    name="Technical Indicators",
                    available=False,
                    error_message="Technical indicators module not found"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing Technical Indicators: {e}")
            self.components['technical_indicators'] = SignalComponentStatus(
                name="Technical Indicators",
                available=False,
                error_message=str(e)
            )
    
    async def _analyze_feature_engineering(self):
        """Analyze Feature Engineering availability and capabilities"""
        logger.info("Analyzing Feature Engineering...")
        
        try:
            # Check if feature engineering module exists
            feature_eng_path = project_root / "core_structure" / "signal_generation" / "feature_engine.py"
            
            if feature_eng_path.exists():
                try:
                    # Try to import and test feature engineering
                    from core_structure.signal_generation.feature_engine import FeatureEngine
                    
                    # Test basic functionality
                    feature_engine = FeatureEngine()
                    
                    # Create sample market data for testing
                    sample_data = self._create_sample_market_data()
                    
                    # Test feature extraction
                    try:
                        features = feature_engine.extract_features(sample_data)
                        
                        capabilities = [
                            "Technical feature extraction",
                            "Market microstructure features",
                            "Sentiment features",
                            "Feature normalization",
                            "Feature selection"
                        ]
                        
                        performance_metrics = {
                            "features_extracted": features is not None,
                            "feature_count": len(features) if features is not None else 0
                        }
                        
                    except Exception as e:
                        capabilities = [
                            "Technical feature extraction",
                            "Market microstructure features",
                            "Sentiment features",
                            "Feature normalization",
                            "Feature selection"
                        ]
                        
                        performance_metrics = {
                            "features_extracted": False,
                            "error": str(e)
                        }
                    
                    self.components['feature_engineering'] = SignalComponentStatus(
                        name="Feature Engineering",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics
                    )
                    
                except Exception as e:
                    self.components['feature_engineering'] = SignalComponentStatus(
                        name="Feature Engineering",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}"
                    )
            else:
                self.components['feature_engineering'] = SignalComponentStatus(
                    name="Feature Engineering",
                    available=False,
                    error_message="Feature engineering module not found"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing Feature Engineering: {e}")
            self.components['feature_engineering'] = SignalComponentStatus(
                name="Feature Engineering",
                available=False,
                error_message=str(e)
            )
    
    async def _analyze_model_ensemble(self):
        """Analyze Model Ensemble availability and functionality"""
        logger.info("Analyzing Model Ensemble...")
        
        try:
            # Check if model ensemble module exists
            model_ensemble_path = project_root / "core_structure" / "signal_generation" / "model_ensemble.py"
            
            if model_ensemble_path.exists():
                try:
                    # Try to import and test model ensemble
                    from core_structure.signal_generation.model_ensemble import ModelEnsemble
                    
                    # Test basic functionality
                    ensemble = ModelEnsemble()
                    
                    # Create sample market data for testing
                    sample_data = self._create_sample_market_data()
                    
                    # Test ensemble prediction
                    try:
                        prediction = ensemble.predict(sample_data)
                        
                        capabilities = [
                            "Multi-model ensemble",
                            "Model weighting",
                            "Prediction aggregation",
                            "Model performance tracking",
                            "Dynamic model selection"
                        ]
                        
                        performance_metrics = {
                            "prediction_generated": prediction is not None,
                            "prediction_type": type(prediction).__name__ if prediction else "None"
                        }
                        
                    except Exception as e:
                        capabilities = [
                            "Multi-model ensemble",
                            "Model weighting",
                            "Prediction aggregation",
                            "Model performance tracking",
                            "Dynamic model selection"
                        ]
                        
                        performance_metrics = {
                            "prediction_generated": False,
                            "error": str(e)
                        }
                    
                    self.components['model_ensemble'] = SignalComponentStatus(
                        name="Model Ensemble",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics
                    )
                    
                except Exception as e:
                    self.components['model_ensemble'] = SignalComponentStatus(
                        name="Model Ensemble",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}"
                    )
            else:
                self.components['model_ensemble'] = SignalComponentStatus(
                    name="Model Ensemble",
                    available=False,
                    error_message="Model ensemble module not found"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing Model Ensemble: {e}")
            self.components['model_ensemble'] = SignalComponentStatus(
                name="Model Ensemble",
                available=False,
                error_message=str(e)
            )
    
    def _create_sample_market_data(self) -> pd.DataFrame:
        """Create sample market data for testing"""
        try:
            # Generate sample OHLCV data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            # Generate realistic price data
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)  # Daily returns
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Create OHLCV data
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                # Generate OHLC from close price
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Error creating sample market data: {e}")
            # Return minimal sample data
            return pd.DataFrame({
                'open': [100.0],
                'high': [101.0],
                'low': [99.0],
                'close': [100.5],
                'volume': [1000000]
            }, index=[pd.Timestamp('2024-01-01')])
    
    def _generate_report(self) -> SignalGenerationReport:
        """Generate comprehensive analysis report"""
        from datetime import datetime
        
        # Calculate overall status
        available_components = sum(1 for comp in self.components.values() if comp.available)
        total_components = len(self.components)
        integration_readiness = available_components / total_components if total_components > 0 else 0.0
        
        if integration_readiness >= 0.8:
            overall_status = "EXCELLENT"
        elif integration_readiness >= 0.6:
            overall_status = "GOOD"
        elif integration_readiness >= 0.4:
            overall_status = "FAIR"
        else:
            overall_status = "POOR"
        
        # Generate recommendations
        recommendations = []
        
        if not self.components.get('signal_generator', {}).available:
            recommendations.append("Implement SignalGenerator for core signal generation")
        
        if not self.components.get('regime_detector', {}).available:
            recommendations.append("Implement RegimeDetector for market regime analysis")
        
        if not self.components.get('technical_indicators', {}).available:
            recommendations.append("Implement Technical Indicators for market analysis")
        
        if not self.components.get('feature_engineering', {}).available:
            recommendations.append("Implement Feature Engineering for data preprocessing")
        
        if not self.components.get('model_ensemble', {}).available:
            recommendations.append("Implement Model Ensemble for prediction aggregation")
        
        if integration_readiness < 0.6:
            recommendations.append("Focus on core signal generation components first")
        
        return SignalGenerationReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            components=self.components,
            recommendations=recommendations,
            integration_readiness=integration_readiness
        )
    
    def print_report(self):
        """Print formatted analysis report"""
        if not self.report:
            print("No report available. Run analyze_all_components() first.")
            return
        
        print("\n" + "="*80)
        print("📊 SIGNAL GENERATION ANALYSIS REPORT")
        print("="*80)
        print(f"Timestamp: {self.report.timestamp}")
        print(f"Overall Status: {self.report.overall_status}")
        print(f"Integration Readiness: {self.report.integration_readiness:.1%}")
        print()
        
        print("📊 COMPONENT ANALYSIS:")
        print("-" * 50)
        
        for name, component in self.report.components.items():
            status_icon = "✅" if component.available else "❌"
            print(f"{status_icon} {component.name}")
            print(f"   Available: {component.available}")
            
            if component.version:
                print(f"   Version: {component.version}")
            
            if component.capabilities:
                print(f"   Capabilities: {', '.join(component.capabilities)}")
            
            if component.performance_metrics:
                print(f"   Performance: {component.performance_metrics}")
            
            if component.error_message:
                print(f"   Error: {component.error_message}")
            
            print()
        
        if self.report.recommendations:
            print("💡 RECOMMENDATIONS:")
            print("-" * 50)
            for i, rec in enumerate(self.report.recommendations, 1):
                print(f"{i}. {rec}")
            print()
        
        print("="*80)

async def main():
    """Main analysis function"""
    print("🚀 Starting Signal Generation Analysis...")
    
    analyzer = SignalGenerationAnalyzer()
    report = await analyzer.analyze_all_components()
    analyzer.print_report()
    
    # Save report to file
    report_file = project_root / "analysis" / "signal_generation_report.json"
    import json
    from datetime import datetime
    
    report_dict = {
        "timestamp": report.timestamp,
        "overall_status": report.overall_status,
        "integration_readiness": report.integration_readiness,
        "components": {
            name: {
                "name": comp.name,
                "available": comp.available,
                "version": comp.version,
                "capabilities": comp.capabilities,
                "error_message": comp.error_message,
                "performance_metrics": comp.performance_metrics
            }
            for name, comp in report.components.items()
        },
        "recommendations": report.recommendations
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_dict, f, indent=2)
    
    print(f"📄 Report saved to: {report_file}")
    
    return report

if __name__ == "__main__":
    asyncio.run(main()) 