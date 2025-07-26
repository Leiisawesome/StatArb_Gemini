"""
Comprehensive Flow Monitoring System for Statistical Arbitrage
============================================================

Professional-grade monitoring system that tracks:
1. Functionality Flow: How modules interact and pass messages
2. Data Flow: Raw data → Features → Signals → Execution → Portfolio
3. Performance Metrics: Timing, throughput, quality at each step
4. Visualization: Real-time flow charts and bottleneck analysis

Author: Pro Quant Desk Trader
"""

import logging
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import threading
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

class FlowStage(Enum):
    """Flow processing stages"""
    DATA_LOADING = "data_loading"
    DATA_PROCESSING = "data_processing"
    FEATURE_ENGINEERING = "feature_engineering"
    REGIME_DETECTION = "regime_detection"
    SIGNAL_GENERATION = "signal_generation"
    POSITION_SIZING = "position_sizing"
    TRADE_EXECUTION = "trade_execution"
    PORTFOLIO_UPDATE = "portfolio_update"
    PERFORMANCE_CALCULATION = "performance_calculation"

class ComponentType(Enum):
    """System component types"""
    DATA_MANAGER = "data_manager"
    STRATEGY = "strategy"
    SIGNAL_GENERATOR = "signal_generator"
    EXECUTION_ENGINE = "execution_engine"
    OPTIMIZER = "optimizer"
    PERFORMANCE_ANALYZER = "performance_analyzer"

@dataclass
class FlowEvent:
    """Individual flow event tracking"""
    timestamp: datetime
    stage: FlowStage
    component: ComponentType
    event_type: str  # start, complete, error
    symbol: Optional[str] = None
    data_size: Optional[int] = None
    processing_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'stage': self.stage.value,
            'component': self.component.value,
            'event_type': self.event_type,
            'symbol': self.symbol,
            'data_size': self.data_size,
            'processing_time_ms': self.processing_time_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'metadata': self.metadata
        }

@dataclass
class DataFlowMetrics:
    """Data flow quality and performance metrics"""
    stage: FlowStage
    input_records: int = 0
    output_records: int = 0
    data_quality_score: float = 1.0
    processing_latency_ms: float = 0.0
    memory_peak_mb: float = 0.0
    error_count: int = 0
    throughput_records_per_sec: float = 0.0
    
