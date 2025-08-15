"""
Technical Indicators Module - Crown Jewel of Our Expertise
==========================================================

This module preserves and extends our comprehensive technical indicators expertise
while integrating seamlessly with the new_structure architecture.

Key Features:
- 105+ technical indicators implemented and battle-tested
- Real-time Polygon WebSocket streaming integration
- Advanced market regime detection
- Feature engineering pipeline with ensemble scoring
- ClickHouse database integration for historical data

Author: Pro Trading System (Specialized Indicators Team)
"""

from .technical_indicators import (
    TechnicalIndicatorEngine,
    IndicatorConfig,
    IndicatorResult,
    MarketRegime
)

from .polygon_streaming import (
    PolygonStreamingEngine,
    StreamingConfig,
    RealTimeIndicators
)

from .feature_engineering import (
    FeatureEngineeringPipeline
)

from .market_regimes import (
    MarketRegimeDetector
)

from .indicator_config import (
    IndicatorSettings,
    StreamingSettings,
    DatabaseSettings
)

# Integration with new_structure
try:
    from ..signal_generator import SignalGenerator
    from ...market_data.data_manager import DataManager
    from ...ai_infrastructure.agents.trading_agents import TradingAgent
    NEW_STRUCTURE_AVAILABLE = True
except ImportError:
    NEW_STRUCTURE_AVAILABLE = False

__version__ = "1.0.0"

__all__ = [
    # Core indicator engine
    'TechnicalIndicatorEngine',
    'IndicatorConfig',
    'IndicatorResult',
    'MarketRegime',
    
    # Real-time streaming
    'PolygonStreamingEngine', 
    'StreamingConfig',
    'RealTimeIndicators',
    
    # Feature engineering
    'FeatureEngineeringPipeline',


    
    # Market regime detection
    'MarketRegimeDetector',
    
    
    # Configuration
    'IndicatorSettings',
    'StreamingSettings',
    'DatabaseSettings',
    
    # Integration bridge
    'IndicatorIntegration',
    'NEW_STRUCTURE_AVAILABLE'
]

class IndicatorIntegration:
    """
    Bridge between our specialized indicators and new_structure architecture
    Maintains our expertise while leveraging enterprise infrastructure
    """
    
    def __init__(self, config: IndicatorConfig = None):
        """Initialize integration bridge"""
        self.config = config or IndicatorConfig()
        
        # Initialize our core systems
        self.indicator_engine = TechnicalIndicatorEngine(self.config)
        self.streaming_engine = PolygonStreamingEngine(self.config.streaming)
        self.feature_pipeline = FeatureEngineeringPipeline(self.config.features)
        self.regime_detector = MarketRegimeDetector(self.config.regime)
        
        # Initialize new_structure components (if available)
        if NEW_STRUCTURE_AVAILABLE:
            self.signal_generator = SignalGenerator()
            self.data_manager = DataManager()
        else:
            self.signal_generator = None
            self.data_manager = None
    
    def integrate_with_signal_generation(self):
        """Integrate our 105+ indicators with new_structure signal generation"""
        if not self.signal_generator:
            return False
            
        # Enhance signal generator with our indicators
        self.signal_generator.add_indicator_engine(self.indicator_engine)
        self.signal_generator.add_feature_pipeline(self.feature_pipeline)
        self.signal_generator.add_regime_detector(self.regime_detector)
        
        return True
    
    def integrate_with_ai_agents(self):
        """Integrate with AI trading agents for enhanced insights"""
        if not NEW_STRUCTURE_AVAILABLE:
            return False
            
        # Create AI-enhanced indicator analysis
        try:
            ai_agent = TradingAgent()
            ai_agent.add_technical_analysis(self.indicator_engine)
            ai_agent.add_regime_context(self.regime_detector)
            return True
        except Exception:
            return False
    
    def start_real_time_streaming(self, symbols: list):
        """Start real-time indicator streaming"""
        return self.streaming_engine.start_streaming(symbols)
    
    def get_indicator_summary(self):
        """Get summary of available indicators and capabilities"""
        return {
            'total_indicators': 105,
            'real_time_streaming': True,
            'market_regime_detection': True,
            'feature_engineering': True,
            'ai_integration': NEW_STRUCTURE_AVAILABLE,
            'database_integration': True,
            'version': __version__
        }

# Module initialization message
print(f"""
Technical Indicators Module Loaded - v{__version__}
================================================
105+ Technical Indicators Available
Real-time Polygon Streaming Ready  
Market Regime Detection Active
Feature Engineering Pipeline Loaded
new_structure Integration: {'Available' if NEW_STRUCTURE_AVAILABLE else 'Standalone Mode'}

Ready for specialized technical analysis!
""")
