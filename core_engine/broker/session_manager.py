"""
Broker Engine - Session Manager
Multi-session management with authentication, state tracking, and session recovery
"""

import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from collections import defaultdict
import uuid
import warnings
import json
import secrets

from .broker_adapter import BrokerType, ConnectionStatus, BrokerCredentials
from .protocol_handler import ProtocolType, ProtocolMessage, MessageType

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states"""
    CREATED = "created"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
    ERROR = "error"


class AuthenticationMethod(Enum):
    """Authentication methods"""
    API_KEY = "api_key"
    USERNAME_PASSWORD = "username_password"
    CERTIFICATE = "certificate"
    TOKEN = "token"
    OAUTH = "oauth"
    KERBEROS = "kerberos"
    LDAP = "ldap"
    SAML = "saml"
    CUSTOM = "custom"


class SessionType(Enum):
    """Session types"""
    TRADING = "trading"
    MARKET_DATA = "market_data"
    ADMIN = "admin"
    REPORTING = "reporting"
    RESEARCH = "research"
    RISK = "risk"
    SETTLEMENT = "settlement"
    CUSTOM = "custom"


@dataclass
class SessionConfig:
    """Session configuration"""
    # Session settings
    session_timeout: float = 3600.0  # 1 hour
    idle_timeout: float = 1800.0     # 30 minutes
    max_sessions_per_user: int = 5
    
    # Authentication
    authentication_method: AuthenticationMethod = AuthenticationMethod.API_KEY
    require_2fa: bool = False
    password_policy: Dict[str, Any] = field(default_factory=dict)
    
    # Security
    encrypt_session_data: bool = True
    session_token_length: int = 32
    require_ssl: bool = True
    
    # Session persistence
    persist_sessions: bool = True
    session_store_path: Optional[str] = None
    
    # Heartbeat
    heartbeat_interval: float = 30.0
    max_missed_heartbeats: int = 3
    
    # Recovery
    enable_session_recovery: bool = True
    recovery_timeout: float = 300.0  # 5 minutes
    
    # Monitoring
    log_session_events: bool = True
    track_session_metrics: bool = True


@dataclass
class AuthenticationRequest:
    """Authentication request"""
    request_id: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    token: Optional[str] = None
    certificate: Optional[bytes] = None
    two_factor_code: Optional[str] = None
    
    # Request metadata
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthenticationResult:
    """Authentication result"""
    success: bool
    session_token: Optional[str] = None
    user_id: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # Session metadata
    expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None
    
    # Security
    requires_password_change: bool = False
    account_locked: bool = False


@dataclass
class SessionInfo:
    """Session information"""
    session_id: str
    user_id: str
    session_type: SessionType
    broker_type: BrokerType
    protocol_type: ProtocolType
    
    # State
    state: SessionState = SessionState.CREATED
    
    # Authentication
    authentication_method: AuthenticationMethod = AuthenticationMethod.API_KEY
    session_token: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    authenticated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Connection details
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    broker_credentials: Optional[BrokerCredentials] = None
    
    # Session data
    session_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    # Heartbeat
    last_heartbeat: Optional[datetime] = None
    missed_heartbeats: int = 0
    
    # Recovery
    recovery_attempts: int = 0
    last_recovery_attempt: Optional[datetime] = None


class SessionAuthenticator:
    """Session authentication manager"""
    
    def __init__(self, config: SessionConfig):
        self.config = config
        
        # User store (in practice, would use database)
        self._users: Dict[str, Dict[str, Any]] = {}
        self._failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        
        # Token management
        self._active_tokens: Dict[str, str] = {}  # token -> user_id
        
        logger.info("Session authenticator initialized")
    
    async def authenticate(self, request: AuthenticationRequest) -> AuthenticationResult:
        """Authenticate user request"""
        
        try:
            # Check for account lockout
            if self._is_account_locked(request.username):
                return AuthenticationResult(
                    success=False,
                    error_code="ACCOUNT_LOCKED",
                    error_message="Account is locked due to failed login attempts",
                    account_locked=True
                )
            
            # Perform authentication based on method
            if self.config.authentication_method == AuthenticationMethod.API_KEY:
                result = await self._authenticate_api_key(request)
            elif self.config.authentication_method == AuthenticationMethod.USERNAME_PASSWORD:
                result = await self._authenticate_username_password(request)
            elif self.config.authentication_method == AuthenticationMethod.TOKEN:
                result = await self._authenticate_token(request)
            else:
                result = AuthenticationResult(
                    success=False,
                    error_code="UNSUPPORTED_METHOD",
                    error_message=f"Authentication method {self.config.authentication_method.value} not supported"
                )
            
            # Handle failed authentication
            if not result.success and request.username:
                self._record_failed_attempt(request.username)
            
            # Generate session token on success
            if result.success:
                result.session_token = self._generate_session_token()
                result.expires_at = datetime.now() + timedelta(seconds=self.config.session_timeout)
                
                # Store token
                if result.session_token and result.user_id:
                    self._active_tokens[result.session_token] = result.user_id
            
            return result
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return AuthenticationResult(
                success=False,
                error_code="AUTHENTICATION_ERROR",
                error_message=str(e)
            )
    
    async def validate_token(self, token: str) -> Optional[str]:
        """Validate session token and return user ID"""
        
        user_id = self._active_tokens.get(token)
        if user_id:
            # Check if token is expired (would check database in practice)
            return user_id
        
        return None
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke session token"""
        
        if token in self._active_tokens:
            del self._active_tokens[token]
            return True
        
        return False
    
    async def _authenticate_api_key(self, request: AuthenticationRequest) -> AuthenticationResult:
        """Authenticate using API key"""
        
        if not request.api_key:
            return AuthenticationResult(
                success=False,
                error_code="MISSING_API_KEY",
                error_message="API key is required"
            )
        
        # Validate API key (mock implementation)
        if request.api_key.startswith("valid_"):
            user_id = request.api_key.replace("valid_", "")
            return AuthenticationResult(
                success=True,
                user_id=user_id,
                permissions=["trading", "market_data", "account"]
            )
        
        return AuthenticationResult(
            success=False,
            error_code="INVALID_API_KEY",
            error_message="Invalid API key"
        )
    
    async def _authenticate_username_password(self, request: AuthenticationRequest) -> AuthenticationResult:
        """Authenticate using username/password"""
        
        if not request.username or not request.password:
            return AuthenticationResult(
                success=False,
                error_code="MISSING_CREDENTIALS",
                error_message="Username and password are required"
            )
        
        # Check user exists (mock implementation)
        user_data = self._users.get(request.username)
        if not user_data:
            return AuthenticationResult(
                success=False,
                error_code="INVALID_CREDENTIALS",
                error_message="Invalid username or password"
            )
        
        # Verify password (would use proper hashing in practice)
        stored_password = user_data.get("password")
        if stored_password != request.password:
            return AuthenticationResult(
                success=False,
                error_code="INVALID_CREDENTIALS",
                error_message="Invalid username or password"
            )
        
        # Check 2FA if required
        if self.config.require_2fa:
            if not request.two_factor_code:
                return AuthenticationResult(
                    success=False,
                    error_code="2FA_REQUIRED",
                    error_message="Two-factor authentication code required"
                )
            
            # Validate 2FA code (mock implementation)
            if request.two_factor_code != "123456":
                return AuthenticationResult(
                    success=False,
                    error_code="INVALID_2FA",
                    error_message="Invalid two-factor authentication code"
                )
        
        return AuthenticationResult(
            success=True,
            user_id=request.username,
            permissions=user_data.get("permissions", [])
        )
    
    async def _authenticate_token(self, request: AuthenticationRequest) -> AuthenticationResult:
        """Authenticate using token"""
        
        if not request.token:
            return AuthenticationResult(
                success=False,
                error_code="MISSING_TOKEN",
                error_message="Token is required"
            )
        
        # Validate token
        user_id = await self.validate_token(request.token)
        
        if user_id:
            return AuthenticationResult(
                success=True,
                user_id=user_id,
                permissions=["trading", "market_data"]
            )
        
        return AuthenticationResult(
            success=False,
            error_code="INVALID_TOKEN",
            error_message="Invalid or expired token"
        )
    
    def _generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(self.config.session_token_length)
    
    def _is_account_locked(self, username: Optional[str]) -> bool:
        """Check if account is locked due to failed attempts"""
        
        if not username:
            return False
        
        failed_attempts = self._failed_attempts.get(username, [])
        
        # Clean old attempts (older than 1 hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_attempts = [attempt for attempt in failed_attempts if attempt > cutoff_time]
        self._failed_attempts[username] = recent_attempts
        
        # Lock account if more than 5 failed attempts in last hour
        return len(recent_attempts) >= 5
    
    def _record_failed_attempt(self, username: str) -> None:
        """Record failed authentication attempt"""
        self._failed_attempts[username].append(datetime.now())
    
    def add_user(self, username: str, password: str, permissions: List[str]) -> None:
        """Add user (for testing)"""
        self._users[username] = {
            "password": password,
            "permissions": permissions,
            "created_at": datetime.now()
        }


