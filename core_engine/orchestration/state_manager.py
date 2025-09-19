"""
State Manager for Core Engine Orchestration
Manages system state, persistence, and state transitions
"""
from typing import Dict, List, Any, Optional, Union, Type, Callable
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
import json
import pickle
import threading
import logging
import os
import sqlite3
from pathlib import Path
import uuid

class SystemState(Enum):
    """Core system states"""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class ComponentState(Enum):
    """Individual component states"""
    OFFLINE = "offline"
    INITIALIZING = "initializing"
    ONLINE = "online"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"

@dataclass
class StateSnapshot:
    """System state snapshot"""
    timestamp: datetime
    system_state: SystemState
    component_states: Dict[str, ComponentState]
    system_metrics: Dict[str, Any]
    component_metrics: Dict[str, Dict[str, Any]]
    active_processes: List[str]
    errors: List[str]
    warnings: List[str]
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class StateTransition:
    """State transition record"""
    transition_id: str
    timestamp: datetime
    from_state: Union[SystemState, ComponentState]
    to_state: Union[SystemState, ComponentState]
    component: Optional[str] = None
    trigger: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class StatePersistence:
    """Handles state persistence to disk"""
    
    def __init__(self, persistence_path: str):
        self.persistence_path = Path(persistence_path)
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.persistence_path / "state.db"
        self.logger = logging.getLogger(__name__)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for state persistence"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create snapshots table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS state_snapshots (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        system_state TEXT NOT NULL,
                        component_states TEXT NOT NULL,
                        system_metrics TEXT,
                        component_metrics TEXT,
                        active_processes TEXT,
                        errors TEXT,
                        warnings TEXT
                    )
                """)
                
                # Create transitions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS state_transitions (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        from_state TEXT NOT NULL,
                        to_state TEXT NOT NULL,
                        component TEXT,
                        trigger TEXT,
                        metadata TEXT
                    )
                """)
                
                # Create indices
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp 
                    ON state_snapshots(timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_transitions_timestamp 
                    ON state_transitions(timestamp)
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error initializing state database: {e}")
    
    def save_snapshot(self, snapshot: StateSnapshot) -> bool:
        """Save state snapshot to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO state_snapshots 
                    (id, timestamp, system_state, component_states, system_metrics, 
                     component_metrics, active_processes, errors, warnings)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.snapshot_id,
                    snapshot.timestamp.isoformat(),
                    snapshot.system_state.value,
                    json.dumps({k: v.value for k, v in snapshot.component_states.items()}),
                    json.dumps(snapshot.system_metrics),
                    json.dumps(snapshot.component_metrics),
                    json.dumps(snapshot.active_processes),
                    json.dumps(snapshot.errors),
                    json.dumps(snapshot.warnings)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving snapshot: {e}")
            return False
    
    def save_transition(self, transition: StateTransition) -> bool:
        """Save state transition to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO state_transitions 
                    (id, timestamp, from_state, to_state, component, trigger, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    transition.transition_id,
                    transition.timestamp.isoformat(),
                    transition.from_state.value,
                    transition.to_state.value,
                    transition.component,
                    transition.trigger,
                    json.dumps(transition.metadata)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving transition: {e}")
            return False
    
    def load_latest_snapshot(self) -> Optional[StateSnapshot]:
        """Load most recent state snapshot"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM state_snapshots 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return StateSnapshot(
                    snapshot_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    system_state=SystemState(row[2]),
                    component_states={
                        k: ComponentState(v) 
                        for k, v in json.loads(row[3]).items()
                    },
                    system_metrics=json.loads(row[4]) if row[4] else {},
                    component_metrics=json.loads(row[5]) if row[5] else {},
                    active_processes=json.loads(row[6]) if row[6] else [],
                    errors=json.loads(row[7]) if row[7] else [],
                    warnings=json.loads(row[8]) if row[8] else []
                )
                
        except Exception as e:
            self.logger.error(f"Error loading snapshot: {e}")
            return None
    
    def get_recent_transitions(self, hours: int = 24) -> List[StateTransition]:
        """Get recent state transitions"""
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM state_transitions 
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (since.isoformat(),))
                
                transitions = []
                for row in cursor.fetchall():
                    transitions.append(StateTransition(
                        transition_id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        from_state=SystemState(row[2]) if not row[4] else ComponentState(row[2]),
                        to_state=SystemState(row[3]) if not row[4] else ComponentState(row[3]),
                        component=row[4],
                        trigger=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    ))
                
                return transitions
                
        except Exception as e:
            self.logger.error(f"Error loading transitions: {e}")
            return []

class StateManager:
    """
    Manages system and component states with persistence and monitoring
    """
    
    def __init__(self, persistence_path: str = "./state_data"):
        self.logger = logging.getLogger(__name__)
        self.persistence = StatePersistence(persistence_path)
        
        # Current state
        self.system_state = SystemState.INITIALIZING
        self.component_states: Dict[str, ComponentState] = {}
        self.system_metrics: Dict[str, Any] = {}
        self.component_metrics: Dict[str, Dict[str, Any]] = {}
        self.active_processes: List[str] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # State history
        self.state_history: List[StateSnapshot] = []
        self.transition_history: List[StateTransition] = []
        
        # Threading
        self.state_lock = threading.RLock()
        
        # State change callbacks
        self.state_change_callbacks: Dict[str, List[Callable]] = {
            'system': [],
            'component': []
        }
        
        # Monitoring
        self.snapshot_interval = 60  # seconds
        self.max_history_size = 1000
        
        # Try to restore previous state
        self._restore_state()
    
    def register_component(self, component_name: str, initial_state: ComponentState = ComponentState.OFFLINE) -> bool:
        """Register a new component"""
        try:
            with self.state_lock:
                if component_name in self.component_states:
                    self.logger.warning(f"Component {component_name} already registered")
                    return False
                
                self.component_states[component_name] = initial_state
                self.component_metrics[component_name] = {}
                
                self.logger.info(f"Registered component {component_name} with state {initial_state.value}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error registering component {component_name}: {e}")
            return False
    
    def set_system_state(self, new_state: SystemState, trigger: str = "") -> bool:
        """Set system state with validation and callbacks"""
        try:
            with self.state_lock:
                if not self._is_valid_system_transition(self.system_state, new_state):
                    self.logger.warning(f"Invalid system state transition: {self.system_state} -> {new_state}")
                    return False
                
                old_state = self.system_state
                self.system_state = new_state
                
                # Record transition
                transition = StateTransition(
                    transition_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    from_state=old_state,
                    to_state=new_state,
                    trigger=trigger
                )
                
                self.transition_history.append(transition)
                self.persistence.save_transition(transition)
                
                # Trigger callbacks
                self._trigger_callbacks('system', old_state, new_state)
                
                self.logger.info(f"System state changed: {old_state.value} -> {new_state.value}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting system state: {e}")
            return False
    
    def set_component_state(self, component_name: str, new_state: ComponentState, trigger: str = "") -> bool:
        """Set component state with validation and callbacks"""
        try:
            with self.state_lock:
                if component_name not in self.component_states:
                    self.logger.error(f"Component {component_name} not registered")
                    return False
                
                old_state = self.component_states[component_name]
                
                if not self._is_valid_component_transition(old_state, new_state):
                    self.logger.warning(f"Invalid component state transition for {component_name}: {old_state} -> {new_state}")
                    return False
                
                self.component_states[component_name] = new_state
                
                # Record transition
                transition = StateTransition(
                    transition_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    from_state=old_state,
                    to_state=new_state,
                    component=component_name,
                    trigger=trigger
                )
                
                self.transition_history.append(transition)
                self.persistence.save_transition(transition)
                
                # Trigger callbacks
                self._trigger_callbacks('component', old_state, new_state, component_name)
                
                self.logger.info(f"Component {component_name} state changed: {old_state.value} -> {new_state.value}")
                
                # Check if system state should change based on component states
                self._evaluate_system_state()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting component state for {component_name}: {e}")
            return False
    
    def update_system_metrics(self, metrics: Dict[str, Any]):
        """Update system-level metrics"""
        with self.state_lock:
            self.system_metrics.update(metrics)
    
    def update_component_metrics(self, component_name: str, metrics: Dict[str, Any]):
        """Update component-specific metrics"""
        with self.state_lock:
            if component_name not in self.component_metrics:
                self.component_metrics[component_name] = {}
            self.component_metrics[component_name].update(metrics)
    
    def add_error(self, error_msg: str, component: str = None):
        """Add error message"""
        with self.state_lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            error_entry = f"[{timestamp}] {component or 'SYSTEM'}: {error_msg}"
            self.errors.append(error_entry)
            
            # Keep error list manageable
            if len(self.errors) > 100:
                self.errors = self.errors[-50:]
    
    def add_warning(self, warning_msg: str, component: str = None):
        """Add warning message"""
        with self.state_lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            warning_entry = f"[{timestamp}] {component or 'SYSTEM'}: {warning_msg}"
            self.warnings.append(warning_entry)
            
            # Keep warning list manageable
            if len(self.warnings) > 100:
                self.warnings = self.warnings[-50:]
    
    def create_snapshot(self) -> StateSnapshot:
        """Create current state snapshot"""
        with self.state_lock:
            snapshot = StateSnapshot(
                timestamp=datetime.now(timezone.utc),
                system_state=self.system_state,
                component_states=self.component_states.copy(),
                system_metrics=self.system_metrics.copy(),
                component_metrics=self.component_metrics.copy(),
                active_processes=self.active_processes.copy(),
                errors=self.errors.copy(),
                warnings=self.warnings.copy()
            )
            
            # Save to history and persistence
            self.state_history.append(snapshot)
            self.persistence.save_snapshot(snapshot)
            
            # Limit history size
            if len(self.state_history) > self.max_history_size:
                self.state_history = self.state_history[-self.max_history_size//2:]
            
            return snapshot
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current system state"""
        with self.state_lock:
            return {
                'system_state': self.system_state.value,
                'component_states': {k: v.value for k, v in self.component_states.items()},
                'system_metrics': self.system_metrics.copy(),
                'component_metrics': self.component_metrics.copy(),
                'active_processes': self.active_processes.copy(),
                'error_count': len(self.errors),
                'warning_count': len(self.warnings),
                'last_update': datetime.now(timezone.utc).isoformat()
            }
    
    def _is_valid_system_transition(self, from_state: SystemState, to_state: SystemState) -> bool:
        """Validate system state transitions"""
        valid_transitions = {
            SystemState.INITIALIZING: [SystemState.READY, SystemState.ERROR],
            SystemState.READY: [SystemState.RUNNING, SystemState.MAINTENANCE, SystemState.STOPPED],
            SystemState.RUNNING: [SystemState.PAUSED, SystemState.STOPPING, SystemState.ERROR],
            SystemState.PAUSED: [SystemState.RUNNING, SystemState.STOPPING],
            SystemState.STOPPING: [SystemState.STOPPED],
            SystemState.STOPPED: [SystemState.INITIALIZING],
            SystemState.ERROR: [SystemState.INITIALIZING, SystemState.MAINTENANCE],
            SystemState.MAINTENANCE: [SystemState.READY]
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def _is_valid_component_transition(self, from_state: ComponentState, to_state: ComponentState) -> bool:
        """Validate component state transitions"""
        valid_transitions = {
            ComponentState.OFFLINE: [ComponentState.INITIALIZING],
            ComponentState.INITIALIZING: [ComponentState.ONLINE, ComponentState.FAILED],
            ComponentState.ONLINE: [ComponentState.DEGRADED, ComponentState.FAILED, ComponentState.MAINTENANCE, ComponentState.OFFLINE],
            ComponentState.DEGRADED: [ComponentState.ONLINE, ComponentState.FAILED, ComponentState.MAINTENANCE],
            ComponentState.FAILED: [ComponentState.INITIALIZING, ComponentState.OFFLINE],
            ComponentState.MAINTENANCE: [ComponentState.INITIALIZING, ComponentState.OFFLINE]
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def _evaluate_system_state(self):
        """Evaluate whether system state should change based on component states"""
        if self.system_state == SystemState.RUNNING:
            # Check if any critical components failed
            failed_components = [
                name for name, state in self.component_states.items()
                if state == ComponentState.FAILED
            ]
            
            if failed_components:
                self.set_system_state(SystemState.ERROR, f"Component failures: {failed_components}")
                return
            
            # Check if all components are degraded
            degraded_components = [
                name for name, state in self.component_states.items()
                if state == ComponentState.DEGRADED
            ]
            
            if len(degraded_components) == len(self.component_states):
                self.add_warning("All components in degraded state")
    
    def _trigger_callbacks(self, callback_type: str, old_state, new_state, component: str = None):
        """Trigger registered state change callbacks"""
        try:
            for callback in self.state_change_callbacks.get(callback_type, []):
                if callback_type == 'system':
                    callback(old_state, new_state)
                else:
                    callback(component, old_state, new_state)
        except Exception as e:
            self.logger.error(f"Error in state change callback: {e}")
    
    def _restore_state(self):
        """Restore state from persistence"""
        try:
            snapshot = self.persistence.load_latest_snapshot()
            if snapshot:
                self.system_state = snapshot.system_state
                self.component_states = snapshot.component_states
                self.system_metrics = snapshot.system_metrics
                self.component_metrics = snapshot.component_metrics
                self.active_processes = snapshot.active_processes
                self.errors = snapshot.errors
                self.warnings = snapshot.warnings
                
                self.logger.info(f"Restored state from snapshot {snapshot.snapshot_id}")
            else:
                self.logger.info("No previous state found, starting fresh")
                
        except Exception as e:
            self.logger.error(f"Error restoring state: {e}")
    
    def register_state_change_callback(self, callback_type: str, callback: Callable):
        """Register callback for state changes"""
        if callback_type in self.state_change_callbacks:
            self.state_change_callbacks[callback_type].append(callback)
    
    def cleanup(self):
        """Cleanup state manager"""
        self.create_snapshot()  # Final snapshot
        self.logger.info("State manager cleaned up")