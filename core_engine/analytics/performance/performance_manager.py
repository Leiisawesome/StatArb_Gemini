"""
Performance Engine - Performance Manager
Unified performance measurement and reporting system
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import json
import warnings
from pathlib import Path

# Import performance components
from .performance_calculator import (
    PerformanceCalculator, PerformanceConfig, PerformanceMetrics,
    PerformancePeriod, ReturnType, PerformanceFrequency
)
from .attribution_engine import (
    AttributionEngine, AttributionConfig, AttributionResult,
    AttributionMethod, AttributionLevel
)
from .benchmark_tracker import (
    BenchmarkTracker, BenchmarkConfig, BenchmarkType,
    RelativePerformanceMetrics
)
from .drawdown_tracker import (
    DrawdownTracker, DrawdownConfig, DrawdownEvent,
    UnderwaterMetrics, DrawdownAnalyzer
)
from .risk_adjusted_metrics import (
    RiskAdjustedMetricsCalculator, RiskAdjustedConfig,
    RiskAdjustedMetrics, RiskAdjustmentMethod
)

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Performance report formats"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    HTML = "html"


class PerformanceLevel(Enum):
    """Performance analysis levels"""
    PORTFOLIO = "portfolio"
    STRATEGY = "strategy"
    POSITION = "position"
    SECTOR = "sector"
    SECURITY = "security"


class ReportingFrequency(Enum):
    """Reporting frequency options"""
    REAL_TIME = "real_time"
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass
class PerformanceManagerConfig:
    """Configuration for performance manager"""
    
    # Core settings
    enable_real_time: bool = True
    enable_attribution: bool = True
    enable_benchmarking: bool = True
    enable_risk_adjustment: bool = True
    enable_drawdown_analysis: bool = True
    
    # Data settings
    max_history_days: int = 1000
    min_data_points: int = 30
    data_validation: bool = True
    
    # Performance calculation settings
    performance_config: Optional[PerformanceConfig] = None
    attribution_config: Optional[AttributionConfig] = None
    benchmark_config: Optional[BenchmarkConfig] = None
    drawdown_config: Optional[DrawdownConfig] = None
    risk_adjusted_config: Optional[RiskAdjustedConfig] = None
    
    # Reporting settings
    default_report_format: ReportFormat = ReportFormat.JSON
    auto_generate_reports: bool = True
    report_frequency: ReportingFrequency = ReportingFrequency.DAILY
    
    # Performance settings
    max_concurrent_calculations: int = 4
    calculation_timeout: float = 30.0
    cache_results: bool = True
    
    # Output settings
    output_directory: str = "performance_reports"
    save_intermediate_results: bool = True


@dataclass 
class ComprehensivePerformanceReport:
    """Comprehensive performance analysis report"""
    
    # Report metadata
    report_id: str = ""
    generation_time: datetime = field(default_factory=datetime.now)
    period_start: datetime = field(default_factory=lambda: datetime.now() - timedelta(days=30))
    period_end: datetime = field(default_factory=datetime.now)
    
    # Core performance metrics
    performance_metrics: Optional[PerformanceMetrics] = None
    risk_adjusted_metrics: Optional[RiskAdjustedMetrics] = None
    
    # Attribution analysis
    attribution_results: Dict[str, AttributionResult] = field(default_factory=dict)
    
    # Benchmark analysis
    benchmark_metrics: Dict[str, RelativePerformanceMetrics] = field(default_factory=dict)
    
    # Drawdown analysis
    drawdown_metrics: Optional[UnderwaterMetrics] = None
    drawdown_events: List[DrawdownEvent] = field(default_factory=list)
    underwater_periods: List[DrawdownEvent] = field(default_factory=list)
    
    # Summary statistics
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    # Risk metrics
    var_95: float = 0.0
    cvar_95: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    
    # Additional analysis
    correlation_matrix: Optional[pd.DataFrame] = None
    rolling_metrics: Optional[pd.DataFrame] = None
    
    # Metadata
    data_quality: Dict[str, Any] = field(default_factory=dict)
    calculation_time: float = 0.0
    warnings: List[str] = field(default_factory=list)


class PerformanceDataValidator:
    """Validate performance data quality"""
    
    def __init__(self):
        self.validation_rules = {
            'min_observations': 10,
            'max_return_threshold': 0.5,  # 50% daily return threshold
            'min_return_threshold': -0.9,  # -90% daily return threshold
            'max_missing_pct': 0.1  # 10% missing data threshold
        }
        
        logger.info("Performance data validator initialized")
    
    def validate_returns(self, returns: Union[pd.Series, np.ndarray]) -> Dict[str, Any]:
        """Validate return data quality"""
        
        try:
            if isinstance(returns, pd.Series):
                returns_array = returns.dropna().values
                has_dates = True
            else:
                returns_array = returns[~np.isnan(returns)]
                has_dates = False
            
            validation_result = {
                'is_valid': True,
                'warnings': [],
                'statistics': {},
                'issues': []
            }
            
            # Check minimum observations
            if len(returns_array) < self.validation_rules['min_observations']:
                validation_result['is_valid'] = False
                validation_result['issues'].append(
                    f"Insufficient data: {len(returns_array)} < {self.validation_rules['min_observations']}"
                )
            
            # Check for extreme returns
            extreme_high = returns_array > self.validation_rules['max_return_threshold']
            extreme_low = returns_array < self.validation_rules['min_return_threshold']
            
            if np.any(extreme_high):
                validation_result['warnings'].append(
                    f"Extreme high returns detected: {np.sum(extreme_high)} observations"
                )
            
            if np.any(extreme_low):
                validation_result['warnings'].append(
                    f"Extreme low returns detected: {np.sum(extreme_low)} observations"
                )
            
            # Check for missing data (if pandas series)
            if has_dates and isinstance(returns, pd.Series):
                missing_pct = returns.isna().sum() / len(returns)
                if missing_pct > self.validation_rules['max_missing_pct']:
                    validation_result['warnings'].append(
                        f"High missing data percentage: {missing_pct:.2%}"
                    )
            
            # Calculate basic statistics
            validation_result['statistics'] = {
                'count': len(returns_array),
                'mean': np.mean(returns_array),
                'std': np.std(returns_array),
                'min': np.min(returns_array),
                'max': np.max(returns_array),
                'skewness': self._calculate_skewness(returns_array),
                'kurtosis': self._calculate_kurtosis(returns_array)
            }
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating returns data: {e}")
            return {
                'is_valid': False,
                'warnings': [],
                'statistics': {},
                'issues': [f"Validation error: {e}"]
            }
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """Calculate skewness"""
        try:
            n = len(data)
            if n < 3:
                return 0.0
            
            mean = np.mean(data)
            std = np.std(data, ddof=1)
            
            if std == 0:
                return 0.0
            
            skewness = np.sum(((data - mean) / std) ** 3) / n
            return skewness
            
        except:
            return 0.0
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """Calculate excess kurtosis"""
        try:
            n = len(data)
            if n < 4:
                return 0.0
            
            mean = np.mean(data)
            std = np.std(data, ddof=1)
            
            if std == 0:
                return 0.0
            
            kurtosis = np.sum(((data - mean) / std) ** 4) / n - 3
            return kurtosis
            
        except:
            return 0.0


class PerformanceReportGenerator:
    """Generate performance reports in various formats"""
    
    def __init__(self, output_directory: str = "performance_reports"):
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        
        logger.info(f"Performance report generator initialized: {self.output_directory}")
    
    def generate_report(self, report: ComprehensivePerformanceReport,
                       format_type: ReportFormat = ReportFormat.JSON,
                       filename: Optional[str] = None) -> str:
        """Generate performance report in specified format"""
        
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"performance_report_{timestamp}"
            
            if format_type == ReportFormat.JSON:
                return self._generate_json_report(report, filename)
            elif format_type == ReportFormat.CSV:
                return self._generate_csv_report(report, filename)
            elif format_type == ReportFormat.EXCEL:
                return self._generate_excel_report(report, filename)
            elif format_type == ReportFormat.HTML:
                return self._generate_html_report(report, filename)
            else:
                logger.warning(f"Unsupported report format: {format_type}")
                return self._generate_json_report(report, filename)
                
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return ""
    
    def _generate_json_report(self, report: ComprehensivePerformanceReport,
                            filename: str) -> str:
        """Generate JSON format report"""
        
        try:
            report_data = {
                'report_metadata': {
                    'report_id': report.report_id,
                    'generation_time': report.generation_time.isoformat(),
                    'period_start': report.period_start.isoformat(),
                    'period_end': report.period_end.isoformat(),
                    'calculation_time': report.calculation_time
                },
                'summary_metrics': {
                    'total_return': report.total_return,
                    'annualized_return': report.annualized_return,
                    'volatility': report.volatility,
                    'sharpe_ratio': report.sharpe_ratio,
                    'max_drawdown': report.max_drawdown,
                    'var_95': report.var_95,
                    'cvar_95': report.cvar_95,
                    'beta': report.beta,
                    'alpha': report.alpha
                }
            }
            
            # Add performance metrics
            if report.performance_metrics:
                report_data['performance_metrics'] = self._serialize_performance_metrics(
                    report.performance_metrics
                )
            
            # Add risk-adjusted metrics
            if report.risk_adjusted_metrics:
                report_data['risk_adjusted_metrics'] = self._serialize_risk_adjusted_metrics(
                    report.risk_adjusted_metrics
                )
            
            # Add attribution results
            if report.attribution_results:
                report_data['attribution_analysis'] = {}
                for method, result in report.attribution_results.items():
                    report_data['attribution_analysis'][method] = self._serialize_attribution_result(result)
            
            # Add benchmark analysis
            if report.benchmark_metrics:
                report_data['benchmark_analysis'] = {}
                for benchmark, metrics in report.benchmark_metrics.items():
                    report_data['benchmark_analysis'][benchmark] = self._serialize_benchmark_metrics(metrics)
            
            # Add drawdown analysis
            if report.drawdown_metrics:
                report_data['drawdown_analysis'] = self._serialize_drawdown_metrics(
                    report.drawdown_metrics, report.drawdown_events, report.underwater_periods
                )
            
            # Add data quality information
            report_data['data_quality'] = report.data_quality
            report_data['warnings'] = report.warnings
            
            # Save to file
            output_path = self.output_directory / f"{filename}.json"
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.info(f"JSON report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")
            return ""
    
    def _generate_csv_report(self, report: ComprehensivePerformanceReport,
                           filename: str) -> str:
        """Generate CSV format report (summary metrics)"""
        
        try:
            # Create summary DataFrame
            summary_data = {
                'Metric': [
                    'Total Return', 'Annualized Return', 'Volatility',
                    'Sharpe Ratio', 'Max Drawdown', 'VaR 95%', 'CVaR 95%',
                    'Beta', 'Alpha'
                ],
                'Value': [
                    report.total_return, report.annualized_return, report.volatility,
                    report.sharpe_ratio, report.max_drawdown, report.var_95,
                    report.cvar_95, report.beta, report.alpha
                ]
            }
            
            df_summary = pd.DataFrame(summary_data)
            
            # Save to file
            output_path = self.output_directory / f"{filename}_summary.csv"
            df_summary.to_csv(output_path, index=False)
            
            # Save rolling metrics if available
            if report.rolling_metrics is not None:
                rolling_path = self.output_directory / f"{filename}_rolling.csv"
                report.rolling_metrics.to_csv(rolling_path)
            
            logger.info(f"CSV report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating CSV report: {e}")
            return ""
    
    def _generate_excel_report(self, report: ComprehensivePerformanceReport,
                             filename: str) -> str:
        """Generate Excel format report with multiple sheets"""
        
        try:
            output_path = self.output_directory / f"{filename}.xlsx"
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Summary sheet
                summary_data = {
                    'Metric': [
                        'Total Return', 'Annualized Return', 'Volatility',
                        'Sharpe Ratio', 'Max Drawdown', 'VaR 95%', 'CVaR 95%',
                        'Beta', 'Alpha'
                    ],
                    'Value': [
                        report.total_return, report.annualized_return, report.volatility,
                        report.sharpe_ratio, report.max_drawdown, report.var_95,
                        report.cvar_95, report.beta, report.alpha
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # Rolling metrics sheet
                if report.rolling_metrics is not None:
                    report.rolling_metrics.to_excel(writer, sheet_name='Rolling_Metrics')
                
                # Drawdown events sheet
                if report.drawdown_events:
                    drawdown_data = []
                    for event in report.drawdown_events:
                        drawdown_data.append({
                            'Start_Date': event.start_date,
                            'End_Date': event.end_date,
                            'Duration_Days': event.duration_days,
                            'Peak_Value': event.peak_value,
                            'Trough_Value': event.trough_value,
                            'Drawdown_Percent': event.drawdown_percent,
                            'Recovery_Date': event.recovery_date
                        })
                    
                    if drawdown_data:
                        pd.DataFrame(drawdown_data).to_excel(writer, sheet_name='Drawdown_Events', index=False)
            
            logger.info(f"Excel report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating Excel report: {e}")
            return ""
    
    def _generate_html_report(self, report: ComprehensivePerformanceReport,
                            filename: str) -> str:
        """Generate HTML format report"""
        
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Performance Report - {report.report_id}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; }}
                    .section {{ margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Performance Report</h1>
                    <p>Report ID: {report.report_id}</p>
                    <p>Period: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}</p>
                    <p>Generated: {report.generation_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="section">
                    <h2>Summary Metrics</h2>
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>
                        <tr><td>Total Return</td><td>{report.total_return:.2%}</td></tr>
                        <tr><td>Annualized Return</td><td>{report.annualized_return:.2%}</td></tr>
                        <tr><td>Volatility</td><td>{report.volatility:.2%}</td></tr>
                        <tr><td>Sharpe Ratio</td><td>{report.sharpe_ratio:.3f}</td></tr>
                        <tr><td>Max Drawdown</td><td>{report.max_drawdown:.2%}</td></tr>
                        <tr><td>VaR 95%</td><td>{report.var_95:.2%}</td></tr>
                        <tr><td>CVaR 95%</td><td>{report.cvar_95:.2%}</td></tr>
                        <tr><td>Beta</td><td>{report.beta:.3f}</td></tr>
                        <tr><td>Alpha</td><td>{report.alpha:.2%}</td></tr>
                    </table>
                </div>
            </body>
            </html>
            """
            
            output_path = self.output_directory / f"{filename}.html"
            with open(output_path, 'w') as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            return ""
    
    def _serialize_performance_metrics(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Serialize performance metrics to dictionary"""
        
        return {
            'total_return': metrics.total_return,
            'annualized_return': metrics.annualized_return,
            'volatility': metrics.volatility,
            'sharpe_ratio': metrics.sharpe_ratio,
            'sortino_ratio': metrics.sortino_ratio,
            'calmar_ratio': metrics.calmar_ratio,
            'max_drawdown': metrics.max_drawdown,
            'var_95': metrics.var_95,
            'cvar_95': metrics.cvar_95,
            'skewness': metrics.skewness,
            'kurtosis': metrics.kurtosis,
            'win_rate': metrics.win_rate,
            'profit_factor': metrics.profit_factor,
            'calculation_time': metrics.calculation_time.isoformat() if metrics.calculation_time else None
        }
    
    def _serialize_risk_adjusted_metrics(self, metrics: RiskAdjustedMetrics) -> Dict[str, Any]:
        """Serialize risk-adjusted metrics to dictionary"""
        
        return {
            'sharpe_ratio': metrics.sharpe_ratio,
            'sortino_ratio': metrics.sortino_ratio,
            'calmar_ratio': metrics.calmar_ratio,
            'omega_ratio': metrics.omega_ratio,
            'treynor_ratio': metrics.treynor_ratio,
            'jensen_alpha': metrics.jensen_alpha,
            'information_ratio': metrics.information_ratio,
            'modigliani_ratio': metrics.modigliani_ratio,
            'beta': metrics.beta,
            'alpha': metrics.alpha,
            'correlation': metrics.correlation,
            'tracking_error': metrics.tracking_error
        }
    
    def _serialize_attribution_result(self, result: AttributionResult) -> Dict[str, Any]:
        """Serialize attribution result to dictionary"""
        
        return {
            'total_attribution': result.total_attribution,
            'active_return': result.active_return,
            'calculation_time': result.calculation_time.isoformat() if result.calculation_time else None
        }
    
    def _serialize_benchmark_metrics(self, metrics: RelativePerformanceMetrics) -> Dict[str, Any]:
        """Serialize benchmark metrics to dictionary"""
        
        return {
            'excess_return': metrics.excess_return,
            'tracking_error': metrics.tracking_error,
            'information_ratio': metrics.information_ratio,
            'correlation': metrics.correlation,
            'beta': metrics.beta,
            'alpha': metrics.alpha
        }
    
    def _serialize_drawdown_metrics(self, metrics: UnderwaterMetrics,
                                  events: List[DrawdownEvent],
                                  underwater_periods: List[DrawdownEvent]) -> Dict[str, Any]:
        """Serialize drawdown analysis to dictionary"""
        
        return {
            'max_drawdown': metrics.max_drawdown,
            'avg_drawdown': metrics.avg_drawdown,
            'drawdown_frequency': metrics.drawdown_frequency,
            'avg_recovery_time': metrics.avg_recovery_time,
            'max_recovery_time': metrics.max_recovery_time,
            'total_events': len(events),
            'total_underwater_periods': len(underwater_periods)
        }


class PerformanceManager:
    """
    Unified Performance Management System
    
    Orchestrates all performance analysis components including calculation,
    attribution, benchmarking, risk adjustment, and reporting.
    """
    
    def __init__(self, config: Optional[PerformanceManagerConfig] = None):
        """Initialize performance manager"""
        
        self.config = config or PerformanceManagerConfig()
        
        # Initialize component calculators
        self._performance_calculator = PerformanceCalculator(
            self.config.performance_config or PerformanceConfig()
        )
        
        self._attribution_engine = AttributionEngine(
            self.config.attribution_config or AttributionConfig()
        ) if self.config.enable_attribution else None
        
        self._benchmark_tracker = BenchmarkTracker(
            self.config.benchmark_config or BenchmarkConfig()
        ) if self.config.enable_benchmarking else None
        
        self._drawdown_tracker = DrawdownTracker(
            self.config.drawdown_config or DrawdownConfig()
        ) if self.config.enable_drawdown_analysis else None
        
        self._risk_adjusted_calculator = RiskAdjustedMetricsCalculator(
            self.config.risk_adjusted_config or RiskAdjustedConfig()
        ) if self.config.enable_risk_adjustment else None
        
        # Initialize utilities
        self._data_validator = PerformanceDataValidator()
        self._report_generator = PerformanceReportGenerator(self.config.output_directory)
        
        # Performance tracking
        self._analysis_cache: Dict[str, ComprehensivePerformanceReport] = {}
        self._calculation_history: List[Dict[str, Any]] = []
        
        # Async execution
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_calculations)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Performance statistics
        self._manager_stats = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'avg_calculation_time': 0.0,
            'last_analysis_time': None
        }
        
        logger.info("Performance manager initialized with all components")
    
    def analyze_performance(self, returns: Union[pd.Series, np.ndarray],
                          portfolio_weights: Optional[Union[pd.DataFrame, np.ndarray]] = None,
                          benchmark_returns: Optional[Union[pd.Series, np.ndarray]] = None,
                          market_returns: Optional[Union[pd.Series, np.ndarray]] = None,
                          factor_returns: Optional[pd.DataFrame] = None,
                          identifier: str = "default",
                          report_format: ReportFormat = ReportFormat.JSON) -> ComprehensivePerformanceReport:
        """Perform comprehensive performance analysis"""
        
        start_time = datetime.now()
        
        try:
            with self._lock:
                self._manager_stats['total_analyses'] += 1
                
                logger.info(f"Starting comprehensive performance analysis for {identifier}")
                
                # Initialize report
                report = ComprehensivePerformanceReport()
                report.report_id = f"{identifier}_{int(datetime.now().timestamp())}"
                report.generation_time = start_time
                
                # Validate input data
                if self.config.data_validation:
                    validation_result = self._data_validator.validate_returns(returns)
                    report.data_quality = validation_result
                    
                    if not validation_result['is_valid']:
                        report.warnings.extend(validation_result['issues'])
                        logger.warning(f"Data validation failed for {identifier}")
                
                # Convert inputs to consistent format
                if isinstance(returns, pd.Series):
                    returns_array = returns.dropna().values
                    report.period_start = returns.index[0] if len(returns.index) > 0 else start_time
                    report.period_end = returns.index[-1] if len(returns.index) > 0 else start_time
                else:
                    returns_array = returns[~np.isnan(returns)]
                    report.period_start = start_time - timedelta(days=len(returns_array))
                    report.period_end = start_time
                
                # Core performance metrics
                performance_metrics = self._performance_calculator.calculate_comprehensive_metrics(
                    returns, identifier
                )
                report.performance_metrics = performance_metrics
                
                # Extract key metrics for summary
                if performance_metrics:
                    report.total_return = performance_metrics.total_return
                    report.annualized_return = performance_metrics.annualized_return
                    report.volatility = performance_metrics.volatility
                    report.sharpe_ratio = performance_metrics.sharpe_ratio
                    report.max_drawdown = performance_metrics.max_drawdown
                    report.var_95 = performance_metrics.var_95
                    report.cvar_95 = performance_metrics.cvar_95
                
                # Risk-adjusted metrics
                if self._risk_adjusted_calculator:
                    risk_metrics = self._risk_adjusted_calculator.calculate_all_metrics(
                        returns_array, market_returns, benchmark_returns, identifier
                    )
                    report.risk_adjusted_metrics = risk_metrics
                    
                    # Update summary with risk-adjusted metrics
                    if risk_metrics:
                        report.beta = risk_metrics.beta
                        report.alpha = risk_metrics.alpha
                
                # Attribution analysis
                if self._attribution_engine and portfolio_weights is not None:
                    try:
                        attribution_results = {}
                        
                        # Brinson attribution
                        brinson_result = self._attribution_engine.calculate_brinson_attribution(
                            returns, portfolio_weights, benchmark_returns, identifier
                        )
                        if brinson_result:
                            attribution_results['brinson'] = brinson_result
                        
                        # Factor attribution (if factor data provided)
                        if factor_returns is not None:
                            factor_result = self._attribution_engine.calculate_factor_attribution(
                                returns, factor_returns, identifier
                            )
                            if factor_result:
                                attribution_results['factor'] = factor_result
                        
                        report.attribution_results = attribution_results
                        
                    except Exception as e:
                        logger.warning(f"Attribution analysis failed: {e}")
                        report.warnings.append(f"Attribution analysis failed: {e}")
                
                # Benchmark analysis
                if self._benchmark_tracker and benchmark_returns is not None:
                    try:
                        benchmark_metrics = self._benchmark_tracker.calculate_relative_performance(
                            returns, benchmark_returns, identifier
                        )
                        if benchmark_metrics:
                            report.benchmark_metrics['primary'] = benchmark_metrics
                        
                    except Exception as e:
                        logger.warning(f"Benchmark analysis failed: {e}")
                        report.warnings.append(f"Benchmark analysis failed: {e}")
                
                # Drawdown analysis
                if self._drawdown_tracker:
                    try:
                        drawdown_metrics = self._drawdown_tracker.analyze_drawdowns(returns, identifier)
                        drawdown_events = self._drawdown_tracker.get_drawdown_events(identifier)
                        underwater_periods = self._drawdown_tracker.get_underwater_periods(identifier)
                        
                        report.drawdown_metrics = drawdown_metrics
                        report.drawdown_events = drawdown_events or []
                        report.underwater_periods = underwater_periods or []
                        
                    except Exception as e:
                        logger.warning(f"Drawdown analysis failed: {e}")
                        report.warnings.append(f"Drawdown analysis failed: {e}")
                
                # Calculate rolling metrics
                if len(returns_array) > 30:  # Sufficient data for rolling analysis
                    try:
                        rolling_metrics = self._calculate_rolling_metrics(returns)
                        report.rolling_metrics = rolling_metrics
                    except Exception as e:
                        logger.warning(f"Rolling metrics calculation failed: {e}")
                
                # Calculate calculation time
                end_time = datetime.now()
                calculation_time = (end_time - start_time).total_seconds()
                report.calculation_time = calculation_time
                
                # Cache report
                if self.config.cache_results:
                    self._analysis_cache[identifier] = report
                
                # Generate report file
                if self.config.auto_generate_reports:
                    try:
                        report_path = self._report_generator.generate_report(
                            report, report_format, f"performance_{identifier}"
                        )
                        logger.info(f"Performance report saved: {report_path}")
                    except Exception as e:
                        logger.warning(f"Report generation failed: {e}")
                        report.warnings.append(f"Report generation failed: {e}")
                
                # Update statistics
                self._manager_stats['successful_analyses'] += 1
                self._manager_stats['last_analysis_time'] = end_time
                
                # Update average calculation time
                total_time = (self._manager_stats['avg_calculation_time'] * 
                            (self._manager_stats['successful_analyses'] - 1) + calculation_time)
                self._manager_stats['avg_calculation_time'] = total_time / self._manager_stats['successful_analyses']
                
                # Store calculation history
                self._calculation_history.append({
                    'identifier': identifier,
                    'timestamp': end_time,
                    'calculation_time': calculation_time,
                    'data_points': len(returns_array),
                    'warnings': len(report.warnings)
                })
                
                logger.info(f"Performance analysis completed for {identifier} in {calculation_time:.2f}s")
                
                return report
                
        except Exception as e:
            logger.error(f"Error in performance analysis for {identifier}: {e}")
            self._manager_stats['failed_analyses'] += 1
            
            # Return minimal report with error information
            error_report = ComprehensivePerformanceReport()
            error_report.report_id = f"{identifier}_error_{int(datetime.now().timestamp())}"
            error_report.generation_time = start_time
            error_report.warnings = [f"Analysis failed: {e}"]
            error_report.calculation_time = (datetime.now() - start_time).total_seconds()
            
            return error_report
    
    async def analyze_performance_async(self, returns: Union[pd.Series, np.ndarray],
                                      **kwargs) -> ComprehensivePerformanceReport:
        """Asynchronous performance analysis"""
        
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self._executor,
            self.analyze_performance,
            returns,
            **kwargs
        )
    
    def compare_performance(self, identifiers: List[str]) -> Dict[str, Any]:
        """Compare performance across multiple identifiers"""
        
        try:
            with self._lock:
                comparison_results = {
                    'identifiers': identifiers,
                    'comparison_time': datetime.now(),
                    'metrics_comparison': {},
                    'rankings': {},
                    'correlation_matrix': None
                }
                
                reports = []
                for identifier in identifiers:
                    report = self._analysis_cache.get(identifier)
                    if report:
                        reports.append((identifier, report))
                    else:
                        logger.warning(f"No cached report found for {identifier}")
                
                if len(reports) < 2:
                    logger.warning("Insufficient reports for comparison")
                    return comparison_results
                
                # Metrics comparison
                metrics_data = []
                for identifier, report in reports:
                    metrics_data.append({
                        'identifier': identifier,
                        'total_return': report.total_return,
                        'annualized_return': report.annualized_return,
                        'volatility': report.volatility,
                        'sharpe_ratio': report.sharpe_ratio,
                        'max_drawdown': report.max_drawdown,
                        'var_95': report.var_95,
                        'beta': report.beta,
                        'alpha': report.alpha
                    })
                
                comparison_df = pd.DataFrame(metrics_data)
                comparison_results['metrics_comparison'] = comparison_df.to_dict('records')
                
                # Rankings by key metrics
                ranking_metrics = ['total_return', 'sharpe_ratio', 'annualized_return']
                for metric in ranking_metrics:
                    ranked = comparison_df.nlargest(len(comparison_df), metric)
                    comparison_results['rankings'][metric] = ranked[['identifier', metric]].to_dict('records')
                
                return comparison_results
                
        except Exception as e:
            logger.error(f"Error comparing performance: {e}")
            return {}
    
    def _calculate_rolling_metrics(self, returns: Union[pd.Series, np.ndarray],
                                 window: int = 30) -> pd.DataFrame:
        """Calculate rolling performance metrics"""
        
        try:
            if isinstance(returns, np.ndarray):
                returns = pd.Series(returns)
            
            rolling_data = []
            
            for i in range(window, len(returns)):
                window_returns = returns.iloc[i-window:i]
                
                # Calculate basic rolling metrics
                rolling_metrics = {
                    'date': returns.index[i] if hasattr(returns, 'index') else i,
                    'rolling_return': window_returns.mean(),
                    'rolling_volatility': window_returns.std(),
                    'rolling_sharpe': self._calculate_rolling_sharpe(window_returns),
                    'rolling_max_drawdown': self._calculate_rolling_max_drawdown(window_returns)
                }
                
                rolling_data.append(rolling_metrics)
            
            return pd.DataFrame(rolling_data)
            
        except Exception as e:
            logger.error(f"Error calculating rolling metrics: {e}")
            return pd.DataFrame()
    
    def _calculate_rolling_sharpe(self, returns: pd.Series,
                                risk_free_rate: float = 0.02) -> float:
        """Calculate rolling Sharpe ratio"""
        
        try:
            period_rf_rate = risk_free_rate / 252  # Daily risk-free rate
            excess_returns = returns - period_rf_rate
            
            if returns.std() == 0:
                return 0.0
            
            sharpe = excess_returns.mean() / returns.std()
            return sharpe * np.sqrt(252)  # Annualized
            
        except:
            return 0.0
    
    def _calculate_rolling_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate rolling maximum drawdown"""
        
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return drawdown.min()
            
        except:
            return 0.0
    
    def get_cached_report(self, identifier: str) -> Optional[ComprehensivePerformanceReport]:
        """Get cached performance report"""
        
        with self._lock:
            return self._analysis_cache.get(identifier)
    
    def export_report(self, identifier: str,
                     format_type: ReportFormat = ReportFormat.JSON,
                     filename: Optional[str] = None) -> str:
        """Export cached report in specified format"""
        
        try:
            with self._lock:
                report = self._analysis_cache.get(identifier)
                
                if not report:
                    logger.warning(f"No cached report found for {identifier}")
                    return ""
                
                return self._report_generator.generate_report(report, format_type, filename)
                
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return ""
    
    def get_manager_summary(self) -> Dict[str, Any]:
        """Get performance manager summary and statistics"""
        
        with self._lock:
            return {
                'configuration': {
                    'enable_real_time': self.config.enable_real_time,
                    'enable_attribution': self.config.enable_attribution,
                    'enable_benchmarking': self.config.enable_benchmarking,
                    'enable_risk_adjustment': self.config.enable_risk_adjustment,
                    'enable_drawdown_analysis': self.config.enable_drawdown_analysis,
                    'max_concurrent_calculations': self.config.max_concurrent_calculations,
                    'cache_results': self.config.cache_results
                },
                'statistics': self._manager_stats.copy(),
                'cached_reports': len(self._analysis_cache),
                'calculation_history_size': len(self._calculation_history),
                'component_status': {
                    'performance_calculator': self._performance_calculator is not None,
                    'attribution_engine': self._attribution_engine is not None,
                    'benchmark_tracker': self._benchmark_tracker is not None,
                    'drawdown_tracker': self._drawdown_tracker is not None,
                    'risk_adjusted_calculator': self._risk_adjusted_calculator is not None
                }
            }
    
    def clear_cache(self, identifier: Optional[str] = None) -> None:
        """Clear cached reports"""
        
        with self._lock:
            if identifier:
                self._analysis_cache.pop(identifier, None)
                logger.info(f"Cleared cached report for {identifier}")
            else:
                self._analysis_cache.clear()
                logger.info("Cleared all cached reports")
    
    def shutdown(self) -> None:
        """Shutdown performance manager"""
        
        try:
            self._executor.shutdown(wait=True)
            logger.info("Performance manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")