# 🚀 StatArb Gemini Enhancement Plan - REVISED
## Core System Focus with Clear Separation

### 📊 **Revised Approach Based on Feedback**

**Key Principles:**
1. ✅ **Use local ClickHouse data** (2.5 years) instead of Polygon.io historical
2. ✅ **All enhancements in core system** (indicators → signals → features → execution)
3. ✅ **Clear separation** between backtesting framework and core system
4. ✅ **Same strategy implementation** for historical backtesting and real-time
5. ✅ **Comprehensive configuration mechanism** for consistent architecture

---

## 🎯 **Phase 0: Configuration Architecture Enhancement**

### **0.1 Unified Configuration Management System**

**File: `core_structure/infrastructure/config/enhanced_config_manager.py`**

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import yaml
import json
import os
from pathlib import Path
from enum import Enum
from datetime import datetime

class Environment(Enum):
    DEVELOPMENT = "development"
    BACKTESTING = "backtesting"
    PRODUCTION = "production"
    REAL_TIME = "real_time"

@dataclass
class StrategyConfig:
    """Strategy-specific configuration"""
    name: str
    version: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_limits: Dict[str, float] = field(default_factory=dict)
    timeframes: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'parameters': self.parameters,
            'risk_limits': self.risk_limits,
            'timeframes': self.timeframes,
            'symbols': self.symbols
        }

@dataclass
class TrainingConfig:
    """Training period configuration"""
    start_date: str
    end_date: str
    validation_split: float = 0.2
    parameter_optimization: bool = True
    optimization_method: str = "grid_search"  # grid_search, bayesian, genetic
    optimization_metrics: List[str] = field(default_factory=lambda: ["sharpe_ratio", "max_drawdown"])
    
@dataclass
class TradingConfig:
    """Trading period configuration"""
    start_date: str
    end_date: str
    real_time: bool = False
    execution_mode: str = "simulation"  # simulation, paper, live
    position_sizing: str = "fixed"  # fixed, kelly, volatility_targeting

