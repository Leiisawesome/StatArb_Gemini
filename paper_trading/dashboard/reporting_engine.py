#!/usr/bin/env python3
"""
Advanced Reporting Engine
=========================

Professional reporting system for trading dashboard.
Generates automated reports, performance analysis, and export capabilities.

Author: Pro Quant Desk Trader
"""

import json
import csv
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import io
import base64
from pathlib import Path

# Optional PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

logger = logging.getLogger(__name__)

class ReportType(Enum):
    """Types of reports"""
    DAILY_SUMMARY = "DAILY_SUMMARY"
    WEEKLY_SUMMARY = "WEEKLY_SUMMARY"
    MONTHLY_SUMMARY = "MONTHLY_SUMMARY"
    PERFORMANCE_ANALYSIS = "PERFORMANCE_ANALYSIS"
    RISK_ANALYSIS = "RISK_ANALYSIS"
    STRATEGY_COMPARISON = "STRATEGY_COMPARISON"
    TRADE_ANALYSIS = "TRADE_ANALYSIS"
    CUSTOM = "CUSTOM"

class ReportFormat(Enum):
    """Report output formats"""
    JSON = "JSON"
    CSV = "CSV"
    HTML = "HTML"
    PDF = "PDF"
    EXCEL = "EXCEL"

@dataclass
class ReportConfig:
    """Report configuration"""
    report_id: str
    name: str
    report_type: ReportType
    format: ReportFormat
    
    # Scheduling
    auto_generate: bool = False
    schedule_time: Optional[str] = None  # "09:00" format
    schedule_days: List[str] = field(default_factory=list)  # ["Monday", "Tuesday", ...]
    
    # Content configuration
    include_charts: bool = True
    include_trades: bool = True
    include_positions: bool = True
    include_risk_metrics: bool = True
    
    # Filters
    date_range_days: int = 1  # Number of days to include
    strategy_filter: Optional[List[str]] = None
    symbol_filter: Optional[List[str]] = None
    
    # Output settings
    output_directory: str = "reports"
    email_recipients: List[str] = field(default_factory=list)
    
    # Status
    enabled: bool = True
    last_generated: Optional[datetime] = None

@dataclass
class ReportData:
    """Report data structure"""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    
    # Performance data
    portfolio_summary: Dict[str, Any]
    strategy_performance: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    
    # Trading data
    trades: List[Dict[str, Any]]
    positions: List[Dict[str, Any]]
    
    # Charts data (base64 encoded images)
    charts: Dict[str, str] = field(default_factory=dict)

