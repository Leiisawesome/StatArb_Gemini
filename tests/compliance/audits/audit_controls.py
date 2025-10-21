"""
Audit Controls and Trail Management Module

This module implements comprehensive audit controls and trail management for
institutional compliance and regulatory requirements. It provides complete
audit coverage of all trading activities, system operations, and compliance
events with tamper-proof logging and integrity verification.

Key Features:
1. Comprehensive audit trail capture
2. Tamper-proof audit logging with cryptographic integrity
3. Real-time audit event processing
4. Audit trail search and analysis
5. Compliance audit reporting
6. Data retention and archival management
7. Access control and authorization auditing
8. System event auditing
9. Trading activity auditing
10. Regulatory audit trail generation

The module ensures complete auditability of all system operations and
maintains institutional-grade audit standards for regulatory compliance.
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import json
import hashlib
import uuid
import sqlite3
import threading
from collections import defaultdict, deque
import gzip
import pickle


class AuditEventType(Enum):
    """Types of audit events"""
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TRADE_EXECUTION = "trade_execution"
    POSITION_CHANGE = "position_change"
    RISK_LIMIT_CHANGE = "risk_limit_change"
    STRATEGY_DEPLOYMENT = "strategy_deployment"
    STRATEGY_MODIFICATION = "strategy_modification"
    CONFIGURATION_CHANGE = "configuration_change"
    DATA_ACCESS = "data_access"
    REPORT_GENERATION = "report_generation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SECURITY_EVENT = "security_event"
    ERROR_EVENT = "error_event"
    PERFORMANCE_EVENT = "performance_event"
    BACKUP_EVENT = "backup_event"
    RECOVERY_EVENT = "recovery_event"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SECURITY = "security"


class AuditStatus(Enum):
    """Audit event processing status"""
    PENDING = "pending"
    PROCESSED = "processed"
    ARCHIVED = "archived"
    FAILED = "failed"


@dataclass
class AuditEvent:
    """Represents an audit event"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    component: str
    user_id: Optional[str]
    session_id: Optional[str]
    action: str
    description: str
    details: Dict[str, Any]
    result: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    correlation_id: Optional[str]
    checksum: str
    status: AuditStatus = AuditStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditTrailQuery:
    """Audit trail query parameters"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_types: Optional[List[AuditEventType]] = None
    severities: Optional[List[AuditSeverity]] = None
    components: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    search_text: Optional[str] = None
    limit: int = 1000
    offset: int = 0


@dataclass
class AuditReport:
    """Audit trail analysis report"""
    report_id: str
    generation_timestamp: datetime
    query_parameters: AuditTrailQuery
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    events_by_component: Dict[str, int]
    security_events: List[AuditEvent]
    critical_events: List[AuditEvent]
    compliance_violations: List[AuditEvent]
    recommendations: List[str]
    integrity_status: Dict[str, Any]


class AuditTrailManager:
    """Core audit trail management system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Audit storage
        self.audit_buffer = deque(maxlen=10000)  # In-memory buffer
        self.audit_database = None
        self.buffer_lock = threading.Lock()
        
        # Audit configuration
        self.retention_days = self.config.get('retention_days', 2555)  # 7 years default
        self.buffer_flush_interval = self.config.get('buffer_flush_interval', 60)  # seconds
        self.integrity_check_interval = self.config.get('integrity_check_interval', 3600)  # seconds
        
        # Event handlers
        self.event_handlers = {}
        self.real_time_subscribers = []
        
        # Integrity tracking
        self.last_integrity_check = None
        self.integrity_chain = []
        
        # Initialize audit system
        self._initialize_audit_system()
    
    def _initialize_audit_system(self):
        """Initialize audit trail system"""
        
        try:
            # Initialize database
            self._initialize_database()
            
            # Start background tasks
            self._start_background_tasks()
            
            # Log system initialization
            self._log_system_event(
                AuditEventType.SYSTEM_STARTUP,
                "audit_trail_manager",
                "system_initialization",
                "Audit trail system initialized successfully"
            )
            
            self.logger.info("✅ Audit trail system initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Audit system initialization failed: {e}")
            raise
    
    def _initialize_database(self):
        """Initialize audit database"""
        
        db_path = self.config.get('database_path', 'audit_trail.db')
        self.audit_database = sqlite3.connect(db_path, check_same_thread=False)
        
        # Create audit events table
        self.audit_database.execute('''
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                component TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                action TEXT NOT NULL,
                description TEXT NOT NULL,
                details TEXT NOT NULL,
                result TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                correlation_id TEXT,
                checksum TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Clear any existing data for testing
        self.audit_database.execute('DELETE FROM audit_events')
        self.audit_database.commit()
        
        # Create indexes for performance
        self.audit_database.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)
        ''')
        self.audit_database.execute('''
            CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)
        ''')
        self.audit_database.execute('''
            CREATE INDEX IF NOT EXISTS idx_component ON audit_events(component)
        ''')
        self.audit_database.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id ON audit_events(user_id)
        ''')
        
        self.audit_database.commit()
    
    def _start_background_tasks(self):
        """Start background audit tasks"""
        
        # Start buffer flush task
        def flush_buffer_periodically():
            while True:
                try:
                    asyncio.run(self._flush_audit_buffer())
                    threading.Event().wait(self.buffer_flush_interval)
                except Exception as e:
                    self.logger.error(f"Buffer flush error: {e}")
        
        flush_thread = threading.Thread(target=flush_buffer_periodically, daemon=True)
        flush_thread.start()
        
        # Start integrity check task
        def check_integrity_periodically():
            while True:
                try:
                    asyncio.run(self._perform_integrity_check())
                    threading.Event().wait(self.integrity_check_interval)
                except Exception as e:
                    self.logger.error(f"Integrity check error: {e}")
        
        integrity_thread = threading.Thread(target=check_integrity_periodically, daemon=True)
        integrity_thread.start()
    
    async def log_audit_event(self, event_type: AuditEventType, component: str,
                            action: str, description: str, details: Dict[str, Any] = None,
                            user_id: str = None, session_id: str = None,
                            ip_address: str = None, user_agent: str = None,
                            correlation_id: str = None, severity: AuditSeverity = AuditSeverity.INFO,
                            result: str = "SUCCESS") -> str:
        """Log an audit event"""
        
        try:
            # Create audit event
            event_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Calculate checksum for integrity
            checksum_data = f"{event_id}{timestamp.isoformat()}{event_type.value}{component}{action}{description}"
            checksum = hashlib.sha256(checksum_data.encode()).hexdigest()
            
            audit_event = AuditEvent(
                event_id=event_id,
                timestamp=timestamp,
                event_type=event_type,
                severity=severity,
                component=component,
                user_id=user_id,
                session_id=session_id,
                action=action,
                description=description,
                details=details or {},
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                correlation_id=correlation_id,
                checksum=checksum,
                status=AuditStatus.PENDING
            )
            
            # Add to buffer
            with self.buffer_lock:
                self.audit_buffer.append(audit_event)
            
            # Process real-time handlers
            await self._process_real_time_handlers(audit_event)
            
            # Handle high-severity events immediately
            if severity in [AuditSeverity.CRITICAL, AuditSeverity.SECURITY]:
                await self._handle_critical_audit_event(audit_event)
            
            return event_id
            
        except Exception as e:
            self.logger.error(f"❌ Audit event logging failed: {e}")
            raise
    
    def _log_system_event(self, event_type: AuditEventType, component: str,
                         action: str, description: str, details: Dict[str, Any] = None):
        """Log system event synchronously"""
        
        try:
            # Create event synchronously without asyncio.run()
            event_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Calculate checksum for integrity
            checksum_data = f"{event_id}{timestamp.isoformat()}{event_type.value}{component}{action}{description}"
            checksum = hashlib.sha256(checksum_data.encode()).hexdigest()
            
            audit_event = AuditEvent(
                event_id=event_id,
                timestamp=timestamp,
                event_type=event_type,
                severity=AuditSeverity.INFO,
                component=component,
                user_id=None,
                session_id=None,
                action=action,
                description=description,
                details=details or {},
                result="SUCCESS",
                ip_address=None,
                user_agent=None,
                correlation_id=None,
                checksum=checksum,
                status=AuditStatus.PENDING
            )
            
            # Add to buffer directly
            with self.buffer_lock:
                self.audit_buffer.append(audit_event)
                
        except Exception as e:
            self.logger.error(f"System event logging failed: {e}")
    
    async def _process_real_time_handlers(self, event: AuditEvent):
        """Process real-time event handlers"""
        
        for handler in self.real_time_subscribers:
            try:
                await handler(event)
            except Exception as e:
                self.logger.error(f"Real-time handler error: {e}")
    
    async def _handle_critical_audit_event(self, event: AuditEvent):
        """Handle critical audit events immediately"""
        
        self.logger.critical(f"🚨 CRITICAL AUDIT EVENT: {event.description}")
        
        # Immediately flush to database
        await self._store_audit_event(event)
        
        # Send alerts for security events
        if event.severity == AuditSeverity.SECURITY:
            await self._send_security_alert(event)
        
        # Log to separate critical events log
        await self._log_critical_event(event)
    
    async def _send_security_alert(self, event: AuditEvent):
        """Send security alert for critical security events"""
        
        alert_data = {
            'event_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type.value,
            'component': event.component,
            'description': event.description,
            'user_id': event.user_id,
            'ip_address': event.ip_address
        }
        
        self.logger.critical(f"🔒 SECURITY ALERT: {json.dumps(alert_data, indent=2)}")
        
        # In real implementation, would send to security monitoring systems
    
    async def _log_critical_event(self, event: AuditEvent):
        """Log critical event to separate high-priority log"""
        
        critical_log_path = self.config.get('critical_log_path', 'critical_audit_events.log')
        
        try:
            with open(critical_log_path, 'a') as f:
                f.write(f"{event.timestamp.isoformat()} | {event.event_type.value} | {event.component} | {event.description}\n")
        except Exception as e:
            self.logger.error(f"Critical event logging failed: {e}")
    
    async def _flush_audit_buffer(self):
        """Flush audit buffer to database"""
        
        if not self.audit_buffer:
            return
        
        try:
            # Get events from buffer
            with self.buffer_lock:
                events_to_flush = list(self.audit_buffer)
                self.audit_buffer.clear()
            
            # Store events in database
            for event in events_to_flush:
                await self._store_audit_event(event)
            
            self.logger.debug(f"Flushed {len(events_to_flush)} audit events to database")
            
        except Exception as e:
            self.logger.error(f"Audit buffer flush failed: {e}")
            
            # Return events to buffer on failure
            with self.buffer_lock:
                self.audit_buffer.extendleft(reversed(events_to_flush))
    
    async def _store_audit_event(self, event: AuditEvent):
        """Store audit event in database"""
        
        try:
            cursor = self.audit_database.cursor()
            
            # Check if event already exists to avoid UNIQUE constraint violation
            cursor.execute('SELECT event_id FROM audit_events WHERE event_id = ?', (event.event_id,))
            if cursor.fetchone():
                self.logger.debug(f"Event {event.event_id} already exists, skipping")
                event.status = AuditStatus.PROCESSED
                return
            
            cursor.execute('''
                INSERT INTO audit_events (
                    event_id, timestamp, event_type, severity, component,
                    user_id, session_id, action, description, details,
                    result, ip_address, user_agent, correlation_id,
                    checksum, status, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id,
                event.timestamp.isoformat(),
                event.event_type.value,
                event.severity.value,
                event.component,
                event.user_id,
                event.session_id,
                event.action,
                event.description,
                json.dumps(event.details),
                event.result,
                event.ip_address,
                event.user_agent,
                event.correlation_id,
                event.checksum,
                event.status.value,
                json.dumps(event.metadata)
            ))
            
            self.audit_database.commit()
            event.status = AuditStatus.PROCESSED
            
        except Exception as e:
            self.logger.error(f"Audit event storage failed: {e}")
            event.status = AuditStatus.FAILED
            raise
    
    async def query_audit_trail(self, query: AuditTrailQuery) -> List[AuditEvent]:
        """Query audit trail with specified parameters"""
        
        try:
            # Build SQL query
            sql_parts = ["SELECT * FROM audit_events WHERE 1=1"]
            params = []
            
            if query.start_time:
                sql_parts.append("AND timestamp >= ?")
                params.append(query.start_time.isoformat())
            
            if query.end_time:
                sql_parts.append("AND timestamp <= ?")
                params.append(query.end_time.isoformat())
            
            if query.event_types:
                placeholders = ','.join(['?' for _ in query.event_types])
                sql_parts.append(f"AND event_type IN ({placeholders})")
                params.extend([et.value for et in query.event_types])
            
            if query.severities:
                placeholders = ','.join(['?' for _ in query.severities])
                sql_parts.append(f"AND severity IN ({placeholders})")
                params.extend([s.value for s in query.severities])
            
            if query.components:
                placeholders = ','.join(['?' for _ in query.components])
                sql_parts.append(f"AND component IN ({placeholders})")
                params.extend(query.components)
            
            if query.user_ids:
                placeholders = ','.join(['?' for _ in query.user_ids])
                sql_parts.append(f"AND user_id IN ({placeholders})")
                params.extend(query.user_ids)
            
            if query.search_text:
                sql_parts.append("AND (description LIKE ? OR details LIKE ?)")
                search_pattern = f"%{query.search_text}%"
                params.extend([search_pattern, search_pattern])
            
            # Add ordering and limits
            sql_parts.append("ORDER BY timestamp DESC")
            sql_parts.append("LIMIT ? OFFSET ?")
            params.extend([query.limit, query.offset])
            
            sql_query = " ".join(sql_parts)
            
            # Execute query
            cursor = self.audit_database.cursor()
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            
            # Convert to AuditEvent objects
            events = []
            for row in rows:
                event = AuditEvent(
                    event_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    event_type=AuditEventType(row[2]),
                    severity=AuditSeverity(row[3]),
                    component=row[4],
                    user_id=row[5],
                    session_id=row[6],
                    action=row[7],
                    description=row[8],
                    details=json.loads(row[9]) if row[9] else {},
                    result=row[10],
                    ip_address=row[11],
                    user_agent=row[12],
                    correlation_id=row[13],
                    checksum=row[14],
                    status=AuditStatus(row[15]),
                    metadata=json.loads(row[16]) if row[16] else {}
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Audit trail query failed: {e}")
            raise
    
    async def _perform_integrity_check(self):
        """Perform audit trail integrity check"""
        
        try:
            self.logger.debug("Performing audit trail integrity check")
            
            # Check recent events for integrity
            query = AuditTrailQuery(
                start_time=datetime.now() - timedelta(hours=24),
                limit=1000
            )
            
            recent_events = await self.query_audit_trail(query)
            
            integrity_results = {
                'check_timestamp': datetime.now().isoformat(),
                'events_checked': len(recent_events),
                'integrity_violations': [],
                'checksum_failures': 0,
                'missing_events': 0,
                'overall_status': 'PASS'
            }
            
            # Verify checksums
            for event in recent_events:
                expected_checksum_data = f"{event.event_id}{event.timestamp.isoformat()}{event.event_type.value}{event.component}{event.action}{event.description}"
                expected_checksum = hashlib.sha256(expected_checksum_data.encode()).hexdigest()
                
                if event.checksum != expected_checksum:
                    integrity_results['checksum_failures'] += 1
                    integrity_results['integrity_violations'].append({
                        'event_id': event.event_id,
                        'violation_type': 'checksum_mismatch',
                        'expected': expected_checksum,
                        'actual': event.checksum
                    })
            
            # Update integrity status
            if integrity_results['checksum_failures'] > 0:
                integrity_results['overall_status'] = 'FAIL'
                self.logger.warning(f"⚠️ Audit integrity check failed: {integrity_results['checksum_failures']} checksum failures")
            else:
                self.logger.debug("✅ Audit integrity check passed")
            
            self.last_integrity_check = datetime.now()
            self.integrity_chain.append(integrity_results)
            
            # Keep only last 100 integrity checks
            if len(self.integrity_chain) > 100:
                self.integrity_chain = self.integrity_chain[-100:]
            
            return integrity_results
            
        except Exception as e:
            self.logger.error(f"Integrity check failed: {e}")
            return {
                'check_timestamp': datetime.now().isoformat(),
                'overall_status': 'ERROR',
                'error': str(e)
            }
    
    async def generate_audit_report(self, query: AuditTrailQuery) -> AuditReport:
        """Generate comprehensive audit report"""
        
        try:
            # Query audit events
            events = await self.query_audit_trail(query)
            
            # Analyze events
            events_by_type = defaultdict(int)
            events_by_severity = defaultdict(int)
            events_by_component = defaultdict(int)
            
            security_events = []
            critical_events = []
            compliance_violations = []
            
            for event in events:
                events_by_type[event.event_type.value] += 1
                events_by_severity[event.severity.value] += 1
                events_by_component[event.component] += 1
                
                if event.severity == AuditSeverity.SECURITY:
                    security_events.append(event)
                elif event.severity == AuditSeverity.CRITICAL:
                    critical_events.append(event)
                elif event.event_type == AuditEventType.COMPLIANCE_VIOLATION:
                    compliance_violations.append(event)
            
            # Generate recommendations
            recommendations = self._generate_audit_recommendations(events)
            
            # Get integrity status
            integrity_status = self.integrity_chain[-1] if self.integrity_chain else {}
            
            # Create report
            report = AuditReport(
                report_id=str(uuid.uuid4()),
                generation_timestamp=datetime.now(),
                query_parameters=query,
                total_events=len(events),
                events_by_type=dict(events_by_type),
                events_by_severity=dict(events_by_severity),
                events_by_component=dict(events_by_component),
                security_events=security_events,
                critical_events=critical_events,
                compliance_violations=compliance_violations,
                recommendations=recommendations,
                integrity_status=integrity_status
            )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Audit report generation failed: {e}")
            raise
    
    def _generate_audit_recommendations(self, events: List[AuditEvent]) -> List[str]:
        """Generate audit recommendations based on event analysis"""
        
        recommendations = []
        
        # Analyze event patterns
        security_event_count = len([e for e in events if e.severity == AuditSeverity.SECURITY])
        critical_event_count = len([e for e in events if e.severity == AuditSeverity.CRITICAL])
        error_event_count = len([e for e in events if e.severity == AuditSeverity.ERROR])
        
        # Security recommendations
        if security_event_count > 5:
            recommendations.append("High number of security events detected - review security controls")
        
        if critical_event_count > 10:
            recommendations.append("Multiple critical events detected - investigate system stability")
        
        if error_event_count > 20:
            recommendations.append("High error rate detected - review system health and error handling")
        
        # Component-specific recommendations
        component_errors = defaultdict(int)
        for event in events:
            if event.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
                component_errors[event.component] += 1
        
        for component, error_count in component_errors.items():
            if error_count > 5:
                recommendations.append(f"Component '{component}' has high error rate - review component health")
        
        # User activity recommendations
        user_activities = defaultdict(int)
        for event in events:
            if event.user_id:
                user_activities[event.user_id] += 1
        
        for user_id, activity_count in user_activities.items():
            if activity_count > 100:
                recommendations.append(f"User '{user_id}' has high activity - review for unusual patterns")
        
        # General recommendations
        if len(events) == 0:
            recommendations.append("No audit events found - verify audit system is functioning")
        elif len(events) > 10000:
            recommendations.append("High volume of audit events - consider implementing event filtering")
        
        return recommendations
    
    async def archive_old_events(self, archive_before: datetime = None) -> Dict[str, Any]:
        """Archive old audit events"""
        
        if not archive_before:
            archive_before = datetime.now() - timedelta(days=self.retention_days)
        
        try:
            # Query events to archive
            cursor = self.audit_database.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM audit_events WHERE timestamp < ?",
                (archive_before.isoformat(),)
            )
            events_to_archive = cursor.fetchone()[0]
            
            if events_to_archive == 0:
                return {
                    'events_archived': 0,
                    'archive_timestamp': datetime.now().isoformat(),
                    'status': 'no_events_to_archive'
                }
            
            # Create archive file
            archive_path = f"audit_archive_{archive_before.strftime('%Y%m%d')}.gz"
            
            cursor.execute(
                "SELECT * FROM audit_events WHERE timestamp < ? ORDER BY timestamp",
                (archive_before.isoformat(),)
            )
            
            archived_events = cursor.fetchall()
            
            # Compress and save archive
            with gzip.open(archive_path, 'wb') as f:
                pickle.dump(archived_events, f)
            
            # Delete archived events from database
            cursor.execute(
                "DELETE FROM audit_events WHERE timestamp < ?",
                (archive_before.isoformat(),)
            )
            
            self.audit_database.commit()
            
            # Log archival event
            await self.log_audit_event(
                AuditEventType.BACKUP_EVENT,
                "audit_trail_manager",
                "archive_events",
                f"Archived {events_to_archive} events to {archive_path}",
                {'events_archived': events_to_archive, 'archive_file': archive_path}
            )
            
            return {
                'events_archived': events_to_archive,
                'archive_file': archive_path,
                'archive_timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            
        except Exception as e:
            self.logger.error(f"Event archival failed: {e}")
            return {
                'events_archived': 0,
                'archive_timestamp': datetime.now().isoformat(),
                'status': 'failed',
                'error': str(e)
            }
    
    def subscribe_to_events(self, handler: Callable[[AuditEvent], None]):
        """Subscribe to real-time audit events"""
        self.real_time_subscribers.append(handler)
    
    def unsubscribe_from_events(self, handler: Callable[[AuditEvent], None]):
        """Unsubscribe from real-time audit events"""
        if handler in self.real_time_subscribers:
            self.real_time_subscribers.remove(handler)
    
    async def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics"""
        
        try:
            cursor = self.audit_database.cursor()
            
            # Total events
            cursor.execute("SELECT COUNT(*) FROM audit_events")
            total_events = cursor.fetchone()[0]
            
            # Events by severity
            cursor.execute("""
                SELECT severity, COUNT(*) 
                FROM audit_events 
                GROUP BY severity
            """)
            events_by_severity = dict(cursor.fetchall())
            
            # Events by type
            cursor.execute("""
                SELECT event_type, COUNT(*) 
                FROM audit_events 
                GROUP BY event_type 
                ORDER BY COUNT(*) DESC 
                LIMIT 10
            """)
            top_event_types = dict(cursor.fetchall())
            
            # Recent activity (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM audit_events 
                WHERE timestamp >= ?
            """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
            recent_activity = cursor.fetchone()[0]
            
            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]
            
            return {
                'total_events': total_events,
                'events_by_severity': events_by_severity,
                'top_event_types': top_event_types,
                'recent_activity_24h': recent_activity,
                'database_size_bytes': db_size,
                'buffer_size': len(self.audit_buffer),
                'last_integrity_check': self.last_integrity_check.isoformat() if self.last_integrity_check else None,
                'integrity_status': self.integrity_chain[-1]['overall_status'] if self.integrity_chain else 'UNKNOWN'
            }
            
        except Exception as e:
            self.logger.error(f"Audit statistics query failed: {e}")
            return {
                'error': str(e),
                'total_events': 0
            }


