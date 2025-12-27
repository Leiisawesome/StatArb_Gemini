"""
Adapter for the Core Engine's Regime Analyzer.
"""
import pandas as pd
import logging
from typing import Dict, Any, List
from datetime import datetime

# Import the core regime engine and canonical regime type
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.type_definitions.regime import MarketRegime
from core_engine.data.feeds.polygon_rest import PolygonRestService

logger = logging.getLogger("core_engine.picker.regime_adapter")

class RegimeAdapter:
    """
    Wraps the core EnhancedRegimeEngine to generate regime labels for the symbol picker.
    Ensures the analyzer gets the broad market context it needs (SPY)
    consistent with how the live trading engine detects regime.
    """
    
    # Primary benchmark used for canonical regime detection
    BENCHMARK = 'SPY'
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Initialize core engine with default config
        self.engine = EnhancedRegimeEngine({})
        
    async def generate_regime_label(self, 
                                  polygon_service: PolygonRestService,
                                  asof_date: datetime) -> Dict[str, Any]:
        """
        Fetch benchmark data and run the canonical regime engine.
        
        Args:
            polygon_service: Initialized Polygon service
            asof_date: The reference date for analysis
            
        Returns:
            Dict containing the regime label and metadata.
        """
        try:
            # 1. Fetch Benchmark Data (Lookback 200 days for indicator warmup)
            logger.info(f"Fetching {self.BENCHMARK} data for regime analysis as of {asof_date.strftime('%Y-%m-%d')}...")
            
            # We need enough history for the engine's lookback_window (default 60)
            bench_df = await polygon_service.get_bars(
                self.BENCHMARK, 
                timeframe='1d', 
                days=200,
                end=asof_date
            )
            
            if bench_df.empty:
                logger.warning(f"No {self.BENCHMARK} data available for regime analysis.")
                return self._default_regime()
                
            # 2. Run Engine
            # EnhancedRegimeEngine.process_market_data(df) expects a dataframe with symbol column or assumes single symbol
            bench_df['symbol'] = self.BENCHMARK
            result = self.engine.process_market_data(bench_df)
            
            # 3. Extract Structured Output
            if not result or not result.get('market_data_processed'):
                logger.warning("Regime engine failed to process market data.")
                return self._default_regime()
                
            # The engine stores the last analysis in self.engine.current_regime
            analysis = self.engine.current_regime
            if not analysis:
                return self._default_regime()
                
            # Format strictly for the artifact (v3 schema)
            return {
                "primary": analysis.primary_regime.value,
                "confidence": float(analysis.confidence),
                "asof_date": asof_date.strftime('%Y-%m-%d'),
                "details": {
                    "directional": analysis.directional_regime,
                    "volatility": analysis.volatility_regime,
                    "stress": float(analysis.stress_level)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating regime label: {e}")
            return self._default_regime()
            
    def _default_regime(self) -> Dict[str, Any]:
        return {
            "primary": MarketRegime.UNKNOWN.value,
            "confidence": 0.0,
            "asof_date": None,
            "note": "Regime generation failed"
        }