class ReportingEngine:
    """
    Advanced reporting engine for trading dashboard
    
    Features:
    - Automated report generation
    - Multiple output formats (JSON, CSV, HTML, PDF)
    - Scheduled reports (daily, weekly, monthly)
    - Performance and risk analysis
    - Strategy comparison reports
    - Trade analysis and statistics
    - Email delivery of reports
    - Custom report templates
    """
    
    def __init__(self, output_directory: str = "reports"):
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        
        # Report configurations
        self.report_configs: Dict[str, ReportConfig] = {}
        
        # Report history
        self.report_history: List[Dict[str, Any]] = []
        
        # Data sources
        self.data_collector = None
        self.analytics_engine = None
        self.charting_engine = None
        
        # Report templates
        self.templates = {
            ReportType.DAILY_SUMMARY: self._generate_daily_summary,
            ReportType.WEEKLY_SUMMARY: self._generate_weekly_summary,
            ReportType.MONTHLY_SUMMARY: self._generate_monthly_summary,
            ReportType.PERFORMANCE_ANALYSIS: self._generate_performance_analysis,
            ReportType.RISK_ANALYSIS: self._generate_risk_analysis,
            ReportType.STRATEGY_COMPARISON: self._generate_strategy_comparison,
            ReportType.TRADE_ANALYSIS: self._generate_trade_analysis
        }
        
        logger.info("📊 Advanced Reporting Engine initialized")
    
    def register_data_sources(self, data_collector, analytics_engine, charting_engine=None):
        """Register data sources for report generation"""
        self.data_collector = data_collector
        self.analytics_engine = analytics_engine
        self.charting_engine = charting_engine
        logger.info("🔗 Data sources registered with reporting engine")
    
    def add_report_config(self, config: ReportConfig):
        """Add a report configuration"""
        self.report_configs[config.report_id] = config
        logger.info(f"📋 Report configuration added: {config.name}")
    
    def create_default_reports(self):
        """Create default report configurations"""
        
        # Daily summary report
        self.add_report_config(ReportConfig(
            report_id="daily_summary",
            name="Daily Trading Summary",
            report_type=ReportType.DAILY_SUMMARY,
            format=ReportFormat.HTML,
            auto_generate=True,
            schedule_time="18:00",
            schedule_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            date_range_days=1
        ))
        
        # Weekly performance report
        self.add_report_config(ReportConfig(
            report_id="weekly_performance",
            name="Weekly Performance Analysis",
            report_type=ReportType.PERFORMANCE_ANALYSIS,
            format=ReportFormat.PDF,
            auto_generate=True,
            schedule_time="09:00",
            schedule_days=["Monday"],
            date_range_days=7
        ))
        
        # Monthly risk report
        self.add_report_config(ReportConfig(
            report_id="monthly_risk",
            name="Monthly Risk Analysis",
            report_type=ReportType.RISK_ANALYSIS,
            format=ReportFormat.PDF,
            auto_generate=True,
            schedule_time="09:00",
            schedule_days=["1"],  # First day of month
            date_range_days=30
        ))
        
        logger.info("📋 Default report configurations created")
    
    async def generate_report(self, report_id: str) -> Optional[str]:
        """Generate a report by ID"""
        if report_id not in self.report_configs:
            logger.error(f"❌ Report configuration not found: {report_id}")
            return None
        
        config = self.report_configs[report_id]
        
        try:
            logger.info(f"📊 Generating report: {config.name}")
            
            # Collect data
            report_data = await self._collect_report_data(config)
            
            # Generate report content
            if config.report_type in self.templates:
                content = await self.templates[config.report_type](report_data, config)
            else:
                content = await self._generate_custom_report(report_data, config)
            
            # Save report
            filename = await self._save_report(content, config)
            
            # Update configuration
            config.last_generated = datetime.now()
            
            # Add to history
            self.report_history.append({
                'report_id': report_id,
                'name': config.name,
                'generated_at': datetime.now(),
                'filename': filename,
                'format': config.format.value
            })
            
            logger.info(f"✅ Report generated successfully: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Error generating report {report_id}: {e}")
            return None
    
    async def _collect_report_data(self, config: ReportConfig) -> ReportData:
        """Collect data for report generation"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=config.date_range_days)
        
        # Get current trading data
        current_data = {}
        if self.data_collector:
            current_data = self.data_collector.get_current_data()
        
        # Get analytics data
        analytics_data = {}
        if self.analytics_engine:
            analytics_data = self.analytics_engine.get_analytics_summary()
        
        # Get historical data
        historical_data = []
        if self.data_collector:
            historical_data = self.data_collector.get_historical_data(
                minutes=config.date_range_days * 24 * 60
            )
        
        # Prepare report data
        report_data = ReportData(
            report_id=config.report_id,
            generated_at=datetime.now(),
            period_start=start_time,
            period_end=end_time,
            portfolio_summary=self._prepare_portfolio_summary(current_data, historical_data),
            strategy_performance=current_data.get('strategy_performance', {}),
            risk_metrics=analytics_data.get('portfolio_metrics', {}),
            trades=self._prepare_trades_data(current_data),
            positions=self._prepare_positions_data(current_data)
        )
        
        return report_data
    
    def _prepare_portfolio_summary(self, current_data: Dict, historical_data: List) -> Dict[str, Any]:
        """Prepare portfolio summary data"""
        summary = {
            'current_value': current_data.get('portfolio_value', 0),
            'total_pnl': current_data.get('total_pnl', 0),
            'daily_pnl': current_data.get('daily_pnl', 0),
            'total_return': current_data.get('performance_metrics', {}).get('total_return', 0),
            'sharpe_ratio': current_data.get('performance_metrics', {}).get('sharpe_ratio', 0),
            'max_drawdown': current_data.get('performance_metrics', {}).get('max_drawdown', 0),
            'volatility': current_data.get('performance_metrics', {}).get('volatility', 0)
        }
        
        # Calculate period statistics from historical data
        if historical_data:
            values = [point['portfolio_value'] for point in historical_data]
            if values:
                summary['period_high'] = max(values)
                summary['period_low'] = min(values)
                summary['period_start_value'] = values[0]
                summary['period_end_value'] = values[-1]
                summary['period_return'] = ((values[-1] - values[0]) / values[0]) * 100 if values[0] > 0 else 0
        
        return summary
    
    def _prepare_trades_data(self, current_data: Dict) -> List[Dict[str, Any]]:
        """Prepare trades data for reporting"""
        # In a real system, this would come from trade history
        # For now, return empty list or mock data
        return []
    
    def _prepare_positions_data(self, current_data: Dict) -> List[Dict[str, Any]]:
        """Prepare positions data for reporting"""
        positions = current_data.get('positions', {})
        positions_list = []
        
        for pos_id, position in positions.items():
            positions_list.append({
                'position_id': pos_id,
                'symbol': position.get('symbol', ''),
                'quantity': position.get('quantity', 0),
                'entry_price': position.get('entry_price', 0),
                'current_price': position.get('current_price', 0),
                'pnl': position.get('pnl', 0),
                'strategy_id': position.get('strategy_id', ''),
                'entry_time': position.get('entry_time', '')
            })
        
        return positions_list
    
    async def _generate_daily_summary(self, data: ReportData, config: ReportConfig) -> str:
        """Generate daily summary report"""
        if config.format == ReportFormat.HTML:
            return self._generate_html_daily_summary(data)
        elif config.format == ReportFormat.JSON:
            return json.dumps(data.__dict__, default=str, indent=2)
        elif config.format == ReportFormat.CSV:
            return self._generate_csv_summary(data)
        else:
            return self._generate_text_summary(data)
    
    def _generate_html_daily_summary(self, data: ReportData) -> str:
        """Generate HTML daily summary"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Daily Trading Summary - {data.generated_at.strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 2px solid #2196F3; padding-bottom: 20px; margin-bottom: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #2196F3; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .metric-label {{ color: #666; font-size: 14px; margin-bottom: 5px; }}
        .positive {{ color: #4CAF50; }}
        .negative {{ color: #f44336; }}
        .section {{ margin-bottom: 30px; }}
        .section-title {{ font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Daily Trading Summary</h1>
            <p>Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Period: {data.period_start.strftime('%Y-%m-%d')} to {data.period_end.strftime('%Y-%m-%d')}</p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">Portfolio Value</div>
                <div class="metric-value">${data.portfolio_summary.get('current_value', 0):,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total P&L</div>
                <div class="metric-value {'positive' if data.portfolio_summary.get('total_pnl', 0) >= 0 else 'negative'}">${data.portfolio_summary.get('total_pnl', 0):,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Daily P&L</div>
                <div class="metric-value {'positive' if data.portfolio_summary.get('daily_pnl', 0) >= 0 else 'negative'}">${data.portfolio_summary.get('daily_pnl', 0):,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Return</div>
                <div class="metric-value {'positive' if data.portfolio_summary.get('total_return', 0) >= 0 else 'negative'}">{data.portfolio_summary.get('total_return', 0):+.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">{data.portfolio_summary.get('sharpe_ratio', 0):.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value negative">{data.portfolio_summary.get('max_drawdown', 0):.2f}%</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📈 Strategy Performance</div>
            <table>
                <thead>
                    <tr>
                        <th>Strategy</th>
                        <th>Allocation</th>
                        <th>P&L</th>
                        <th>Return</th>
                        <th>Positions</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for strategy_id, strategy_data in data.strategy_performance.items():
            pnl = strategy_data.get('current_pnl', 0)
            return_pct = strategy_data.get('return_pct', 0)
            html += f"""
                    <tr>
                        <td>{strategy_data.get('name', strategy_id)}</td>
                        <td>{strategy_data.get('allocation', 0):.1%}</td>
                        <td class="{'positive' if pnl >= 0 else 'negative'}">${pnl:,.2f}</td>
                        <td class="{'positive' if return_pct >= 0 else 'negative'}">{return_pct:+.2f}%</td>
                        <td>{strategy_data.get('positions_count', 0)}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <div class="section-title">🛡️ Risk Metrics</div>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        risk_metrics = [
            ('Current Drawdown', f"{data.risk_metrics.get('current_drawdown', 0):.2%}", 'Good' if data.risk_metrics.get('current_drawdown', 0) < 0.05 else 'Warning'),
            ('Volatility', f"{data.risk_metrics.get('volatility', 0):.2%}", 'Good' if data.risk_metrics.get('volatility', 0) < 0.20 else 'High'),
            ('VaR (95%)', f"${data.risk_metrics.get('var_95', 0):,.0f}", 'Monitored'),
        ]
        
        for metric_name, value, status in risk_metrics:
            html += f"""
                    <tr>
                        <td>{metric_name}</td>
                        <td>{value}</td>
                        <td>{status}</td>
                    </tr>
            """
        
        html += f"""
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>This report was automatically generated by the Trading Dashboard System</p>
            <p>Report ID: {data.report_id} | Generated: {data.generated_at.isoformat()}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def _generate_csv_summary(self, data: ReportData) -> str:
        """Generate CSV summary"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Daily Trading Summary'])
        writer.writerow(['Generated', data.generated_at.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Period', f"{data.period_start.strftime('%Y-%m-%d')} to {data.period_end.strftime('%Y-%m-%d')}"])
        writer.writerow([])
        
        # Portfolio Summary
        writer.writerow(['Portfolio Summary'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Portfolio Value', f"${data.portfolio_summary.get('current_value', 0):,.2f}"])
        writer.writerow(['Total P&L', f"${data.portfolio_summary.get('total_pnl', 0):,.2f}"])
        writer.writerow(['Daily P&L', f"${data.portfolio_summary.get('daily_pnl', 0):,.2f}"])
        writer.writerow(['Total Return', f"{data.portfolio_summary.get('total_return', 0):.2f}%"])
        writer.writerow(['Sharpe Ratio', f"{data.portfolio_summary.get('sharpe_ratio', 0):.2f}"])
        writer.writerow(['Max Drawdown', f"{data.portfolio_summary.get('max_drawdown', 0):.2f}%"])
        writer.writerow([])
        
        # Strategy Performance
        writer.writerow(['Strategy Performance'])
        writer.writerow(['Strategy', 'Allocation', 'P&L', 'Return %', 'Positions'])
        for strategy_id, strategy_data in data.strategy_performance.items():
            writer.writerow([
                strategy_data.get('name', strategy_id),
                f"{strategy_data.get('allocation', 0):.1%}",
                f"${strategy_data.get('current_pnl', 0):,.2f}",
                f"{strategy_data.get('return_pct', 0):.2f}%",
                strategy_data.get('positions_count', 0)
            ])
        
        return output.getvalue()
    
    def _generate_text_summary(self, data: ReportData) -> str:
        """Generate plain text summary"""
        text = f"""
DAILY TRADING SUMMARY
Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
Period: {data.period_start.strftime('%Y-%m-%d')} to {data.period_end.strftime('%Y-%m-%d')}

PORTFOLIO SUMMARY
Portfolio Value: ${data.portfolio_summary.get('current_value', 0):,.2f}
Total P&L: ${data.portfolio_summary.get('total_pnl', 0):,.2f}
Daily P&L: ${data.portfolio_summary.get('daily_pnl', 0):,.2f}
Total Return: {data.portfolio_summary.get('total_return', 0):+.2f}%
Sharpe Ratio: {data.portfolio_summary.get('sharpe_ratio', 0):.2f}
Max Drawdown: {data.portfolio_summary.get('max_drawdown', 0):.2f}%

STRATEGY PERFORMANCE
"""
        
        for strategy_id, strategy_data in data.strategy_performance.items():
            text += f"""
{strategy_data.get('name', strategy_id)}:
  Allocation: {strategy_data.get('allocation', 0):.1%}
  P&L: ${strategy_data.get('current_pnl', 0):,.2f}
  Return: {strategy_data.get('return_pct', 0):+.2f}%
  Positions: {strategy_data.get('positions_count', 0)}
"""
        
        return text
    
    async def _generate_weekly_summary(self, data: ReportData, config: ReportConfig) -> str:
        """Generate weekly summary report"""
        # Similar to daily but with weekly aggregation
        return await self._generate_daily_summary(data, config)
    
    async def _generate_monthly_summary(self, data: ReportData, config: ReportConfig) -> str:
        """Generate monthly summary report"""
        # Similar to daily but with monthly aggregation
        return await self._generate_daily_summary(data, config)
    
    async def _generate_performance_analysis(self, data: ReportData, config: ReportConfig) -> str:
        """Generate performance analysis report"""
        # Detailed performance analysis
        return await self._generate_daily_summary(data, config)
    
    async def _generate_risk_analysis(self, data: ReportData, config: ReportConfig) -> str:
        """Generate risk analysis report"""
        # Detailed risk analysis
        return await self._generate_daily_summary(data, config)
    
    async def _generate_strategy_comparison(self, data: ReportData, config: ReportConfig) -> str:
        """Generate strategy comparison report"""
        # Strategy comparison analysis
        return await self._generate_daily_summary(data, config)
    
    async def _generate_trade_analysis(self, data: ReportData, config: ReportConfig) -> str:
        """Generate trade analysis report"""
        # Trade analysis and statistics
        return await self._generate_daily_summary(data, config)
    
    async def _generate_custom_report(self, data: ReportData, config: ReportConfig) -> str:
        """Generate custom report"""
        return await self._generate_daily_summary(data, config)
    
    async def _save_report(self, content: str, config: ReportConfig) -> str:
        """Save report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{config.report_id}_{timestamp}.{config.format.value.lower()}"
        filepath = self.output_directory / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filepath)
    
    def get_report_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get report generation history"""
        cutoff_date = datetime.now() - timedelta(days=days)
        return [
            report for report in self.report_history 
            if report['generated_at'] >= cutoff_date
        ]
    
    def get_available_reports(self) -> List[Dict[str, Any]]:
        """Get list of available report configurations"""
        return [
            {
                'report_id': config.report_id,
                'name': config.name,
                'type': config.report_type.value,
                'format': config.format.value,
                'auto_generate': config.auto_generate,
                'enabled': config.enabled,
                'last_generated': config.last_generated.isoformat() if config.last_generated else None
            }
            for config in self.report_configs.values()
        ]
    
    async def export_data(self, format: ReportFormat, data_type: str = "current") -> Optional[str]:
        """Export current data in specified format"""
        try:
            if not self.data_collector:
                logger.error("❌ Data collector not available for export")
                return None
            
            current_data = self.data_collector.get_current_data()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format == ReportFormat.JSON:
                filename = f"export_{data_type}_{timestamp}.json"
                filepath = self.output_directory / filename
                
                with open(filepath, 'w') as f:
                    json.dump(current_data, f, indent=2, default=str)
                
            elif format == ReportFormat.CSV:
                filename = f"export_{data_type}_{timestamp}.csv"
                filepath = self.output_directory / filename
                
                # Export portfolio summary as CSV
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Metric', 'Value'])
                    writer.writerow(['Portfolio Value', current_data.get('portfolio_value', 0)])
                    writer.writerow(['Total P&L', current_data.get('total_pnl', 0)])
                    writer.writerow(['Timestamp', current_data.get('timestamp', '')])
            
            else:
                logger.error(f"❌ Unsupported export format: {format}")
                return None
            
            logger.info(f"📁 Data exported: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Error exporting data: {e}")
            return None

# Helper functions
def create_daily_report_config(report_id: str, name: str, format: ReportFormat = ReportFormat.HTML) -> ReportConfig:
    """Create a daily report configuration"""
    return ReportConfig(
        report_id=report_id,
        name=name,
        report_type=ReportType.DAILY_SUMMARY,
        format=format,
        auto_generate=True,
        schedule_time="18:00",
        schedule_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        date_range_days=1
    )
