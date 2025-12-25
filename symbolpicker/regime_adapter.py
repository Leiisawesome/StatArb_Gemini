"""
Adapter for the Core Engine's Regime Analyzer.
"""
import pandas as pd
import logging
from typing import Dict, Any, List
from datetime import datetime

# Import the core regime analyzer
from core_engine.regime.market_regime_analyzer import MarketRegimeAnalyzer, RegimeConfig
from core_engine.data.feeds.polygon_rest import PolygonRestService

logger = logging.getLogger("core_engine.symbolpicker.regime_adapter")

class RegimeAdapter:
    """
    Wraps the core MarketRegimeAnalyzer to generate regime labels for the symbol picker.
    Ensures the analyzer gets the broad market context it needs (SPY, TLT, etc.)
    even if the picker is focused on a narrow universe.
    """
    
    # Key benchmarks required for meaningful regime analysis
    BENCHMARKS = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'UUP']
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Initialize core analyzer with default config
        self.analyzer = MarketRegimeAnalyzer()
        
    async def generate_regime_label(self, 
                                  polygon_service: PolygonRestService,
                                  asof_date: datetime) -> Dict[str, Any]:
        """
        Fetch benchmark data and run the core regime analyzer.
        
        Args:
            polygon_service: Initialized Polygon service
            asof_date: The reference date for analysis
            
        Returns:
            Dict containing the regime label and metadata.
        """
        try:
            # 1. Fetch Benchmark Data (Lookback 252 days for robust macro analysis)
            logger.info("Fetching benchmark data for regime analysis...")
            bench_data = await polygon_service.get_bars_multi(
                self.BENCHMARKS, 
                timeframe='1d', 
                days=300 # ample buffer
            )
            
            # Filter empty results
            valid_data = {k: v for k, v in bench_data.items() if not v.empty}
            
            if not valid_data:
                logger.warning("No benchmark data available for regime analysis.")
                return self._default_regime()
                
            # 2. Run Analysis
            analysis = self.analyzer.analyze_market_regime(valid_data)
            
            # 3. Extract Simplified Output for Downstream
            if not analysis:
                return self._default_regime()
                
            summary = analysis.get('regime_summary', {})
            
            # Format strictly for the artifact
            return {
                "label": summary.get('primary_regime', 'UNKNOWN'),
                "risk_environment": summary.get('risk_environment', 'UNKNOWN'),
                "volatility_regime": summary.get('market_cycle', 'UNKNOWN'), # Mapping cycle to vol proxy roughly
                "confidence": summary.get('confidence', 0.0),
                "stress_levels": summary.get('stress_levels', {})
            }
            
        except Exception as e:
            logger.error(f"Error generating regime label: {e}")
            return self._default_regime()
            
    def _default_regime(self) -> Dict[str, Any]:
        return {
            "label": "UNKNOWN",
            "risk_environment": "UNKNOWN",
            "confidence": 0.0,
            "note": "Regime generation failed"
        }