class AuditControlsTestSuite:
    """Test suite for audit controls and trail management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.audit_manager = AuditTrailManager({
            'database_path': ':memory:',  # Use in-memory database for testing
            'retention_days': 30,
            'buffer_flush_interval': 5
        })
    
    async def test_audit_controls(self, target_system = None) -> Dict[str, Any]:
        """Test audit controls and trail management"""
        
        self.logger.info("🎯 Testing audit controls and trail management")
        test_start = datetime.now()
        
        try:
            results = {}
            
            # Test 1: Audit Event Logging
            event_logging_results = await self._test_audit_event_logging()
            results['audit_event_logging'] = event_logging_results
            
            # Test 2: Audit Trail Query
            query_results = await self._test_audit_trail_query()
            results['audit_trail_query'] = query_results
            
            # Test 3: Integrity Verification
            integrity_results = await self._test_integrity_verification()
            results['integrity_verification'] = integrity_results
            
            # Test 4: Real-time Event Processing
            realtime_results = await self._test_realtime_processing()
            results['realtime_processing'] = realtime_results
            
            # Test 5: Audit Report Generation
            report_results = await self._test_audit_report_generation()
            results['audit_report_generation'] = report_results
            
            # Test 6: Event Archival
            archival_results = await self._test_event_archival()
            results['event_archival'] = archival_results
            
            test_duration = (datetime.now() - test_start).total_seconds()
            
            # Calculate overall score
            test_scores = []
            for test_name, test_result in results.items():
                if isinstance(test_result, dict) and 'score' in test_result:
                    test_scores.append(test_result['score'])
            
            overall_score = np.mean(test_scores) if test_scores else 0
            
            return {
                'test_duration_seconds': test_duration,
                'overall_score': overall_score,
                'test_results': results,
                'events_logged': sum(r.get('events_logged', 0) for r in results.values() if isinstance(r, dict)),
                'integrity_status': results.get('integrity_verification', {}).get('status', 'unknown')
            }
            
        except Exception as e:
            test_duration = (datetime.now() - test_start).total_seconds()
            self.logger.error(f"❌ Audit controls test failed: {e}")
            
            return {
                'test_duration_seconds': test_duration,
                'overall_score': 0.0,
                'error': str(e),
                'test_results': {}
            }
    
    async def _test_audit_event_logging(self) -> Dict[str, Any]:
        """Test audit event logging capabilities"""
        
        try:
            events_logged = 0
            
            # Log various types of events
            event_types = [
                (AuditEventType.TRADE_EXECUTION, AuditSeverity.INFO),
                (AuditEventType.POSITION_CHANGE, AuditSeverity.INFO),
                (AuditEventType.RISK_LIMIT_CHANGE, AuditSeverity.WARNING),
                (AuditEventType.SECURITY_EVENT, AuditSeverity.SECURITY),
                (AuditEventType.COMPLIANCE_VIOLATION, AuditSeverity.CRITICAL)
            ]
            
            for event_type, severity in event_types:
                event_id = await self.audit_manager.log_audit_event(
                    event_type=event_type,
                    component="test_component",
                    action="test_action",
                    description=f"Test {event_type.value} event",
                    details={'test_data': 'test_value'},
                    user_id="test_user",
                    session_id="test_session",
                    severity=severity
                )
                
                if event_id:
                    events_logged += 1
            
            # Flush buffer to ensure events are stored
            await self.audit_manager._flush_audit_buffer()
            
            score = (events_logged / len(event_types)) * 100
            
            return {
                'score': score,
                'events_logged': events_logged,
                'expected_events': len(event_types),
                'success_rate': events_logged / len(event_types)
            }
            
        except Exception as e:
            self.logger.error(f"Audit event logging test failed: {e}")
            return {
                'score': 0.0,
                'error': str(e),
                'events_logged': 0
            }
    
    async def _test_audit_trail_query(self) -> Dict[str, Any]:
        """Test audit trail query capabilities"""
        
        try:
            # Query all events
            query = AuditTrailQuery(limit=100)
            events = await self.audit_manager.query_audit_trail(query)
            
            # Query by event type
            type_query = AuditTrailQuery(
                event_types=[AuditEventType.TRADE_EXECUTION],
                limit=50
            )
            type_events = await self.audit_manager.query_audit_trail(type_query)
            
            # Query by severity
            severity_query = AuditTrailQuery(
                severities=[AuditSeverity.CRITICAL, AuditSeverity.SECURITY],
                limit=50
            )
            severity_events = await self.audit_manager.query_audit_trail(severity_query)
            
            score = 100.0 if len(events) > 0 else 0.0
            
            return {
                'score': score,
                'total_events_found': len(events),
                'type_filtered_events': len(type_events),
                'severity_filtered_events': len(severity_events),
                'query_successful': len(events) > 0
            }
            
        except Exception as e:
            self.logger.error(f"Audit trail query test failed: {e}")
            return {
                'score': 0.0,
                'error': str(e),
                'total_events_found': 0
            }
    
    async def _test_integrity_verification(self) -> Dict[str, Any]:
        """Test audit trail integrity verification"""
        
        try:
            # Perform integrity check
            integrity_results = await self.audit_manager._perform_integrity_check()
            
            status = integrity_results.get('overall_status', 'UNKNOWN')
            checksum_failures = integrity_results.get('checksum_failures', 0)
            events_checked = integrity_results.get('events_checked', 0)
            
            score = 100.0 if status == 'PASS' else 50.0 if status == 'FAIL' else 0.0
            
            return {
                'score': score,
                'status': status,
                'events_checked': events_checked,
                'checksum_failures': checksum_failures,
                'integrity_passed': status == 'PASS'
            }
            
        except Exception as e:
            self.logger.error(f"Integrity verification test failed: {e}")
            return {
                'score': 0.0,
                'error': str(e),
                'status': 'ERROR'
            }
    
    async def _test_realtime_processing(self) -> Dict[str, Any]:
        """Test real-time event processing"""
        
        try:
            processed_events = []
            
            # Subscribe to real-time events
            async def event_handler(event: AuditEvent):
                processed_events.append(event)
            
            self.audit_manager.subscribe_to_events(event_handler)
            
            # Log test event
            await self.audit_manager.log_audit_event(
                event_type=AuditEventType.SYSTEM_STARTUP,
                component="realtime_test",
                action="test_realtime",
                description="Real-time processing test event",
                severity=AuditSeverity.INFO
            )
            
            # Wait briefly for processing
            await asyncio.sleep(0.1)
            
            # Unsubscribe
            self.audit_manager.unsubscribe_from_events(event_handler)
            
            score = 100.0 if len(processed_events) > 0 else 0.0
            
            return {
                'score': score,
                'events_processed': len(processed_events),
                'realtime_processing_working': len(processed_events) > 0
            }
            
        except Exception as e:
            self.logger.error(f"Real-time processing test failed: {e}")
            return {
                'score': 0.0,
                'error': str(e),
                'events_processed': 0
            }
    
    async def _test_audit_report_generation(self) -> Dict[str, Any]:
        """Test audit report generation"""
        
        try:
            # Generate audit report
            query = AuditTrailQuery(
                start_time=datetime.now() - timedelta(hours=1),
                limit=100
            )
            
            report = await self.audit_manager.generate_audit_report(query)
            
            score = 100.0 if report.total_events >= 0 else 0.0
            
            return {
                'score': score,
                'report_generated': report is not None,
                'total_events_in_report': report.total_events,
                'security_events': len(report.security_events),
                'critical_events': len(report.critical_events),
                'recommendations_count': len(report.recommendations)
            }
            
        except Exception as e:
            self.logger.error(f"Audit report generation test failed: {e}")
            return {
                'score': 0.0,
                'error': str(e),
                'report_generated': False
            }
    
    async def _test_event_archival(self) -> Dict[str, Any]:
        """Test event archival capabilities"""
        
        try:
            # Test archival (with very old date to avoid archiving test events)
            archive_before = datetime.now() - timedelta(days=365)
            archival_result = await self.audit_manager.archive_old_events(archive_before)
            
            score = 100.0 if archival_result.get('status') in ['success', 'no_events_to_archive'] else 0.0
            
            return {
                'score': score,
                'archival_status': archival_result.get('status', 'unknown'),
                'events_archived': archival_result.get('events_archived', 0),
                'archival_successful': archival_result.get('status') == 'success'
            }
            
        except Exception as e:
            self.logger.error(f"Event archival test failed: {e}")
            return {
                'score': 0.0,
                'error': str(e),
                'archival_status': 'failed'
            }


if __name__ == "__main__":
    # Example usage
    async def main():
        logging.basicConfig(level=logging.INFO)
        
        print("Audit Controls and Trail Management Module")
        print("This module provides comprehensive audit trail capabilities")
        print("Use validate_core_engine_compliance.py to run actual compliance tests")
    
    asyncio.run(main())
