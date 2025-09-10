"""
Regime Engine Production Monitoring and Analytics
================================================

Provides comprehensive monitoring, persistence, and analytics for the
centralized regime engine in production environments.

Author: Assistant
Date: September 2025
"""

import json
import sqlite3
import asyncio
import threading
import time
import queue
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Import regime types
from .regime_engine import (
    RegimeState, RegimeType, RegimeTransition, 
    UnifiedRegimeEngine
)

logger = logging.getLogger(__name__)

# ================================================================================
# DATABASE UTILITIES
# ================================================================================

class DatabaseManager:
    """
    Enhanced database manager with connection pooling and retry logic
    Prevents database lock issues and provides resilient data access
    """
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self.connection_pool = queue.Queue(maxsize=pool_size)
        self._pool_lock = threading.Lock()
        
        # Initialize connection pool
        for _ in range(pool_size):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
            self.connection_pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        """Get connection with automatic return to pool"""
        conn = None
        try:
            conn = self.connection_pool.get(timeout=5.0)
            yield conn
        except queue.Empty:
            # Fallback to new connection if pool exhausted
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            yield conn
        finally:
            if conn:
                try:
                    self.connection_pool.put_nowait(conn)
                except queue.Full:
                    conn.close()  # Close if pool is full
    
    def execute_with_retry(self, query: str, params: tuple = (), max_retries: int = 3) -> Any:
        """Execute query with retry logic"""
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    result = cursor.execute(query, params)
                    conn.commit()
                    return result
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise e
            except Exception as e:
                logger.error(f"Database error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                raise e
    
    def fetch_with_retry(self, query: str, params: tuple = (), max_retries: int = 3) -> List[Any]:
        """Fetch data with retry logic"""
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    return cursor.fetchall()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise e
            except Exception as e:
                logger.error(f"Database fetch error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                raise e
    
    def close(self):
        """Close all connections in pool"""
        while not self.connection_pool.empty():
            try:
                conn = self.connection_pool.get_nowait()
                conn.close()
            except queue.Empty:
                break

# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class RegimePerformanceMetrics:
    """Tracks performance metrics for each regime"""
    regime_type: RegimeType
    total_duration: timedelta
    occurrence_count: int
    avg_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    avg_trade_duration: timedelta
    
@dataclass
class RegimeAlert:
    """Alert for significant regime events"""
    alert_id: str
    timestamp: datetime
    alert_type: str  # 'transition', 'stability_change', 'prediction', 'anomaly'
    severity: str  # 'info', 'warning', 'critical'
    message: str
    metadata: Dict[str, Any]

@dataclass 
class ABTestConfig:
    """Configuration for A/B testing regime adaptations"""
    test_id: str
    start_time: datetime
    end_time: Optional[datetime]
    control_params: Dict[str, Any]
    variant_params: Dict[str, Any]
    allocation_ratio: float  # Percentage allocated to variant
    metrics_to_track: List[str]
    
# ================================================================================
# REGIME MONITOR
# ================================================================================

class RegimeMonitor:
    """
    Production monitoring system for regime engine
    
    Features:
    - Real-time regime tracking
    - Performance analytics
    - Alert generation
    - Metric persistence
    - A/B testing support
    """
    
    def __init__(self, 
                 regime_engine: UnifiedRegimeEngine,
                 db_path: str = "regime_monitoring.db",
                 alert_callbacks: Optional[List] = None):
        """Initialize regime monitor"""
        self.regime_engine = regime_engine
        self.db_path = db_path
        self.alert_callbacks = alert_callbacks or []
        
        # Enhanced database management
        self.db_manager = DatabaseManager(db_path, pool_size=5)
        
        # Performance tracking
        self.regime_performance: Dict[RegimeType, RegimePerformanceMetrics] = {}
        self.transition_matrix: Dict[Tuple[RegimeType, RegimeType], int] = {}
        
        # Alert management
        self.active_alerts: List[RegimeAlert] = []
        self.alert_history: List[RegimeAlert] = []
        
        # A/B testing
        self.active_ab_tests: Dict[str, ABTestConfig] = {}
        self.ab_test_results: Dict[str, Dict[str, Any]] = {}
        
        # Monitoring state
        self._monitoring_active = False
        self._monitor_thread = None
        self._db_lock = threading.Lock()
        
        # Initialize database
        self._initialize_database()
        
        # Subscribe to regime changes
        regime_engine.subscribe_to_regime_changes(self)
        
        logger.info("📊 Regime Monitor initialized")
    
    def _initialize_database(self):
        """Create monitoring database tables with enhanced schema"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Regime states table with indexes
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS regime_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        symbol TEXT NOT NULL,
                        regime_type TEXT NOT NULL,
                        confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                        volatility REAL NOT NULL CHECK(volatility >= 0),
                        trend_strength REAL NOT NULL,
                        metadata TEXT,
                        UNIQUE(timestamp, symbol)
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_regime_timestamp ON regime_states(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_regime_symbol ON regime_states(symbol)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_regime_type ON regime_states(regime_type)")
                
                # Transitions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS regime_transitions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        from_regime TEXT NOT NULL,
                        to_regime TEXT NOT NULL,
                        confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                        triggers TEXT
                    )
                """)
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_transition_timestamp ON regime_transitions(timestamp)")
                
                # Performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        regime_type TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL
                    )
                """)
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp)")
                
                # Alerts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_id TEXT UNIQUE NOT NULL,
                        timestamp DATETIME NOT NULL,
                        alert_type TEXT NOT NULL,
                        severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'critical')),
                        message TEXT NOT NULL,
                        metadata TEXT
                    )
                """)
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)")
                
                # A/B test results table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ab_test_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        test_id TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        variant TEXT NOT NULL CHECK(variant IN ('control', 'variant')),
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL
                    )
                """)
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_abtest_test_id ON ab_test_results(test_id)")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def on_regime_change(self, 
                             old_regime: RegimeState, 
                             new_regime: RegimeState,
                             transition: RegimeTransition) -> None:
        """Handle regime change notifications"""
        # Log transition
        self._log_transition(transition)
        
        # Update transition matrix
        key = (old_regime.primary_regime, new_regime.primary_regime)
        self.transition_matrix[key] = self.transition_matrix.get(key, 0) + 1
        
        # Generate alerts if needed
        await self._check_transition_alerts(old_regime, new_regime, transition)
        
        # Update performance metrics
        self._update_performance_metrics(new_regime)
    
    def get_subscriber_id(self) -> str:
        """Get unique subscriber identifier"""
        return "regime_monitor"
    
    def start_monitoring(self, update_interval: int = 60):
        """Start background monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(update_interval,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("🚀 Regime monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("🛑 Regime monitoring stopped")
    
    def _monitoring_loop(self, update_interval: int):
        """Background monitoring loop"""
        while self._monitoring_active:
            try:
                # Collect current metrics
                self._collect_regime_metrics()
                
                # Check for anomalies
                self._detect_regime_anomalies()
                
                # Update A/B test results
                self._update_ab_test_results()
                
                # Persist metrics
                self._persist_current_state()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Sleep for update interval
            threading.Event().wait(update_interval)
    
    def _collect_regime_metrics(self):
        """Collect current regime metrics with enhanced error handling"""
        try:
            current_regime = self.regime_engine.get_current_regime()
            if not current_regime:
                return
            
            # Get engine performance metrics
            perf_metrics = self.regime_engine.get_performance_metrics()
            
            # Store current state with retry logic
            self.db_manager.execute_with_retry("""
                INSERT OR REPLACE INTO regime_states 
                (timestamp, symbol, regime_type, confidence, volatility, trend_strength, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(),
                "aggregate",  # Could be per-symbol
                current_regime.primary_regime.value,
                current_regime.confidence,
                current_regime.market_volatility,
                current_regime.trend_strength,
                json.dumps(current_regime.to_dict())
            ))
            
            # Store performance metrics
            for metric_name, metric_value in perf_metrics.items():
                if isinstance(metric_value, (int, float)):
                    self.db_manager.execute_with_retry("""
                        INSERT INTO performance_metrics
                        (timestamp, regime_type, metric_name, metric_value)
                        VALUES (?, ?, ?, ?)
                    """, (
                        datetime.now(),
                        current_regime.primary_regime.value,
                        metric_name,
                        metric_value
                    ))
                    
        except Exception as e:
            logger.error(f"Error collecting regime metrics: {e}")
    
    def _detect_regime_anomalies(self):
        """Detect anomalous regime behavior"""
        # Check for rapid regime changes
        recent_transitions = self._get_recent_transitions(minutes=60)
        if len(recent_transitions) > 5:
            self._create_alert(
                alert_type="anomaly",
                severity="warning",
                message=f"Rapid regime changes detected: {len(recent_transitions)} in last hour",
                metadata={"transition_count": len(recent_transitions)}
            )
        
        # Check for low confidence regimes
        current_regime = self.regime_engine.get_current_regime()
        if current_regime and current_regime.confidence < 0.3:
            self._create_alert(
                alert_type="anomaly", 
                severity="warning",
                message=f"Low regime confidence: {current_regime.confidence:.2%}",
                metadata={"regime": current_regime.primary_regime.value}
            )
    
    async def _check_transition_alerts(self, 
                                     old_regime: RegimeState,
                                     new_regime: RegimeState,
                                     transition: RegimeTransition):
        """Check if transition warrants an alert"""
        # Alert on significant regime changes
        significant_regimes = [RegimeType.CRISIS, RegimeType.HIGH_VOLATILITY]
        
        if new_regime.primary_regime in significant_regimes:
            severity = "critical" if new_regime.primary_regime == RegimeType.CRISIS else "warning"
            
            self._create_alert(
                alert_type="transition",
                severity=severity,
                message=f"Transitioned to {new_regime.primary_regime.value} regime",
                metadata={
                    "from_regime": old_regime.primary_regime.value,
                    "confidence": new_regime.confidence,
                    "triggers": transition.transition_triggers
                }
            )
    
    def _create_alert(self, alert_type: str, severity: str, 
                     message: str, metadata: Dict[str, Any]):
        """Create and store alert"""
        alert = RegimeAlert(
            alert_id=f"{alert_type}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata=metadata
        )
        
        # Add to active alerts
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        
        # Store in database
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO alerts
                (alert_id, timestamp, alert_type, severity, message, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.timestamp,
                alert.alert_type,
                alert.severity,
                alert.message,
                json.dumps(alert.metadata)
            ))
            
            conn.commit()
            conn.close()
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        logger.warning(f"🚨 Alert: {message}")
    
    def _log_transition(self, transition: RegimeTransition):
        """Log regime transition to database"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO regime_transitions
                (timestamp, from_regime, to_regime, confidence, triggers)
                VALUES (?, ?, ?, ?, ?)
            """, (
                transition.transition_time,
                transition.from_regime.value,
                transition.to_regime.value,
                transition.transition_confidence,
                json.dumps(transition.transition_triggers)
            ))
            
            conn.commit()
            conn.close()
    
    def _get_recent_transitions(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent regime transitions"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            cursor.execute("""
                SELECT * FROM regime_transitions
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff_time,))
            
            transitions = cursor.fetchall()
            conn.close()
            
            return transitions
    
    def _update_performance_metrics(self, regime: RegimeState):
        """Update regime performance metrics"""
        # This would integrate with actual trading performance
        # For now, we'll store regime characteristics
        pass
    
    def _persist_current_state(self):
        """Persist current monitoring state"""
        # Already handled in _collect_regime_metrics
        pass
    
    # ================================================================================
    # A/B TESTING
    # ================================================================================
    
    def start_ab_test(self, test_config: ABTestConfig):
        """Start A/B test for regime adaptations"""
        self.active_ab_tests[test_config.test_id] = test_config
        logger.info(f"🧪 Started A/B test: {test_config.test_id}")
    
    def stop_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Stop A/B test and return results"""
        if test_id not in self.active_ab_tests:
            return {}
        
        test_config = self.active_ab_tests.pop(test_id)
        test_config.end_time = datetime.now()
        
        # Analyze results
        results = self._analyze_ab_test_results(test_config)
        self.ab_test_results[test_id] = results
        
        logger.info(f"🏁 Completed A/B test: {test_id}")
        return results
    
    def _update_ab_test_results(self):
        """Update results for active A/B tests"""
        for test_id, config in self.active_ab_tests.items():
            # This would collect actual performance metrics
            # For demonstration, we'll generate synthetic metrics
            
            # Random assignment to control/variant
            variant = "variant" if np.random.random() < config.allocation_ratio else "control"
            
            # Generate synthetic metrics
            for metric in config.metrics_to_track:
                value = np.random.normal(1.0, 0.1)  # Placeholder
                
                with self._db_lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT INTO ab_test_results
                        (test_id, timestamp, variant, metric_name, metric_value)
                        VALUES (?, ?, ?, ?, ?)
                    """, (test_id, datetime.now(), variant, metric, value))
                    
                    conn.commit()
                    conn.close()
    
    def _analyze_ab_test_results(self, test_config: ABTestConfig) -> Dict[str, Any]:
        """Analyze A/B test results"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Get results for this test
            df = pd.read_sql_query("""
                SELECT * FROM ab_test_results
                WHERE test_id = ?
            """, conn, params=[test_config.test_id])
            
            conn.close()
        
        if df.empty:
            return {"status": "no_data"}
        
        results = {"test_id": test_config.test_id}
        
        # Analyze each metric
        for metric in test_config.metrics_to_track:
            metric_df = df[df['metric_name'] == metric]
            
            control_values = metric_df[metric_df['variant'] == 'control']['metric_value']
            variant_values = metric_df[metric_df['variant'] == 'variant']['metric_value']
            
            if len(control_values) > 0 and len(variant_values) > 0:
                # Calculate statistics
                control_mean = control_values.mean()
                variant_mean = variant_values.mean()
                improvement = (variant_mean - control_mean) / control_mean
                
                # Simple t-test (in production, use proper statistical tests)
                from scipy import stats
                t_stat, p_value = stats.ttest_ind(control_values, variant_values)
                
                results[metric] = {
                    "control_mean": control_mean,
                    "variant_mean": variant_mean,
                    "improvement": improvement,
                    "p_value": p_value,
                    "significant": p_value < 0.05
                }
        
        return results
    
    # ================================================================================
    # ANALYTICS AND REPORTING
    # ================================================================================
    
    def get_regime_statistics(self, 
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive regime statistics"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Build query
            query = "SELECT * FROM regime_states"
            params = []
            
            if start_date or end_date:
                query += " WHERE"
                if start_date:
                    query += " timestamp >= ?"
                    params.append(start_date)
                if start_date and end_date:
                    query += " AND"
                if end_date:
                    query += " timestamp <= ?"
                    params.append(end_date)
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
        
        if df.empty:
            return {}
        
        # Calculate statistics
        stats = {
            "total_observations": len(df),
            "date_range": {
                "start": df['timestamp'].min(),
                "end": df['timestamp'].max()
            },
            "regime_distribution": df['regime_type'].value_counts().to_dict(),
            "avg_confidence": df['confidence'].mean(),
            "confidence_std": df['confidence'].std(),
            "regime_durations": self._calculate_regime_durations(df),
            "transition_matrix": self._get_transition_matrix()
        }
        
        return stats
    
    def _calculate_regime_durations(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate average duration for each regime"""
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        durations = {}
        current_regime = None
        start_time = None
        
        for _, row in df.iterrows():
            if row['regime_type'] != current_regime:
                if current_regime and start_time:
                    duration = (row['timestamp'] - start_time).total_seconds() / 60
                    if current_regime not in durations:
                        durations[current_regime] = []
                    durations[current_regime].append(duration)
                
                current_regime = row['regime_type']
                start_time = row['timestamp']
        
        # Calculate averages
        avg_durations = {
            regime: np.mean(dur_list) 
            for regime, dur_list in durations.items()
        }
        
        return avg_durations
    
    def _get_transition_matrix(self) -> Dict[str, Dict[str, float]]:
        """Get regime transition probability matrix"""
        matrix = {}
        
        # Convert counts to probabilities
        total_transitions = {}
        for (from_regime, to_regime), count in self.transition_matrix.items():
            from_str = from_regime.value
            to_str = to_regime.value
            
            if from_str not in matrix:
                matrix[from_str] = {}
                total_transitions[from_str] = 0
            
            matrix[from_str][to_str] = count
            total_transitions[from_str] += count
        
        # Normalize to probabilities
        for from_regime in matrix:
            total = total_transitions[from_regime]
            if total > 0:
                for to_regime in matrix[from_regime]:
                    matrix[from_regime][to_regime] /= total
        
        return matrix
    
    def export_monitoring_data(self, 
                             output_path: str,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None):
        """Export monitoring data for analysis"""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Export regime states
            query = "SELECT * FROM regime_states"
            params = []
            
            if start_date:
                query += " WHERE timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?" if start_date else " WHERE timestamp <= ?"
                params.append(end_date)
            
            regime_df = pd.read_sql_query(query, conn, params=params)
            
            # Export transitions
            transitions_df = pd.read_sql_query(
                "SELECT * FROM regime_transitions", conn
            )
            
            # Export alerts
            alerts_df = pd.read_sql_query(
                "SELECT * FROM alerts", conn
            )
            
            conn.close()
        
        # Save to files
        output_dir = Path(output_path)
        output_dir.mkdir(exist_ok=True)
        
        regime_df.to_csv(output_dir / "regime_states.csv", index=False)
        transitions_df.to_csv(output_dir / "regime_transitions.csv", index=False)
        alerts_df.to_csv(output_dir / "regime_alerts.csv", index=False)
        
        # Save statistics
        stats = self.get_regime_statistics(start_date, end_date)
        with open(output_dir / "regime_statistics.json", 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        logger.info(f"📁 Exported monitoring data to {output_path}")

# ================================================================================
# REGIME DASHBOARD DATA PROVIDER
# ================================================================================

class RegimeDashboardDataProvider:
    """Provides real-time data for regime monitoring dashboard"""
    
    def __init__(self, monitor: RegimeMonitor):
        self.monitor = monitor
        self.regime_engine = monitor.regime_engine
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current regime state for dashboard"""
        current_regime = self.regime_engine.get_current_regime()
        
        if not current_regime:
            return {"status": "no_regime"}
        
        # Get recent performance
        recent_metrics = self.regime_engine.get_performance_metrics()
        
        # Get active alerts
        active_alerts = [
            {
                "id": alert.alert_id,
                "time": alert.timestamp.isoformat(),
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message
            }
            for alert in self.monitor.active_alerts[-10:]  # Last 10 alerts
        ]
        
        return {
            "current_regime": {
                "type": current_regime.primary_regime.value,
                "confidence": current_regime.confidence,
                "volatility": current_regime.market_volatility,
                "trend": current_regime.trend_strength,
                "duration": current_regime.regime_duration.total_seconds() / 60  # minutes
            },
            "performance_metrics": recent_metrics,
            "active_alerts": active_alerts,
            "multi_timeframe": {
                tf: state.primary_regime.value 
                for tf, state in self.regime_engine.multi_timeframe_states.items()
            },
            "stability_scores": self.regime_engine.regime_stability_scores
        }
    
    def get_historical_data(self, hours: int = 24) -> Dict[str, Any]:
        """Get historical regime data for charts"""
        start_date = datetime.now() - timedelta(hours=hours)
        
        with self.monitor._db_lock:
            conn = sqlite3.connect(self.monitor.db_path)
            
            # Get regime history
            regime_df = pd.read_sql_query("""
                SELECT timestamp, regime_type, confidence, volatility
                FROM regime_states
                WHERE timestamp > ?
                ORDER BY timestamp
            """, conn, params=[start_date])
            
            # Get transitions
            transition_df = pd.read_sql_query("""
                SELECT timestamp, from_regime, to_regime
                FROM regime_transitions
                WHERE timestamp > ?
                ORDER BY timestamp
            """, conn, params=[start_date])
            
            conn.close()
        
        return {
            "regime_history": regime_df.to_dict('records'),
            "transitions": transition_df.to_dict('records')
        }
    
    def get_ab_test_status(self) -> List[Dict[str, Any]]:
        """Get status of active A/B tests"""
        return [
            {
                "test_id": test.test_id,
                "start_time": test.start_time.isoformat(),
                "allocation_ratio": test.allocation_ratio,
                "metrics": test.metrics_to_track
            }
            for test in self.monitor.active_ab_tests.values()
        ]

# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_regime_monitor(regime_engine: UnifiedRegimeEngine,
                        db_path: str = "regime_monitoring.db",
                        alert_callbacks: Optional[List] = None) -> RegimeMonitor:
    """Create and configure regime monitor"""
    monitor = RegimeMonitor(regime_engine, db_path, alert_callbacks)
    
    # Start monitoring
    monitor.start_monitoring()
    
    return monitor

def create_dashboard_provider(monitor: RegimeMonitor) -> RegimeDashboardDataProvider:
    """Create dashboard data provider"""
    return RegimeDashboardDataProvider(monitor)
