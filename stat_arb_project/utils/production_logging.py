"""
Production Logging System
Structured logging with monitoring and alerting capabilities.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import structlog
from structlog.stdlib import LoggerFactory

class ProductionLogger:
    """
    Production-ready logging system with structured logging.
    """
    
    def __init__(self, 
                 log_level: str = "INFO",
                 log_format: str = "json",
                 log_file: Optional[str] = None,
                 service_name: str = "stat_arb"):
        self.log_level = getattr(logging, log_level.upper())
        self.log_format = log_format
        self.log_file = log_file
        self.service_name = service_name
        
        # Configure structlog
        self._configure_structlog()
        
        # Create logger
        self.logger = structlog.get_logger()
        
    def _configure_structlog(self):
        """Configure structlog for production logging."""
        # Configure processors
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]
        
        if self.log_format == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())
        
        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=self.log_level
        )
        
        # Add file handler if specified
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(self.log_level)
            logging.getLogger().addHandler(file_handler)
    
    def log_trade(self, 
                  symbol: str,
                  side: str,
                  quantity: float,
                  price: float,
                  order_id: str,
                  strategy: str,
                  **kwargs):
        """Log trade execution."""
        self.logger.info(
            "trade_executed",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_id=order_id,
            strategy=strategy,
            notional=quantity * price,
            **kwargs
        )
    
    def log_signal(self,
                   symbol: str,
                   signal_strength: float,
                   signal_type: str,
                   confidence: float,
                   **kwargs):
        """Log trading signal."""
        self.logger.info(
            "signal_generated",
            symbol=symbol,
            signal_strength=signal_strength,
            signal_type=signal_type,
            confidence=confidence,
            **kwargs
        )
    
    def log_risk_alert(self,
                       alert_type: str,
                       severity: str,
                       message: str,
                       **kwargs):
        """Log risk alerts."""
        self.logger.warning(
            "risk_alert",
            alert_type=alert_type,
            severity=severity,
            message=message,
            **kwargs
        )
    
    def log_performance(self,
                        metric: str,
                        value: float,
                        period: str = "daily",
                        **kwargs):
        """Log performance metrics."""
        self.logger.info(
            "performance_metric",
            metric=metric,
            value=value,
            period=period,
            **kwargs
        )
    
    def log_error(self,
                  error_type: str,
                  error_message: str,
                  stack_trace: Optional[str] = None,
                  **kwargs):
        """Log errors with context."""
        self.logger.error(
            "error_occurred",
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            **kwargs
        )
    
    def log_system_health(self,
                          component: str,
                          status: str,
                          metrics: Dict[str, Any],
                          **kwargs):
        """Log system health metrics."""
        self.logger.info(
            "system_health",
            component=component,
            status=status,
            metrics=metrics,
            **kwargs
        )

class MetricsCollector:
    """
    Metrics collection for monitoring and alerting.
    """
    
    def __init__(self, logger: ProductionLogger):
        self.logger = logger
        self.metrics = {}
        
    def record_trade_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record trade-related metrics."""
        metric_key = f"trade.{metric_name}"
        self.metrics[metric_key] = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'tags': tags or {}
        }
        
        # Log metric
        self.logger.log_performance(metric_name, value, tags=tags)
    
    def record_risk_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record risk-related metrics."""
        metric_key = f"risk.{metric_name}"
        self.metrics[metric_key] = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'tags': tags or {}
        }
        
        # Check thresholds and alert if needed
        self._check_risk_thresholds(metric_name, value, tags)
    
    def record_system_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record system-related metrics."""
        metric_key = f"system.{metric_name}"
        self.metrics[metric_key] = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'tags': tags or {}
        }
        
        # Log system health
        self.logger.log_system_health(
            component=tags.get('component', 'unknown'),
            status='healthy' if value < 0.8 else 'warning',
            metrics={metric_name: value}
        )
    
    def _check_risk_thresholds(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Check risk thresholds and generate alerts."""
        thresholds = {
            'drawdown': 0.15,  # 15% max drawdown
            'leverage': 2.0,   # 2x max leverage
            'var_95': 0.05,    # 5% VaR
            'position_concentration': 0.2  # 20% max position
        }
        
        threshold = thresholds.get(metric_name)
        if threshold and value > threshold:
            self.logger.log_risk_alert(
                alert_type=f"{metric_name}_threshold_exceeded",
                severity="high" if value > threshold * 1.5 else "medium",
                message=f"{metric_name} exceeded threshold: {value:.4f} > {threshold:.4f}",
                metric_name=metric_name,
                value=value,
                threshold=threshold,
                tags=tags
            )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics."""
        summary = {
            'total_metrics': len(self.metrics),
            'metrics_by_category': {},
            'latest_values': {}
        }
        
        for metric_key, metric_data in self.metrics.items():
            category = metric_key.split('.')[0]
            summary['metrics_by_category'].setdefault(category, 0)
            summary['metrics_by_category'][category] += 1
            
            summary['latest_values'][metric_key] = {
                'value': metric_data['value'],
                'timestamp': metric_data['timestamp']
            }
        
        return summary

def setup_production_logging(config: Dict[str, Any]) -> ProductionLogger:
    """
    Setup production logging based on configuration.
    
    Args:
        config: Logging configuration dictionary
        
    Returns:
        Configured production logger
    """
    return ProductionLogger(
        log_level=config.get('level', 'INFO'),
        log_format=config.get('format', 'json'),
        log_file=config.get('file_path'),
        service_name=config.get('service_name', 'stat_arb')
    ) 