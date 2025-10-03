"""
Analytics Engine - Report Generator
Advanced report generation with customizable layouts and export formats
"""

import logging
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from pathlib import Path
import base64
import io
import warnings

# Import plotting libraries with fallbacks
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_pdf import PdfPages
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    logger.warning("Matplotlib/Seaborn not available - plots will be disabled")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Report output formats"""
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    MARKDOWN = "markdown"


class ChartType(Enum):
    """Chart types"""
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    CANDLESTICK = "candlestick"
    WATERFALL = "waterfall"
    PIE = "pie"
    BOX = "box"
    VIOLIN = "violin"


class ReportSection(Enum):
    """Report sections"""
    EXECUTIVE_SUMMARY = "executive_summary"
    PERFORMANCE_OVERVIEW = "performance_overview"
    RISK_ANALYSIS = "risk_analysis"
    ATTRIBUTION_ANALYSIS = "attribution_analysis"
    HOLDINGS_ANALYSIS = "holdings_analysis"
    TRADING_ANALYSIS = "trading_analysis"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    DETAILED_METRICS = "detailed_metrics"
    CHARTS = "charts"
    APPENDIX = "appendix"


@dataclass
class ChartConfig:
    """Chart configuration"""
    chart_type: ChartType
    title: str
    data_source: str  # Key in data dictionary
    
    # Style settings
    width: int = 800
    height: int = 400
    color_scheme: str = "viridis"
    
    # Axis settings
    x_label: str = ""
    y_label: str = ""
    x_axis_format: str = ""
    y_axis_format: str = ""
    
    # Data settings
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    color_column: Optional[str] = None
    size_column: Optional[str] = None
    
    # Display options
    show_legend: bool = True
    show_grid: bool = True
    interactive: bool = True
    
    # Statistical overlays
    show_trend: bool = False
    show_confidence_bands: bool = False
    show_moving_average: bool = False
    moving_average_periods: int = 20


@dataclass
class ReportConfig:
    """Report generation configuration"""
    # Output settings
    output_format: ReportFormat = ReportFormat.HTML
    output_directory: str = "reports"
    include_timestamp: bool = True
    
    # Content settings
    sections: List[ReportSection] = field(default_factory=lambda: [
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.PERFORMANCE_OVERVIEW,
        ReportSection.RISK_ANALYSIS,
        ReportSection.CHARTS
    ])
    
    # Formatting
    decimal_places: int = 4
    percentage_format: str = "0.2%"
    currency_format: str = "$0.2f"
    date_format: str = "%Y-%m-%d"
    
    # Charts
    include_charts: bool = True
    chart_configs: List[ChartConfig] = field(default_factory=list)
    max_charts_per_section: int = 10
    
    # Styling
    theme: str = "professional"
    logo_path: Optional[str] = None
    company_name: str = "Analytics Engine"
    
    # Data filtering
    date_range: Optional[Tuple[datetime, datetime]] = None
    symbols_filter: Optional[List[str]] = None
    
    # Performance
    max_data_points: int = 10000
    chart_quality: str = "high"  # low, medium, high


@dataclass
class ReportData:
    """Container for report data"""
    # Core data
    returns_data: Dict[str, pd.Series] = field(default_factory=dict)
    price_data: Dict[str, pd.Series] = field(default_factory=dict)
    benchmark_data: Dict[str, pd.Series] = field(default_factory=dict)
    
    # Metrics
    performance_metrics: Dict[str, Dict] = field(default_factory=dict)
    risk_metrics: Dict[str, Dict] = field(default_factory=dict)
    attribution_data: Dict[str, Dict] = field(default_factory=dict)
    
    # Portfolio data
    holdings_data: Dict[str, pd.DataFrame] = field(default_factory=dict)
    trades_data: Dict[str, pd.DataFrame] = field(default_factory=dict)
    
    # Metadata
    report_period: Tuple[datetime, datetime] = field(
        default_factory=lambda: (datetime.now() - timedelta(days=365), datetime.now())
    )
    symbols: List[str] = field(default_factory=list)
    benchmark_symbol: str = "SPY"
    
    # Custom data
    custom_data: Dict[str, Any] = field(default_factory=dict)


class ChartGenerator:
    """Chart generation engine"""
    
    def __init__(self):
        self.matplotlib_style = 'seaborn-v0_8' if PLOTTING_AVAILABLE else None
        self.plotly_template = 'plotly_white'
    
    def generate_chart(
        self,
        config: ChartConfig,
        data: Union[pd.DataFrame, pd.Series, Dict],
        output_format: str = 'html'
    ) -> Optional[str]:
        """Generate chart based on configuration"""
        
        if not PLOTTING_AVAILABLE and not PLOTLY_AVAILABLE:
            logger.warning("No plotting libraries available")
            return None
        
        try:
            if config.interactive and PLOTLY_AVAILABLE:
                return self._generate_plotly_chart(config, data, output_format)
            elif PLOTTING_AVAILABLE:
                return self._generate_matplotlib_chart(config, data, output_format)
            else:
                logger.warning("No suitable plotting library available")
                return None
                
        except Exception as e:
            logger.error(f"Error generating chart '{config.title}': {e}")
            return None
    
    def _generate_plotly_chart(
        self,
        config: ChartConfig,
        data: Union[pd.DataFrame, pd.Series, Dict],
        output_format: str
    ) -> str:
        """Generate Plotly chart"""
        
        fig = None
        
        if isinstance(data, pd.Series):
            data = data.to_frame('value')
        elif isinstance(data, dict):
            data = pd.DataFrame(data)
        
        if config.chart_type == ChartType.LINE:
            if config.x_column and config.y_column:
                fig = px.line(
                    data, 
                    x=config.x_column, 
                    y=config.y_column,
                    title=config.title,
                    template=self.plotly_template
                )
            else:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data.iloc[:, 0] if len(data.columns) > 0 else [],
                    mode='lines',
                    name=config.title
                ))
        
        elif config.chart_type == ChartType.BAR:
            if config.x_column and config.y_column:
                fig = px.bar(
                    data,
                    x=config.x_column,
                    y=config.y_column,
                    title=config.title,
                    template=self.plotly_template
                )
            else:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=data.index,
                    y=data.iloc[:, 0] if len(data.columns) > 0 else [],
                    name=config.title
                ))
        
        elif config.chart_type == ChartType.HISTOGRAM:
            y_col = config.y_column or data.columns[0]
            fig = px.histogram(
                data,
                x=y_col,
                title=config.title,
                template=self.plotly_template
            )
        
        elif config.chart_type == ChartType.HEATMAP:
            if isinstance(data, pd.DataFrame) and len(data.columns) > 1:
                corr_matrix = data.corr()
                fig = px.imshow(
                    corr_matrix,
                    title=config.title,
                    template=self.plotly_template,
                    color_continuous_scale=config.color_scheme
                )
        
        elif config.chart_type == ChartType.SCATTER:
            if config.x_column and config.y_column:
                fig = px.scatter(
                    data,
                    x=config.x_column,
                    y=config.y_column,
                    title=config.title,
                    template=self.plotly_template
                )
        
        if fig is None:
            return ""
        
        # Apply common formatting
        fig.update_layout(
            width=config.width,
            height=config.height,
            showlegend=config.show_legend,
            title_x=0.5
        )
        
        if config.show_grid:
            fig.update_xaxes(showgrid=True)
            fig.update_yaxes(showgrid=True)
        
        if config.x_label:
            fig.update_xaxes(title_text=config.x_label)
        if config.y_label:
            fig.update_yaxes(title_text=config.y_label)
        
        # Return HTML or base64 encoded image
        if output_format == 'html':
            return fig.to_html(include_plotlyjs='cdn', div_id=f"chart_{hash(config.title)}")
        else:
            # Convert to image for PDF
            img_bytes = fig.to_image(format="png", width=config.width, height=config.height)
            return base64.b64encode(img_bytes).decode()
    
    def _generate_matplotlib_chart(
        self,
        config: ChartConfig,
        data: Union[pd.DataFrame, pd.Series, Dict],
        output_format: str
    ) -> str:
        """Generate Matplotlib chart"""
        
        if self.matplotlib_style:
            plt.style.use(self.matplotlib_style)
        
        fig, ax = plt.subplots(figsize=(config.width/100, config.height/100))
        
        if isinstance(data, pd.Series):
            data = data.to_frame('value')
        elif isinstance(data, dict):
            data = pd.DataFrame(data)
        
        try:
            if config.chart_type == ChartType.LINE:
                if config.x_column and config.y_column:
                    ax.plot(data[config.x_column], data[config.y_column])
                else:
                    data.iloc[:, 0].plot(ax=ax)
            
            elif config.chart_type == ChartType.BAR:
                if config.x_column and config.y_column:
                    ax.bar(data[config.x_column], data[config.y_column])
                else:
                    data.iloc[:, 0].plot(kind='bar', ax=ax)
            
            elif config.chart_type == ChartType.HISTOGRAM:
                y_col = config.y_column or data.columns[0]
                ax.hist(data[y_col].dropna(), bins=30, alpha=0.7)
            
            elif config.chart_type == ChartType.HEATMAP:
                if isinstance(data, pd.DataFrame) and len(data.columns) > 1:
                    corr_matrix = data.corr()
                    im = ax.imshow(corr_matrix, cmap=config.color_scheme, aspect='auto')
                    plt.colorbar(im, ax=ax)
                    ax.set_xticks(range(len(corr_matrix.columns)))
                    ax.set_yticks(range(len(corr_matrix.index)))
                    ax.set_xticklabels(corr_matrix.columns, rotation=45)
                    ax.set_yticklabels(corr_matrix.index)
            
            elif config.chart_type == ChartType.SCATTER:
                if config.x_column and config.y_column:
                    ax.scatter(data[config.x_column], data[config.y_column])
            
            # Apply formatting
            ax.set_title(config.title)
            if config.x_label:
                ax.set_xlabel(config.x_label)
            if config.y_label:
                ax.set_ylabel(config.y_label)
            
            ax.grid(config.show_grid)
            
            if not config.show_legend:
                ax.legend().set_visible(False)
            
            plt.tight_layout()
            
            # Return base64 encoded image
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
            buffer.seek(0)
            img_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
            
            return img_data
            
        except Exception as e:
            plt.close(fig)
            logger.error(f"Error creating matplotlib chart: {e}")
            return ""


class HTMLReportBuilder:
    """HTML report builder"""
    
    def __init__(self, config: ReportConfig):
        self.config = config
        self.chart_generator = ChartGenerator()
    
    def build_report(self, data: ReportData) -> str:
        """Build HTML report"""
        
        html_parts = []
        
        # HTML header
        html_parts.append(self._build_html_header())
        
        # Report sections
        for section in self.config.sections:
            section_html = self._build_section(section, data)
            if section_html:
                html_parts.append(section_html)
        
        # HTML footer
        html_parts.append(self._build_html_footer())
        
        return '\n'.join(html_parts)
    
    def _build_html_header(self) -> str:
        """Build HTML header"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if self.config.include_timestamp else ""
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics Report - {self.config.company_name}</title>
    <style>
        {self._get_css_styles()}
    </style>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div class="report-container">
        <header class="report-header">
            <h1>Analytics Report</h1>
            <div class="company-info">
                <span class="company-name">{self.config.company_name}</span>
                {f'<span class="timestamp">{timestamp}</span>' if timestamp else ''}
            </div>
        </header>