@dataclass
class EnhancedConfig:
    """Enhanced unified configuration"""
    environment: Environment
    strategy: StrategyConfig
    training: Optional[TrainingConfig] = None
    trading: TradingConfig
    database: Dict[str, Any] = field(default_factory=dict)
    data_feeds: Dict[str, Any] = field(default_factory=dict)
    execution: Dict[str, Any] = field(default_factory=dict)
    risk_management: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    
    def save_to_file(self, filepath: str):
        """Save configuration to file"""
        config_dict = {
            'environment': self.environment.value,
            'strategy': self.strategy.to_dict(),
            'training': self.training.__dict__ if self.training else None,
            'trading': self.trading.__dict__,
            'database': self.database,
            'data_feeds': self.data_feeds,
            'execution': self.execution,
            'risk_management': self.risk_management,
            'logging': self.logging
        }
        
        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'EnhancedConfig':
        """Load configuration from file"""
        with open(filepath, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        return cls._from_dict(config_dict)
    
    @classmethod
    def _from_dict(cls, config_dict: Dict[str, Any]) -> 'EnhancedConfig':
        """Create config from dictionary"""
        return cls(
            environment=Environment(config_dict['environment']),
            strategy=StrategyConfig(**config_dict['strategy']),
            training=TrainingConfig(**config_dict['training']) if config_dict.get('training') else None,
            trading=TradingConfig(**config_dict['trading']),
            database=config_dict.get('database', {}),
            data_feeds=config_dict.get('data_feeds', {}),
            execution=config_dict.get('execution', {}),
            risk_management=config_dict.get('risk_management', {}),
            logging=config_dict.get('logging', {})
        )

class EnhancedConfigManager:
    """Enhanced configuration manager with parameter persistence"""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.current_config: Optional[EnhancedConfig] = None
        
    def create_step1_backtesting_config(self, strategy_name: str, 
                                       training_start: str, training_end: str,
                                       validation_start: str, validation_end: str) -> EnhancedConfig:
        """Create Step 1 backtesting configuration (historical data)"""
        
        # Load base strategy config
        strategy_config = self._load_strategy_config(strategy_name)
        
        config = EnhancedConfig(
            environment=Environment.BACKTESTING,
            strategy=strategy_config,
            training=TrainingConfig(
                start_date=training_start,
                end_date=training_end,
                parameter_optimization=True,
                optimization_method="grid_search"
            ),
            trading=TradingConfig(
                start_date=validation_start,
                end_date=validation_end,
                real_time=False,
                execution_mode="simulation"
            ),
            database=self._get_database_config(),
            data_feeds=self._get_step1_data_feeds_config(),
            execution=self._get_execution_config(),
            risk_management=self._get_risk_config(),
            logging=self._get_logging_config()
        )
        
        return config
    
    def create_step2_realtime_config(self, strategy_name: str, 
                                    trading_start: str) -> EnhancedConfig:
        """Create Step 2 real-time configuration (Polygon.io data)"""
        
        # Load optimized parameters from Step 1
        optimized_params = self._load_optimized_parameters(strategy_name)
        
        strategy_config = self._load_strategy_config(strategy_name)
        strategy_config.parameters.update(optimized_params)
        
        config = EnhancedConfig(
            environment=Environment.REAL_TIME,
            strategy=strategy_config,
            trading=TradingConfig(
                start_date=trading_start,
                end_date="",  # Ongoing
                real_time=True,
                execution_mode="simulation"  # Change to "paper" or "live" when ready
            ),
            database=self._get_database_config(),
            data_feeds=self._get_step2_data_feeds_config(),
            execution=self._get_execution_config(),
            risk_management=self._get_risk_config(),
            logging=self._get_logging_config()
        )
        
        return config
    
    def create_real_time_config(self, strategy_name: str, 
                               trading_start: str) -> EnhancedConfig:
        """Create real-time configuration"""
        
        # Load optimized parameters from training
        optimized_params = self._load_optimized_parameters(strategy_name)
        
        strategy_config = self._load_strategy_config(strategy_name)
        strategy_config.parameters.update(optimized_params)
        
        config = EnhancedConfig(
            environment=Environment.REAL_TIME,
            strategy=strategy_config,
            trading=TradingConfig(
                start_date=trading_start,
                end_date="",  # Ongoing
                real_time=True,
                execution_mode="simulation"  # Change to "paper" or "live" when ready
            ),
            database=self._get_database_config(),
            data_feeds=self._get_data_feeds_config(),
            execution=self._get_execution_config(),
            risk_management=self._get_risk_config(),
            logging=self._get_logging_config()
        )
        
        return config
    
    def save_optimized_parameters(self, strategy_name: str, 
                                 parameters: Dict[str, Any],
                                 performance_metrics: Dict[str, float]):
        """Save optimized parameters from training"""
        
        param_file = self.config_dir / f"{strategy_name}_optimized_params.json"
        
        param_data = {
            'parameters': parameters,
            'performance_metrics': performance_metrics,
            'optimization_date': datetime.now().isoformat(),
            'training_period': {
                'start': self.current_config.training.start_date,
                'end': self.current_config.training.end_date
            }
        }
        
        with open(param_file, 'w') as f:
            json.dump(param_data, f, indent=2)
    
    def _load_optimized_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Load optimized parameters from training"""
        
        param_file = self.config_dir / f"{strategy_name}_optimized_params.json"
        
        if not param_file.exists():
            return {}
        
        with open(param_file, 'r') as f:
            param_data = json.load(f)
        
        return param_data.get('parameters', {})
    
    def _load_strategy_config(self, strategy_name: str) -> StrategyConfig:
        """Load strategy configuration"""
        
        strategy_file = self.config_dir / f"{strategy_name}_strategy.yaml"
        
        if not strategy_file.exists():
            raise FileNotFoundError(f"Strategy config not found: {strategy_file}")
        
        with open(strategy_file, 'r') as f:
            strategy_dict = yaml.safe_load(f)
        
        return StrategyConfig(**strategy_dict)
    
    def _get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'clickhouse': {
                'host': 'localhost',
                'port': 9000,
                'database': 'market_data',
                'user': 'default',
                'password': ''
            }
        }
    
    def _get_step1_data_feeds_config(self) -> Dict[str, Any]:
        """Get Step 1 data feeds configuration (historical data only)"""
        return {
            'clickhouse': {
                'historical_data': True,
                'real_time_updates': False,
                'data_source': 'local',
                'cache_enabled': True
            },
            'polygon': {
                'enabled': False,  # Not used in Step 1
                'api_key': os.getenv('POLYGON_API_KEY')
            }
        }
    
    def _get_step2_data_feeds_config(self) -> Dict[str, Any]:
        """Get Step 2 data feeds configuration (real-time data)"""
        return {
            'polygon': {
                'api_key': os.getenv('POLYGON_API_KEY'),
                'websocket_url': 'wss://socket.polygon.io/stocks',
                'rate_limit': 1000,  # Unlimited with starter plan
                'real_time_delay': 15,  # 15-minute delay
                'enabled': True
            },
            'clickhouse': {
                'historical_data': False,  # Not used in Step 2
                'real_time_updates': False,
                'data_source': 'polygon'
            }
        }
    
    def _get_execution_config(self) -> Dict[str, Any]:
        """Get execution configuration with enhanced transaction cost modeling"""
        return {
            'simulation': {
                'enabled': True,
                'initial_capital': 10_000_000,
                'commission_rate': 0.001,  # 10 bps
                'slippage': 0.0001,        # 1 bp
                'market_impact': 0.0002,   # 2 bps (simple linear model)
                'min_trade_size': 1000,    # $1K minimum trade
                'max_trade_size': 1000000  # $1M maximum trade
            },
            'paper_trading': {
                'enabled': False,
                'broker': 'alpaca',
                'api_key': os.getenv('ALPACA_API_KEY'),
                'secret_key': os.getenv('ALPACA_SECRET_KEY'),
                'commission_rate': 0.0005,  # 5 bps for paper trading
                'slippage': 0.0001
            },
            'live_trading': {
                'enabled': False,
                'broker': 'alpaca',
                'api_key': os.getenv('ALPACA_LIVE_API_KEY'),
                'secret_key': os.getenv('ALPACA_LIVE_SECRET_KEY'),
                'commission_rate': 0.0005,  # 5 bps for live trading
                'slippage': 0.0001
            }
        }
    
    def _get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration"""
        return {
            'position_limits': {
                'max_position_size': 5_000_000,  # $5M per position
                'max_portfolio_concentration': 0.2,  # 20% max concentration
                'max_daily_trades': 100
            },
            'risk_limits': {
                'max_daily_loss': 0.02,  # 2% daily loss limit
                'max_drawdown': 0.15,  # 15% max drawdown
                'var_limit': 0.01  # 1% VaR limit
            },
            'stop_loss': {
                'enabled': True,
                'percentage': 0.05,  # 5% stop loss
                'trailing': True
            }
        }
    
    def _get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            'level': 'INFO',
            'file': 'logs/trading.log',
            'max_size': '100MB',
            'backup_count': 5,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
```

### **0.2 Strategy Configuration Templates**

**File: `configs/strategies/enhanced_momentum_strategy.yaml`**

```yaml
# Enhanced Momentum Strategy Configuration with Academic Foundation
name: "enhanced_momentum"
version: "2.0.0"

# Academic Research Foundation
academic_basis:
  # Core momentum theories
  jegadeesh_titman_1993: true  # Cross-sectional momentum
  carhart_1997: true           # Four-factor model
  moskowitz_grinblatt_1999: true  # Industry momentum
  
  # Enhanced academic theories
  hong_stein_1999: true        # News diffusion model
  chordia_shivakumar_2002: true  # Business cycle effects
  cooper_gutierrez_hameed_2004: true  # Market states
  moskowitz_ooi_pedersen_2012: true  # Time series momentum
  gervais_kaniel_mingelgrin_2001: true  # Volume premium
  daniel_moskowitz_2016: true  # Momentum crashes

# Strategy Parameters (will be optimized during training)
parameters:
  # Multi-horizon momentum (Moskowitz et al., 2012)
  momentum_lookback_short: 5    # 1 week
  momentum_lookback_medium: 21  # 1 month
  momentum_lookback_long: 63    # 3 months
  momentum_lookback_intermediate: 126  # 6 months
  
  # Multi-horizon weights
  short_term_weight: 0.2
  medium_term_weight: 0.3
  long_term_weight: 0.3
  intermediate_weight: 0.2
  
  # Volume-weighted momentum (Gervais et al., 2001)
  volume_weight: 0.3
  volume_threshold: 1000000
  volume_lookback: 20
  
  # Market regime detection (Cooper et al., 2004)
  regime_lookback: 252
  volatility_threshold: 0.25
  market_state_threshold: 0.0
  
  # Crash protection (Daniel & Moskowitz, 2016)
  crash_volatility_threshold: 0.40
  crash_market_drawdown_threshold: -0.15
  
  # Business cycle effects (Chordia & Shivakumar, 2002)
  gdp_growth_weight: 0.2
  inflation_weight: 0.1
  interest_rate_weight: 0.1
  
  # Signal combination parameters
  signal_threshold: 0.7
  confirmation_weight: 0.4
  divergence_weight: 0.3
  
  # Risk management parameters
  position_size: 0.1
  max_positions: 10
  stop_loss: 0.05
  take_profit: 0.15

# SPY Benchmark Configuration
benchmark:
  symbol: "SPY"
  risk_free_rate: 0.02
  target_information_ratio: 1.0
  target_sharpe_ratio: 1.5
  max_tracking_error: 0.15
  max_beta: 0.3

# Risk Limits
risk_limits:
  max_position_value: 5000000
  max_daily_loss: 0.02
  max_drawdown: 0.15
  max_correlation: 0.7

# Timeframes for multi-timeframe analysis
timeframes:
  - "1min"
  - "5min"
  - "15min"
  - "1hour"
  - "1day"

# Trading symbols (including SPY for benchmark)
symbols:
  - "SPY"  # Benchmark
  - "AAPL"
  - "MSFT"
  - "GOOGL"
  - "AMZN"
  - "TSLA"
  - "NVDA"
  - "META"
  - "NFLX"
  - "AMD"
  - "CRM"

# Minimal Quality Assurance
data_quality:
  enabled: true
  min_data_points: 252
  max_missing_data: 0.05
  validate_price_range: true

error_handling:
  enabled: true
  log_errors: true
  skip_invalid_data: true

academic_validation:
  enabled: true
  validate_parameters: true
  parameter_ranges: true

performance_attribution:
  enabled: false  # Optional - can be enabled if needed
  simple_correlation: true
```

**File: `configs/strategies/technical_momentum_strategy.yaml`**

```yaml
# Technical Momentum Strategy Configuration
name: "technical_momentum"
version: "1.0.0"

# Strategy Parameters
parameters:
  # Technical indicator parameters
  rsi_period: 14
  macd_fast: 12
  macd_slow: 26
  macd_signal: 9
  bollinger_period: 20
  bollinger_std: 2
  
  # Signal thresholds
  rsi_oversold: 30
  rsi_overbought: 70
  macd_threshold: 0.001
  bollinger_threshold: 0.02
  
  # Position sizing
  position_size: 0.1
  max_positions: 15

# Risk Limits
risk_limits:
  max_position_value: 3000000
  max_daily_loss: 0.015
  max_drawdown: 0.12

# Timeframes
timeframes:
  - "5min"
  - "15min"
  - "1hour"

# Trading symbols
symbols:
  - "AAPL"
  - "MSFT"
  - "GOOGL"
  - "AMZN"
  - "TSLA"
```

### **0.3 Configuration Validation and Persistence**

**File: `core_structure/infrastructure/config/config_validator.py`**

```python
from typing import Dict, Any, List
from dataclasses import dataclass
import jsonschema

@dataclass
class ValidationError:
    field: str
    message: str
    value: Any

class ConfigValidator:
    """Configuration validation and schema checking"""
    
    def __init__(self):
        self.schemas = self._load_validation_schemas()
    
    def validate_strategy_config(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate strategy configuration"""
        errors = []
        
        # Required fields
        required_fields = ['name', 'version', 'parameters', 'risk_limits', 'timeframes', 'symbols']
        for field in required_fields:
            if field not in config:
                errors.append(ValidationError(field, f"Required field missing: {field}", None))
        
        # Parameter validation
        if 'parameters' in config:
            param_errors = self._validate_parameters(config['parameters'])
            errors.extend(param_errors)
        
        # Risk limits validation
        if 'risk_limits' in config:
            risk_errors = self._validate_risk_limits(config['risk_limits'])
            errors.extend(risk_errors)
        
        return errors
    
    def _validate_parameters(self, parameters: Dict[str, Any]) -> List[ValidationError]:
        """Validate strategy parameters"""
        errors = []
        
        # Check for reasonable parameter ranges
        if 'momentum_lookback_short' in parameters:
            value = parameters['momentum_lookback_short']
            if not (1 <= value <= 50):
                errors.append(ValidationError(
                    'momentum_lookback_short', 
                    f"Value {value} out of range [1, 50]", 
                    value
                ))
        
        if 'position_size' in parameters:
            value = parameters['position_size']
            if not (0.01 <= value <= 1.0):
                errors.append(ValidationError(
                    'position_size', 
                    f"Value {value} out of range [0.01, 1.0]", 
                    value
                ))
        
        return errors
    
    def _validate_risk_limits(self, risk_limits: Dict[str, Any]) -> List[ValidationError]:
        """Validate risk limits"""
        errors = []
        
        if 'max_daily_loss' in risk_limits:
            value = risk_limits['max_daily_loss']
            if not (0.001 <= value <= 0.1):
                errors.append(ValidationError(
                    'max_daily_loss', 
                    f"Value {value} out of range [0.001, 0.1]", 
                    value
                ))
        
        return errors
    
    def _load_validation_schemas(self) -> Dict[str, Any]:
        """Load JSON schemas for validation"""
        return {
            'strategy': {
                'type': 'object',
                'required': ['name', 'version', 'parameters', 'risk_limits'],
                'properties': {
                    'name': {'type': 'string'},
                    'version': {'type': 'string'},
                    'parameters': {'type': 'object'},
                    'risk_limits': {'type': 'object'}
                }
            }
        }
```

---

## 📚 **Academic Foundation & Research Basis**

### **🎯 Core Academic Theories (Current Implementation)**

**1. Jegadeesh & Titman (1993) - "Returns to Buying Winners and Selling Losers"**
- **Cross-sectional momentum**: Ranking stocks by past performance
- **12-month formation period**: Standard academic momentum window
- **Skip recent month**: Avoid short-term reversal effects
- **Risk-adjusted returns**: Momentum divided by volatility

**2. Carhart (1997) - "Four-Factor Model"**
- **Momentum as systematic factor**: MOM factor in asset pricing
- **Multi-factor framework**: Market, Size, Value, Momentum
- **Sector-neutral implementation**: Controls for sector effects

**3. Moskowitz & Grinblatt (1999) - "Do Industries Explain Momentum?"**
- **Industry momentum**: Much of stock momentum is industry-driven
- **Sector-neutral momentum**: More robust than raw momentum
- **Cross-sectional ranking**: Within-sector momentum ranking

### **🚀 Enhanced Academic Foundation (New Additions)**

**4. Hong & Stein (1999) - "A Unified Theory of Underreaction and Overreaction"**
- **News diffusion model**: Gradual information incorporation
- **Analyst coverage effects**: Momentum stronger in low-coverage stocks
- **Earnings momentum**: Fundamental momentum signals
- **Implementation**: Multi-horizon momentum with volume weighting

**5. Chordia & Shivakumar (2002) - "Momentum, Business Cycle, and Time-Varying Expected Returns"**
- **Business cycle effects**: Momentum varies with economic conditions
- **Macroeconomic factors**: GDP, inflation, interest rate effects
- **Time-varying risk premia**: Dynamic risk adjustment
- **Implementation**: Market regime detection with macro factors

**6. Cooper, Gutierrez & Hameed (2004) - "Market States and Momentum"**
- **Market state dependence**: Momentum stronger in up markets
- **Volatility regimes**: Different momentum performance in high/low vol
- **Conditional momentum**: Market-adaptive signals
- **Implementation**: Regime-dependent signal weighting

**7. Moskowitz, Ooi & Pedersen (2012) - "Time Series Momentum"**
- **Multi-horizon momentum**: 1-month to 12-month horizons
- **Asset class momentum**: Works across stocks, bonds, commodities
- **Volatility scaling**: Risk-adjusted position sizing
- **Implementation**: Multi-timeframe momentum signals

**8. Gervais, Kaniel & Mingelgrin (2001) - "The High-Volume Return Premium"**
- **Volume-momentum interaction**: High volume predicts momentum
- **Volume-weighted signals**: Enhanced momentum with volume
- **Liquidity effects**: Volume as proxy for information flow
- **Implementation**: Volume-weighted momentum indicators

**9. Daniel & Moskowitz (2016) - "Momentum Crashes"**
- **Momentum crashes**: Sharp reversals during market stress
- **Regime-dependent performance**: Momentum works differently in different markets
- **Dynamic signal decay**: Adapt to changing market conditions
- **Implementation**: Crash protection with regime detection

### **📊 SPY Benchmark Integration**

**Benchmark: SPDR S&P 500 ETF (SPY)**
- **Market proxy**: Represents broad US equity market
- **Liquidity**: Most liquid ETF for execution
- **Risk-free rate**: 3-month Treasury yield for excess returns
- **Performance metrics**: Sharpe ratio, information ratio, maximum drawdown

**Optimization Objectives:**
1. **Maximize Information Ratio**: (Strategy Return - SPY Return) / Tracking Error
2. **Minimize Maximum Drawdown**: Relative to SPY drawdown
3. **Maximize Sharpe Ratio**: Risk-adjusted returns vs SPY
4. **Minimize Beta**: Low correlation with market movements

---

## 🎯 **Phase 1: Core System Enhancements**

### **1.1 Enhanced Technical Indicators Engine**

**File: `core_structure/signal_generation/indicators/enhanced_technical_indicators.py`**

```python
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum

class MomentumHorizon(Enum):
    """Multi-horizon momentum based on Moskowitz et al. (2012)"""
    SHORT_TERM = "1w"      # 1 week (5 days)
    MEDIUM_TERM = "1m"     # 1 month (21 days)
    LONG_TERM = "3m"       # 3 months (63 days)
    INTERMEDIATE = "6m"    # 6 months (126 days)
    LONG_TERM_EXTENDED = "12m"  # 12 months (252 days)

class RegimeType(Enum):
    """Market regimes based on Cooper et al. (2004)"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    MOMENTUM_CRASH = "momentum_crash"

@dataclass
class AcademicMomentumConfig:
    """Academic momentum configuration based on latest research"""
    
    # Multi-horizon momentum (Moskowitz et al., 2012)
    momentum_horizons: List[MomentumHorizon] = field(default_factory=lambda: [
        MomentumHorizon.SHORT_TERM,
        MomentumHorizon.MEDIUM_TERM,
        MomentumHorizon.LONG_TERM,
        MomentumHorizon.INTERMEDIATE
    ])
    
    # Volume-weighted momentum (Gervais et al., 2001)
    volume_weight: float = 0.3
    volume_threshold: float = 1_000_000  # $1M minimum volume
    volume_lookback: int = 20  # 20-day volume average
    
    # Regime detection (Cooper et al., 2004)
    regime_lookback: int = 252  # 1 year for regime detection
    volatility_threshold: float = 0.25  # 25% volatility threshold
    market_state_threshold: float = 0.0  # 0% market return threshold
    
    # Crash protection (Daniel & Moskowitz, 2016)
    crash_detection_enabled: bool = True
    crash_volatility_threshold: float = 0.40  # 40% volatility for crash detection
    crash_market_drawdown_threshold: float = -0.15  # -15% market drawdown
    
    # Business cycle effects (Chordia & Shivakumar, 2002)
    macro_factor_enabled: bool = True
    gdp_growth_weight: float = 0.2
    inflation_weight: float = 0.1
    interest_rate_weight: float = 0.1
    
    # News diffusion (Hong & Stein, 1999)
    analyst_coverage_weight: float = 0.15
    earnings_momentum_weight: float = 0.25
    news_sentiment_weight: float = 0.1
    
    def __post_init__(self):
        """Validate academic parameters on initialization"""
        self._validate_momentum_parameters()
        self._validate_volume_parameters()
        self._validate_regime_parameters()
    
    def _validate_momentum_parameters(self):
        """Validate momentum parameters based on academic research"""
        # Validate momentum lookback periods (academic research ranges)
        if not (1 <= self.momentum_lookback_short <= 50):
            raise ValueError("Short-term momentum should be 1-50 days")
        
        if not (20 <= self.momentum_lookback_medium <= 100):
            raise ValueError("Medium-term momentum should be 20-100 days")
        
        if not (50 <= self.momentum_lookback_long <= 150):
            raise ValueError("Long-term momentum should be 50-150 days")
    
    def _validate_volume_parameters(self):
        """Validate volume parameters"""
        # Validate volume threshold (reasonable range)
        if self.volume_threshold < 100000:  # $100K minimum
            raise ValueError("Volume threshold too low (minimum $100K)")
        
        if self.volume_threshold > 10000000:  # $10M maximum
            raise ValueError("Volume threshold too high (maximum $10M)")
        
        # Validate volume weight
        if not (0.0 <= self.volume_weight <= 1.0):
            raise ValueError("Volume weight should be between 0 and 1")
    
    def _validate_regime_parameters(self):
        """Validate regime detection parameters"""
        # Validate regime lookback
        if not (100 <= self.regime_lookback <= 500):
            raise ValueError("Regime lookback should be 100-500 days")
        
        # Validate volatility threshold (empirical ranges)
        if not (0.1 <= self.volatility_threshold <= 0.5):
            raise ValueError("Volatility threshold should be 10-50%")
        
        # Validate crash thresholds
        if not (0.2 <= self.crash_volatility_threshold <= 0.6):
            raise ValueError("Crash volatility threshold should be 20-60%")
        
        if not (-0.3 <= self.crash_market_drawdown_threshold <= -0.05):
            raise ValueError("Crash drawdown threshold should be -30% to -5%")

class EnhancedTechnicalIndicatorEngine:
    """Enhanced technical indicators with latest academic foundations"""
    
    def __init__(self, config: AcademicMomentumConfig):
        self.config = config
        # Validate academic parameters on initialization
        self.config.__post_init__()
        
        self.regime_detector = MarketRegimeDetector(config)
        self.volume_analyzer = VolumeMomentumAnalyzer(config)
        self.crash_protector = MomentumCrashProtector(config)
        
        # Minimal data quality and error handling
        self.data_quality_enabled = True
        self.error_handling_enabled = True
        
    def calculate_academic_momentum_signals(self, data: Dict[str, pd.DataFrame], 
                                          spy_data: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Calculate momentum signals based on latest academic research with minimal validation"""
        
        signals = {}
        
        for symbol, symbol_data in data.items():
            if symbol == 'SPY':
                continue  # Skip benchmark
                
            # Minimal data quality validation
            if self.data_quality_enabled and not self._validate_data_for_momentum(symbol_data):
                logger.warning(f"Skipping {symbol} - insufficient data quality")
                continue
            
            # Generate signals with error handling
            try:
                symbol_signals = {}
                
                # 1. Multi-horizon momentum (Moskowitz et al., 2012)
                multi_horizon_signals = self._calculate_multi_horizon_momentum(symbol_data)
                symbol_signals.update(multi_horizon_signals)
                
                # 2. Volume-weighted momentum (Gervais et al., 2001)
                volume_signals = self._calculate_volume_weighted_momentum(symbol_data)
                symbol_signals.update(volume_signals)
                
                # 3. Regime-adjusted momentum (Cooper et al., 2004)
                regime_signals = self._calculate_regime_adjusted_momentum(symbol_data, spy_data)
                symbol_signals.update(regime_signals)
                
                # 4. Crash-protected momentum (Daniel & Moskowitz, 2016)
                crash_signals = self._calculate_crash_protected_momentum(symbol_data, spy_data)
                symbol_signals.update(crash_signals)
                
                # 5. Business cycle adjusted momentum (Chordia & Shivakumar, 2002)
                macro_signals = self._calculate_macro_adjusted_momentum(symbol_data, spy_data)
                symbol_signals.update(macro_signals)
                
                signals[symbol] = symbol_signals
                
            except Exception as e:
                if self.error_handling_enabled:
                    logger.error(f"Signal calculation failed for {symbol}: {e}")
                    continue
                else:
                    raise
        
        return signals
    
    def _calculate_multi_horizon_momentum(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate multi-horizon momentum (Moskowitz et al., 2012) with error handling"""
        signals = {}
        
        horizon_periods = {
            MomentumHorizon.SHORT_TERM: 5,
            MomentumHorizon.MEDIUM_TERM: 21,
            MomentumHorizon.LONG_TERM: 63,
            MomentumHorizon.INTERMEDIATE: 126
        }
        
        try:
            returns = data['close'].pct_change()
            
            for horizon, period in horizon_periods.items():
                if len(data) >= period:
                    # Calculate momentum for each horizon
                    momentum = returns.rolling(period).mean()
                    volatility = returns.rolling(period).std()
                    
                    # Risk-adjusted momentum with division by zero protection
                    if volatility.iloc[-1] > 0:
                        risk_adjusted_momentum = momentum / volatility
                        signals[f'momentum_{horizon.value}'] = risk_adjusted_momentum.iloc[-1]
                    else:
                        signals[f'momentum_{horizon.value}'] = 0.0
                    
                    # Skip recent month to avoid reversal (Jegadeesh & Titman, 1993)
                    if len(data) >= period + 21:
                        skip_momentum = returns.iloc[:-21].rolling(period).mean()
                        skip_volatility = returns.iloc[:-21].rolling(period).std()
                        if skip_volatility.iloc[-1] > 0:
                            skip_risk_adjusted = skip_momentum / skip_volatility
                            signals[f'momentum_{horizon.value}_skip'] = skip_risk_adjusted.iloc[-1]
                        else:
                            signals[f'momentum_{horizon.value}_skip'] = 0.0
                            
        except Exception as e:
            if self.error_handling_enabled:
                logger.error(f"Multi-horizon momentum calculation failed: {e}")
                return {}
            else:
                raise
        
        return signals
    
    def _calculate_volume_weighted_momentum(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume-weighted momentum (Gervais et al., 2001)"""
        signals = {}
        
        if 'volume' not in data.columns:
            return signals
        
        # Calculate volume-weighted returns
        returns = data['close'].pct_change()
        volume = data['volume']
        
        # Volume threshold filter
        volume_threshold = self.config.volume_threshold
        high_volume_mask = volume > volume_threshold
        
        # Volume-weighted momentum
        volume_weighted_returns = returns * volume
        volume_weighted_momentum = volume_weighted_returns.rolling(20).mean()
        
        # High-volume momentum premium
        high_volume_momentum = returns[high_volume_mask].rolling(20).mean()
        
        signals['volume_weighted_momentum'] = volume_weighted_momentum.iloc[-1]
        signals['high_volume_momentum'] = high_volume_momentum.iloc[-1] if len(high_volume_momentum) > 0 else 0
        
        return signals
    
    def _calculate_regime_adjusted_momentum(self, data: pd.DataFrame, 
                                          spy_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate regime-adjusted momentum (Cooper et al., 2004)"""
        signals = {}
        
        # Detect market regime
        regime = self.regime_detector.detect_regime(spy_data)
        
        # Calculate base momentum
        returns = data['close'].pct_change()
        base_momentum = returns.rolling(63).mean() / returns.rolling(63).std()
        
        # Regime-dependent adjustment
        if regime == RegimeType.BULL_MARKET:
            # Momentum stronger in bull markets
            regime_adjusted = base_momentum * 1.2
        elif regime == RegimeType.BEAR_MARKET:
            # Momentum weaker in bear markets
            regime_adjusted = base_momentum * 0.8
        elif regime == RegimeType.HIGH_VOLATILITY:
            # Momentum crashes in high volatility
            regime_adjusted = base_momentum * 0.5
        elif regime == RegimeType.MOMENTUM_CRASH:
            # Crash protection
            regime_adjusted = base_momentum * 0.0
        else:
            regime_adjusted = base_momentum
        
        signals['regime_adjusted_momentum'] = regime_adjusted.iloc[-1]
        signals['market_regime'] = regime.value
        
        return signals
    
    def _calculate_crash_protected_momentum(self, data: pd.DataFrame, 
                                          spy_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate crash-protected momentum (Daniel & Moskowitz, 2016)"""
        signals = {}
        
        if not self.config.crash_detection_enabled:
            return signals
        
        # Detect momentum crash conditions
        spy_returns = spy_data['close'].pct_change()
        spy_volatility = spy_returns.rolling(20).std()
        spy_drawdown = (spy_data['close'] / spy_data['close'].rolling(252).max() - 1)
        
        # Crash detection
        is_crash = (
            spy_volatility.iloc[-1] > self.config.crash_volatility_threshold or
            spy_drawdown.iloc[-1] < self.config.crash_market_drawdown_threshold
        )
        
        # Calculate base momentum
        returns = data['close'].pct_change()
        base_momentum = returns.rolling(63).mean() / returns.rolling(63).std()
        
        # Apply crash protection
        if is_crash:
            crash_protected_momentum = 0.0  # Zero out momentum during crashes
            signals['crash_protection_active'] = 1.0
        else:
            crash_protected_momentum = base_momentum.iloc[-1]
            signals['crash_protection_active'] = 0.0
        
        signals['crash_protected_momentum'] = crash_protected_momentum
        
        return signals
    
    def _calculate_macro_adjusted_momentum(self, data: pd.DataFrame, 
                                         spy_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate macro-adjusted momentum (Chordia & Shivakumar, 2002)"""
        signals = {}
        
        if not self.config.macro_factor_enabled:
            return signals
        
        # Calculate base momentum
        returns = data['close'].pct_change()
        base_momentum = returns.rolling(63).mean() / returns.rolling(63).std()
        
        # Macro factor adjustments (simplified proxies)
        # GDP growth proxy: Market trend
        market_trend = spy_data['close'].pct_change(252).iloc[-1]
        gdp_adjustment = market_trend * self.config.gdp_growth_weight
        
        # Inflation proxy: Volatility trend
        spy_volatility = spy_data['close'].pct_change().rolling(20).std()
        inflation_proxy = spy_volatility.pct_change(60).iloc[-1]
        inflation_adjustment = inflation_proxy * self.config.inflation_weight
        
        # Interest rate proxy: Market beta
        market_returns = spy_data['close'].pct_change()
        beta = returns.rolling(60).cov(market_returns) / market_returns.rolling(60).var()
        interest_rate_adjustment = beta.iloc[-1] * self.config.interest_rate_weight
        
        # Apply macro adjustments
        macro_adjusted_momentum = (
            base_momentum.iloc[-1] + 
            gdp_adjustment + 
            inflation_adjustment + 
            interest_rate_adjustment
        )
        
        signals['macro_adjusted_momentum'] = macro_adjusted_momentum
        signals['gdp_adjustment'] = gdp_adjustment
        signals['inflation_adjustment'] = inflation_adjustment
        signals['interest_rate_adjustment'] = interest_rate_adjustment
        
        return signals

class MarketRegimeDetector:
    """Market regime detection based on Cooper et al. (2004)"""
    
    def __init__(self, config: AcademicMomentumConfig):
        self.config = config
    
    def detect_regime(self, spy_data: pd.DataFrame) -> RegimeType:
        """Detect current market regime"""
        
        returns = spy_data['close'].pct_change()
        
        # Calculate regime indicators
        market_return = returns.rolling(self.config.regime_lookback).mean().iloc[-1]
        volatility = returns.rolling(self.config.regime_lookback).std().iloc[-1]
        
        # Regime classification
        if volatility > self.config.crash_volatility_threshold:
            return RegimeType.MOMENTUM_CRASH
        elif volatility > self.config.volatility_threshold:
            return RegimeType.HIGH_VOLATILITY
        elif market_return > self.config.market_state_threshold:
            return RegimeType.BULL_MARKET
        else:
            return RegimeType.BEAR_MARKET

class VolumeMomentumAnalyzer:
    """Volume-momentum analysis based on Gervais et al. (2001)"""
    
    def __init__(self, config: AcademicMomentumConfig):
        self.config = config
    
    def analyze_volume_momentum(self, data: pd.DataFrame) -> Dict[str, float]:
        """Analyze volume-momentum interaction"""
        
        if 'volume' not in data.columns:
            return {}
        
        returns = data['close'].pct_change()
        volume = data['volume']
        
        # Volume-momentum correlation
        volume_momentum_corr = returns.rolling(20).corr(volume)
        
        # High-volume return premium
        high_volume_returns = returns[volume > self.config.volume_threshold]
        high_volume_premium = high_volume_returns.rolling(20).mean()
        
        return {
            'volume_momentum_correlation': volume_momentum_corr.iloc[-1],
            'high_volume_premium': high_volume_premium.iloc[-1] if len(high_volume_premium) > 0 else 0
        }

class MomentumCrashProtector:
    """Momentum crash protection based on Daniel & Moskowitz (2016)"""
    
    def __init__(self, config: AcademicMomentumConfig):
        self.config = config
    
    def detect_crash_conditions(self, spy_data: pd.DataFrame) -> bool:
        """Detect momentum crash conditions"""
        
        try:
            returns = spy_data['close'].pct_change()
            volatility = returns.rolling(20).std()
            drawdown = (spy_data['close'] / spy_data['close'].rolling(252).max() - 1)
            
                    return (
            volatility.iloc[-1] > self.config.crash_volatility_threshold or
            drawdown.iloc[-1] < self.config.crash_market_drawdown_threshold
        )
    except Exception as e:
        logger.error(f"Crash detection failed: {e}")
        return False  # Default to no crash if detection fails

    def _validate_data_for_momentum(self, data: pd.DataFrame) -> bool:
        """Minimal data validation for momentum calculations"""
        
        # Check minimum data length (need at least 1 year for momentum)
        if len(data) < 252:
            return False
        
        # Check for missing data (max 5% missing)
        if data['close'].isnull().sum() > len(data) * 0.05:
            return False
        
        # Check for price variation (no flat prices)
        if data['close'].std() == 0:
            return False
        
        # Check for reasonable price range
        if data['close'].min() <= 0 or data['close'].max() > 10000:
            return False
        
        return True
```
```

### **1.2 Enhanced Signal Generator with Academic Foundation**

**File: `core_structure/signal_generation/enhanced_signal_generator.py`**

```python
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum

@dataclass
class AcademicSignalConfig:
    """Academic signal generation configuration"""
    
    # Multi-horizon momentum weights (Moskowitz et al., 2012)
    short_term_weight: float = 0.2
    medium_term_weight: float = 0.3
    long_term_weight: float = 0.3
    intermediate_weight: float = 0.2
    
    # Volume weighting (Gervais et al., 2001)
    volume_weight: float = 0.3
    volume_threshold: float = 1_000_000
    
    # Regime-dependent weights (Cooper et al., 2004)
    bull_market_weight: float = 1.2
    bear_market_weight: float = 0.8
    high_volatility_weight: float = 0.5
    crash_weight: float = 0.0
    
    # Macro factor weights (Chordia & Shivakumar, 2002)
    gdp_weight: float = 0.2
    inflation_weight: float = 0.1
    interest_rate_weight: float = 0.1
    
    # Signal combination
    signal_threshold: float = 0.7
    confirmation_weight: float = 0.4
    divergence_weight: float = 0.3

class EnhancedSignalGenerator:
    """Enhanced signal generator with latest academic foundations"""
    
    def __init__(self, config: AcademicSignalConfig):
        self.config = config
        self.indicator_engine = EnhancedTechnicalIndicatorEngine(AcademicMomentumConfig())
        
    def generate_academic_momentum_signals(self, data: Dict[str, pd.DataFrame], 
                                         spy_data: pd.DataFrame) -> Dict[str, float]:
        """Generate momentum signals based on latest academic research"""
        
        # Calculate all academic momentum indicators
        academic_indicators = self.indicator_engine.calculate_academic_momentum_signals(data, spy_data)
        
        # Combine signals using academic weights
        combined_signals = {}
        
        for symbol, indicators in academic_indicators.items():
            if symbol == 'SPY':
                continue
                
            # Multi-horizon momentum combination (Moskowitz et al., 2012)
            multi_horizon_signal = self._combine_multi_horizon_signals(indicators)
            
            # Volume-weighted adjustment (Gervais et al., 2001)
            volume_adjusted_signal = self._apply_volume_weighting(indicators, multi_horizon_signal)
            
            # Regime-dependent adjustment (Cooper et al., 2004)
            regime_adjusted_signal = self._apply_regime_adjustment(indicators, volume_adjusted_signal)
            
            # Macro factor adjustment (Chordia & Shivakumar, 2002)
            macro_adjusted_signal = self._apply_macro_adjustment(indicators, regime_adjusted_signal)
            
            # Final signal combination
            final_signal = self._combine_academic_signals(indicators, macro_adjusted_signal)
            
            combined_signals[symbol] = final_signal
        
        return combined_signals
    
    def _combine_multi_horizon_signals(self, indicators: Dict[str, float]) -> float:
        """Combine multi-horizon momentum signals (Moskowitz et al., 2012)"""
        
        short_term = indicators.get('momentum_1w', 0)
        medium_term = indicators.get('momentum_1m', 0)
        long_term = indicators.get('momentum_3m', 0)
        intermediate = indicators.get('momentum_6m', 0)
        
        combined = (
            short_term * self.config.short_term_weight +
            medium_term * self.config.medium_term_weight +
            long_term * self.config.long_term_weight +
            intermediate * self.config.intermediate_weight
        )
        
        return combined
    
    def _apply_volume_weighting(self, indicators: Dict[str, float], 
                               base_signal: float) -> float:
        """Apply volume weighting (Gervais et al., 2001)"""
        
        volume_momentum = indicators.get('volume_weighted_momentum', 0)
        high_volume_premium = indicators.get('high_volume_momentum', 0)
        
        volume_adjustment = (
            volume_momentum * self.config.volume_weight +
            high_volume_premium * self.config.volume_weight
        )
        
        return base_signal + volume_adjustment
    
    def _apply_regime_adjustment(self, indicators: Dict[str, float], 
                                base_signal: float) -> float:
        """Apply regime-dependent adjustment (Cooper et al., 2004)"""
        
        regime = indicators.get('market_regime', 'bull_market')
        
        if regime == 'bull_market':
            weight = self.config.bull_market_weight
        elif regime == 'bear_market':
            weight = self.config.bear_market_weight
        elif regime == 'high_volatility':
            weight = self.config.high_volatility_weight
        elif regime == 'momentum_crash':
            weight = self.config.crash_weight
        else:
            weight = 1.0
        
        return base_signal * weight
    
    def _apply_macro_adjustment(self, indicators: Dict[str, float], 
                               base_signal: float) -> float:
        """Apply macro factor adjustment (Chordia & Shivakumar, 2002)"""
        
        gdp_adjustment = indicators.get('gdp_adjustment', 0)
        inflation_adjustment = indicators.get('inflation_adjustment', 0)
        interest_rate_adjustment = indicators.get('interest_rate_adjustment', 0)
        
        macro_adjustment = (
            gdp_adjustment * self.config.gdp_weight +
            inflation_adjustment * self.config.inflation_weight +
            interest_rate_adjustment * self.config.interest_rate_weight
        )
        
        return base_signal + macro_adjustment
    
    def _combine_academic_signals(self, indicators: Dict[str, float], 
                                 base_signal: float) -> float:
        """Combine all academic signals with confirmation and divergence"""
        
        # Base academic signal
        academic_signal = base_signal
        
        # Confirmation signals
        crash_protected = indicators.get('crash_protected_momentum', 0)
        regime_adjusted = indicators.get('regime_adjusted_momentum', 0)
        
        confirmation_signal = (crash_protected + regime_adjusted) / 2
        
        # Divergence signals (when different horizons disagree)
        short_term = indicators.get('momentum_1w', 0)
        long_term = indicators.get('momentum_3m', 0)
        divergence = abs(short_term - long_term)
        
        # Final combination
        final_signal = (
            academic_signal * (1 - self.config.confirmation_weight - self.config.divergence_weight) +
            confirmation_signal * self.config.confirmation_weight +
            divergence * self.config.divergence_weight
        )
        
        return final_signal
```

### **1.3 SPY Benchmark Integration**

**File: `core_structure/performance/benchmark_analyzer.py`**

```python
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum

@dataclass
class BenchmarkConfig:
    """SPY benchmark configuration"""
    benchmark_symbol: str = "SPY"
    risk_free_rate: float = 0.02  # 2% annual risk-free rate
    benchmark_weight: float = 0.0  # 0% benchmark weight (long-short strategy)
    
    # Performance metrics
    target_information_ratio: float = 1.0
    target_sharpe_ratio: float = 1.5
    max_tracking_error: float = 0.15  # 15% max tracking error
    max_beta: float = 0.3  # 30% max beta to market

class BenchmarkAnalyzer:
    """SPY benchmark analysis and optimization"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
    
    def calculate_benchmark_metrics(self, strategy_returns: pd.Series, 
                                  spy_returns: pd.Series) -> Dict[str, float]:
        """Calculate benchmark-relative performance metrics"""
        
        # Excess returns
        excess_returns = strategy_returns - spy_returns
        
        # Risk metrics
        strategy_vol = strategy_returns.std() * np.sqrt(252)
        spy_vol = spy_returns.std() * np.sqrt(252)
        tracking_error = excess_returns.std() * np.sqrt(252)
        
        # Beta calculation
        beta = np.cov(strategy_returns, spy_returns)[0, 1] / np.var(spy_returns)
        
        # Performance metrics
        information_ratio = excess_returns.mean() / tracking_error if tracking_error > 0 else 0
        sharpe_ratio = strategy_returns.mean() / strategy_vol if strategy_vol > 0 else 0
        spy_sharpe = spy_returns.mean() / spy_vol if spy_vol > 0 else 0
        
        # Drawdown analysis
        strategy_cumulative = (1 + strategy_returns).cumprod()
        spy_cumulative = (1 + spy_returns).cumprod()
        
        strategy_drawdown = (strategy_cumulative / strategy_cumulative.expanding().max() - 1)
        spy_drawdown = (spy_cumulative / spy_cumulative.expanding().max() - 1)
        
        max_strategy_drawdown = strategy_drawdown.min()
        max_spy_drawdown = spy_drawdown.min()
        
        return {
            'information_ratio': information_ratio,
            'sharpe_ratio': sharpe_ratio,
            'spy_sharpe_ratio': spy_sharpe,
            'tracking_error': tracking_error,
            'beta': beta,
            'excess_return': excess_returns.mean() * 252,
            'strategy_volatility': strategy_vol,
            'spy_volatility': spy_vol,
            'max_strategy_drawdown': max_strategy_drawdown,
            'max_spy_drawdown': max_spy_drawdown,
            'relative_drawdown': max_strategy_drawdown - max_spy_drawdown
        }
    
    def optimize_for_benchmark(self, strategy_returns: pd.Series, 
                             spy_returns: pd.Series) -> Dict[str, float]:
        """Optimize strategy parameters for SPY benchmark performance"""
        
        # Calculate current metrics
        current_metrics = self.calculate_benchmark_metrics(strategy_returns, spy_returns)
        
        # Optimization objectives
        objectives = {
            'maximize_information_ratio': -current_metrics['information_ratio'],
            'minimize_tracking_error': current_metrics['tracking_error'],
            'minimize_beta': current_metrics['beta'],
            'minimize_relative_drawdown': current_metrics['relative_drawdown']
        }
        
        # Check if objectives are met
        constraints_met = {
            'information_ratio_target': current_metrics['information_ratio'] >= self.config.target_information_ratio,
            'tracking_error_limit': current_metrics['tracking_error'] <= self.config.max_tracking_error,
            'beta_limit': current_metrics['beta'] <= self.config.max_beta
        }
        
        return {
            'current_metrics': current_metrics,
            'objectives': objectives,
            'constraints_met': constraints_met,
            'optimization_score': self._calculate_optimization_score(current_metrics)
        }
    
    def _calculate_optimization_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall optimization score"""
        
        # Weighted score based on key metrics
        information_ratio_score = min(metrics['information_ratio'] / self.config.target_information_ratio, 1.0)
        tracking_error_score = max(0, 1 - metrics['tracking_error'] / self.config.max_tracking_error)
        beta_score = max(0, 1 - metrics['beta'] / self.config.max_beta)
        drawdown_score = max(0, 1 + metrics['relative_drawdown'])  # Prefer lower relative drawdown
        
        # Combined score
        total_score = (
            information_ratio_score * 0.4 +
            tracking_error_score * 0.3 +
            beta_score * 0.2 +
            drawdown_score * 0.1
        )
        
        return total_score

class SimplePerformanceAttribution:
    """Minimal performance attribution for academic factors"""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
    
    def attribute_performance(self, signals: Dict[str, float], 
                            returns: pd.Series) -> Dict[str, float]:
        """Simple correlation-based attribution - only if enabled"""
        if not self.enabled:
            return {}
        
        attribution = {}
        
        try:
            for signal_name, signal_values in signals.items():
                if isinstance(signal_values, (list, pd.Series)) and len(signal_values) == len(returns):
                    # Calculate correlation with returns
                    correlation = np.corrcoef(signal_values, returns)[0, 1]
                    if not np.isnan(correlation):
                        attribution[f'{signal_name}_contribution'] = abs(correlation)
                        
        except Exception as e:
            logger.warning(f"Performance attribution failed: {e}")
            return {}
        
        return attribution

```

### **1.4 Market Regime Detection Engine**

**File: `core_structure/signal_generation/regime_detection/market_regime_detector.py`**

```python
class MarketRegimeDetector:
    """Market regime detection using local ClickHouse data"""
    
    def __init__(self, config: RegimeDetectionConfig):
        self.config = config
        self.regimes = {
            'trending_bull': 'Strong upward momentum',
            'trending_bear': 'Strong downward momentum', 
            'sideways': 'Low volatility, no clear direction',
            'volatile': 'High volatility, choppy market',
            'crisis': 'Extreme volatility, panic selling'
        }
        
    def detect_regime(self, market_data: pd.DataFrame, 
                     technical_indicators: Dict[str, float]) -> Dict[str, Any]:
        """Detect current market regime using technical indicators"""
        
        # Calculate regime indicators
        volatility_regime = self._calculate_volatility_regime(market_data)
        momentum_regime = self._calculate_momentum_regime(market_data)
        volume_regime = self._calculate_volume_regime(market_data)
        technical_regime = self._calculate_technical_regime(technical_indicators)
        
        # Combine indicators for regime classification
        regime = self._classify_regime(volatility_regime, momentum_regime, 
                                     volume_regime, technical_regime)
        
        confidence = self._calculate_regime_confidence(volatility_regime, 
                                                     momentum_regime, 
                                                     volume_regime, 
                                                     technical_regime)
        
        return {
            'regime': regime,
            'confidence': confidence,
            'indicators': {
                'volatility': volatility_regime,
                'momentum': momentum_regime,
                'volume': volume_regime,
                'technical': technical_regime
            }
        }
    
    def _calculate_volatility_regime(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate volatility regime indicators"""
        
        returns = data['close'].pct_change().dropna()
        
        # Multiple volatility measures
        realized_vol = returns.rolling(20).std() * np.sqrt(252)
        garch_vol = self._calculate_garch_volatility(returns)
        implied_vol = self._calculate_implied_volatility(data)
        
        return {
            'realized_vol': realized_vol.iloc[-1],
            'garch_vol': garch_vol,
            'implied_vol': implied_vol,
            'vol_regime': self._classify_volatility_regime(realized_vol.iloc[-1])
        }
    
    def _calculate_momentum_regime(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate momentum regime indicators"""
        
        close = data['close']
        
        # Multiple momentum measures
        short_momentum = (close.iloc[-1] / close.iloc[-5] - 1) * 100
        medium_momentum = (close.iloc[-1] / close.iloc[-20] - 1) * 100
        long_momentum = (close.iloc[-1] / close.iloc[-60] - 1) * 100
        
        # Momentum consistency
        momentum_consistency = self._calculate_momentum_consistency(data)
        
        return {
            'short_momentum': short_momentum,
            'medium_momentum': medium_momentum,
            'long_momentum': long_momentum,
            'momentum_consistency': momentum_consistency,
            'momentum_regime': self._classify_momentum_regime(medium_momentum)
        }
```

### **1.3 Enhanced Signal Generator**

**File: `core_structure/signal_generation/enhanced_signal_generator.py`**

```python
class EnhancedSignalGenerator(SignalGenerator):
    """Enhanced signal generator with regime-aware multi-timeframe signals"""
    
    def __init__(self, config: EnhancedSignalConfig):
        super().__init__(config)
        self.enhanced_indicators = EnhancedTechnicalIndicatorEngine(config)
        self.regime_detector = MarketRegimeDetector(config)
        
    async def generate_enhanced_signals(self, market_data: Dict[str, pd.DataFrame], 
                                      symbol: str) -> Dict[str, Any]:
        """Generate enhanced signals using multi-timeframe analysis and regime detection"""
        
        # 1. Calculate multi-timeframe indicators
        multi_tf_indicators = self.enhanced_indicators.calculate_multi_timeframe_indicators(
            market_data, symbol
        )
        
        # 2. Calculate volume-weighted indicators
        volume_indicators = self.enhanced_indicators.calculate_volume_weighted_indicators(
            market_data.get('1day', pd.DataFrame()), symbol
        )
        
        # 3. Detect market regime
        regime_info = self.regime_detector.detect_regime(
            market_data.get('1day', pd.DataFrame()),
            multi_tf_indicators.get('1day', {})
        )
        
        # 4. Generate regime-aware signals
        signals = self._generate_regime_aware_signals(
            multi_tf_indicators, volume_indicators, regime_info
        )
        
        return {
            'signals': signals,
            'regime_info': regime_info,
            'indicators': {
                'multi_timeframe': multi_tf_indicators,
                'volume_weighted': volume_indicators
            }
        }
    
    def _generate_regime_aware_signals(self, multi_tf_indicators: Dict, 
                                     volume_indicators: Dict, 
                                     regime_info: Dict) -> Dict[str, float]:
        """Generate signals based on market regime"""
        
        regime = regime_info['regime']
        signals = {}
        
        # Base signals from different timeframes
        for timeframe, indicators in multi_tf_indicators.items():
            base_signal = self._calculate_base_signal_from_indicators(indicators)
            signals[f'{timeframe}_signal'] = base_signal
        
        # Volume-weighted signals
        volume_signal = self._calculate_volume_signal(volume_indicators)
        signals['volume_signal'] = volume_signal
        
        # Regime-based signal combination
        combined_signal = self._combine_signals_by_regime(signals, regime)
        signals['combined_signal'] = combined_signal
        
        return signals
    
    def _combine_signals_by_regime(self, signals: Dict[str, float], 
                                 regime: str) -> float:
        """Combine signals based on market regime"""
        
        if regime == 'trending_bull':
            # Favor longer-term signals in trending markets
            weights = {
                '1day_signal': 0.4,
                '1hour_signal': 0.3,
                '15min_signal': 0.2,
                'volume_signal': 0.1
            }
        elif regime == 'volatile':
            # Favor shorter-term signals in volatile markets
            weights = {
                '1day_signal': 0.1,
                '1hour_signal': 0.2,
                '15min_signal': 0.4,
                'volume_signal': 0.3
            }
        else:
            # Balanced approach for other regimes
            weights = {
                '1day_signal': 0.25,
                '1hour_signal': 0.25,
                '15min_signal': 0.25,
                'volume_signal': 0.25
            }
        
        # Calculate weighted average
        combined = 0.0
        total_weight = 0.0
        
        for signal_name, weight in weights.items():
            if signal_name in signals:
                combined += signals[signal_name] * weight
                total_weight += weight
        
        return combined / total_weight if total_weight > 0 else 0.0
```

---

## 🎯 **Phase 2: Backtesting Framework Integration**

### **2.1 Enhanced Strategy Interface**

**File: `backtesting_framework/strategies/enhanced_strategy_interface.py`**

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import pandas as pd

class EnhancedStrategyInterface(ABC):
    """Interface for enhanced strategies that use core system components"""
    
    @abstractmethod
    def get_strategy_config(self) -> Dict[str, Any]:
        """Return strategy configuration for core system"""
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """Return list of required technical indicators"""
        pass
    
    @abstractmethod
    def get_required_timeframes(self) -> List[str]:
        """Return list of required timeframes"""
        pass
    
    @abstractmethod
    def process_core_signals(self, core_signals: Dict[str, Any]) -> List[TradingSignal]:
        """Process signals from core system into trading signals"""
        pass

class EnhancedMomentumStrategy(EnhancedStrategyInterface):
    """Enhanced momentum strategy using core system components"""
    
    def __init__(self, config: EnhancedMomentumConfig):
        self.config = config
        
    def get_strategy_config(self) -> Dict[str, Any]:
        """Return configuration for core system"""
        return {
            'strategy_type': 'enhanced_momentum',
            'lookback_period': self.config.lookback_period,
            'momentum_threshold': self.config.momentum_threshold,
            'target_volatility': self.config.target_volatility,
            'max_weight_per_asset': self.config.max_weight_per_asset,
            'enable_regime_detection': True,
            'enable_volume_weighting': True,
            'enable_multi_timeframe': True
        }
    
    def get_required_indicators(self) -> List[str]:
        """Return required technical indicators"""
        return [
            'rsi_14', 'rsi_21', 'macd_line', 'macd_signal', 'bb_upper', 'bb_lower',
            'vw_rsi_14', 'vw_momentum_5', 'vw_momentum_10', 'vw_momentum_20',
            'volume_profile', 'volume_trend'
        ]
    
    def get_required_timeframes(self) -> List[str]:
        """Return required timeframes"""
        return ['1min', '5min', '15min', '1hour', '1day']
    
    def process_core_signals(self, core_signals: Dict[str, Any]) -> List[TradingSignal]:
        """Process core system signals into trading signals"""
        
        signals = []
        combined_signal = core_signals['signals']['combined_signal']
        regime_info = core_signals['regime_info']
        
        # Apply strategy-specific logic
        if abs(combined_signal) > self.config.momentum_threshold:
            signal_type = SignalType.LONG if combined_signal > 0 else SignalType.SHORT
            confidence = min(abs(combined_signal) / (2 * self.config.momentum_threshold), 1.0)
            
            # Adjust confidence based on regime
            regime_confidence = regime_info['confidence']
            final_confidence = confidence * regime_confidence
            
            signals.append(TradingSignal(
                timestamp=datetime.now(),
                symbol=core_signals.get('symbol', 'UNKNOWN'),
                signal_type=signal_type,
                strength=abs(combined_signal),
                confidence=final_confidence,
                price=core_signals.get('current_price', 0.0),
                metadata={
                    'regime': regime_info['regime'],
                    'regime_confidence': regime_confidence,
                    'strategy_type': 'enhanced_momentum'
                }
            ))
        
        return signals
```

### **2.2 Backtesting Framework Integration**

**File: `backtesting_framework/experiments/enhanced_experiment_runner.py`**

```python
class EnhancedExperimentRunner(ExperimentRunner):
    """Enhanced experiment runner that uses core system components"""
    
    def __init__(self, config: EnhancedExperimentConfig):
        super().__init__(config)
        self.core_signal_generator = None
        self.enhanced_strategy = None
        
    async def setup_core_system(self):
        """Setup core system components"""
        
        # Initialize enhanced signal generator
        from core_structure.signal_generation.enhanced_signal_generator import EnhancedSignalGenerator
        signal_config = self._create_signal_config()
        self.core_signal_generator = EnhancedSignalGenerator(signal_config)
        
        # Initialize enhanced strategy
        strategy_class = self._get_strategy_class()
        self.enhanced_strategy = strategy_class(self.config.strategy_params)
        
    async def run_enhanced_experiment(self) -> ExperimentResult:
        """Run enhanced experiment using core system"""
        
        # Setup core system
        await self.setup_core_system()
        
        # Load data from ClickHouse
        data = await self._load_clickhouse_data()
        
        # Generate signals using core system
        core_signals = await self._generate_core_signals(data)
        
        # Process signals through strategy
        trading_signals = self.enhanced_strategy.process_core_signals(core_signals)
        
        # Execute backtest
        result = await self._execute_backtest(trading_signals, data)
        
        return result
    
    async def _generate_core_signals(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Generate signals using core system"""
        
        all_signals = {}
        
        for symbol in data.keys():
            symbol_data = data[symbol]
            
            # Generate enhanced signals for this symbol
            signals = await self.core_signal_generator.generate_enhanced_signals(
                symbol_data, symbol
            )
            
            all_signals[symbol] = signals
        
        return all_signals
```

---

## 🎯 **Phase 3: Real-Time Integration**

### **3.1 Real-Time Signal Generator**

**File: `core_structure/signal_generation/real_time_signal_generator.py`**

```python
class RealTimeSignalGenerator(EnhancedSignalGenerator):
    """Real-time signal generator using same logic as backtesting"""
    
    def __init__(self, config: RealTimeSignalConfig):
        super().__init__(config)
        self.polygon_client = PolygonClient()  # For real-time data
        
    async def generate_real_time_signals(self, symbols: List[str]) -> Dict[str, Any]:
        """Generate real-time signals using same logic as backtesting"""
        
        all_signals = {}
        
        for symbol in symbols:
            # Get real-time data from Polygon.io
            real_time_data = await self._get_real_time_data(symbol)
            
            # Use same signal generation logic as backtesting
            signals = await self.generate_enhanced_signals(real_time_data, symbol)
            
            all_signals[symbol] = signals
        
        return all_signals
    
    async def _get_real_time_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Get real-time data from Polygon.io"""
        
        data = {}
        
        # Get data for different timeframes
        for timeframe in self.timeframes:
            if timeframe == '1min':
                # Use real-time aggregates (15-min delayed)
                aggregates = await self.polygon_client.get_aggregates(
                    symbol, timeframe, limit=1000
                )
                data[timeframe] = aggregates
            else:
                # Use historical data for other timeframes
                historical = await self.polygon_client.get_aggregates(
                    symbol, timeframe, limit=1000
                )
                data[timeframe] = historical
        
        return data
```

### **3.2 Real-Time Strategy Runner**

**File: `core_structure/real_time/real_time_strategy_runner.py`**

```python
class RealTimeStrategyRunner:
    """Real-time strategy runner using same strategy implementation"""
    
    def __init__(self, strategy_config: Dict[str, Any]):
        self.strategy_config = strategy_config
        self.real_time_signal_generator = RealTimeSignalGenerator(strategy_config)
        self.enhanced_strategy = self._create_strategy(strategy_config)
        
    async def run_real_time_strategy(self, symbols: List[str]) -> List[TradingSignal]:
        """Run real-time strategy using same logic as backtesting"""
        
        # Generate real-time signals using core system
        core_signals = await self.real_time_signal_generator.generate_real_time_signals(symbols)
        
        # Process signals using same strategy logic
        trading_signals = self.enhanced_strategy.process_core_signals(core_signals)
        
        return trading_signals
```

---

## 🎯 **Phase 4: Testing & Validation**

### **4.1 Comprehensive Test Suite**

**File: `backtesting_framework/tests/test_enhanced_system.py`**

```python
class TestEnhancedSystem:
    """Test suite for enhanced system"""
    
    def test_core_system_consistency(self):
        """Test that core system produces consistent results"""
        
        # Test with same data
        test_data = self._create_test_data()
        
        # Generate signals using core system
        core_signals = self.enhanced_signal_generator.generate_enhanced_signals(test_data)
        
        # Verify consistency
        assert core_signals is not None
        assert 'signals' in core_signals
        assert 'regime_info' in core_signals
    
    def test_strategy_consistency(self):
        """Test that strategy produces consistent results"""
        
        # Test with same core signals
        test_core_signals = self._create_test_core_signals()
        
        # Process through strategy
        trading_signals = self.enhanced_strategy.process_core_signals(test_core_signals)
        
        # Verify consistency
        assert len(trading_signals) > 0
        assert all(isinstance(s, TradingSignal) for s in trading_signals)
    
    def test_backtesting_real_time_consistency(self):
        """Test consistency between backtesting and real-time"""
        
        # Use same test data for both
        test_data = self._create_test_data()
        
        # Backtesting signals
        backtest_signals = self.enhanced_signal_generator.generate_enhanced_signals(test_data)
        
        # Real-time signals (simulated)
        real_time_signals = self.real_time_signal_generator.generate_enhanced_signals(test_data)
        
        # Verify consistency
        assert backtest_signals['signals']['combined_signal'] == real_time_signals['signals']['combined_signal']
```

---

## 🎯 **2-Step Implementation Approach**

### **📊 Overview**

**STEP 1: Backtesting with Historical Data (Weeks 1-3)**
- **Data Source**: Local ClickHouse (2.5 years historical data)
- **Focus**: Training + Out-of-Sample Testing
- **Goal**: Validate strategy, optimize parameters, ensure academic fidelity

**STEP 2: Real-Time Trading Simulation (Weeks 4-5)**
- **Data Source**: Polygon.io (15-min delayed real-time data)
- **Focus**: Real-Time Execution with Optimized Parameters
- **Goal**: Validate real-time performance, ensure consistency with backtesting

### **🎯 Why 2-Step Approach?**

**1. Clear Separation of Concerns**
- **Step 1**: Strategy validation and parameter optimization
- **Step 2**: Real-time execution validation
- **No mixing** of historical and real-time data

**2. Academic Rigor**
- **Step 1**: Proper training/validation split with historical data
- **Step 2**: Out-of-sample testing in real-time environment
- **Prevents overfitting** by clear separation

**3. Risk Management**
- **Step 1**: Validate strategy thoroughly before real-time execution
- **Step 2**: Start with simulation before live trading
- **Reduces risk** of strategy failures

**4. Data Source Optimization**
- **Step 1**: Use local ClickHouse data (cost-effective)
- **Step 2**: Use Polygon.io only for real-time (minimize API costs)
- **Maximizes** data usage efficiency

### **🔄 Data Flow Between Steps**

```
Step 1: Historical Backtesting
├── Training Data (2023-2024) → Parameter Optimization
├── Validation Data (2024-2025) → Out-of-Sample Testing
└── Optimized Parameters → Saved for Step 2

Step 2: Real-Time Simulation
├── Load Optimized Parameters from Step 1
├── Real-Time Data (Polygon.io) → Signal Generation
└── Same Strategy Logic → Consistency Validation
```

## 🎯 **2-Step Implementation Timeline**

### **STEP 1: Backtesting with Historical Data (Weeks 1-3)**
**Focus: Training + Out-of-Sample Testing with Local ClickHouse Data**

#### **Week 1: Core System Enhancements**
- [ ] Implement `EnhancedTechnicalIndicatorEngine` with academic foundations
- [ ] Implement `MarketRegimeDetector` with regime classification
- [ ] Implement `EnhancedSignalGenerator` with academic signal combination
- [ ] Implement `BenchmarkAnalyzer` for SPY benchmark integration
- [ ] Test with local ClickHouse data (2.5 years historical)

#### **Week 2: Backtesting Framework Integration**
- [ ] Implement `EnhancedStrategyInterface` for core system integration
- [ ] Implement `EnhancedMomentumStrategy` with academic momentum logic
- [ ] Implement `EnhancedExperimentRunner` for training/validation split
- [ ] Implement parameter optimization with academic validation
- [ ] Test strategy consistency across training and validation periods

#### **Week 3: Training & Out-of-Sample Testing**
- [ ] **Training Phase**: Optimize parameters on training data (2023-2024)
- [ ] **Validation Phase**: Test on out-of-sample data (2024-2025)
- [ ] **Performance Analysis**: Compare against SPY benchmark
- [ ] **Academic Validation**: Verify against research benchmarks
- [ ] **Parameter Persistence**: Save optimized parameters for Step 2

### **STEP 2: Real-Time Trading Simulation (Weeks 4-5)**
**Focus: Real-Time Execution with Polygon.io Data**

#### **Week 4: Real-Time System Integration**
- [ ] Implement `RealTimeSignalGenerator` using same core system logic
- [ ] Implement `RealTimeStrategyRunner` with optimized parameters
- [ ] Implement Polygon.io integration for real-time data feeds
- [ ] Implement real-time execution engine with transaction cost modeling
- [ ] Test real-time vs backtesting consistency

#### **Week 5: Real-Time Testing & Validation**
- [ ] **Real-Time Simulation**: Run with Polygon.io 15-min delayed data
- [ ] **Performance Comparison**: Compare real-time vs backtesting results
- [ ] **Consistency Validation**: Ensure same strategy logic across both systems
- [ ] **Documentation & Deployment**: Final testing and documentation

---

## 🎯 **Step-by-Step Execution Scripts**

### **Step 1: Historical Backtesting Execution**

**File: `backtesting_framework/run_step1_historical_backtest.py`**

```python
#!/usr/bin/env python3
"""
Step 1: Historical Backtesting with Local ClickHouse Data
Training + Out-of-Sample Testing
"""

import asyncio
import logging
from datetime import datetime
from enhanced_config_manager import EnhancedConfigManager
from enhanced_experiment_runner import EnhancedExperimentRunner

async def run_step1_backtesting():
    """Execute Step 1: Historical backtesting with training and validation"""
    
    # Initialize configuration manager
    config_manager = EnhancedConfigManager()
    
    # Create Step 1 configuration
    config = config_manager.create_step1_backtesting_config(
        strategy_name="enhanced_momentum",
        training_start="2023-01-01",
        training_end="2024-12-31",
        validation_start="2025-01-01", 
        validation_end="2025-06-30"
    )
    
    # Initialize experiment runner
    experiment_runner = EnhancedExperimentRunner(config)
    
    # Run training phase
    print("=== STEP 1: TRAINING PHASE ===")
    training_result = await experiment_runner.run_training_phase()
    
    # Save optimized parameters
    config_manager.save_optimized_parameters(
        strategy_name="enhanced_momentum",
        parameters=training_result['optimized_parameters'],
        performance_metrics=training_result['performance_metrics']
    )
    
    # Run validation phase
    print("=== STEP 1: VALIDATION PHASE ===")
    validation_result = await experiment_runner.run_validation_phase()
    
    # Compare against SPY benchmark
    benchmark_analyzer = BenchmarkAnalyzer(config.benchmark)
    benchmark_metrics = benchmark_analyzer.calculate_benchmark_metrics(
        validation_result['strategy_returns'],
        validation_result['spy_returns']
    )
    
    # Print results
    print(f"Information Ratio: {benchmark_metrics['information_ratio']:.3f}")
    print(f"Sharpe Ratio: {benchmark_metrics['sharpe_ratio']:.3f}")
    print(f"Max Drawdown: {benchmark_metrics['max_strategy_drawdown']:.3f}")
    print(f"Beta: {benchmark_metrics['beta']:.3f}")
    
    return {
        'training_result': training_result,
        'validation_result': validation_result,
        'benchmark_metrics': benchmark_metrics
    }

if __name__ == "__main__":
    asyncio.run(run_step1_backtesting())
```

### **Step 2: Real-Time Trading Simulation**

**File: `backtesting_framework/run_step2_realtime_simulation.py`**

```python
#!/usr/bin/env python3
"""
Step 2: Real-Time Trading Simulation with Polygon.io Data
Using Optimized Parameters from Step 1
"""

import asyncio
import logging
from datetime import datetime
from enhanced_config_manager import EnhancedConfigManager
from real_time_strategy_runner import RealTimeStrategyRunner

async def run_step2_realtime_simulation():
    """Execute Step 2: Real-time trading simulation"""
    
    # Initialize configuration manager
    config_manager = EnhancedConfigManager()
    
    # Create Step 2 configuration (loads optimized parameters from Step 1)
    config = config_manager.create_step2_realtime_config(
        strategy_name="enhanced_momentum",
        trading_start="2025-07-01"  # Start after Step 1 validation period
    )
    
    # Initialize real-time strategy runner
    real_time_runner = RealTimeStrategyRunner(config)
    
    # Run real-time simulation
    print("=== STEP 2: REAL-TIME SIMULATION ===")
    print("Using optimized parameters from Step 1")
    print("Data source: Polygon.io (15-min delayed)")
    
    # Start real-time simulation
    simulation_result = await real_time_runner.run_realtime_simulation(
        duration_days=30  # Run for 30 days
    )
    
    # Compare with Step 1 results
    print("=== CONSISTENCY VALIDATION ===")
    consistency_check = real_time_runner.validate_consistency_with_step1()
    
    # Print results
    print(f"Real-time Information Ratio: {simulation_result['information_ratio']:.3f}")
    print(f"Real-time Sharpe Ratio: {simulation_result['sharpe_ratio']:.3f}")
    print(f"Consistency Score: {consistency_check['consistency_score']:.3f}")
    
    return {
        'simulation_result': simulation_result,
        'consistency_check': consistency_check
    }

if __name__ == "__main__":
    asyncio.run(run_step2_realtime_simulation())
```

### **Step Execution Commands**

```bash
# Step 1: Historical Backtesting
python backtesting_framework/run_step1_historical_backtest.py

# Step 2: Real-Time Simulation (after Step 1 completes)
python backtesting_framework/run_step2_realtime_simulation.py
```

---

## 🎯 **Key Benefits of 2-Step Approach**

### **✅ Clear Step Separation**
- **Step 1**: Historical backtesting with training/validation split
- **Step 2**: Real-time simulation with optimized parameters
- **No Data Mixing**: Clear separation between historical and real-time data

### **✅ Academic Rigor**
- **Proper Training/Validation**: Step 1 follows academic best practices
- **Out-of-Sample Testing**: Step 2 validates in real-time environment
- **Parameter Persistence**: Optimized parameters carry forward to Step 2

### **✅ Risk Management**
- **Step 1 Validation**: Thorough testing before real-time execution
- **Step 2 Simulation**: Safe real-time testing before live trading
- **Consistency Validation**: Ensure same logic across both steps

### **✅ Data Source Optimization**
- **Step 1**: Local ClickHouse data (cost-effective, 2.5 years)
- **Step 2**: Polygon.io real-time data (minimal API usage)
- **Efficient Usage**: Maximize local data, minimize external API calls

### **✅ Maintainability**
- **Same Core System**: Identical signal generation across both steps
- **Clear Interfaces**: Well-defined boundaries between components
- **Easy Testing**: Test each step independently

This revised approach ensures that your enhancements are properly integrated into the core system while maintaining clear separation and consistency between backtesting and real-time execution.

---

## 🎯 **Minimal Additions Summary**

### **✅ What Was Added (Minimal & Focused)**

**1. Data Quality Validation**
- **Minimal validation**: Only critical checks (data length, missing data, price range)
- **Simple implementation**: Single method with basic checks
- **Non-intrusive**: Skips invalid data without breaking strategy

**2. Error Handling**
- **Essential error handling**: Division by zero, data access errors
- **Graceful degradation**: Continues processing other symbols if one fails
- **Configurable**: Can be enabled/disabled via configuration

**3. Academic Parameter Validation**
- **Research-backed ranges**: Parameters validated against academic literature
- **Automatic validation**: Runs on configuration initialization
- **Clear error messages**: Specific validation failures with suggested ranges

**4. Enhanced Transaction Costs**
- **Simple linear models**: Market impact, slippage, commission
- **Realistic ranges**: Based on typical institutional costs
- **Configurable per environment**: Different costs for simulation/paper/live

**5. Optional Performance Attribution**
- **Simple correlation analysis**: Basic factor contribution measurement
- **Disabled by default**: Only enabled if needed
- **Minimal overhead**: No complex statistical analysis

### **❌ What Was NOT Added (Avoiding Over-Engineering)**

**1. Complex Frameworks**
- No sophisticated data quality frameworks
- No advanced academic validation systems
- No complex performance attribution models

**2. Over-Fitting Risks**
- No factor correlation analysis
- No multiple out-of-sample testing methods
- No sophisticated parameter optimization

**3. Architecture Complexity**
- No new major components
- No complex interfaces
- No additional dependencies

### **🎯 Benefits of Minimal Approach**

**✅ Maintains Simplicity**
- **Existing architecture** preserved
- **Minimal code changes** required
- **Easy to understand** and maintain

**✅ Prevents Overfitting**
- **Simple validation** only
- **No sophisticated analysis** added
- **Basic error handling** only

**✅ Addresses Critical Issues**
- **Data quality** - Prevents strategy failures
- **Error handling** - Prevents crashes
- **Parameter validation** - Ensures academic fidelity
- **Transaction costs** - Realistic implementation

**✅ Easy Implementation**
- **Add to existing classes** - No new frameworks
- **Minimal configuration** - Simple YAML additions
- **Backward compatible** - Doesn't break existing code

### **📊 Implementation Impact**

**Code Changes**: ~200 lines added (minimal)
**Configuration**: 4 new sections (simple)
**Dependencies**: None added
**Performance**: Negligible impact
**Complexity**: No increase in architecture complexity

The minimal additions provide **essential robustness** while maintaining your **clean, simple architecture** and avoiding **over-engineering**. 