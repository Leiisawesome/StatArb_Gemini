"""
Data Flow Visualization System for Statistical Arbitrage
======================================================

Professional-grade data flow visualization that traces:
1. Raw Data → Cleaned Data → Features → Signals → Positions → P&L
2. Real-time pipeline monitoring with quality scores
3. Interactive Sankey diagrams and flow charts
4. Data lineage and transformation tracking

Author: Pro Quant Desk Trader
"""

import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json

logger = logging.getLogger(__name__)

@dataclass
class DataFlowStep:
    """Individual data flow step"""
    step_id: str
    stage: str
    input_data: Any
    output_data: Any
    transformation: str
    timestamp: datetime
    processing_time_ms: float
    data_quality_score: float
    memory_usage_mb: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class DataFlowVisualizer:
    """
    Comprehensive data flow visualization system
    
    Tracks and visualizes the complete data pipeline from:
    Raw ClickHouse Data → Processing → Features → Signals → Execution → Portfolio
    """
    
    def __init__(self, output_dir: str = "results/data_flow"):
        """
        Initialize data flow visualizer
        
        Args:
            output_dir: Directory to save visualizations
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data flow tracking
        self.flow_steps: List[DataFlowStep] = []
        self.data_lineage: Dict[str, List[str]] = {}  # parent -> children mapping
        self.data_quality_history: List[Tuple[datetime, str, float]] = []
        
        # Pipeline stages definition
        self.pipeline_stages = [
            "Configuration",
            "Data Requirements",
            "Symbol Resolution", 
            "Strategy Configuration",
            "Full Backtest Execution",
            "Raw Data Loading",
            "Data Cleaning",
            "Feature Engineering",
            "Technical Indicators",
            "Market Regime Detection",
            "Signal Generation",
            "Position Sizing",
            "Trade Execution",
            "Portfolio Update",
            "Performance Calculation"
        ]
        
        logger.info(f"DataFlowVisualizer initialized - output: {self.output_dir}")
    
    def track_data_transformation(
        self, 
        step_id: str,
        stage: str,
        input_data: Any,
        output_data: Any,
        transformation: str,
        processing_time_ms: float = 0,
        **metadata
    ) -> None:
        """
        Track a data transformation step
        
        Args:
            step_id: Unique identifier for this step
            stage: Pipeline stage name
            input_data: Input data
            output_data: Transformed output data
            transformation: Description of transformation
            processing_time_ms: Processing time in milliseconds
            **metadata: Additional tracking metadata
        """
        # Calculate data quality scores
        input_quality = self._assess_data_quality(input_data)
        output_quality = self._assess_data_quality(output_data)
        
        # Estimate memory usage
        memory_usage = self._estimate_memory_usage(output_data)
        
        # Create flow step
        flow_step = DataFlowStep(
            step_id=step_id,
            stage=stage,
            input_data=input_data,
            output_data=output_data,
            transformation=transformation,
            timestamp=datetime.now(),
            processing_time_ms=processing_time_ms,
            data_quality_score=output_quality,
            memory_usage_mb=memory_usage,
            metadata={
                'input_quality': input_quality,
                'quality_change': output_quality - input_quality,
                'input_size': self._get_data_size(input_data),
                'output_size': self._get_data_size(output_data),
                **metadata
            }
        )
        
        self.flow_steps.append(flow_step)
        
        # Track quality history
        self.data_quality_history.append((datetime.now(), stage, output_quality))
        
        logger.info(f"📊 Tracked {stage}: {transformation} - Quality: {output_quality:.3f}")
    
    def create_sankey_diagram(self, symbols: List[str] = None) -> go.Figure:
        """
        Create Sankey diagram showing data flow through pipeline
        
        Args:
            symbols: Optional list of symbols to focus on
            
        Returns:
            Plotly figure with Sankey diagram
        """
        if not self.flow_steps:
            logger.warning("No flow steps to visualize")
            return go.Figure()
        
        # Build nodes and links for Sankey
        nodes = []
        links = []
        node_colors = []
        
        # Define stage colors
        stage_colors = {
            "Configuration": "#FF9F9F",
            "Data Requirements": "#9FD3FF", 
            "Symbol Resolution": "#B8E6B8",
            "Strategy Configuration": "#FFD700",
            "Full Backtest Execution": "#DDA0DD",
            "Raw Data Loading": "#FF6B6B",
            "Data Cleaning": "#4ECDC4", 
            "Feature Engineering": "#45B7D1",
            "Technical Indicators": "#96CEB4",
            "Market Regime Detection": "#FFEAA7",
            "Signal Generation": "#DDA0DD",
            "Position Sizing": "#98D8C8",
            "Trade Execution": "#F7DC6F",
            "Portfolio Update": "#BB8FCE",
            "Performance Calculation": "#85C1E9"
        }
        
        # Group steps by stage
        stage_data = {}
        for step in self.flow_steps:
            if step.stage not in stage_data:
                stage_data[step.stage] = {
                    'input_size': 0,
                    'output_size': 0,
                    'quality_score': 0,
                    'count': 0
                }
            
            stage_data[step.stage]['input_size'] += step.metadata.get('input_size', 0)
            stage_data[step.stage]['output_size'] += step.metadata.get('output_size', 0)
            stage_data[step.stage]['quality_score'] += step.data_quality_score
            stage_data[step.stage]['count'] += 1
        
        # Average quality scores
        for stage in stage_data:
            if stage_data[stage]['count'] > 0:
                stage_data[stage]['quality_score'] /= stage_data[stage]['count']
        
        # Create nodes
        node_index = {}
        for i, stage in enumerate(self.pipeline_stages):
            if stage in stage_data:
                nodes.append(f"{stage}<br>Quality: {stage_data[stage]['quality_score']:.3f}")
                node_colors.append(stage_colors.get(stage, "#CCCCCC"))
                node_index[stage] = i
        
        # Create links between consecutive stages
        for i in range(len(self.pipeline_stages) - 1):
            current_stage = self.pipeline_stages[i]
            next_stage = self.pipeline_stages[i + 1]
            
            if current_stage in stage_data and next_stage in stage_data:
                # Link value is output size of current stage
                link_value = stage_data[current_stage]['output_size']
                if link_value > 0:
                    links.append({
                        'source': node_index[current_stage],
                        'target': node_index[next_stage],
                        'value': link_value
                    })
        
        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color=node_colors
            ),
            link=dict(
                source=[link['source'] for link in links],
                target=[link['target'] for link in links],
                value=[link['value'] for link in links],
                color="rgba(255,255,255,0.4)"
            )
        )])
        
        fig.update_layout(
            title_text="Statistical Arbitrage Data Flow Pipeline",
            font_size=12,
            height=600
        )
        
        return fig
    
    def create_quality_timeline(self) -> go.Figure:
        """Create timeline showing data quality through pipeline stages"""
        if not self.data_quality_history:
            return go.Figure()
        
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(self.data_quality_history, columns=['timestamp', 'stage', 'quality'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create timeline plot
        fig = px.line(df, x='timestamp', y='quality', color='stage',
                     title='Data Quality Through Pipeline Stages',
                     labels={'quality': 'Data Quality Score', 'timestamp': 'Time'})
        
        fig.update_layout(
            yaxis=dict(range=[0, 1]),
            hovermode='x unified'
        )
        
        return fig
    
    def create_data_lineage_graph(self) -> go.Figure:
        """Create network graph showing data lineage"""
        if not self.flow_steps:
            return go.Figure()
        
        # Build network structure
        nodes = []
        edges = []
        node_trace = []
        edge_trace = []
        
        # Create nodes for each unique data transformation
        unique_transformations = list(set(step.transformation for step in self.flow_steps))
        
        for i, transformation in enumerate(unique_transformations):
            nodes.append({
                'id': i,
                'label': transformation,
                'x': i % 5,  # Simple grid layout
                'y': i // 5
            })
        
        # Create network graph (simplified for now)
        fig = go.Figure()
        
        # Add nodes
        for node in nodes:
            fig.add_trace(go.Scatter(
                x=[node['x']], 
                y=[node['y']],
                mode='markers+text',
                text=[node['label']],
                textposition='middle center',
                marker=dict(size=20, color='lightblue'),
                showlegend=False
            ))
        
        fig.update_layout(
            title='Data Transformation Lineage',
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        
        return fig
    
    def create_performance_dashboard(self) -> go.Figure:
        """Create comprehensive performance dashboard"""
        if not self.flow_steps:
            return go.Figure()
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Processing Time by Stage',
                'Data Quality by Stage',
                'Memory Usage Timeline',
                'Throughput Analysis'
            ],
            specs=[[{'type': 'bar'}, {'type': 'box'}],
                   [{'type': 'scatter'}, {'type': 'bar'}]]
        )
        
        # Group data by stage
        stage_times = {}
        stage_qualities = {}
        stage_memory = {}
        
        for step in self.flow_steps:
            stage = step.stage
            if stage not in stage_times:
                stage_times[stage] = []
                stage_qualities[stage] = []
                stage_memory[stage] = []
            
            stage_times[stage].append(step.processing_time_ms)
            stage_qualities[stage].append(step.data_quality_score)
            stage_memory[stage].append(step.memory_usage_mb)
        
        # 1. Processing time by stage
        stages = list(stage_times.keys())
        avg_times = [np.mean(stage_times[stage]) for stage in stages]
        
        fig.add_trace(
            go.Bar(x=stages, y=avg_times, name='Avg Processing Time'),
            row=1, col=1
        )
        
        # 2. Data quality distribution
        for stage in stages:
            fig.add_trace(
                go.Box(y=stage_qualities[stage], name=stage, showlegend=False),
                row=1, col=2
            )
        
        # 3. Memory usage timeline
        timestamps = [step.timestamp for step in self.flow_steps]
        memory_usage = [step.memory_usage_mb for step in self.flow_steps]
        
        fig.add_trace(
            go.Scatter(x=timestamps, y=memory_usage, mode='lines+markers', 
                      name='Memory Usage', showlegend=False),
            row=2, col=1
        )
        
        # 4. Throughput analysis
        stage_throughput = {}
        for step in self.flow_steps:
            stage = step.stage
            if stage not in stage_throughput:
                stage_throughput[stage] = 0
            
            if step.processing_time_ms > 0:
                throughput = step.metadata.get('output_size', 0) / (step.processing_time_ms / 1000)
                stage_throughput[stage] = max(stage_throughput[stage], throughput)
        
        fig.add_trace(
            go.Bar(x=list(stage_throughput.keys()), 
                  y=list(stage_throughput.values()), 
                  name='Throughput', showlegend=False),
            row=2, col=2
        )
        
        fig.update_layout(height=800, title_text="Data Flow Performance Dashboard")
        return fig
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive data flow analysis report"""
        logger.info("📊 Generating comprehensive data flow report...")
        
        # Generate all visualizations
        sankey_fig = self.create_sankey_diagram()
        quality_fig = self.create_quality_timeline()
        lineage_fig = self.create_data_lineage_graph()
        dashboard_fig = self.create_performance_dashboard()
        
        # Save visualizations
        plots = {}
        
        sankey_file = self.output_dir / 'data_flow_sankey.html'
        sankey_fig.write_html(str(sankey_file))
        plots['sankey'] = str(sankey_file)
        
        quality_file = self.output_dir / 'data_quality_timeline.html'
        quality_fig.write_html(str(quality_file))
        plots['quality'] = str(quality_file)
        
        lineage_file = self.output_dir / 'data_lineage.html'
        lineage_fig.write_html(str(lineage_file))
        plots['lineage'] = str(lineage_file)
        
        dashboard_file = self.output_dir / 'performance_dashboard.html'
        dashboard_fig.write_html(str(dashboard_file))
        plots['dashboard'] = str(dashboard_file)
        
        # Calculate summary statistics
        summary = self._calculate_summary_stats()
        
        # Identify bottlenecks and issues
        bottlenecks = self._identify_data_bottlenecks()
        
        # Generate optimization recommendations
        recommendations = self._generate_data_optimization_recommendations()
        
        # Create comprehensive report
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary_statistics': summary,
            'data_quality_analysis': self._analyze_overall_data_quality(),
            'performance_bottlenecks': bottlenecks,
            'optimization_recommendations': recommendations,
            'visualizations': plots,
            'pipeline_stages': self.pipeline_stages,
            'total_flow_steps': len(self.flow_steps)
        }
        
        # Save report
        report_file = self.output_dir / f"data_flow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📋 Data flow report saved: {report_file}")
        return report
    
    def _assess_data_quality(self, data: Any) -> float:
        """Assess data quality score (0-1)"""
        if data is None:
            return 0.0
        
        try:
            if isinstance(data, pd.DataFrame):
                if data.empty:
                    return 0.0
                
                # Check for missing values
                missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))
                
                # Check for infinite values
                numeric_cols = data.select_dtypes(include=[np.number])
                if numeric_cols.empty:
                    inf_ratio = 0.0
                else:
                    inf_ratio = np.isinf(numeric_cols).sum().sum() / (len(data) * len(numeric_cols.columns))
                
                # Check for duplicates
                duplicate_ratio = data.duplicated().sum() / len(data)
                
                # Quality score (1.0 = perfect, 0.0 = unusable)
                quality = 1.0 - (missing_ratio * 0.4) - (inf_ratio * 0.4) - (duplicate_ratio * 0.2)
                return max(0.0, min(1.0, quality))
            
            elif isinstance(data, (list, tuple)):
                return 1.0 if len(data) > 0 else 0.0
            
            elif isinstance(data, dict):
                return 1.0 if data else 0.0
            
            else:
                return 1.0
                
        except Exception:
            return 0.5  # Default moderate quality
    
    def _get_data_size(self, data: Any) -> int:
        """Get data size (number of records/elements)"""
        try:
            if isinstance(data, pd.DataFrame):
                return len(data)
            elif isinstance(data, (list, tuple, dict)):
                return len(data)
            elif hasattr(data, '__len__'):
                return len(data)
            else:
                return 1
        except Exception:
            return 0
    
    def _estimate_memory_usage(self, data: Any) -> float:
        """Estimate memory usage in MB"""
        try:
            if isinstance(data, pd.DataFrame):
                return data.memory_usage(deep=True).sum() / 1024 / 1024
            elif isinstance(data, (list, tuple)):
                return len(data) * 8 / 1024 / 1024  # Rough estimate
            elif isinstance(data, dict):
                return len(data) * 16 / 1024 / 1024  # Rough estimate
            else:
                return 0.001  # Minimal usage
        except Exception:
            return 0.0
    
    def _calculate_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics for data flow"""
        if not self.flow_steps:
            return {}
        
        # Processing time statistics
        processing_times = [step.processing_time_ms for step in self.flow_steps]
        
        # Quality statistics
        quality_scores = [step.data_quality_score for step in self.flow_steps]
        
        # Memory usage statistics
        memory_usage = [step.memory_usage_mb for step in self.flow_steps]
        
        # Data size statistics
        input_sizes = [step.metadata.get('input_size', 0) for step in self.flow_steps]
        output_sizes = [step.metadata.get('output_size', 0) for step in self.flow_steps]
        
        return {
            'processing_time': {
                'avg_ms': np.mean(processing_times),
                'p95_ms': np.percentile(processing_times, 95),
                'total_ms': np.sum(processing_times)
            },
            'data_quality': {
                'avg_score': np.mean(quality_scores),
                'min_score': np.min(quality_scores),
                'quality_degradation_steps': len([s for s in self.flow_steps if s.metadata.get('quality_change', 0) < -0.1])
            },
            'memory_usage': {
                'avg_mb': np.mean(memory_usage),
                'peak_mb': np.max(memory_usage),
                'total_mb': np.sum(memory_usage)
            },
            'data_throughput': {
                'total_input_records': np.sum(input_sizes),
                'total_output_records': np.sum(output_sizes),
                'avg_records_per_step': np.mean(output_sizes)
            }
        }
    
    def _analyze_overall_data_quality(self) -> Dict[str, Any]:
        """Analyze overall data quality trends"""
        if not self.flow_steps:
            return {}
        
        # Quality by stage
        stage_quality = {}
        for step in self.flow_steps:
            if step.stage not in stage_quality:
                stage_quality[step.stage] = []
            stage_quality[step.stage].append(step.data_quality_score)
        
        # Average quality by stage
        avg_stage_quality = {
            stage: np.mean(scores) for stage, scores in stage_quality.items()
        }
        
        # Identify quality degradation points
        quality_issues = []
        for step in self.flow_steps:
            quality_change = step.metadata.get('quality_change', 0)
            if quality_change < -0.1:  # Significant quality drop
                quality_issues.append({
                    'stage': step.stage,
                    'transformation': step.transformation,
                    'quality_drop': quality_change,
                    'timestamp': step.timestamp.isoformat()
                })
        
        return {
            'avg_quality_by_stage': avg_stage_quality,
            'overall_avg_quality': np.mean([step.data_quality_score for step in self.flow_steps]),
            'quality_degradation_points': quality_issues,
            'stages_below_threshold': [
                stage for stage, quality in avg_stage_quality.items() 
                if quality < 0.8
            ]
        }
    
    def _identify_data_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify data processing bottlenecks"""
        bottlenecks = []
        
        # Group by stage for analysis
        stage_stats = {}
        for step in self.flow_steps:
            if step.stage not in stage_stats:
                stage_stats[step.stage] = {
                    'processing_times': [],
                    'memory_usage': [],
                    'data_sizes': []
                }
            
            stage_stats[step.stage]['processing_times'].append(step.processing_time_ms)
            stage_stats[step.stage]['memory_usage'].append(step.memory_usage_mb)
            stage_stats[step.stage]['data_sizes'].append(step.metadata.get('output_size', 0))
        
        # Identify slow stages
        for stage, stats in stage_stats.items():
            avg_time = np.mean(stats['processing_times'])
            if avg_time > 1000:  # > 1 second
                bottlenecks.append({
                    'type': 'processing_time',
                    'stage': stage,
                    'severity': 'high' if avg_time > 5000 else 'medium',
                    'avg_time_ms': avg_time,
                    'recommendation': f"Optimize {stage} processing - avg {avg_time:.0f}ms"
                })
        
        # Identify memory-intensive stages
        for stage, stats in stage_stats.items():
            avg_memory = np.mean(stats['memory_usage'])
            if avg_memory > 100:  # > 100MB
                bottlenecks.append({
                    'type': 'memory_usage',
                    'stage': stage,
                    'severity': 'high' if avg_memory > 500 else 'medium',
                    'avg_memory_mb': avg_memory,
                    'recommendation': f"Optimize memory usage in {stage} - avg {avg_memory:.0f}MB"
                })
        
        return sorted(bottlenecks, key=lambda x: x.get('severity', 'low'), reverse=True)
    
    def _generate_data_optimization_recommendations(self) -> List[str]:
        """Generate data optimization recommendations"""
        recommendations = []
        
        if not self.flow_steps:
            return recommendations
        
        # Analyze processing times
        avg_times = {}
        for step in self.flow_steps:
            stage = step.stage
            if stage not in avg_times:
                avg_times[stage] = []
            avg_times[stage].append(step.processing_time_ms)
        
        for stage, times in avg_times.items():
            avg_time = np.mean(times)
            if avg_time > 2000:  # > 2 seconds
                recommendations.append(
                    f"🚀 Optimize {stage}: avg {avg_time:.0f}ms - consider parallel processing, caching, or algorithm optimization"
                )
        
        # Analyze data quality
        quality_by_stage = {}
        for step in self.flow_steps:
            stage = step.stage
            if stage not in quality_by_stage:
                quality_by_stage[stage] = []
            quality_by_stage[stage].append(step.data_quality_score)
        
        for stage, scores in quality_by_stage.items():
            avg_quality = np.mean(scores)
            if avg_quality < 0.85:
                recommendations.append(
                    f"🎯 Improve data quality in {stage}: avg score {avg_quality:.3f} - add validation, cleaning, or error handling"
                )
        
        # Analyze memory usage
        memory_by_stage = {}
        for step in self.flow_steps:
            stage = step.stage
            if stage not in memory_by_stage:
                memory_by_stage[stage] = []
            memory_by_stage[stage].append(step.memory_usage_mb)
        
        for stage, memory in memory_by_stage.items():
            avg_memory = np.mean(memory)
            if avg_memory > 200:  # > 200MB
                recommendations.append(
                    f"💾 Optimize memory usage in {stage}: avg {avg_memory:.0f}MB - consider streaming, chunking, or data compression"
                )
        
        return recommendations


# Global data flow visualizer instance
_data_flow_visualizer = None

def get_data_flow_visualizer() -> DataFlowVisualizer:
    """Get global data flow visualizer instance"""
    global _data_flow_visualizer
    if _data_flow_visualizer is None:
        _data_flow_visualizer = DataFlowVisualizer()
    return _data_flow_visualizer 