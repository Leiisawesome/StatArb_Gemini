"""
Data Visualization and Charting System

Professional-grade visualization system providing:
- Interactive charts and plots
- Real-time data visualization
- Custom chart themes
- Performance visualization
- Risk visualization
- Portfolio analytics charts

Author: Pro Quant Desk Trader
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging


class ChartType(Enum):
    """Chart types"""
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    CANDLESTICK = "candlestick"


@dataclass
class PlotConfig:
    """Plot configuration"""
    title: str
    x_label: str = ""
    y_label: str = ""
    width: int = 800
    height: int = 600
    theme: str = "default"


@dataclass
class ChartTheme:
    """Chart theme definition"""
    theme_id: str
    name: str
    colors: List[str] = field(default_factory=list)
    background_color: str = "#FFFFFF"
    grid_color: str = "#E0E0E0"


@dataclass
class Chart:
    """Chart definition"""
    chart_id: str
    chart_type: ChartType
    data: pd.DataFrame
    config: PlotConfig
    created_at: datetime = field(default_factory=datetime.now)


class ChartGenerator:
    """Chart generation system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.themes = {}
        
    def create_performance_chart(self, 
                               returns: pd.Series,
                               benchmark_returns: pd.Series = None) -> Chart:
        """Create performance chart"""
        
        # Calculate cumulative returns
        cum_returns = (1 + returns).cumprod()
        
        data = pd.DataFrame({'Portfolio': cum_returns})
        if benchmark_returns is not None:
            data['Benchmark'] = (1 + benchmark_returns).cumprod()
        
        config = PlotConfig(
            title="Portfolio Performance",
            x_label="Date",
            y_label="Cumulative Return"
        )
        
        return Chart(
            chart_id=f"perf_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            chart_type=ChartType.LINE,
            data=data,
            config=config
        )


class InteractiveCharts:
    """Interactive charting system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def create_dashboard_chart(self, chart_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create interactive dashboard chart"""
        return {
            'chart_id': chart_config.get('id', 'chart_1'),
            'type': chart_config.get('type', 'line'),
            'data': chart_config.get('data', {}),
            'layout': chart_config.get('layout', {})
        }


class VisualizationEngine:
    """Main visualization engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chart_generator = ChartGenerator()
        self.interactive_charts = InteractiveCharts()
        
    def generate_analytics_dashboard(self, 
                                   portfolio_data: pd.DataFrame) -> Dict[str, Any]:
        """Generate analytics dashboard"""
        
        dashboard = {
            'title': 'Portfolio Analytics Dashboard',
            'charts': [],
            'created_at': datetime.now().isoformat()
        }
        
        # Add performance chart if returns data exists
        if 'returns' in portfolio_data.columns:
            perf_chart = self.chart_generator.create_performance_chart(
                portfolio_data['returns']
            )
            dashboard['charts'].append({
                'id': perf_chart.chart_id,
                'type': perf_chart.chart_type.value,
                'title': perf_chart.config.title,
                'data': perf_chart.data.to_dict()
            })
        
        return dashboard 