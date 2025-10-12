"""
Broker Engine - Protocol Handler
Multi-protocol support for broker communications (FIX, REST, WebSocket, etc.)
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import uuid
import warnings
from abc import ABC, abstractmethod
import json

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ProtocolType(Enum):
    """Supported protocol types"""
    FIX = "fix"
    REST = "rest"
    WEBSOCKET = "websocket"
    TCP = "tcp"
    UDP = "udp"
    BINARY = "binary"
    JSON = "json"
    XML = "xml"
    CUSTOM = "custom"


class MessageType(Enum):
    """Message types"""
    # Orders
    NEW_ORDER = "new_order"
    ORDER_CANCEL = "order_cancel"
    ORDER_REPLACE = "order_replace"
    ORDER_STATUS = "order_status"
    
    # Executions
    EXECUTION_REPORT = "execution_report"
    FILL_REPORT = "fill_report"
    
    # Market Data
    MARKET_DATA_REQUEST = "market_data_request"
    MARKET_DATA_SNAPSHOT = "market_data_snapshot"
    MARKET_DATA_INCREMENTAL = "market_data_incremental"
    
    # Session
    LOGON = "logon"
    LOGOUT = "logout"
    HEARTBEAT = "heartbeat"
    TEST_REQUEST = "test_request"
    
    # Admin
    SEQUENCE_RESET = "sequence_reset"
    RESEND_REQUEST = "resend_request"
    REJECT = "reject"
    
    # Custom
    CUSTOM = "custom"


class MessageDirection(Enum):
    """Message direction"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class ProtocolConfig:
    """Protocol configuration"""
    protocol_type: ProtocolType
    
    # Connection details
    host: Optional[str] = None
    port: Optional[int] = None
    url: Optional[str] = None
    
    # Authentication
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    
    # Protocol specific settings
    version: Optional[str] = None
    sender_comp_id: Optional[str] = None
    target_comp_id: Optional[str] = None
    
    # Timeouts and intervals
    connect_timeout: float = 30.0
    read_timeout: float = 10.0
    heartbeat_interval: float = 30.0
    
    # Message handling
    message_encoding: str = "utf-8"
    validate_messages: bool = True
    store_messages: bool = True
    max_stored_messages: int = 10000
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Compression
    enable_compression: bool = False
    compression_level: int = 6
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProtocolMessage:
    """Protocol message"""
    message_id: str
    message_type: MessageType
    direction: MessageDirection
    protocol_type: ProtocolType
    
    # Content
    raw_data: bytes
    parsed_data: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    
    # Metadata
    session_id: Optional[str] = None
    sequence_number: Optional[int] = None
    correlation_id: Optional[str] = None
    
    # Error handling
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class SessionState:
    """Protocol session state"""
    session_id: str
    protocol_type: ProtocolType
    
    # Connection state
    is_connected: bool = False
    is_authenticated: bool = False
    
    # Sequence tracking
    next_outbound_seq: int = 1
    expected_inbound_seq: int = 1
    
    # Timing
    last_heartbeat_sent: Optional[datetime] = None
    last_heartbeat_received: Optional[datetime] = None
    last_message_sent: Optional[datetime] = None
    last_message_received: Optional[datetime] = None
    
    # Counters
    messages_sent: int = 0
    messages_received: int = 0
    errors_count: int = 0