class FlowMonitor:
    """
    Comprehensive flow monitoring system
    
    Tracks both functionality flow (how components interact) and 
    data flow (data transformation pipeline) with detailed metrics.
    """
    
    def __init__(self, output_dir: str = "results/flow_analysis"):
        """
        Initialize flow monitor
        
        Args:
            output_dir: Directory to save monitoring outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Event storage
        self.events: List[FlowEvent] = []
        self.data_metrics: Dict[FlowStage, DataFlowMetrics] = {}
        self.component_timing: Dict[ComponentType, List[float]] = defaultdict(list)
        
        # Active context tracking
        self.active_contexts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # Performance tracking
        self.stage_performance: Dict[FlowStage, deque] = {
            stage: deque(maxlen=1000) for stage in FlowStage
        }
        self.component_performance: Dict[ComponentType, deque] = {
            comp: deque(maxlen=1000) for comp in ComponentType
        }
        
        # Data flow tracking
        self.data_lineage: List[Dict[str, Any]] = []
        self.data_quality_history: Dict[str, List[float]] = defaultdict(list)
        
        logger.info(f"FlowMonitor initialized - output: {self.output_dir}")
    
    def start_stage(self, stage: FlowStage, component: ComponentType, 
                   symbol: Optional[str] = None, **metadata) -> str:
        """
        Start monitoring a processing stage
        
        Args:
            stage: Processing stage
            component: System component
            symbol: Optional symbol being processed
            **metadata: Additional context
            
        Returns:
            Context ID for tracking
        """
        context_id = f"{stage.value}_{component.value}_{int(time.time()*1000)}"
        
        with self._lock:
            # Record start event
            event = FlowEvent(
                timestamp=datetime.now(),
                stage=stage,
                component=component,
                event_type="start",
                symbol=symbol,
                metadata=metadata
            )
            self.events.append(event)
            
            # Track active context
            self.active_contexts[context_id] = {
                'stage': stage,
                'component': component,
                'symbol': symbol,
                'start_time': time.time(),
                'start_memory': self._get_memory_usage(),
                'metadata': metadata
            }
        
        logger.info(f"🚀 Started {stage.value} in {component.value}" + 
                   (f" for {symbol}" if symbol else ""))
        return context_id
    
    def complete_stage(self, context_id: str, data_size: Optional[int] = None,
                      output_data: Optional[Any] = None, **metadata) -> None:
        """
        Complete monitoring a processing stage
        
        Args:
            context_id: Context ID from start_stage
            data_size: Size of processed data
            output_data: Output data for quality assessment
            **metadata: Additional completion metadata
        """
        if context_id not in self.active_contexts:
            logger.warning(f"Unknown context ID: {context_id}")
            return
        
        with self._lock:
            context = self.active_contexts.pop(context_id)
            
            # Calculate metrics
            processing_time = (time.time() - context['start_time']) * 1000
            current_memory = self._get_memory_usage()
            memory_delta = current_memory - context['start_memory']
            
            # Record completion event
            event = FlowEvent(
                timestamp=datetime.now(),
                stage=context['stage'],
                component=context['component'],
                event_type="complete",
                symbol=context['symbol'],
                data_size=data_size,
                processing_time_ms=processing_time,
                memory_usage_mb=memory_delta,
                metadata={**context['metadata'], **metadata}
            )
            self.events.append(event)
            
            # Update performance tracking
            self.stage_performance[context['stage']].append(processing_time)
            self.component_performance[context['component']].append(processing_time)
            
            # Assess data quality if output provided
            quality_score = self._assess_data_quality(output_data) if output_data is not None else 1.0
            
            # Update data metrics
            if context['stage'] not in self.data_metrics:
                self.data_metrics[context['stage']] = DataFlowMetrics(stage=context['stage'])
            
            metrics = self.data_metrics[context['stage']]
            metrics.output_records = data_size or 0
            metrics.processing_latency_ms = processing_time
            metrics.memory_peak_mb = max(metrics.memory_peak_mb, memory_delta)
            metrics.data_quality_score = quality_score
            
            if processing_time > 0:
                metrics.throughput_records_per_sec = (data_size or 0) / (processing_time / 1000)
        
        logger.info(f"✅ Completed {context['stage'].value} in {processing_time:.2f}ms" +
                   (f" - {data_size} records" if data_size else "") +
                   (f" - Quality: {quality_score:.3f}" if output_data is not None else ""))
    
    def record_error(self, context_id: str, error: Exception, **metadata) -> None:
        """
        Record an error during processing
        
        Args:
            context_id: Context ID from start_stage
            error: Exception that occurred
            **metadata: Additional error context
        """
        if context_id not in self.active_contexts:
            logger.warning(f"Unknown context ID for error: {context_id}")
            return
        
        with self._lock:
            context = self.active_contexts[context_id]
            
            # Record error event
            event = FlowEvent(
                timestamp=datetime.now(),
                stage=context['stage'],
                component=context['component'],
                event_type="error",
                symbol=context['symbol'],
                metadata={
                    **context['metadata'],
                    **metadata,
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
            )
            self.events.append(event)
            
            # Update error count
            if context['stage'] in self.data_metrics:
                self.data_metrics[context['stage']].error_count += 1
        
        logger.error(f"❌ Error in {context['stage'].value}: {error}")
    
    def track_data_lineage(self, input_data: Any, output_data: Any, 
                          transformation: str, metadata: Dict[str, Any] = None) -> None:
        """
        Track data transformation lineage
        
        Args:
            input_data: Input data
            output_data: Transformed output data
            transformation: Description of transformation
            metadata: Additional lineage metadata
        """
        lineage_entry = {
            'timestamp': datetime.now().isoformat(),
            'transformation': transformation,
            'input_size': self._get_data_size(input_data),
            'output_size': self._get_data_size(output_data),
            'input_type': type(input_data).__name__,
            'output_type': type(output_data).__name__,
            'quality_change': self._assess_data_quality(output_data) - self._assess_data_quality(input_data),
            'metadata': metadata or {}
        }
        
        self.data_lineage.append(lineage_entry)
        logger.debug(f"📊 Data lineage: {transformation} - {lineage_entry['input_size']} → {lineage_entry['output_size']}")
    
    def get_flow_summary(self) -> Dict[str, Any]:
        """Get comprehensive flow analysis summary"""
        with self._lock:
            # Stage performance summary
            stage_summary = {}
            for stage, timings in self.stage_performance.items():
                if timings:
                    stage_summary[stage.value] = {
                        'avg_time_ms': np.mean(timings),
                        'p95_time_ms': np.percentile(timings, 95),
                        'min_time_ms': np.min(timings),
                        'max_time_ms': np.max(timings),
                        'total_executions': len(timings)
                    }
            
            # Component performance summary
            component_summary = {}
            for component, timings in self.component_performance.items():
                if timings:
                    component_summary[component.value] = {
                        'avg_time_ms': np.mean(timings),
                        'p95_time_ms': np.percentile(timings, 95),
                        'total_executions': len(timings)
                    }
            
            # Data quality summary
            quality_summary = {}
            for stage, metrics in self.data_metrics.items():
                quality_summary[stage.value] = {
                    'data_quality_score': metrics.data_quality_score,
                    'throughput_rps': metrics.throughput_records_per_sec,
                    'error_count': metrics.error_count,
                    'memory_peak_mb': metrics.memory_peak_mb
                }
            
            return {
                'total_events': len(self.events),
                'active_contexts': len(self.active_contexts),
                'stage_performance': stage_summary,
                'component_performance': component_summary,
                'data_quality': quality_summary,
                'data_lineage_steps': len(self.data_lineage)
            }
    
    def generate_flow_report(self, save_plots: bool = True) -> Dict[str, Any]:
        """
        Generate comprehensive flow analysis report
        
        Args:
            save_plots: Whether to save visualization plots
            
        Returns:
            Complete flow analysis report
        """
        logger.info("📊 Generating comprehensive flow report...")
        
        # Get summary statistics
        summary = self.get_flow_summary()
        
        # Generate visualizations if requested
        plots = {}
        if save_plots:
            plots = self._generate_visualizations()
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks()
        
        # Data quality analysis
        quality_analysis = self._analyze_data_quality()
        
        # Create comprehensive report
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'bottlenecks': bottlenecks,
            'data_quality_analysis': quality_analysis,
            'optimization_recommendations': self._generate_optimization_recommendations(),
            'visualizations': plots,
            'raw_events': [event.to_dict() for event in self.events[-100:]]  # Last 100 events
        }
        
        # Save report
        report_file = self.output_dir / f"flow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📋 Flow report saved: {report_file}")
        return report
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
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
                if data.select_dtypes(include=[np.number]).empty:
                    inf_ratio = 0.0
                else:
                    inf_ratio = np.isinf(data.select_dtypes(include=[np.number])).sum().sum() / (len(data) * len(data.select_dtypes(include=[np.number]).columns))
                
                # Quality score (1.0 = perfect, 0.0 = unusable)
                quality = 1.0 - (missing_ratio * 0.5) - (inf_ratio * 0.5)
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
    
    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Stage-level bottlenecks
        for stage, timings in self.stage_performance.items():
            if len(timings) > 5:  # Need sufficient data
                avg_time = np.mean(timings)
                p95_time = np.percentile(timings, 95)
                
                if avg_time > 1000:  # > 1 second average
                    bottlenecks.append({
                        'type': 'stage_performance',
                        'stage': stage.value,
                        'severity': 'high' if avg_time > 5000 else 'medium',
                        'avg_time_ms': avg_time,
                        'p95_time_ms': p95_time,
                        'recommendation': f"Optimize {stage.value} processing - avg {avg_time:.0f}ms"
                    })
        
        # Data quality bottlenecks
        for stage, metrics in self.data_metrics.items():
            if metrics.data_quality_score < 0.9:
                bottlenecks.append({
                    'type': 'data_quality',
                    'stage': stage.value,
                    'severity': 'high' if metrics.data_quality_score < 0.7 else 'medium',
                    'quality_score': metrics.data_quality_score,
                    'recommendation': f"Improve data quality in {stage.value} - score {metrics.data_quality_score:.3f}"
                })
        
        return sorted(bottlenecks, key=lambda x: x.get('severity', 'low'), reverse=True)
    
    def _analyze_data_quality(self) -> Dict[str, Any]:
        """Analyze data quality across the pipeline"""
        quality_trends = {}
        
        for stage, metrics in self.data_metrics.items():
            quality_trends[stage.value] = {
                'current_quality': metrics.data_quality_score,
                'error_rate': metrics.error_count / max(1, metrics.output_records),
                'throughput': metrics.throughput_records_per_sec,
                'memory_efficiency': metrics.output_records / max(1, metrics.memory_peak_mb)
            }
        
        return {
            'stage_quality': quality_trends,
            'overall_quality': np.mean([m.data_quality_score for m in self.data_metrics.values()]) if self.data_metrics else 1.0,
            'quality_trend': 'stable'  # TODO: Calculate trend over time
        }
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Performance recommendations
        for stage, timings in self.stage_performance.items():
            if len(timings) > 5 and np.mean(timings) > 1000:
                recommendations.append(
                    f"🚀 Optimize {stage.value}: avg {np.mean(timings):.0f}ms - consider parallel processing or caching"
                )
        
        # Memory recommendations
        for stage, metrics in self.data_metrics.items():
            if metrics.memory_peak_mb > 500:  # > 500MB
                recommendations.append(
                    f"💾 Memory optimization needed in {stage.value}: peak {metrics.memory_peak_mb:.0f}MB"
                )
        
        # Data quality recommendations
        for stage, metrics in self.data_metrics.items():
            if metrics.data_quality_score < 0.9:
                recommendations.append(
                    f"🎯 Improve data quality in {stage.value}: score {metrics.data_quality_score:.3f}"
                )
        
        return recommendations
    
    def _generate_visualizations(self) -> Dict[str, str]:
        """Generate flow visualizations"""
        plots = {}
        
        try:
            # Performance timeline
            if self.events:
                df_events = pd.DataFrame([event.to_dict() for event in self.events])
                df_events['timestamp'] = pd.to_datetime(df_events['timestamp'])
                
                fig = px.timeline(
                    df_events[df_events['event_type'] == 'complete'],
                    x_start='timestamp', 
                    x_end='timestamp',
                    y='stage',
                    color='processing_time_ms',
                    title='Processing Stage Timeline'
                )
                
                timeline_file = self.output_dir / 'flow_timeline.html'
                fig.write_html(str(timeline_file))
                plots['timeline'] = str(timeline_file)
            
            # Performance by stage
            if self.stage_performance:
                stage_data = []
                for stage, timings in self.stage_performance.items():
                    if timings:
                        stage_data.extend([{'stage': stage.value, 'time_ms': t} for t in timings])
                
                if stage_data:
                    df_performance = pd.DataFrame(stage_data)
                    fig = px.box(df_performance, x='stage', y='time_ms', 
                               title='Processing Time by Stage')
                    fig.update_layout(xaxis_tickangle=45)
                    
                    performance_file = self.output_dir / 'stage_performance.html'
                    fig.write_html(str(performance_file))
                    plots['performance'] = str(performance_file)
        
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
        
        return plots


# Global flow monitor instance
_flow_monitor = None

def get_flow_monitor() -> FlowMonitor:
    """Get global flow monitor instance"""
    global _flow_monitor
    if _flow_monitor is None:
        _flow_monitor = FlowMonitor()
    return _flow_monitor

def monitor_stage(stage: FlowStage, component: ComponentType):
    """Decorator for monitoring function/method execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_flow_monitor()
            context_id = monitor.start_stage(stage, component)
            
            try:
                result = func(*args, **kwargs)
                monitor.complete_stage(context_id, output_data=result)
                return result
            except Exception as e:
                monitor.record_error(context_id, e)
                raise
        return wrapper
    return decorator 