class SessionManager:
    """
    Multi-Session Manager
    
    Manages broker sessions with authentication, state tracking,
    session recovery, and advanced session lifecycle management.
    """
    
    def __init__(self, config: Optional[SessionConfig] = None):
        """Initialize session manager"""
        
        self.config = config or SessionConfig()
        
        # Session storage
        self._sessions: Dict[str, SessionInfo] = {}
        self._user_sessions: Dict[str, Set[str]] = defaultdict(set)  # user_id -> session_ids
        self._token_sessions: Dict[str, str] = {}  # token -> session_id
        
        # Authentication
        self._authenticator = SessionAuthenticator(self.config)
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._stop_background_tasks = False
        
        # Session monitoring
        self._session_metrics = {
            'total_sessions': 0,
            'active_sessions': 0,
            'failed_authentications': 0,
            'expired_sessions': 0,
            'recovered_sessions': 0
        }
        
        # Event handlers
        self._event_handlers = defaultdict(list)
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        logger.info("Session manager initialized")
    
    async def start(self) -> None:
        """Start session manager"""
        
        try:
            # Start background tasks
            self._background_tasks.add(
                asyncio.create_task(self._session_monitor_loop())
            )
            
            self._background_tasks.add(
                asyncio.create_task(self._heartbeat_monitor_loop())
            )
            
            if self.config.enable_session_recovery:
                self._background_tasks.add(
                    asyncio.create_task(self._session_recovery_loop())
                )
            
            logger.info("Session manager started")
            
        except Exception as e:
            logger.error(f"Failed to start session manager: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop session manager"""
        
        try:
            # Signal background tasks to stop
            self._stop_background_tasks = True
            
            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            self._background_tasks.clear()
            
            # Close all sessions
            await self.close_all_sessions()
            
            logger.info("Session manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping session manager: {e}")
    
    async def create_session(self, user_id: str, session_type: SessionType,
                           broker_type: BrokerType, protocol_type: ProtocolType,
                           credentials: BrokerCredentials,
                           client_ip: Optional[str] = None,
                           user_agent: Optional[str] = None) -> str:
        """Create new session"""
        
        try:
            with self._lock:
                # Check session limits
                user_session_count = len(self._user_sessions[user_id])
                if user_session_count >= self.config.max_sessions_per_user:
                    raise RuntimeError(f"Maximum sessions ({self.config.max_sessions_per_user}) exceeded for user {user_id}")
                
                # Generate session ID
                session_id = f"session_{uuid.uuid4().hex}"
                
                # Calculate expiration
                expires_at = datetime.now() + timedelta(seconds=self.config.session_timeout)
                
                # Create session info
                session_info = SessionInfo(
                    session_id=session_id,
                    user_id=user_id,
                    session_type=session_type,
                    broker_type=broker_type,
                    protocol_type=protocol_type,
                    state=SessionState.CREATED,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    broker_credentials=credentials,
                    expires_at=expires_at
                )
                
                # Store session
                self._sessions[session_id] = session_info
                self._user_sessions[user_id].add(session_id)
                
                # Update metrics
                self._session_metrics['total_sessions'] += 1
                self._session_metrics['active_sessions'] += 1
                
                logger.info(f"Created session {session_id} for user {user_id}")
                
                self._trigger_event('session_created', {
                    'session_id': session_id,
                    'user_id': user_id,
                    'session_type': session_type.value,
                    'broker_type': broker_type.value
                })
                
                return session_id
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def authenticate_session(self, session_id: str, 
                                 auth_request: AuthenticationRequest) -> AuthenticationResult:
        """Authenticate session"""
        
        try:
            with self._lock:
                if session_id not in self._sessions:
                    return AuthenticationResult(
                        success=False,
                        error_code="SESSION_NOT_FOUND",
                        error_message="Session not found"
                    )
                
                session = self._sessions[session_id]
                
                if session.state != SessionState.CREATED:
                    return AuthenticationResult(
                        success=False,
                        error_code="INVALID_SESSION_STATE",
                        error_message=f"Session is in {session.state.value} state"
                    )
                
                # Update session state
                session.state = SessionState.AUTHENTICATING
                
                # Perform authentication
                auth_result = await self._authenticator.authenticate(auth_request)
                
                if auth_result.success:
                    # Update session with authentication result
                    session.state = SessionState.ACTIVE
                    session.authenticated_at = datetime.now()
                    session.last_activity = datetime.now()
                    session.session_token = auth_result.session_token
                    session.permissions = auth_result.permissions
                    session.authentication_method = self.config.authentication_method
                    
                    # Store token mapping
                    if auth_result.session_token:
                        self._token_sessions[auth_result.session_token] = session_id
                    
                    logger.info(f"Session {session_id} authenticated successfully")
                    
                    self._trigger_event('session_authenticated', {
                        'session_id': session_id,
                        'user_id': session.user_id,
                        'authentication_method': session.authentication_method.value
                    })
                    
                else:
                    # Authentication failed
                    session.state = SessionState.ERROR
                    self._session_metrics['failed_authentications'] += 1
                    
                    logger.warning(f"Session {session_id} authentication failed: {auth_result.error_message}")
                
                return auth_result
                
        except Exception as e:
            logger.error(f"Session authentication error: {e}")
            return AuthenticationResult(
                success=False,
                error_code="AUTHENTICATION_ERROR",
                error_message=str(e)
            )
    
    async def close_session(self, session_id: str, reason: Optional[str] = None) -> bool:
        """Close session"""
        
        try:
            with self._lock:
                if session_id not in self._sessions:
                    logger.warning(f"Attempted to close non-existent session {session_id}")
                    return False
                
                session = self._sessions[session_id]
                
                # Revoke session token
                if session.session_token:
                    await self._authenticator.revoke_token(session.session_token)
                    
                    if session.session_token in self._token_sessions:
                        del self._token_sessions[session.session_token]
                
                # Update session state
                session.state = SessionState.DISCONNECTED
                
                # Remove from user sessions
                self._user_sessions[session.user_id].discard(session_id)
                
                # Remove session
                del self._sessions[session_id]
                
                # Update metrics
                self._session_metrics['active_sessions'] -= 1
                
                logger.info(f"Closed session {session_id}" + (f" ({reason})" if reason else ""))
                
                self._trigger_event('session_closed', {
                    'session_id': session_id,
                    'user_id': session.user_id,
                    'reason': reason
                })
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to close session {session_id}: {e}")
            return False
    
    async def close_all_sessions(self, user_id: Optional[str] = None) -> int:
        """Close all sessions or all sessions for specific user"""
        
        session_ids_to_close = []
        
        with self._lock:
            if user_id:
                session_ids_to_close = list(self._user_sessions[user_id])
            else:
                session_ids_to_close = list(self._sessions.keys())
        
        closed_count = 0
        for session_id in session_ids_to_close:
            success = await self.close_session(session_id, "batch_close")
            if success:
                closed_count += 1
        
        logger.info(f"Closed {closed_count} sessions" + (f" for user {user_id}" if user_id else ""))
        
        return closed_count
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        with self._lock:
            return self._sessions.get(session_id)
    
    def get_session_by_token(self, token: str) -> Optional[SessionInfo]:
        """Get session by token"""
        with self._lock:
            session_id = self._token_sessions.get(token)
            if session_id:
                return self._sessions.get(session_id)
            return None
    
    def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """Get all sessions for user"""
        with self._lock:
            session_ids = self._user_sessions[user_id]
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
    
    def update_session_activity(self, session_id: str, 
                              messages_sent: int = 0, messages_received: int = 0,
                              bytes_sent: int = 0, bytes_received: int = 0) -> bool:
        """Update session activity metrics"""
        
        with self._lock:
            if session_id not in self._sessions:
                return False
            
            session = self._sessions[session_id]
            session.last_activity = datetime.now()
            session.messages_sent += messages_sent
            session.messages_received += messages_received
            session.bytes_sent += bytes_sent
            session.bytes_received += bytes_received
            
            # Reset idle state if was idle
            if session.state == SessionState.IDLE:
                session.state = SessionState.ACTIVE
            
            return True
    
    def record_heartbeat(self, session_id: str) -> bool:
        """Record session heartbeat"""
        
        with self._lock:
            if session_id not in self._sessions:
                return False
            
            session = self._sessions[session_id]
            session.last_heartbeat = datetime.now()
            session.missed_heartbeats = 0
            
            return True
    
    async def recover_session(self, session_id: str) -> bool:
        """Attempt to recover session"""
        
        try:
            with self._lock:
                if session_id not in self._sessions:
                    return False
                
                session = self._sessions[session_id]
                
                # Check if session can be recovered
                if session.state not in [SessionState.SUSPENDED, SessionState.ERROR]:
                    return False
                
                # Check recovery timeout
                if session.last_recovery_attempt:
                    time_since_last_attempt = (datetime.now() - session.last_recovery_attempt).total_seconds()
                    if time_since_last_attempt < self.config.recovery_timeout:
                        return False
                
                # Update recovery tracking
                session.recovery_attempts += 1
                session.last_recovery_attempt = datetime.now()
                
                # Attempt recovery (mock implementation)
                if session.recovery_attempts <= 3:  # Max 3 recovery attempts
                    session.state = SessionState.ACTIVE
                    session.last_activity = datetime.now()
                    
                    self._session_metrics['recovered_sessions'] += 1
                    
                    logger.info(f"Recovered session {session_id} (attempt {session.recovery_attempts})")
                    
                    self._trigger_event('session_recovered', {
                        'session_id': session_id,
                        'recovery_attempts': session.recovery_attempts
                    })
                    
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Session recovery failed for {session_id}: {e}")
            return False
    
    async def _session_monitor_loop(self) -> None:
        """Monitor sessions for timeouts and cleanup"""
        
        while not self._stop_background_tasks:
            try:
                current_time = datetime.now()
                expired_sessions = []
                idle_sessions = []
                
                with self._lock:
                    for session_id, session in list(self._sessions.items()):
                        # Check for expired sessions
                        if session.expires_at and current_time > session.expires_at:
                            expired_sessions.append(session_id)
                            continue
                        
                        # Check for idle sessions
                        if session.last_activity:
                            idle_time = (current_time - session.last_activity).total_seconds()
                            if idle_time > self.config.idle_timeout and session.state == SessionState.ACTIVE:
                                idle_sessions.append(session_id)
                
                # Handle expired sessions
                for session_id in expired_sessions:
                    await self.close_session(session_id, "expired")
                    self._session_metrics['expired_sessions'] += 1
                
                # Handle idle sessions
                for session_id in idle_sessions:
                    with self._lock:
                        if session_id in self._sessions:
                            self._sessions[session_id].state = SessionState.IDLE
                    
                    logger.debug(f"Session {session_id} marked as idle")
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _heartbeat_monitor_loop(self) -> None:
        """Monitor session heartbeats"""
        
        while not self._stop_background_tasks:
            try:
                current_time = datetime.now()
                stale_sessions = []
                
                with self._lock:
                    for session_id, session in list(self._sessions.items()):
                        if session.state not in [SessionState.ACTIVE, SessionState.IDLE]:
                            continue
                        
                        # Check heartbeat timeout
                        if session.last_heartbeat:
                            time_since_heartbeat = (current_time - session.last_heartbeat).total_seconds()
                            
                            if time_since_heartbeat > self.config.heartbeat_interval * 2:
                                session.missed_heartbeats += 1
                                
                                if session.missed_heartbeats >= self.config.max_missed_heartbeats:
                                    stale_sessions.append(session_id)
                
                # Handle stale sessions
                for session_id in stale_sessions:
                    with self._lock:
                        if session_id in self._sessions:
                            self._sessions[session_id].state = SessionState.SUSPENDED
                    
                    logger.warning(f"Session {session_id} suspended due to missed heartbeats")
                    
                    self._trigger_event('session_suspended', {
                        'session_id': session_id,
                        'reason': 'missed_heartbeats'
                    })
                
                await asyncio.sleep(self.config.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _session_recovery_loop(self) -> None:
        """Attempt to recover suspended sessions"""
        
        while not self._stop_background_tasks:
            try:
                suspended_sessions = []
                
                with self._lock:
                    for session_id, session in list(self._sessions.items()):
                        if session.state == SessionState.SUSPENDED:
                            suspended_sessions.append(session_id)
                
                # Attempt recovery for suspended sessions
                for session_id in suspended_sessions:
                    await self.recover_session(session_id)
                
                await asyncio.sleep(self.config.recovery_timeout)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session recovery loop: {e}")
                await asyncio.sleep(60)
    
    def add_event_handler(self, event_type: str, 
                         handler: Callable[[Dict[str, Any]], None]) -> None:
        """Add event handler"""
        self._event_handlers[event_type].append(handler)
    
    def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger event handlers"""
        for handler in self._event_handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics"""
        
        with self._lock:
            # Count sessions by state
            state_counts = defaultdict(int)
            for session in self._sessions.values():
                state_counts[session.state.value] += 1
            
            # Count sessions by type
            type_counts = defaultdict(int)
            for session in self._sessions.values():
                type_counts[session.session_type.value] += 1
            
            # Count sessions by broker
            broker_counts = defaultdict(int)
            for session in self._sessions.values():
                broker_counts[session.broker_type.value] += 1
            
            return {
                'total_sessions': len(self._sessions),
                'sessions_by_state': dict(state_counts),
                'sessions_by_type': dict(type_counts),
                'sessions_by_broker': dict(broker_counts),
                'unique_users': len(self._user_sessions),
                'metrics': self._session_metrics.copy()
            }
    
    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed session information"""
        
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            
            return {
                'session_id': session.session_id,
                'user_id': session.user_id,
                'session_type': session.session_type.value,
                'broker_type': session.broker_type.value,
                'protocol_type': session.protocol_type.value,
                'state': session.state.value,
                'authentication_method': session.authentication_method.value,
                'permissions': session.permissions,
                'created_at': session.created_at,
                'authenticated_at': session.authenticated_at,
                'last_activity': session.last_activity,
                'expires_at': session.expires_at,
                'client_ip': session.client_ip,
                'user_agent': session.user_agent,
                'messages_sent': session.messages_sent,
                'messages_received': session.messages_received,
                'bytes_sent': session.bytes_sent,
                'bytes_received': session.bytes_received,
                'last_heartbeat': session.last_heartbeat,
                'missed_heartbeats': session.missed_heartbeats,
                'recovery_attempts': session.recovery_attempts,
                'last_recovery_attempt': session.last_recovery_attempt
            }
    
    def export_session_data(self, format_type: str = "json") -> Union[str, bytes]:
        """Export session data for backup/analysis"""
        
        with self._lock:
            sessions_data = []
            
            for session in self._sessions.values():
                session_data = {
                    'session_id': session.session_id,
                    'user_id': session.user_id,
                    'session_type': session.session_type.value,
                    'broker_type': session.broker_type.value,
                    'protocol_type': session.protocol_type.value,
                    'state': session.state.value,
                    'created_at': session.created_at.isoformat(),
                    'last_activity': session.last_activity.isoformat() if session.last_activity else None,
                    'messages_sent': session.messages_sent,
                    'messages_received': session.messages_received
                }
                sessions_data.append(session_data)
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_sessions': len(sessions_data),
                'sessions': sessions_data,
                'metrics': self._session_metrics
            }
            
            if format_type == "json":
                return json.dumps(export_data, indent=2)
            elif format_type == "csv":
                # Convert to CSV format
                df = pd.DataFrame(sessions_data)
                return df.to_csv(index=False)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
    
    def get_authenticator(self) -> SessionAuthenticator:
        """Get session authenticator for testing"""
        return self._authenticator