class ProtocolHandlerInterface(ABC):
    """Abstract base class for protocol handlers"""
    
    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.protocol_type = config.protocol_type
        self._session_state = None
        self._message_handlers = defaultdict(list)
        self._event_handlers = defaultdict(list)
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect using protocol"""
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from protocol"""
    
    @abstractmethod
    async def send_message(self, message: ProtocolMessage) -> bool:
        """Send message using protocol"""
    
    @abstractmethod
    async def receive_message(self) -> Optional[ProtocolMessage]:
        """Receive message using protocol"""
    
    @abstractmethod
    def create_message(self, message_type: MessageType, 
                      data: Dict[str, Any]) -> ProtocolMessage:
        """Create protocol-specific message"""
    
    @abstractmethod
    def parse_message(self, raw_data: bytes) -> ProtocolMessage:
        """Parse raw data into protocol message"""
    
    @abstractmethod
    def validate_message(self, message: ProtocolMessage) -> bool:
        """Validate protocol message"""
    
    def add_message_handler(self, message_type: MessageType, 
                           handler: Callable[[ProtocolMessage], None]) -> None:
        """Add message handler"""
        self._message_handlers[message_type].append(handler)
    
    def add_event_handler(self, event_type: str,
                         handler: Callable[[Dict[str, Any]], None]) -> None:
        """Add event handler"""
        self._event_handlers[event_type].append(handler)
    
    def _trigger_message_handlers(self, message: ProtocolMessage) -> None:
        """Trigger message handlers"""
        for handler in self._message_handlers[message.message_type]:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger event handlers"""
        for handler in self._event_handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")


class FIXProtocolHandler(ProtocolHandlerInterface):
    """FIX Protocol Handler"""
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self._connection = None
        self._reader = None
        self._writer = None
        self._heartbeat_task = None
        
        # FIX specific
        self.fix_version = config.version or "FIX.4.4"
        self.sender_comp_id = config.sender_comp_id
        self.target_comp_id = config.target_comp_id
        
        # Message storage
        self._message_store = deque(maxlen=config.max_stored_messages)
        
        logger.info(f"FIX protocol handler initialized for {self.fix_version}")
    
    async def connect(self) -> bool:
        """Connect using FIX protocol"""
        try:
            # Open TCP connection
            self._reader, self._writer = await asyncio.open_connection(
                self.config.host, 
                self.config.port
            )
            
            # Create session state
            self._session_state = SessionState(
                session_id=f"FIX_{uuid.uuid4().hex[:8]}",
                protocol_type=ProtocolType.FIX
            )
            
            # Send logon message
            logon_success = await self._send_logon()
            
            if logon_success:
                self._session_state.is_connected = True
                self._session_state.is_authenticated = True
                
                # Start heartbeat
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                logger.info("FIX protocol connected")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect via FIX protocol: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from FIX protocol"""
        try:
            # Send logout message
            await self._send_logout()
            
            # Stop heartbeat
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            
            # Close connection
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
            
            if self._session_state:
                self._session_state.is_connected = False
                self._session_state.is_authenticated = False
            
            logger.info("FIX protocol disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting FIX protocol: {e}")
            return False
    
    async def send_message(self, message: ProtocolMessage) -> bool:
        """Send FIX message"""
        try:
            if not self._session_state or not self._session_state.is_connected:
                raise RuntimeError("FIX session not connected")
            
            # Add FIX headers
            fix_message = self._add_fix_headers(message)
            
            # Calculate checksum
            fix_message_with_checksum = self._add_checksum(fix_message)
            
            # Send message
            self._writer.write(fix_message_with_checksum.encode(self.config.message_encoding))
            await self._writer.drain()
            
            # Update session state
            message.sent_at = datetime.now()
            self._session_state.next_outbound_seq += 1
            self._session_state.messages_sent += 1
            self._session_state.last_message_sent = message.sent_at
            
            # Store message
            if self.config.store_messages:
                self._message_store.append(message)
            
            logger.debug(f"Sent FIX message: {message.message_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send FIX message: {e}")
            return False
    
    async def receive_message(self) -> Optional[ProtocolMessage]:
        """Receive FIX message"""
        try:
            if not self._reader:
                return None
            
            # Read until SOH (Start of Header)
            raw_data = await self._read_fix_message()
            
            if raw_data:
                message = self.parse_message(raw_data)
                
                # Update session state
                message.received_at = datetime.now()
                self._session_state.messages_received += 1
                self._session_state.last_message_received = message.received_at
                
                # Validate sequence number
                if message.sequence_number:
                    if message.sequence_number == self._session_state.expected_inbound_seq:
                        self._session_state.expected_inbound_seq += 1
                    else:
                        logger.warning(f"Sequence number gap: expected {self._session_state.expected_inbound_seq}, got {message.sequence_number}")
                
                # Store message
                if self.config.store_messages:
                    self._message_store.append(message)
                
                # Trigger handlers
                self._trigger_message_handlers(message)
                
                return message
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to receive FIX message: {e}")
            return None
    
    def create_message(self, message_type: MessageType, data: Dict[str, Any]) -> ProtocolMessage:
        """Create FIX message"""
        
        # Map message type to FIX message type
        fix_msg_type = self._get_fix_message_type(message_type)
        
        # Build FIX message fields
        fix_fields = {
            '35': fix_msg_type,  # MsgType
            '49': self.sender_comp_id,  # SenderCompID
            '56': self.target_comp_id,  # TargetCompID
            '52': datetime.now().strftime('%Y%m%d-%H:%M:%S.%f')[:-3],  # SendingTime
        }
        
        # Add data fields
        fix_fields.update(self._map_data_to_fix_fields(message_type, data))
        
        # Create message
        message = ProtocolMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            direction=MessageDirection.OUTBOUND,
            protocol_type=ProtocolType.FIX,
            raw_data=b'',  # Will be set when sending
            parsed_data=fix_fields
        )
        
        return message
    
    def parse_message(self, raw_data: bytes) -> ProtocolMessage:
        """Parse FIX message"""
        
        try:
            # Decode message
            message_str = raw_data.decode(self.config.message_encoding)
            
            # Parse FIX fields
            fields = {}
            for field in message_str.split('\x01'):  # SOH separator
                if '=' in field:
                    tag, value = field.split('=', 1)
                    fields[tag] = value
            
            # Extract message type
            fix_msg_type = fields.get('35', '')
            message_type = self._get_message_type_from_fix(fix_msg_type)
            
            # Extract sequence number
            sequence_number = int(fields.get('34', '0'))
            
            message = ProtocolMessage(
                message_id=str(uuid.uuid4()),
                message_type=message_type,
                direction=MessageDirection.INBOUND,
                protocol_type=ProtocolType.FIX,
                raw_data=raw_data,
                parsed_data=fields,
                sequence_number=sequence_number
            )
            
            # Validate if configured
            if self.config.validate_messages:
                message.is_valid = self.validate_message(message)
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to parse FIX message: {e}")
            
            # Return invalid message
            return ProtocolMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.CUSTOM,
                direction=MessageDirection.INBOUND,
                protocol_type=ProtocolType.FIX,
                raw_data=raw_data,
                parsed_data={},
                is_valid=False,
                validation_errors=[str(e)]
            )
    
    def validate_message(self, message: ProtocolMessage) -> bool:
        """Validate FIX message"""
        
        errors = []
        
        # Check required fields
        required_fields = ['8', '9', '35', '49', '56', '34', '52', '10']  # Version, BodyLength, MsgType, etc.
        
        for field in required_fields:
            if field not in message.parsed_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate checksum
        if '10' in message.parsed_data:
            calculated_checksum = self._calculate_checksum(message.raw_data)
            received_checksum = message.parsed_data['10']
            
            if str(calculated_checksum) != received_checksum:
                errors.append(f"Checksum mismatch: calculated {calculated_checksum}, received {received_checksum}")
        
        message.validation_errors = errors
        return len(errors) == 0
    
    async def _send_logon(self) -> bool:
        """Send FIX logon message"""
        
        logon_data = {
            'EncryptMethod': '0',  # None
            'HeartBtInt': str(int(self.config.heartbeat_interval)),
            'Username': self.config.username,
            'Password': self.config.password
        }
        
        logon_message = self.create_message(MessageType.LOGON, logon_data)
        return await self.send_message(logon_message)
    
    async def _send_logout(self) -> bool:
        """Send FIX logout message"""
        
        logout_message = self.create_message(MessageType.LOGOUT, {})
        return await self.send_message(logout_message)
    
    async def _send_heartbeat(self) -> bool:
        """Send FIX heartbeat message"""
        
        heartbeat_message = self.create_message(MessageType.HEARTBEAT, {})
        success = await self.send_message(heartbeat_message)
        
        if success and self._session_state:
            self._session_state.last_heartbeat_sent = datetime.now()
        
        return success
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop"""
        
        while self._session_state and self._session_state.is_connected:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                await self._send_heartbeat()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _read_fix_message(self) -> Optional[bytes]:
        """Read complete FIX message"""
        
        try:
            # Read until we have enough for header
            header_data = await self._reader.read(1024)
            
            if not header_data:
                return None
            
            # Find body length field (tag 9)
            header_str = header_data.decode(self.config.message_encoding)
            
            # Look for body length
            body_length = 0
            for field in header_str.split('\x01'):
                if field.startswith('9='):
                    body_length = int(field[2:])
                    break
            
            # Read remaining message based on body length
            if body_length > 0:
                remaining_data = await self._reader.read(body_length + 7)  # +7 for checksum
                return header_data + remaining_data
            
            return header_data
            
        except Exception as e:
            logger.error(f"Error reading FIX message: {e}")
            return None
    
    def _add_fix_headers(self, message: ProtocolMessage) -> str:
        """Add FIX headers to message"""
        
        fields = message.parsed_data.copy()
        
        # Add standard headers
        fields['8'] = self.fix_version  # BeginString
        fields['34'] = str(self._session_state.next_outbound_seq)  # MsgSeqNum
        
        # Calculate body length (everything after BodyLength field)
        body_fields = {k: v for k, v in fields.items() if k not in ['8', '9']}
        body_str = '\x01'.join([f"{k}={v}" for k, v in body_fields.items()])
        fields['9'] = str(len(body_str) + 1)  # BodyLength (+1 for final SOH)
        
        # Build message string
        header_fields = ['8', '9']  # Fixed order
        message_parts = []
        
        # Add headers first
        for field in header_fields:
            if field in fields:
                message_parts.append(f"{field}={fields[field]}")
        
        # Add body fields
        for field, value in body_fields.items():
            message_parts.append(f"{field}={value}")
        
        return '\x01'.join(message_parts) + '\x01'
    
    def _add_checksum(self, message: str) -> str:
        """Add checksum to FIX message"""
        
        checksum = self._calculate_checksum(message.encode(self.config.message_encoding))
        return message + f"10={checksum:03d}\x01"
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate FIX checksum"""
        
        # Sum all bytes except checksum field
        checksum_pos = data.rfind(b'10=')
        if checksum_pos >= 0:
            data = data[:checksum_pos]
        
        return sum(data) % 256
    
    def _get_fix_message_type(self, message_type: MessageType) -> str:
        """Map message type to FIX message type"""
        
        mapping = {
            MessageType.LOGON: 'A',
            MessageType.LOGOUT: '5',
            MessageType.HEARTBEAT: '0',
            MessageType.TEST_REQUEST: '1',
            MessageType.NEW_ORDER: 'D',
            MessageType.ORDER_CANCEL: 'F',
            MessageType.ORDER_REPLACE: 'G',
            MessageType.EXECUTION_REPORT: '8',
            MessageType.ORDER_STATUS: 'H',
            MessageType.MARKET_DATA_REQUEST: 'V',
            MessageType.MARKET_DATA_SNAPSHOT: 'W',
            MessageType.SEQUENCE_RESET: '4',
            MessageType.RESEND_REQUEST: '2',
            MessageType.REJECT: '3'
        }
        
        return mapping.get(message_type, 'U')  # User-defined
    
    def _get_message_type_from_fix(self, fix_msg_type: str) -> MessageType:
        """Map FIX message type to message type"""
        
        mapping = {
            'A': MessageType.LOGON,
            '5': MessageType.LOGOUT,
            '0': MessageType.HEARTBEAT,
            '1': MessageType.TEST_REQUEST,
            'D': MessageType.NEW_ORDER,
            'F': MessageType.ORDER_CANCEL,
            'G': MessageType.ORDER_REPLACE,
            '8': MessageType.EXECUTION_REPORT,
            'H': MessageType.ORDER_STATUS,
            'V': MessageType.MARKET_DATA_REQUEST,
            'W': MessageType.MARKET_DATA_SNAPSHOT,
            '4': MessageType.SEQUENCE_RESET,
            '2': MessageType.RESEND_REQUEST,
            '3': MessageType.REJECT
        }
        
        return mapping.get(fix_msg_type, MessageType.CUSTOM)
    
    def _map_data_to_fix_fields(self, message_type: MessageType, data: Dict[str, Any]) -> Dict[str, str]:
        """Map data to FIX fields"""
        
        fields = {}
        
        if message_type == MessageType.NEW_ORDER:
            fields.update({
                '11': data.get('ClOrdID', str(uuid.uuid4())),  # Client Order ID
                '55': data.get('Symbol', ''),  # Symbol
                '54': data.get('Side', ''),  # Side
                '38': str(data.get('OrderQty', 0)),  # Order Quantity
                '40': data.get('OrdType', ''),  # Order Type
                '44': str(data.get('Price', 0)) if 'Price' in data else '',  # Price
                '59': data.get('TimeInForce', ''),  # Time in Force
            })
        
        elif message_type == MessageType.ORDER_CANCEL:
            fields.update({
                '11': data.get('ClOrdID', str(uuid.uuid4())),
                '41': data.get('OrigClOrdID', ''),  # Original Client Order ID
                '55': data.get('Symbol', ''),
                '54': data.get('Side', ''),
            })
        
        elif message_type == MessageType.MARKET_DATA_REQUEST:
            fields.update({
                '262': data.get('MDReqID', str(uuid.uuid4())),  # Market Data Request ID
                '263': data.get('SubscriptionRequestType', ''),  # Subscription Request Type
                '264': str(data.get('MarketDepth', 0)),  # Market Depth
            })
        
        # Add custom fields
        for key, value in data.items():
            if key not in fields and isinstance(key, str) and key.isdigit():
                fields[key] = str(value)
        
        return fields


