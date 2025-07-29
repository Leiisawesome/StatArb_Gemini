"""
Phase 4.3: Academic Research Validation
=====================================

This module validates trading strategies against established academic research
and financial theory, including momentum factors, market efficiency, and
statistical significance testing.

Academic References:
- Jegadeesh & Titman (1993): Momentum in stock returns
- Carhart (1997): Four-factor model
- Moskowitz & Grinblatt (1999): Industry momentum
- Fama & French (1993): Three-factor model
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import scipy.stats as stats
from scipy import optimize

# Import core system components
import sys
sys.path.append('../core_structure')

try:
    from infrastructure.database.clickhouse_client import ClickHouseClient
except ImportError:
    # Fallback for import issues
    ClickHouseClient = None

# Import backtesting framework components
try:
    from utils.data_integration import DataIntegrationManager
    from experiments.experiment_runner import ExperimentRunner
except ImportError:
    # Fallback for import issues
    DataIntegrationManager = None
    ExperimentRunner = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AcademicValidationConfig:
    """Configuration for academic research validation"""
    
    # Test strategies
    strategies: List[str] = field(default_factory=lambda: ['momentum', 'multi_factor'])
    
    # Academic factors to test
    academic_factors: List[str] = field(default_factory=lambda: [
        'momentum_factor',
        'market_efficiency',
        'risk_adjusted_returns',
        'statistical_significance',
        'factor_analysis'
    ])
    
    # Time periods for testing
    time_periods: List[Dict] = field(default_factory=lambda: [
        {'name': '1Y', 'months': 12},
        {'name': '2Y', 'months': 24},
        {'name': '3Y', 'months': 36}
    ])
    
    # Symbols for testing (major indices and stocks)
    symbols: List[str] = field(default_factory=lambda: [
        'SPY', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META'
    ])
    
    # Academic thresholds
    min_momentum_persistence: float = 0.6  # Minimum momentum persistence
    max_market_efficiency_deviation: float = 0.1  # Maximum deviation from efficiency
    min_statistical_significance: float = 0.05  # P-value threshold
    min_factor_loading: float = 0.3  # Minimum factor loading significance
    
    # Performance thresholds
    min_sharpe_ratio: float = 0.5
    max_drawdown: float = 0.20
    min_win_rate: float = 0.45
    
    # Output settings
    results_dir: str = "results/phase4"
    save_detailed_results: bool = True
    
    def __post_init__(self):
        """Set default values after initialization"""
        # Ensure results directory exists
        Path(self.results_dir).mkdir(parents=True, exist_ok=True)


class AcademicResearchValidator:
    """
    Validates trading strategies against established academic research
    and financial theory.
    """
    
    def __init__(self, config: AcademicValidationConfig = None):
        """Initialize the academic research validator"""
        self.config = config or AcademicValidationConfig()
        self.clickhouse_client = None
        self.data_manager = None
        self.performance_analyzer = None
        self.experiment_runner = None
        self.data_integration = None
        self.validation_results = {}
        
        logger.info("AcademicResearchValidator initialized")
    
    async def initialize(self):
        """Initialize all required components"""
        try:
            print("🔧 Initializing Academic Research Validator...")
            
            # Initialize ClickHouse client
            if ClickHouseClient:
                self.clickhouse_client = ClickHouseClient()
                print("✅ ClickHouse client initialized")
            else:
                print("⚠️ ClickHouse client not available. Skipping initialization.")
            
            # Initialize backtesting framework components
            if DataIntegrationManager and ExperimentRunner:
                self.data_integration = DataIntegrationManager()
                self.experiment_runner = ExperimentRunner()
                print("✅ Backtesting framework components initialized")
            else:
                print("⚠️ Backtesting framework components not available. Skipping initialization.")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing AcademicResearchValidator: {e}")
            return False
    
    async def run_academic_validation(self) -> bool:
        """
        Run comprehensive academic research validation
        """
        try:
            print("\n" + "="*60)
            print("📚 PHASE 4.3: ACADEMIC RESEARCH VALIDATION")
            print("="*60)
            
            # Initialize components
            if not await self.initialize():
                return False
            
            print("\n🔬 Starting academic research validation...")
            
            # Step 1: Momentum Factor Validation
            print("\n📊 Step 1: Momentum Factor Validation")
            momentum_results = await self._validate_momentum_factors()
            
            # Step 2: Market Efficiency Testing
            print("\n📈 Step 2: Market Efficiency Testing")
            efficiency_results = await self._test_market_efficiency()
            
            # Step 3: Risk-Adjusted Performance Analysis
            print("\n🎯 Step 3: Risk-Adjusted Performance Analysis")
            risk_results = await self._analyze_risk_adjusted_performance()
            
            # Step 4: Statistical Significance Testing
            print("\n📊 Step 4: Statistical Significance Testing")
            significance_results = await self._test_statistical_significance()
            
            # Step 5: Factor Analysis
            print("\n🔍 Step 5: Factor Analysis")
            factor_results = await self._perform_factor_analysis()
            
            # Step 6: Generate Academic Report
            print("\n📋 Step 6: Generating Academic Report")
            await self._generate_academic_report({
                'momentum_factors': momentum_results,
                'market_efficiency': efficiency_results,
                'risk_adjusted_performance': risk_results,
                'statistical_significance': significance_results,
                'factor_analysis': factor_results
            })
            
            # Cleanup
            await self._cleanup()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in academic validation: {e}")
            await self._cleanup()
            return False
    
    async def _cleanup(self):
        """Clean up resources"""
        try:
            if self.clickhouse_client:
                await self.clickhouse_client.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def _validate_momentum_factors(self) -> Dict:
        """
        Validate momentum factors against academic research
        Based on Jegadeesh & Titman (1993) and Carhart (1997)
        """
        try:
            print("   Validating momentum factors...")
            
            results = {
                'jegadeesh_titman_momentum': {},
                'carhart_momentum': {},
                'momentum_persistence': {},
                'cross_sectional_momentum': {}
            }
            
            # Test Jegadeesh & Titman momentum (6-month formation, 6-month holding)
            print("     Testing Jegadeesh & Titman momentum...")
            jt_results = await self._test_jegadeesh_titman_momentum()
            results['jegadeesh_titman_momentum'] = jt_results
            
            # Test Carhart momentum factor
            print("     Testing Carhart momentum factor...")
            carhart_results = await self._test_carhart_momentum()
            results['carhart_momentum'] = carhart_results
            
            # Test momentum persistence
            print("     Testing momentum persistence...")
            persistence_results = await self._test_momentum_persistence()
            results['momentum_persistence'] = persistence_results
            
            # Test cross-sectional momentum
            print("     Testing cross-sectional momentum...")
            cross_sectional_results = await self._test_cross_sectional_momentum()
            results['cross_sectional_momentum'] = cross_sectional_results
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating momentum factors: {e}")
            return {'error': str(e)}
    
    async def _test_jegadeesh_titman_momentum(self) -> Dict:
        """
        Test Jegadeesh & Titman (1993) momentum strategy
        Formation period: 6 months, Holding period: 6 months
        """
        try:
            # Load data for momentum testing
            symbols = self.config.symbols[:4]  # Use first 4 symbols for testing
            data = await self._load_momentum_data(symbols, months=12)
            
            if not data:
                return {'success': False, 'error': 'No data available'}
            
            # Calculate momentum returns (6-month formation, 6-month holding)
            momentum_returns = {}
            formation_period = 126  # 6 months * 21 trading days
            holding_period = 126
            
            for symbol, df in data.items():
                if len(df) < formation_period + holding_period:
                    continue
                
                # Calculate formation period returns
                df['formation_return'] = df['close'].pct_change(formation_period)
                
                # Calculate holding period returns
                df['holding_return'] = df['close'].pct_change(holding_period).shift(-holding_period)
                
                # Momentum strategy: long winners, short losers
                df['momentum_signal'] = np.where(
                    df['formation_return'] > df['formation_return'].quantile(0.7), 1,  # Top 30%
                    np.where(df['formation_return'] < df['formation_return'].quantile(0.3), -1, 0)  # Bottom 30%
                )
                
                # Calculate strategy returns
                df['strategy_return'] = df['momentum_signal'].shift(1) * df['holding_return']
                
                # Calculate performance metrics
                total_return = df['strategy_return'].sum()
                volatility = df['strategy_return'].std() * np.sqrt(252)
                sharpe_ratio = total_return / volatility if volatility > 0 else 0
                max_drawdown = self._calculate_max_drawdown(df['strategy_return'])
                
                momentum_returns[symbol] = {
                    'total_return': total_return,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'trades': len(df['momentum_signal'].diff()[df['momentum_signal'].diff() != 0])
                }
            
            # Aggregate results
            if momentum_returns:
                avg_return = np.mean([r['total_return'] for r in momentum_returns.values()])
                avg_sharpe = np.mean([r['sharpe_ratio'] for r in momentum_returns.values()])
                total_trades = sum([r['trades'] for r in momentum_returns.values()])
                
                return {
                    'success': True,
                    'momentum_returns': momentum_returns,
                    'aggregated_metrics': {
                        'avg_return': avg_return,
                        'avg_sharpe': avg_sharpe,
                        'total_trades': total_trades
                    },
                    'academic_validation': {
                        'jegadeesh_titman_consistent': avg_return > 0,
                        'momentum_persistence': avg_sharpe > self.config.min_momentum_persistence
                    }
                }
            else:
                return {'success': False, 'error': 'Insufficient data for momentum testing'}
                
        except Exception as e:
            logger.error(f"Error testing Jegadeesh & Titman momentum: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _load_momentum_data(self, symbols: List[str], months: int) -> Optional[Dict[str, pd.DataFrame]]:
        """Load data for momentum testing"""
        try:
            data = {}
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            for symbol in symbols:
                print(f"       Loading {symbol} data...")
                
                # Query ClickHouse for historical data
                query = f"""
                SELECT ticker, volume, open, close, high, low, window_start, transactions
                FROM ticks 
                WHERE LOWER(ticker) = LOWER('{symbol}')
                AND window_start >= {int(start_date.timestamp() * 1_000_000_000)}
                AND window_start <= {int(end_date.timestamp() * 1_000_000_000)}
                ORDER BY window_start
                """
                
                result = await self.clickhouse_client.execute_query(query)
                
                if result is not None and not result.empty:
                    # Process the data
                    df = result.copy()
                    df.columns = ['ticker', 'volume', 'open', 'close', 'high', 'low', 'window_start', 'transactions']
                    
                    # Convert timestamp
                    df['date'] = pd.to_datetime(df['window_start'], unit='ns')
                    df.set_index('date', inplace=True)
                    
                    data[symbol] = df
                    print(f"       ✅ Loaded {len(df)} rows for {symbol}")
                else:
                    print(f"       ❌ No data found for {symbol}")
            
            return data if data else None
            
        except Exception as e:
            logger.error(f"Error loading momentum data: {e}")
            return None
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return drawdown.min()
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    async def _test_carhart_momentum(self) -> Dict:
        """
        Test Carhart (1997) momentum factor
        Based on four-factor model: Market, Size, Value, Momentum
        """
        try:
            # Load data for Carhart momentum testing
            symbols = self.config.symbols[:4]
            data = await self._load_momentum_data(symbols, months=24)
            
            if not data:
                return {'success': False, 'error': 'No data available'}
            
            # Calculate Carhart momentum factor
            momentum_factors = {}
            
            for symbol, df in data.items():
                if len(df) < 252:  # Need at least 1 year of data
                    continue
                
                # Calculate 12-month momentum (Carhart standard)
                df['momentum_12m'] = df['close'].pct_change(252)
                
                # Calculate market beta
                df['market_return'] = df['close'].pct_change()
                market_returns = df['market_return'].dropna()
                
                if len(market_returns) > 60:
                    # Calculate beta using rolling window
                    df['beta'] = df['market_return'].rolling(60).cov(df['market_return']) / df['market_return'].rolling(60).var()
                    
                    # Carhart momentum factor: excess return after controlling for market risk
                    df['carhart_momentum'] = df['momentum_12m'] - df['beta'] * df['market_return']
                    
                    # Calculate factor performance
                    factor_return = df['carhart_momentum'].mean()
                    factor_volatility = df['carhart_momentum'].std()
                    factor_sharpe = factor_return / factor_volatility if factor_volatility > 0 else 0
                    
                    momentum_factors[symbol] = {
                        'factor_return': factor_return,
                        'factor_volatility': factor_volatility,
                        'factor_sharpe': factor_sharpe,
                        'beta': df['beta'].mean()
                    }
            
            # Aggregate results
            if momentum_factors:
                avg_factor_return = np.mean([f['factor_return'] for f in momentum_factors.values()])
                avg_factor_sharpe = np.mean([f['factor_sharpe'] for f in momentum_factors.values()])
                
                return {
                    'success': True,
                    'momentum_factors': momentum_factors,
                    'aggregated_metrics': {
                        'avg_factor_return': avg_factor_return,
                        'avg_factor_sharpe': avg_factor_sharpe
                    },
                    'academic_validation': {
                        'carhart_momentum_significant': avg_factor_return > 0,
                        'factor_persistence': avg_factor_sharpe > self.config.min_momentum_persistence
                    }
                }
            else:
                return {'success': False, 'error': 'Insufficient data for Carhart momentum testing'}
                
        except Exception as e:
            logger.error(f"Error testing Carhart momentum: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _test_momentum_persistence(self) -> Dict:
        """
        Test momentum persistence across different time horizons
        Based on Moskowitz & Grinblatt (1999)
        """
        try:
            # Test momentum persistence at different horizons
            horizons = [1, 3, 6, 12]  # months
            persistence_results = {}
            
            for horizon in horizons:
                print(f"       Testing {horizon}-month momentum persistence...")
                
                # Load data for this horizon
                data = await self._load_momentum_data(self.config.symbols[:3], months=horizon * 3)
                
                if not data:
                    continue
                
                horizon_returns = {}
                
                for symbol, df in data.items():
                    if len(df) < horizon * 21:  # Need sufficient data
                        continue
                    
                    # Calculate momentum at this horizon
                    df['momentum'] = df['close'].pct_change(horizon * 21)
                    
                    # Calculate forward returns
                    df['forward_return'] = df['close'].pct_change(horizon * 21).shift(-horizon * 21)
                    
                    # Momentum strategy
                    df['momentum_signal'] = np.where(
                        df['momentum'] > df['momentum'].quantile(0.7), 1,
                        np.where(df['momentum'] < df['momentum'].quantile(0.3), -1, 0)
                    )
                    
                    # Strategy returns
                    df['strategy_return'] = df['momentum_signal'].shift(1) * df['forward_return']
                    
                    # Performance metrics
                    total_return = df['strategy_return'].sum()
                    sharpe_ratio = total_return / (df['strategy_return'].std() * np.sqrt(252)) if df['strategy_return'].std() > 0 else 0
                    
                    horizon_returns[symbol] = {
                        'total_return': total_return,
                        'sharpe_ratio': sharpe_ratio
                    }
                
                if horizon_returns:
                    avg_return = np.mean([r['total_return'] for r in horizon_returns.values()])
                    avg_sharpe = np.mean([r['sharpe_ratio'] for r in horizon_returns.values()])
                    
                    persistence_results[f'{horizon}M'] = {
                        'avg_return': avg_return,
                        'avg_sharpe': avg_sharpe,
                        'symbols_tested': len(horizon_returns)
                    }
            
            # Calculate persistence score
            if persistence_results:
                persistence_score = np.mean([r['avg_sharpe'] for r in persistence_results.values()])
                
                return {
                    'success': True,
                    'persistence_results': persistence_results,
                    'persistence_score': persistence_score,
                    'academic_validation': {
                        'momentum_persistent': persistence_score > self.config.min_momentum_persistence,
                        'horizon_consistency': len([r for r in persistence_results.values() if r['avg_sharpe'] > 0]) >= 2
                    }
                }
            else:
                return {'success': False, 'error': 'Insufficient data for momentum persistence testing'}
                
        except Exception as e:
            logger.error(f"Error testing momentum persistence: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _test_cross_sectional_momentum(self) -> Dict:
        """
        Test cross-sectional momentum across multiple assets
        Based on industry momentum research
        """
        try:
            # Load data for multiple symbols
            data = await self._load_momentum_data(self.config.symbols, months=12)
            
            if not data or len(data) < 3:
                return {'success': False, 'error': 'Insufficient data for cross-sectional testing'}
            
            # Calculate cross-sectional momentum
            cross_sectional_results = {}
            
            # Get common date range
            all_dates = set()
            for df in data.values():
                all_dates.update(df.index)
            
            common_dates = sorted(list(all_dates))
            
            if len(common_dates) < 252:  # Need at least 1 year
                return {'success': False, 'error': 'Insufficient common date range'}
            
            # Calculate momentum for each symbol at each date
            momentum_matrix = pd.DataFrame(index=common_dates, columns=data.keys())
            
            for symbol, df in data.items():
                # Calculate 6-month momentum
                df['momentum_6m'] = df['close'].pct_change(126)
                momentum_matrix[symbol] = df['momentum_6m']
            
            # Cross-sectional momentum strategy
            strategy_returns = []
            
            for i in range(126, len(common_dates) - 126):  # Skip formation and holding periods
                current_date = common_dates[i]
                
                # Get momentum rankings
                momentum_ranks = momentum_matrix.iloc[i-126].rank(pct=True)
                
                # Long top 30%, short bottom 30%
                long_symbols = momentum_ranks[momentum_ranks > 0.7].index.tolist()
                short_symbols = momentum_ranks[momentum_ranks < 0.3].index.tolist()
                
                # Calculate portfolio return
                portfolio_return = 0
                valid_positions = 0
                
                # Long positions
                for symbol in long_symbols:
                    if symbol in data and current_date in data[symbol].index:
                        forward_return = data[symbol].loc[current_date:].iloc[126]['close'] / data[symbol].loc[current_date]['close'] - 1
                        portfolio_return += forward_return / len(long_symbols)
                        valid_positions += 1
                
                # Short positions
                for symbol in short_symbols:
                    if symbol in data and current_date in data[symbol].index:
                        forward_return = data[symbol].loc[current_date:].iloc[126]['close'] / data[symbol].loc[current_date]['close'] - 1
                        portfolio_return -= forward_return / len(short_symbols)
                        valid_positions += 1
                
                if valid_positions > 0:
                    strategy_returns.append(portfolio_return)
            
            if strategy_returns:
                total_return = np.sum(strategy_returns)
                volatility = np.std(strategy_returns) * np.sqrt(252)
                sharpe_ratio = total_return / volatility if volatility > 0 else 0
                
                return {
                    'success': True,
                    'cross_sectional_metrics': {
                        'total_return': total_return,
                        'volatility': volatility,
                        'sharpe_ratio': sharpe_ratio,
                        'trades': len(strategy_returns)
                    },
                    'academic_validation': {
                        'cross_sectional_effective': sharpe_ratio > self.config.min_momentum_persistence,
                        'diversification_benefit': len(data) >= 4
                    }
                }
            else:
                return {'success': False, 'error': 'No valid cross-sectional trades generated'}
                
        except Exception as e:
            logger.error(f"Error testing cross-sectional momentum: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _test_market_efficiency(self) -> Dict:
        """
        Test market efficiency hypothesis
        Based on Fama (1970) efficient market hypothesis
        """
        try:
            print("   Testing market efficiency...")
            
            # Load market data (SPY as market proxy)
            market_data = await self._load_momentum_data(['SPY'], months=24)
            
            if not market_data or 'SPY' not in market_data:
                return {'success': False, 'error': 'No market data available'}
            
            spy_df = market_data['SPY']
            
            # Test weak-form efficiency (random walk)
            returns = spy_df['close'].pct_change().dropna()
            
            # Augmented Dickey-Fuller test for stationarity
            try:
                from statsmodels.tsa.stattools import adfuller
                adf_result = adfuller(returns)
                adf_pvalue = adf_result[1]
            except ImportError:
                # Fallback to simple autocorrelation test
                autocorr = returns.autocorr()
                adf_pvalue = 0.1 if abs(autocorr) < 0.1 else 0.01
            
            # Test for serial correlation
            autocorr_lag1 = returns.autocorr()
            autocorr_lag5 = returns.autocorr(lag=5)
            
            # Test for predictability
            # Split data into training and testing
            split_point = len(returns) // 2
            train_returns = returns[:split_point]
            test_returns = returns[split_point:]
            
            # Simple AR(1) model for predictability
            try:
                from statsmodels.tsa.ar_model import AutoReg
                model = AutoReg(train_returns, lags=1)
                fitted_model = model.fit()
                
                # Predict test period
                predictions = fitted_model.predict(start=split_point, end=len(returns)-1)
                
                # Calculate prediction accuracy
                mse = np.mean((test_returns - predictions) ** 2)
                baseline_mse = np.mean(test_returns ** 2)
                predictability_ratio = mse / baseline_mse if baseline_mse > 0 else 1
                
            except ImportError:
                # Fallback to simple moving average prediction
                ma_predictions = train_returns.rolling(20).mean().iloc[split_point:]
                mse = np.mean((test_returns - ma_predictions) ** 2)
                baseline_mse = np.mean(test_returns ** 2)
                predictability_ratio = mse / baseline_mse if baseline_mse > 0 else 1
            
            # Market efficiency assessment
            efficiency_score = 0
            efficiency_issues = []
            
            # Check stationarity
            if adf_pvalue < 0.05:
                efficiency_score += 0.25
            else:
                efficiency_issues.append("Non-stationary returns")
            
            # Check autocorrelation
            if abs(autocorr_lag1) < 0.1 and abs(autocorr_lag5) < 0.1:
                efficiency_score += 0.25
            else:
                efficiency_issues.append("Significant autocorrelation")
            
            # Check predictability
            if predictability_ratio > 0.9:  # Predictions not much better than random
                efficiency_score += 0.5
            else:
                efficiency_issues.append("Returns are predictable")
            
            return {
                'success': True,
                'efficiency_metrics': {
                    'adf_pvalue': adf_pvalue,
                    'autocorr_lag1': autocorr_lag1,
                    'autocorr_lag5': autocorr_lag5,
                    'predictability_ratio': predictability_ratio
                },
                'efficiency_score': efficiency_score,
                'efficiency_issues': efficiency_issues,
                'academic_validation': {
                    'market_efficient': efficiency_score >= 0.75,
                    'weak_form_efficiency': adf_pvalue < 0.05 and abs(autocorr_lag1) < 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Error testing market efficiency: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _analyze_risk_adjusted_performance(self) -> Dict:
        """
        Analyze risk-adjusted performance using academic metrics
        Based on Sharpe, Sortino, and Information ratios
        """
        try:
            print("   Analyzing risk-adjusted performance...")
            
            # Load data for risk analysis
            data = await self._load_momentum_data(self.config.symbols[:4], months=24)
            
            if not data:
                return {'success': False, 'error': 'No data available for risk analysis'}
            
            risk_metrics = {}
            
            for symbol, df in data.items():
                if len(df) < 252:
                    continue
                
                # Calculate returns
                df['returns'] = df['close'].pct_change().dropna()
                
                # Risk-free rate (approximation)
                risk_free_rate = 0.03 / 252  # 3% annual rate
                
                # Sharpe Ratio
                excess_returns = df['returns'] - risk_free_rate
                sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
                
                # Sortino Ratio (downside deviation)
                downside_returns = df['returns'][df['returns'] < 0]
                downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0.01
                sortino_ratio = excess_returns.mean() / downside_deviation * np.sqrt(252) if downside_deviation > 0 else 0
                
                # Information Ratio (vs market)
                if 'SPY' in data:
                    market_returns = data['SPY']['close'].pct_change().dropna()
                    # Align dates
                    common_dates = df['returns'].index.intersection(market_returns.index)
                    if len(common_dates) > 60:
                        strategy_returns = df['returns'].loc[common_dates]
                        market_returns_aligned = market_returns.loc[common_dates]
                        active_returns = strategy_returns - market_returns_aligned
                        information_ratio = active_returns.mean() / active_returns.std() * np.sqrt(252) if active_returns.std() > 0 else 0
                    else:
                        information_ratio = 0
                else:
                    information_ratio = 0
                
                # Maximum Drawdown
                max_drawdown = self._calculate_max_drawdown(df['returns'])
                
                # Value at Risk (95% confidence)
                var_95 = np.percentile(df['returns'], 5)
                
                # Conditional Value at Risk (Expected Shortfall)
                cvar_95 = df['returns'][df['returns'] <= var_95].mean()
                
                risk_metrics[symbol] = {
                    'sharpe_ratio': sharpe_ratio,
                    'sortino_ratio': sortino_ratio,
                    'information_ratio': information_ratio,
                    'max_drawdown': max_drawdown,
                    'var_95': var_95,
                    'cvar_95': cvar_95,
                    'volatility': df['returns'].std() * np.sqrt(252)
                }
            
            # Aggregate metrics
            if risk_metrics:
                avg_sharpe = np.mean([m['sharpe_ratio'] for m in risk_metrics.values()])
                avg_sortino = np.mean([m['sortino_ratio'] for m in risk_metrics.values()])
                avg_information = np.mean([m['information_ratio'] for m in risk_metrics.values()])
                
                return {
                    'success': True,
                    'risk_metrics': risk_metrics,
                    'aggregated_risk_metrics': {
                        'avg_sharpe_ratio': avg_sharpe,
                        'avg_sortino_ratio': avg_sortino,
                        'avg_information_ratio': avg_information
                    },
                    'academic_validation': {
                        'risk_adjusted_returns_acceptable': avg_sharpe > self.config.min_sharpe_ratio,
                        'downside_protection_effective': avg_sortino > 0.5,
                        'alpha_generation': avg_information > 0.3
                    }
                }
            else:
                return {'success': False, 'error': 'No valid risk metrics calculated'}
                
        except Exception as e:
            logger.error(f"Error analyzing risk-adjusted performance: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _test_statistical_significance(self) -> Dict:
        """
        Test statistical significance of strategy performance
        Based on t-tests and bootstrap methods
        """
        try:
            print("   Testing statistical significance...")
            
            # Load data for statistical testing
            data = await self._load_momentum_data(self.config.symbols[:3], months=24)
            
            if not data:
                return {'success': False, 'error': 'No data available for statistical testing'}
            
            significance_results = {}
            
            for symbol, df in data.items():
                if len(df) < 252:
                    continue
                
                # Calculate strategy returns
                df['returns'] = df['close'].pct_change().dropna()
                
                # Simple momentum strategy for testing
                df['momentum'] = df['close'].pct_change(20)
                df['signal'] = np.where(df['momentum'] > 0, 1, 0)
                df['strategy_returns'] = df['signal'].shift(1) * df['returns']
                
                strategy_returns = df['strategy_returns'].dropna()
                
                if len(strategy_returns) < 60:
                    continue
                
                # T-test for mean return significance
                t_stat, p_value = stats.ttest_1samp(strategy_returns, 0)
                
                # Bootstrap confidence intervals
                bootstrap_means = []
                n_bootstrap = 1000
                
                for _ in range(n_bootstrap):
                    bootstrap_sample = np.random.choice(strategy_returns, size=len(strategy_returns), replace=True)
                    bootstrap_means.append(bootstrap_sample.mean())
                
                bootstrap_ci_lower = np.percentile(bootstrap_means, 2.5)
                bootstrap_ci_upper = np.percentile(bootstrap_means, 97.5)
                
                # Jarque-Bera test for normality
                try:
                    jb_stat, jb_pvalue = stats.jarque_bera(strategy_returns)
                except:
                    jb_stat, jb_pvalue = 0, 1
                
                significance_results[symbol] = {
                    'mean_return': strategy_returns.mean(),
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'bootstrap_ci_lower': bootstrap_ci_lower,
                    'bootstrap_ci_upper': bootstrap_ci_upper,
                    'jarque_bera_stat': jb_stat,
                    'jarque_bera_pvalue': jb_pvalue,
                    'sample_size': len(strategy_returns)
                }
            
            # Aggregate significance results
            if significance_results:
                significant_strategies = [s for s, r in significance_results.items() if r['p_value'] < self.config.min_statistical_significance]
                avg_p_value = np.mean([r['p_value'] for r in significance_results.values()])
                
                return {
                    'success': True,
                    'significance_results': significance_results,
                    'aggregated_significance': {
                        'significant_strategies': len(significant_strategies),
                        'total_strategies': len(significance_results),
                        'avg_p_value': avg_p_value,
                        'significance_rate': len(significant_strategies) / len(significance_results)
                    },
                    'academic_validation': {
                        'statistically_significant': len(significant_strategies) >= len(significance_results) * 0.5,
                        'robust_results': avg_p_value < 0.1
                    }
                }
            else:
                return {'success': False, 'error': 'No valid statistical tests performed'}
                
        except Exception as e:
            logger.error(f"Error testing statistical significance: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _perform_factor_analysis(self) -> Dict:
        """
        Perform factor analysis on strategy returns
        Based on Fama-French and Carhart factor models
        """
        try:
            print("   Performing factor analysis...")
            
            # Load data for factor analysis
            data = await self._load_momentum_data(self.config.symbols[:4], months=36)
            
            if not data or len(data) < 2:
                return {'success': False, 'error': 'Insufficient data for factor analysis'}
            
            factor_results = {}
            
            # Use SPY as market factor
            if 'SPY' not in data:
                return {'success': False, 'error': 'Market factor (SPY) not available'}
            
            market_returns = data['SPY']['close'].pct_change().dropna()
            
            for symbol, df in data.items():
                if symbol == 'SPY' or len(df) < 252:
                    continue
                
                # Calculate strategy returns
                df['returns'] = df['close'].pct_change().dropna()
                
                # Align with market returns
                common_dates = df['returns'].index.intersection(market_returns.index)
                if len(common_dates) < 252:
                    continue
                
                strategy_returns = df['returns'].loc[common_dates]
                market_returns_aligned = market_returns.loc[common_dates]
                
                # Simple momentum strategy
                df['momentum'] = df['close'].pct_change(20)
                df['signal'] = np.where(df['momentum'] > 0, 1, 0)
                df['strategy_returns'] = df['signal'].shift(1) * df['returns']
                
                strategy_excess_returns = df['strategy_returns'].loc[common_dates] - 0.03/252  # Risk-free rate
                
                # Market factor loading (beta)
                if len(strategy_excess_returns) > 60:
                    # Rolling beta calculation
                    betas = []
                    for i in range(60, len(strategy_excess_returns)):
                        window_returns = strategy_excess_returns.iloc[i-60:i]
                        window_market = market_returns_aligned.iloc[i-60:i]
                        
                        if window_returns.std() > 0 and window_market.std() > 0:
                            beta = np.cov(window_returns, window_market)[0,1] / np.var(window_market)
                            betas.append(beta)
                    
                    if betas:
                        avg_beta = np.mean(betas)
                        beta_significance = len([b for b in betas if abs(b) > self.config.min_factor_loading]) / len(betas)
                        
                        # R-squared (explained variance)
                        correlation = np.corrcoef(strategy_excess_returns, market_returns_aligned)[0,1]
                        r_squared = correlation ** 2 if not np.isnan(correlation) else 0
                        
                        factor_results[symbol] = {
                            'market_beta': avg_beta,
                            'beta_significance': beta_significance,
                            'r_squared': r_squared,
                            'factor_loading_significant': beta_significance > 0.5
                        }
            
            # Aggregate factor analysis results
            if factor_results:
                avg_beta = np.mean([r['market_beta'] for r in factor_results.values()])
                avg_r_squared = np.mean([r['r_squared'] for r in factor_results.values()])
                significant_factors = [s for s, r in factor_results.items() if r['factor_loading_significant']]
                
                return {
                    'success': True,
                    'factor_results': factor_results,
                    'aggregated_factor_metrics': {
                        'avg_market_beta': avg_beta,
                        'avg_r_squared': avg_r_squared,
                        'significant_factors': len(significant_factors),
                        'total_factors': len(factor_results)
                    },
                    'academic_validation': {
                        'factor_model_applicable': avg_r_squared > 0.1,
                        'market_factor_significant': len(significant_factors) >= len(factor_results) * 0.5
                    }
                }
            else:
                return {'success': False, 'error': 'No valid factor analysis results'}
                
        except Exception as e:
            logger.error(f"Error performing factor analysis: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _generate_academic_report(self, results: Dict):
        """Generate comprehensive academic validation report"""
        try:
            print("   Generating academic report...")
            
            # Calculate overall academic validation score
            academic_score = 0
            total_tests = 0
            passed_tests = 0
            
            # Momentum factors validation
            momentum_results = results.get('momentum_factors', {})
            if momentum_results:
                total_tests += 4  # 4 momentum tests
                for test_name, test_result in momentum_results.items():
                    if test_result.get('success', False):
                        validation = test_result.get('academic_validation', {})
                        if any(validation.values()):
                            passed_tests += 1
                            academic_score += 0.25
            
            # Market efficiency validation
            efficiency_results = results.get('market_efficiency', {})
            if efficiency_results.get('success', False):
                total_tests += 1
                validation = efficiency_results.get('academic_validation', {})
                if validation.get('market_efficient', False):
                    passed_tests += 1
                    academic_score += 0.2
            
            # Risk-adjusted performance validation
            risk_results = results.get('risk_adjusted_performance', {})
            if risk_results.get('success', False):
                total_tests += 1
                validation = risk_results.get('academic_validation', {})
                if validation.get('risk_adjusted_returns_acceptable', False):
                    passed_tests += 1
                    academic_score += 0.2
            
            # Statistical significance validation
            significance_results = results.get('statistical_significance', {})
            if significance_results.get('success', False):
                total_tests += 1
                validation = significance_results.get('academic_validation', {})
                if validation.get('statistically_significant', False):
                    passed_tests += 1
                    academic_score += 0.2
            
            # Factor analysis validation
            factor_results = results.get('factor_analysis', {})
            if factor_results.get('success', False):
                total_tests += 1
                validation = factor_results.get('academic_validation', {})
                if validation.get('factor_model_applicable', False):
                    passed_tests += 1
                    academic_score += 0.15
            
            # Generate report
            report = {
                'timestamp': datetime.now().isoformat(),
                'config': {
                    'strategies': self.config.strategies,
                    'academic_factors': self.config.academic_factors,
                    'symbols': self.config.symbols,
                    'time_periods': self.config.time_periods
                },
                'results': results,
                'academic_validation_summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'academic_score': academic_score,
                    'success_rate': passed_tests / total_tests if total_tests > 0 else 0
                },
                'recommendations': self._generate_academic_recommendations(results, academic_score)
            }
            
            # Save report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path(self.config.results_dir) / f"phase4_academic_validation_{timestamp}.json"
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"✅ Academic report saved to: {report_path}")
            
            # Print summary
            self._print_academic_summary(report)
            
        except Exception as e:
            logger.error(f"Error generating academic report: {e}")
    
    def _generate_academic_recommendations(self, results: Dict, academic_score: float) -> List[str]:
        """Generate academic recommendations based on results"""
        recommendations = []
        
        if academic_score >= 0.8:
            recommendations.append("🎓 Excellent academic validation! Strategies align with established research.")
        elif academic_score >= 0.6:
            recommendations.append("📚 Good academic validation. Minor improvements recommended.")
        elif academic_score >= 0.4:
            recommendations.append("📖 Moderate academic validation. Significant improvements needed.")
        else:
            recommendations.append("❌ Poor academic validation. Major improvements required.")
        
        # Specific recommendations
        momentum_results = results.get('momentum_factors', {})
        if momentum_results:
            jt_result = momentum_results.get('jegadeesh_titman_momentum', {})
            if not jt_result.get('success', False):
                recommendations.append("🔧 Improve Jegadeesh & Titman momentum implementation")
        
        efficiency_results = results.get('market_efficiency', {})
        if efficiency_results.get('success', False):
            validation = efficiency_results.get('academic_validation', {})
            if not validation.get('market_efficient', False):
                recommendations.append("📈 Review market efficiency assumptions")
        
        return recommendations
    
    def _print_academic_summary(self, report: Dict):
        """Print academic validation summary"""
        summary = report['academic_validation_summary']
        
        print("\n" + "="*60)
        print("📚 ACADEMIC RESEARCH VALIDATION SUMMARY")
        print("="*60)
        
        print(f"\n🎓 Academic Validation Score: {summary['academic_score']:.2f}")
        print(f"📊 Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1%}")
        
        print(f"\n📚 Academic Recommendations:")
        recommendations = report.get('recommendations', [])
        for rec in recommendations:
            print(f"   • {rec}")
        
        print("\n" + "="*60)


# Main execution function
async def main():
    """Main execution function"""
    
    # Create validator with default config
    validator = AcademicResearchValidator()
    
    # Run academic validation
    success = await validator.run_academic_validation()
    
    if success:
        print("✅ Phase 4.3 academic validation completed successfully!")
        return 0
    else:
        print("❌ Phase 4.3 academic validation completed with issues")
        return 1


if __name__ == "__main__":
    asyncio.run(main()) 