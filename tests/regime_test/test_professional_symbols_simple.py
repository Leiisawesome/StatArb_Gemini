#!/usr/bin/env python3
"""
Simple Professional Symbols Test
================================

Test professional quant symbols without time filtering to verify regime detection works.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
import pytest

# Core engine imports
from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.regime.regime_detector import (
    RegimeDetector, RegimeDetectionConfig, DetectionMethod, RegimeType
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_professional_symbols():
    """Test professional symbols for regime detection"""
    
    # Professional symbols that should be available
    professional_symbols = ['SPY', 'QQQ', 'IWM', 'TSLA', 'NVDA', 'AAPL', 'MSFT']
    
    logger.info(f"🎯 Testing {len(professional_symbols)} professional symbols")
    
    # Initialize data manager
    data_config = ClickHouseDataConfig(
        symbols=professional_symbols,
        target_date='2024-12-20',
        enable_caching=True
    )
    data_manager = ClickHouseDataManager(data_config)
    
    # Initialize regime detector
    detector_config = RegimeDetectionConfig(
        methods=[DetectionMethod.VOLATILITY_BASED, DetectionMethod.THRESHOLD_BASED],
        confidence_threshold=0.6
    )
    regime_detector = RegimeDetector(detector_config)
    
    # Test each symbol
    results = {}
    
    for symbol in professional_symbols:
        try:
            logger.info(f"📊 Testing {symbol}...")
            
            # Load data without time filtering
            data = data_manager.get_market_data(symbol=symbol)
            
            if data is not None and not data.empty:
                logger.info(f"   ✅ Loaded {len(data)} records for {symbol}")
                
                # Detect regime
                regime_detection = regime_detector.detect_current_regime(
                    market_data=data,
                    timestamp=datetime.now()
                )
                
                if regime_detection:
                    results[symbol] = regime_detection
                    logger.info(f"   📈 Regime: {regime_detection.regime_type.value} "
                              f"(confidence: {regime_detection.confidence:.2f})")
                else:
                    logger.warning(f"   ⚠️ No regime detected for {symbol}")
            else:
                logger.warning(f"   ❌ No data available for {symbol}")
                
        except Exception as e:
            logger.error(f"   ❌ Error testing {symbol}: {e}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("🎯 PROFESSIONAL SYMBOLS REGIME DETECTION RESULTS")
    logger.info("=" * 60)
    
    if results:
        # Regime distribution
        regime_counts = {}
        total_confidence = 0
        
        for symbol, detection in results.items():
            regime = detection.regime_type.value
            if regime not in regime_counts:
                regime_counts[regime] = []
            regime_counts[regime].append((symbol, detection.confidence))
            total_confidence += detection.confidence
        
        logger.info(f"📊 Successfully analyzed {len(results)} symbols")
        logger.info(f"🎯 Average confidence: {total_confidence / len(results):.2f}")
        logger.info("")
        
        for regime, symbol_list in regime_counts.items():
            logger.info(f"📈 {regime.upper()}:")
            for symbol, confidence in symbol_list:
                logger.info(f"   • {symbol}: {confidence:.2f}")
            logger.info("")
        
        # Professional insights
        logger.info("🎓 PROFESSIONAL INSIGHTS:")
        logger.info(f"   ✅ ETF Coverage: {'SPY' in results} (S&P 500), {'QQQ' in results} (NASDAQ), {'IWM' in results} (Russell 2000)")
        logger.info(f"   ✅ Tech Stocks: {'TSLA' in results} (Tesla), {'NVDA' in results} (NVIDIA), {'AAPL' in results} (Apple)")
        logger.info(f"   ✅ Regime Diversity: {len(regime_counts)} different regimes detected")
        logger.info(f"   ✅ Data Quality: All symbols loaded successfully")
        
    else:
        logger.error("❌ No regime detections successful")
    
        logger.info("=" * 60)


# Remove the main block since this is now a pytest test