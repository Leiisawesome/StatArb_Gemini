#!/usr/bin/env python3
"""
Data Quality Monitor
Phase 2: Core System Integration - Batch 1
"""

import logging
from typing import Dict, List, Callable
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)

class DataQualityMonitor:
    """Monitor data quality and integrity"""
    
    def __init__(self):
        self.quality_metrics = {}
        self.alert_callbacks = []
        self.quality_thresholds = {
            'max_price_change': 0.1,  # 10% max price change
            'max_volume': 1000000,    # 1M max volume
            'max_staleness': 300,     # 5 minutes max staleness
            'min_data_points': 10     # Minimum data points required
        }
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback for data quality issues"""
        self.alert_callbacks.append(callback)
        logger.info(f"Added alert callback: {callback.__name__}")
    
    def check_data_quality(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Check data quality for all symbols"""
        quality_report = {}
        
        for symbol, df in data.items():
            if df.empty:
                quality_report[symbol] = {
                    'status': 'ERROR',
                    'issues': ['Empty data'],
                    'severity': 'HIGH'
                }
                continue
            
            issues = []
            severity = 'LOW'
            
            # Check for missing values
            missing_values = df.isnull().sum().sum()
            if missing_values > 0:
                issues.append(f"Missing values: {missing_values}")
                severity = 'MEDIUM'
            
            # Check for price anomalies
            if 'close' in df.columns:
                price_changes = df['close'].pct_change().abs()
                max_change = price_changes.max()
                if max_change > self.quality_thresholds['max_price_change']:
                    issues.append(f"Large price change detected: {max_change:.2%}")
                    severity = 'HIGH'
            
            # Check for volume anomalies
            if 'volume' in df.columns:
                max_volume = df['volume'].max()
                if max_volume > self.quality_thresholds['max_volume']:
                    issues.append(f"Unusual volume detected: {max_volume:,}")
                    severity = 'MEDIUM'
            
            # Check data freshness
            if 'timestamp' in df.index:
                latest_time = df.index.max()
                if isinstance(latest_time, datetime):
                    time_diff = datetime.now() - latest_time
                    if time_diff.total_seconds() > self.quality_thresholds['max_staleness']:
                        issues.append(f"Data may be stale: {time_diff.total_seconds():.0f}s old")
                        severity = 'HIGH'
            
            # Check data sufficiency
            if len(df) < self.quality_thresholds['min_data_points']:
                issues.append(f"Insufficient data points: {len(df)}")
                severity = 'MEDIUM'
            
            quality_report[symbol] = {
                'status': 'OK' if not issues else 'WARNING',
                'issues': issues,
                'severity': severity,
                'data_points': len(df),
                'last_update': df.index.max() if not df.empty else None
            }
        
        return quality_report
    
    async def notify_alerts(self, quality_report: Dict):
        """Notify alert callbacks of quality issues"""
        for symbol, report in quality_report.items():
            if report['status'] != 'OK':
                for callback in self.alert_callbacks:
                    try:
                        await callback(symbol, report)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")
    
    def get_quality_summary(self, quality_report: Dict) -> Dict:
        """Get summary of data quality across all symbols"""
        total_symbols = len(quality_report)
        ok_symbols = sum(1 for report in quality_report.values() if report['status'] == 'OK')
        warning_symbols = sum(1 for report in quality_report.values() if report['status'] == 'WARNING')
        error_symbols = sum(1 for report in quality_report.values() if report['status'] == 'ERROR')
        
        high_severity = sum(1 for report in quality_report.values() if report.get('severity') == 'HIGH')
        medium_severity = sum(1 for report in quality_report.values() if report.get('severity') == 'MEDIUM')
        
        return {
            'total_symbols': total_symbols,
            'ok_symbols': ok_symbols,
            'warning_symbols': warning_symbols,
            'error_symbols': error_symbols,
            'high_severity_issues': high_severity,
            'medium_severity_issues': medium_severity,
            'quality_score': (ok_symbols / total_symbols) * 100 if total_symbols > 0 else 0
        } 