"""
    
    def _build_html_footer(self) -> str:
        """Build HTML footer"""
        
        return """
        <footer class="report-footer">
            <p>Generated by Analytics Engine</p>
        </footer>
    </div>
</body>
</html>
"""
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for report"""
        
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .report-container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        .report-header {
            background-color: #2c3e50;
            color: white;
            padding: 2rem;
            text-align: center;
        }
        
        .report-header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .company-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
        }
        
        .section {
            padding: 2rem;
            border-bottom: 1px solid #eee;
        }
        
        .section h2 {
            color: #2c3e50;
            margin-bottom: 1rem;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5rem;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        
        .metric-card {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }
        
        .metric-title {
            font-weight: bold;
            color: #555;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .chart-container {
            margin: 2rem 0;
            text-align: center;
        }
        
        .table-container {
            overflow-x: auto;
            margin: 1rem 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        
        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #555;
        }
        
        tr:hover {
            background-color: #f8f9fa;
        }
        
        .positive {
            color: #27ae60;
        }
        
        .negative {
            color: #e74c3c;
        }
        
        .report-footer {
            background-color: #34495e;
            color: white;
            text-align: center;
            padding: 1rem;
        }
        
        .summary-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.9;
            margin-bottom: 0.5rem;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
        }
        """
    
    def _build_section(self, section: ReportSection, data: ReportData) -> str:
        """Build individual report section"""
        
        if section == ReportSection.EXECUTIVE_SUMMARY:
            return self._build_executive_summary(data)
        elif section == ReportSection.PERFORMANCE_OVERVIEW:
            return self._build_performance_overview(data)
        elif section == ReportSection.RISK_ANALYSIS:
            return self._build_risk_analysis(data)
        elif section == ReportSection.CHARTS:
            return self._build_charts_section(data)
        elif section == ReportSection.DETAILED_METRICS:
            return self._build_detailed_metrics(data)
        else:
            return ""
    
    def _build_executive_summary(self, data: ReportData) -> str:
        """Build executive summary section"""
        
        html = ['<div class="section">', '<h2>Executive Summary</h2>']
        
        # Key performance stats
        if data.performance_metrics:
            html.append('<div class="summary-stats">')
            
            for symbol, metrics in data.performance_metrics.items():
                if 'annualized_return' in metrics:
                    return_val = metrics['annualized_return'].get('value', 0) * 100
                    html.append(f'''
                    <div class="stat-box">
                        <div class="stat-label">Annual Return ({symbol})</div>
                        <div class="stat-value">{return_val:.2f}%</div>
                    </div>
                    ''')
                
                if 'sharpe_ratio' in metrics:
                    sharpe_val = metrics['sharpe_ratio'].get('value', 0)
                    html.append(f'''
                    <div class="stat-box">
                        <div class="stat-label">Sharpe Ratio ({symbol})</div>
                        <div class="stat-value">{sharpe_val:.2f}</div>
                    </div>
                    ''')
            
            html.append('</div>')
        
        # Period summary
        start_date = data.report_period[0].strftime(self.config.date_format)
        end_date = data.report_period[1].strftime(self.config.date_format)
        
        html.append(f'''
        <p>This report covers the period from <strong>{start_date}</strong> to <strong>{end_date}</strong>.</p>
        <p>Analysis includes {len(data.symbols)} symbols with benchmark comparison against {data.benchmark_symbol}.</p>
        ''')
        
        html.append('</div>')
        return '\n'.join(html)
    
    def _build_performance_overview(self, data: ReportData) -> str:
        """Build performance overview section"""
        
        html = ['<div class="section">', '<h2>Performance Overview</h2>']
        
        if data.performance_metrics:
            html.append('<div class="metrics-grid">')
            
            for symbol, metrics in data.performance_metrics.items():
                for metric_name, metric_info in metrics.items():
                    value = metric_info.get('value', 0)
                    
                    # Format value based on metric type
                    if 'return' in metric_name.lower() or 'alpha' in metric_name.lower():
                        formatted_value = f"{value * 100:.2f}%"
                    elif 'ratio' in metric_name.lower():
                        formatted_value = f"{value:.2f}"
                    elif 'volatility' in metric_name.lower():
                        formatted_value = f"{value * 100:.2f}%"
                    else:
                        formatted_value = f"{value:.4f}"
                    
                    # Determine color class
                    color_class = ""
                    if 'return' in metric_name.lower() and value > 0:
                        color_class = "positive"
                    elif 'return' in metric_name.lower() and value < 0:
                        color_class = "negative"
                    
                    html.append(f'''
                    <div class="metric-card">
                        <div class="metric-title">{metric_name.replace('_', ' ').title()} ({symbol})</div>
                        <div class="metric-value {color_class}">{formatted_value}</div>
                    </div>
                    ''')
            
            html.append('</div>')
        
        html.append('</div>')
        return '\n'.join(html)
    
    def _build_risk_analysis(self, data: ReportData) -> str:
        """Build risk analysis section"""
        
        html = ['<div class="section">', '<h2>Risk Analysis</h2>']
        
        if data.risk_metrics:
            html.append('<div class="table-container">')
            html.append('<table>')
            html.append('<thead><tr><th>Symbol</th><th>Metric</th><th>Value</th></tr></thead>')
            html.append('<tbody>')
            
            for symbol, metrics in data.risk_metrics.items():
                for metric_name, metric_info in metrics.items():
                    value = metric_info.get('value', 0)
                    
                    if 'var' in metric_name.lower() or 'drawdown' in metric_name.lower():
                        formatted_value = f"{value * 100:.2f}%"
                        color_class = "negative"
                    elif 'volatility' in metric_name.lower():
                        formatted_value = f"{value * 100:.2f}%"
                        color_class = ""
                    else:
                        formatted_value = f"{value:.4f}"
                        color_class = ""
                    
                    html.append(f'''
                    <tr>
                        <td>{symbol}</td>
                        <td>{metric_name.replace('_', ' ').title()}</td>
                        <td class="{color_class}">{formatted_value}</td>
                    </tr>
                    ''')
            
            html.append('</tbody></table></div>')
        
        html.append('</div>')
        return '\n'.join(html)
    
    def _build_charts_section(self, data: ReportData) -> str:
        """Build charts section"""
        
        html = ['<div class="section">', '<h2>Charts</h2>']
        
        # Generate charts based on available data
        chart_count = 0
        
        # Performance chart
        if data.returns_data and chart_count < self.config.max_charts_per_section:
            performance_data = {}
            for symbol, returns in data.returns_data.items():
                cumulative = (1 + returns).cumprod()
                performance_data[symbol] = cumulative
            
            if performance_data:
                chart_config = ChartConfig(
                    chart_type=ChartType.LINE,
                    title="Cumulative Performance",
                    data_source="performance",
                    width=800,
                    height=400,
                    y_label="Cumulative Return"
                )
                
                chart_html = self.chart_generator.generate_chart(
                    chart_config, 
                    pd.DataFrame(performance_data),
                    'html'
                )
                
                if chart_html:
                    html.append(f'<div class="chart-container">{chart_html}</div>')
                    chart_count += 1
        
        # Returns distribution
        if data.returns_data and chart_count < self.config.max_charts_per_section:
            for symbol, returns in data.returns_data.items():
                if chart_count >= self.config.max_charts_per_section:
                    break
                    
                chart_config = ChartConfig(
                    chart_type=ChartType.HISTOGRAM,
                    title=f"Returns Distribution - {symbol}",
                    data_source="returns",
                    width=600,
                    height=400,
                    y_column="returns"
                )
                
                chart_data = pd.DataFrame({'returns': returns})
                chart_html = self.chart_generator.generate_chart(chart_config, chart_data, 'html')
                
                if chart_html:
                    html.append(f'<div class="chart-container">{chart_html}</div>')
                    chart_count += 1
        
        html.append('</div>')
        return '\n'.join(html)
    
    def _build_detailed_metrics(self, data: ReportData) -> str:
        """Build detailed metrics section"""
        
        html = ['<div class="section">', '<h2>Detailed Metrics</h2>']
        
        # Combine all metrics
        all_metrics = {}
        all_metrics.update(data.performance_metrics)
        all_metrics.update(data.risk_metrics)
        
        if all_metrics:
            html.append('<div class="table-container">')
            html.append('<table>')
            html.append('<thead><tr><th>Symbol</th><th>Category</th><th>Metric</th><th>Value</th></tr></thead>')
            html.append('<tbody>')
            
            for symbol, metrics in all_metrics.items():
                for metric_name, metric_info in metrics.items():
                    category = metric_info.get('category', 'Unknown')
                    value = metric_info.get('value', 0)
                    
                    # Format value
                    if isinstance(value, float):
                        if abs(value) < 0.01:
                            formatted_value = f"{value:.6f}"
                        elif abs(value) < 1:
                            formatted_value = f"{value:.4f}"
                        else:
                            formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = str(value)
                    
                    html.append(f'''
                    <tr>
                        <td>{symbol}</td>
                        <td>{category}</td>
                        <td>{metric_name.replace('_', ' ').title()}</td>
                        <td>{formatted_value}</td>
                    </tr>
                    ''')
            
            html.append('</tbody></table></div>')
        
        html.append('</div>')
        return '\n'.join(html)


class ReportGenerator:
    """
    Advanced Report Generator
    
    Generates comprehensive analytics reports with customizable layouts,
    interactive charts, and multiple export formats.
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        """Initialize report generator"""
        self.config = config or ReportConfig()
        
        # Ensure output directory exists
        Path(self.config.output_directory).mkdir(parents=True, exist_ok=True)
        
        # Report builders
        self.html_builder = HTMLReportBuilder(self.config)
        self.chart_generator = ChartGenerator()
        
        # Generated reports cache
        self._reports_cache = {}
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info("Report Generator initialized")
    
    async def generate_report(
        self,
        data: ReportData,
        report_name: str = "analytics_report",
        custom_config: Optional[ReportConfig] = None
    ) -> str:
        """Generate report with specified data"""
        
        config = custom_config or self.config
        
        try:
            # Validate data
            if not self._validate_report_data(data):
                raise ValueError("Invalid report data provided")
            
            # Apply data filters
            filtered_data = self._apply_data_filters(data, config)
            
            # Generate report based on format
            if config.output_format == ReportFormat.HTML:
                report_content = self.html_builder.build_report(filtered_data)
                file_extension = ".html"
            elif config.output_format == ReportFormat.JSON:
                report_content = self._build_json_report(filtered_data)
                file_extension = ".json"
            elif config.output_format == ReportFormat.MARKDOWN:
                report_content = self._build_markdown_report(filtered_data)
                file_extension = ".md"
            else:
                raise ValueError(f"Unsupported report format: {config.output_format}")
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") if config.include_timestamp else ""
            filename = f"{report_name}_{timestamp}{file_extension}" if timestamp else f"{report_name}{file_extension}"
            
            # Save report
            output_path = Path(config.output_directory) / filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # Cache report
            with self._lock:
                self._reports_cache[report_name] = {
                    'path': str(output_path),
                    'timestamp': datetime.now(),
                    'format': config.output_format,
                    'size': len(report_content)
                }
            
            logger.info(f"Report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating report '{report_name}': {e}")
            raise
    
    def _validate_report_data(self, data: ReportData) -> bool:
        """Validate report data"""
        
        # Check for minimum required data
        if not data.symbols:
            logger.warning("No symbols provided in report data")
            return False
        
        if not data.returns_data and not data.performance_metrics:
            logger.warning("No returns data or performance metrics provided")
            return False
        
        return True
    
    def _apply_data_filters(self, data: ReportData, config: ReportConfig) -> ReportData:
        """Apply data filters based on configuration"""
        
        filtered_data = ReportData()
        
        # Date range filter
        if config.date_range:
            start_date, end_date = config.date_range
            
            # Filter returns data
            for symbol, returns in data.returns_data.items():
                mask = (returns.index >= start_date) & (returns.index <= end_date)
                filtered_data.returns_data[symbol] = returns[mask]
            
            # Filter price data
            for symbol, prices in data.price_data.items():
                mask = (prices.index >= start_date) & (prices.index <= end_date)
                filtered_data.price_data[symbol] = prices[mask]
        else:
            filtered_data.returns_data = data.returns_data.copy()
            filtered_data.price_data = data.price_data.copy()
        
        # Symbol filter
        if config.symbols_filter:
            symbols_to_keep = set(config.symbols_filter)
            
            filtered_data.returns_data = {
                k: v for k, v in filtered_data.returns_data.items() 
                if k in symbols_to_keep
            }
            filtered_data.price_data = {
                k: v for k, v in filtered_data.price_data.items() 
                if k in symbols_to_keep
            }
            filtered_data.symbols = [s for s in data.symbols if s in symbols_to_keep]
        else:
            filtered_data.symbols = data.symbols.copy()
        
        # Copy other data
        filtered_data.performance_metrics = data.performance_metrics.copy()
        filtered_data.risk_metrics = data.risk_metrics.copy()
        filtered_data.attribution_data = data.attribution_data.copy()
        filtered_data.holdings_data = data.holdings_data.copy()
        filtered_data.trades_data = data.trades_data.copy()
        filtered_data.benchmark_data = data.benchmark_data.copy()
        filtered_data.custom_data = data.custom_data.copy()
        filtered_data.report_period = data.report_period
        filtered_data.benchmark_symbol = data.benchmark_symbol
        
        return filtered_data
    
    def _build_json_report(self, data: ReportData) -> str:
        """Build JSON report"""
        
        report_dict = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_period': {
                    'start': data.report_period[0].isoformat(),
                    'end': data.report_period[1].isoformat()
                },
                'symbols': data.symbols,
                'benchmark': data.benchmark_symbol
            },
            'performance_metrics': self._serialize_metrics(data.performance_metrics),
            'risk_metrics': self._serialize_metrics(data.risk_metrics),
            'attribution_data': self._serialize_metrics(data.attribution_data)
        }
        
        # Add returns data as summary statistics
        if data.returns_data:
            returns_summary = {}
            for symbol, returns in data.returns_data.items():
                returns_summary[symbol] = {
                    'count': len(returns),
                    'mean': float(returns.mean()),
                    'std': float(returns.std()),
                    'min': float(returns.min()),
                    'max': float(returns.max()),
                    'total_return': float((1 + returns).prod() - 1)
                }
            report_dict['returns_summary'] = returns_summary
        
        return json.dumps(report_dict, indent=2, default=str)
    
    def _build_markdown_report(self, data: ReportData) -> str:
        """Build Markdown report"""
        
        md_lines = []
        
        # Header
        md_lines.append(f"# Analytics Report - {self.config.company_name}")
        md_lines.append("")
        
        if self.config.include_timestamp:
            md_lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
            md_lines.append("")
        
        # Executive Summary
        md_lines.append("## Executive Summary")
        md_lines.append("")
        
        start_date = data.report_period[0].strftime(self.config.date_format)
        end_date = data.report_period[1].strftime(self.config.date_format)
        
        md_lines.append(f"**Report Period:** {start_date} to {end_date}")
        md_lines.append(f"**Symbols Analyzed:** {', '.join(data.symbols)}")
        md_lines.append(f"**Benchmark:** {data.benchmark_symbol}")
        md_lines.append("")
        
        # Performance Metrics
        if data.performance_metrics:
            md_lines.append("## Performance Metrics")
            md_lines.append("")
            md_lines.append("| Symbol | Metric | Value |")
            md_lines.append("|--------|--------|-------|")
            
            for symbol, metrics in data.performance_metrics.items():
                for metric_name, metric_info in metrics.items():
                    value = metric_info.get('value', 0)
                    if isinstance(value, float):
                        formatted_value = f"{value:.4f}"
                    else:
                        formatted_value = str(value)
                    
                    md_lines.append(f"| {symbol} | {metric_name.replace('_', ' ').title()} | {formatted_value} |")
            
            md_lines.append("")
        
        # Risk Metrics
        if data.risk_metrics:
            md_lines.append("## Risk Metrics")
            md_lines.append("")
            md_lines.append("| Symbol | Metric | Value |")
            md_lines.append("|--------|--------|-------|")
            
            for symbol, metrics in data.risk_metrics.items():
                for metric_name, metric_info in metrics.items():
                    value = metric_info.get('value', 0)
                    if isinstance(value, float):
                        formatted_value = f"{value:.4f}"
                    else:
                        formatted_value = str(value)
                    
                    md_lines.append(f"| {symbol} | {metric_name.replace('_', ' ').title()} | {formatted_value} |")
            
            md_lines.append("")
        
        return '\n'.join(md_lines)
    
    def _serialize_metrics(self, metrics_dict: Dict) -> Dict:
        """Serialize metrics for JSON output"""
        
        serialized = {}
        
        for key, value in metrics_dict.items():
            if isinstance(value, dict):
                serialized[key] = self._serialize_metrics(value)
            elif hasattr(value, '__dict__'):  # Custom objects
                serialized[key] = value.__dict__
            elif isinstance(value, (np.ndarray, pd.Series)):
                serialized[key] = value.tolist()
            elif isinstance(value, pd.DataFrame):
                serialized[key] = value.to_dict()
            else:
                serialized[key] = value
        
        return serialized
    
    def get_report_list(self) -> List[Dict[str, Any]]:
        """Get list of generated reports"""
        
        with self._lock:
            return [
                {
                    'name': name,
                    'path': info['path'],
                    'timestamp': info['timestamp'],
                    'format': info['format'],
                    'size': info['size']
                }
                for name, info in self._reports_cache.items()
            ]
    
    def get_chart_capabilities(self) -> Dict[str, Any]:
        """Get chart generation capabilities"""
        
        return {
            'plotting_available': PLOTTING_AVAILABLE,
            'plotly_available': PLOTLY_AVAILABLE,
            'supported_chart_types': [chart_type.value for chart_type in ChartType],
            'supported_formats': [fmt.value for fmt in ReportFormat]
        }
    
    def clear_reports_cache(self) -> None:
        """Clear reports cache"""
        
        with self._lock:
            self._reports_cache.clear()
            logger.info("Reports cache cleared")
    
    def get_generator_statistics(self) -> Dict[str, Any]:
        """Get generator statistics"""
        
        with self._lock:
            total_reports = len(self._reports_cache)
            total_size = sum(info['size'] for info in self._reports_cache.values())
        
        return {
            'total_reports_generated': total_reports,
            'total_size_bytes': total_size,
            'output_directory': self.config.output_directory,
            'capabilities': self.get_chart_capabilities()
        }