class RESTProtocolHandler(ProtocolHandlerInterface):
    """REST Protocol Handler"""
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self._session = None
        self._base_url = config.url
        
        logger.info("REST protocol handler initialized")
    
    async def connect(self) -> bool:
        """Connect using REST (HTTP session)"""
        try:
            import aiohttp
            
            timeout = aiohttp.ClientTimeout(total=self.config.connect_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            
            # Test connection with a simple request
            if self.config.api_key:
                headers = {'Authorization': f'Bearer {self.config.api_key}'}
                async with self._session.get(f"{self._base_url}/health", headers=headers) as response:
                    if response.status == 200:
                        logger.info("REST protocol connected")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect via REST protocol: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from REST"""
        try:
            if self._session:
                await self._session.close()
            
            logger.info("REST protocol disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting REST protocol: {e}")
            return False
    
    async def send_message(self, message: ProtocolMessage) -> bool:
        """Send REST message (HTTP request)"""
        try:
            if not self._session:
                raise RuntimeError("REST session not connected")
            
            # Determine HTTP method and endpoint
            method, endpoint = self._get_rest_method_endpoint(message.message_type)
            url = f"{self._base_url}{endpoint}"
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                **message.headers
            }
            
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            
            # Send request
            async with self._session.request(
                method, 
                url, 
                json=message.parsed_data,
                headers=headers
            ) as response:
                
                message.sent_at = datetime.now()
                
                if response.status in [200, 201, 202]:
                    response_data = await response.json()
                    
                    # Create response message
                    response_message = ProtocolMessage(
                        message_id=str(uuid.uuid4()),
                        message_type=message.message_type,
                        direction=MessageDirection.INBOUND,
                        protocol_type=ProtocolType.REST,
                        raw_data=await response.read(),
                        parsed_data=response_data,
                        correlation_id=message.message_id
                    )
                    
                    self._trigger_message_handlers(response_message)
                    
                    logger.debug(f"Sent REST message: {message.message_type.value}")
                    return True
                else:
                    logger.error(f"REST request failed: {response.status}")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to send REST message: {e}")
            return False
    
    async def receive_message(self) -> Optional[ProtocolMessage]:
        """Receive REST message (not applicable for request-response)"""
        # REST is typically request-response, not streaming
        return None
    
    def create_message(self, message_type: MessageType, data: Dict[str, Any]) -> ProtocolMessage:
        """Create REST message"""
        
        message = ProtocolMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            direction=MessageDirection.OUTBOUND,
            protocol_type=ProtocolType.REST,
            raw_data=b'',
            parsed_data=data
        )
        
        return message
    
    def parse_message(self, raw_data: bytes) -> ProtocolMessage:
        """Parse REST response"""
        
        try:
            data = json.loads(raw_data.decode(self.config.message_encoding))
            
            message = ProtocolMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.CUSTOM,
                direction=MessageDirection.INBOUND,
                protocol_type=ProtocolType.REST,
                raw_data=raw_data,
                parsed_data=data
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to parse REST message: {e}")
            
            return ProtocolMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.CUSTOM,
                direction=MessageDirection.INBOUND,
                protocol_type=ProtocolType.REST,
                raw_data=raw_data,
                parsed_data={},
                is_valid=False,
                validation_errors=[str(e)]
            )
    
    def validate_message(self, message: ProtocolMessage) -> bool:
        """Validate REST message"""
        
        # Basic JSON validation
        try:
            if isinstance(message.parsed_data, dict):
                return True
            return False
        except Exception:
            return False
    
    def _get_rest_method_endpoint(self, message_type: MessageType) -> Tuple[str, str]:
        """Get REST method and endpoint for message type"""
        
        mapping = {
            MessageType.NEW_ORDER: ('POST', '/orders'),
            MessageType.ORDER_CANCEL: ('DELETE', '/orders/{order_id}'),
            MessageType.ORDER_REPLACE: ('PUT', '/orders/{order_id}'),
            MessageType.ORDER_STATUS: ('GET', '/orders/{order_id}'),
            MessageType.MARKET_DATA_REQUEST: ('GET', '/market-data/{symbol}'),
        }
        
        return mapping.get(message_type, ('POST', '/custom'))


class WebSocketProtocolHandler(ProtocolHandlerInterface):
    """WebSocket Protocol Handler"""
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self._websocket = None
        self._receive_task = None
        
        logger.info("WebSocket protocol handler initialized")
    
    async def connect(self) -> bool:
        """Connect using WebSocket"""
        try:
            import websockets
            
            # Create WebSocket connection
            self._websocket = await websockets.connect(
                self.config.url,
                timeout=self.config.connect_timeout
            )
            
            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            logger.info("WebSocket protocol connected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect via WebSocket protocol: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from WebSocket"""
        try:
            if self._receive_task:
                self._receive_task.cancel()
            
            if self._websocket:
                await self._websocket.close()
            
            logger.info("WebSocket protocol disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket protocol: {e}")
            return False
    
    async def send_message(self, message: ProtocolMessage) -> bool:
        """Send WebSocket message"""
        try:
            if not self._websocket:
                raise RuntimeError("WebSocket not connected")
            
            # Convert to JSON
            message_data = {
                'type': message.message_type.value,
                'data': message.parsed_data,
                'id': message.message_id
            }
            
            await self._websocket.send(json.dumps(message_data))
            message.sent_at = datetime.now()
            
            logger.debug(f"Sent WebSocket message: {message.message_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            return False
    
    async def receive_message(self) -> Optional[ProtocolMessage]:
        """Receive WebSocket message"""
        # Messages are received in the background loop
        return None
    
    async def _receive_loop(self) -> None:
        """WebSocket receive loop"""
        
        while self._websocket:
            try:
                raw_data = await self._websocket.recv()
                
                if isinstance(raw_data, str):
                    raw_data = raw_data.encode(self.config.message_encoding)
                
                message = self.parse_message(raw_data)
                message.received_at = datetime.now()
                
                self._trigger_message_handlers(message)
                
            except Exception as e:
                logger.error(f"Error in WebSocket receive loop: {e}")
                break
    
    def create_message(self, message_type: MessageType, data: Dict[str, Any]) -> ProtocolMessage:
        """Create WebSocket message"""
        
        message = ProtocolMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            direction=MessageDirection.OUTBOUND,
            protocol_type=ProtocolType.WEBSOCKET,
            raw_data=b'',
            parsed_data=data
        )
        
        return message
    
    def parse_message(self, raw_data: bytes) -> ProtocolMessage:
        """Parse WebSocket message"""
        
        try:
            message_str = raw_data.decode(self.config.message_encoding)
            data = json.loads(message_str)
            
            message_type_str = data.get('type', 'custom')
            message_type = MessageType(message_type_str) if message_type_str in [mt.value for mt in MessageType] else MessageType.CUSTOM
            
            message = ProtocolMessage(
                message_id=data.get('id', str(uuid.uuid4())),
                message_type=message_type,
                direction=MessageDirection.INBOUND,
                protocol_type=ProtocolType.WEBSOCKET,
                raw_data=raw_data,
                parsed_data=data.get('data', data)
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
            
            return ProtocolMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.CUSTOM,
                direction=MessageDirection.INBOUND,
                protocol_type=ProtocolType.WEBSOCKET,
                raw_data=raw_data,
                parsed_data={},
                is_valid=False,
                validation_errors=[str(e)]
            )
    
    def validate_message(self, message: ProtocolMessage) -> bool:
        """Validate WebSocket message"""
        
        try:
            if isinstance(message.parsed_data, dict):
                return True
            return False
        except Exception:
            return False


class ProtocolHandler:
    """
    Multi-Protocol Handler
    
    Manages multiple communication protocols for broker connectivity
    with automatic protocol selection and message routing.
    """
    
    def __init__(self):
        """Initialize protocol handler"""
        
        self._handlers: Dict[ProtocolType, ProtocolHandlerInterface] = {}
        self._active_protocols: Set[ProtocolType] = set()
        
        # Message routing
        self._message_queue = asyncio.Queue()
        self._response_futures: Dict[str, asyncio.Future] = {}
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        
        # Event handlers
        self._event_handlers = defaultdict(list)
        
        logger.info("Protocol handler initialized")
    
    def register_protocol(self, protocol_type: ProtocolType, 
                         config: ProtocolConfig) -> None:
        """Register protocol handler"""
        
        try:
            if protocol_type == ProtocolType.FIX:
                handler = FIXProtocolHandler(config)
            elif protocol_type == ProtocolType.REST:
                handler = RESTProtocolHandler(config)
            elif protocol_type == ProtocolType.WEBSOCKET:
                handler = WebSocketProtocolHandler(config)
            else:
                raise ValueError(f"Unsupported protocol type: {protocol_type}")
            
            self._handlers[protocol_type] = handler
            
            # Add event handlers
            handler.add_event_handler('message_received', self._handle_message_received)
            handler.add_event_handler('connection_lost', self._handle_connection_lost)
            
            logger.info(f"Registered protocol handler: {protocol_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to register protocol {protocol_type.value}: {e}")
            raise
    
    async def connect_protocol(self, protocol_type: ProtocolType) -> bool:
        """Connect to specific protocol"""
        
        try:
            if protocol_type not in self._handlers:
                logger.error(f"Protocol {protocol_type.value} not registered")
                return False
            
            handler = self._handlers[protocol_type]
            success = await handler.connect()
            
            if success:
                self._active_protocols.add(protocol_type)
                
                self._trigger_event('protocol_connected', {
                    'protocol_type': protocol_type.value
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to connect protocol {protocol_type.value}: {e}")
            return False
    
    async def disconnect_protocol(self, protocol_type: ProtocolType) -> bool:
        """Disconnect from specific protocol"""
        
        try:
            if protocol_type not in self._handlers:
                return True
            
            handler = self._handlers[protocol_type]
            success = await handler.disconnect()
            
            if success and protocol_type in self._active_protocols:
                self._active_protocols.remove(protocol_type)
                
                self._trigger_event('protocol_disconnected', {
                    'protocol_type': protocol_type.value
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to disconnect protocol {protocol_type.value}: {e}")
            return False
    
    async def send_message(self, protocol_type: ProtocolType,
                          message_type: MessageType,
                          data: Dict[str, Any],
                          wait_for_response: bool = False) -> Union[bool, ProtocolMessage]:
        """Send message via specific protocol"""
        
        try:
            if protocol_type not in self._active_protocols:
                logger.error(f"Protocol {protocol_type.value} not active")
                return False
            
            handler = self._handlers[protocol_type]
            message = handler.create_message(message_type, data)
            
            # Set up response waiting if needed
            response_future = None
            if wait_for_response:
                response_future = asyncio.Future()
                self._response_futures[message.message_id] = response_future
            
            # Send message
            success = await handler.send_message(message)
            
            if success and wait_for_response:
                try:
                    # Wait for response with timeout
                    response = await asyncio.wait_for(response_future, timeout=30.0)
                    return response
                except asyncio.TimeoutError:
                    logger.warning(f"Response timeout for message {message.message_id}")
                    return False
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send message via {protocol_type.value}: {e}")
            return False
    
    def get_active_protocols(self) -> List[ProtocolType]:
        """Get list of active protocols"""
        return list(self._active_protocols)
    
    def is_protocol_active(self, protocol_type: ProtocolType) -> bool:
        """Check if protocol is active"""
        return protocol_type in self._active_protocols
    
    def add_message_handler(self, protocol_type: ProtocolType,
                           message_type: MessageType,
                           handler: Callable[[ProtocolMessage], None]) -> None:
        """Add message handler for specific protocol and message type"""
        
        if protocol_type in self._handlers:
            self._handlers[protocol_type].add_message_handler(message_type, handler)
    
    def add_event_handler(self, event_type: str,
                         handler: Callable[[Dict[str, Any]], None]) -> None:
        """Add event handler"""
        self._event_handlers[event_type].append(handler)
    
    def _handle_message_received(self, data: Dict[str, Any]) -> None:
        """Handle received message"""
        
        message = data.get('message')
        if not message:
            return
        
        # Check if this is a response to a pending request
        if message.correlation_id and message.correlation_id in self._response_futures:
            future = self._response_futures.pop(message.correlation_id)
            if not future.done():
                future.set_result(message)
    
    def _handle_connection_lost(self, data: Dict[str, Any]) -> None:
        """Handle connection lost"""
        
        protocol_type = data.get('protocol_type')
        if protocol_type and ProtocolType(protocol_type) in self._active_protocols:
            self._active_protocols.remove(ProtocolType(protocol_type))
            
            self._trigger_event('protocol_connection_lost', data)
    
    def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger event handlers"""
        for handler in self._event_handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup protocol handler"""
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Disconnect all protocols
        for protocol_type in list(self._active_protocols):
            await self.disconnect_protocol(protocol_type)
        
        # Clear response futures
        for future in self._response_futures.values():
            if not future.done():
                future.cancel()
        
        self._response_futures.clear()
        
        logger.info("Protocol handler cleaned up")
    
    def get_protocol_stats(self) -> Dict[str, Any]:
        """Get protocol statistics"""
        
        stats = {
            'total_protocols': len(self._handlers),
            'active_protocols': len(self._active_protocols),
            'protocol_details': {}
        }
        
        for protocol_type, handler in self._handlers.items():
            is_active = protocol_type in self._active_protocols
            
            stats['protocol_details'][protocol_type.value] = {
                'active': is_active,
                'type': handler.protocol_type.value,
                'config': {
                    'host': handler.config.host,
                    'port': handler.config.port,
                    'url': handler.config.url
                }
            }
        
        return stats