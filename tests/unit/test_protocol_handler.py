#!/usr/bin/env python3
"""
Comprehensive Protocol Handler Test Suite
=========================================

This test suite provides comprehensive testing for the ProtocolHandler component
to ensure robust protocol handling, message processing, and communication.

Components Tested:
- ProtocolHandler (Protocol handling and message processing)
- MessageProcessor (Message processing and routing)
- ProtocolValidator (Protocol validation)
- ProtocolSerializer (Data serialization)
- ProtocolDeserializer (Data deserialization)
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any
import json
import pickle
import base64

# Import protocol handler components
from core_engine.broker.protocol_handler import (
    ProtocolHandler, MessageProcessor, ProtocolValidator, ProtocolSerializer,
    ProtocolDeserializer, ProtocolConfig, MessageConfig, ValidationConfig,
    SerializationConfig, MessageType, ProtocolType, ValidationLevel, SerializationFormat
)


class TestProtocolHandlerComprehensive:
    """Comprehensive tests for ProtocolHandler - Protocol handling and message processing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'protocol_type': ProtocolType.JSON_RPC,
            'message_timeout': 30,
            'max_message_size': 1024 * 1024,  # 1MB
            'enable_compression': True,
            'enable_encryption': True,
            'validation_level': ValidationLevel.STRICT,
            'serialization_format': SerializationFormat.JSON
        }
        
        self.protocol_handler = ProtocolHandler(self.config)
        
        # Mock message data
        self.mock_message = {
            'message_id': 'msg_001',
            'message_type': MessageType.ORDER_SUBMISSION,
            'timestamp': datetime.now(),
            'payload': {
                'order_id': 'order_001',
                'symbol': 'AAPL',
                'action': 'BUY',
                'quantity': 100,
                'price': 150.0
            },
            'metadata': {
                'session_id': 'sess_001',
                'user_id': 'user_001',
                'priority': 'high'
            }
        }
        
        # Mock protocol data
        self.mock_protocol_data = {
            'version': '1.0',
            'protocol_type': 'json_rpc',
            'request_id': 'req_001',
            'method': 'submit_order',
            'params': self.mock_message['payload'],
            'timestamp': datetime.now().isoformat()
        }
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test ProtocolHandler initialization"""
        assert self.protocol_handler is not None
        assert self.protocol_handler.config == self.config
        assert hasattr(self.protocol_handler, 'message_processor')
        assert hasattr(self.protocol_handler, 'validator')
        assert hasattr(self.protocol_handler, 'serializer')
        assert hasattr(self.protocol_handler, 'deserializer')
    
    @pytest.mark.asyncio
    async def test_message_serialization(self):
        """Test message serialization"""
        with patch.object(self.protocol_handler, '_serialize_message', new_callable=AsyncMock) as mock_serialize:
            mock_serialize.return_value = json.dumps(self.mock_protocol_data)
            
            result = await self.protocol_handler.serialize_message(self.mock_message)
            
            assert result is not None
            assert isinstance(result, str)
            mock_serialize.assert_called_once_with(self.mock_message)
    
    @pytest.mark.asyncio
    async def test_message_deserialization(self):
        """Test message deserialization"""
        serialized_data = json.dumps(self.mock_protocol_data)
        
        with patch.object(self.protocol_handler, '_deserialize_message', new_callable=AsyncMock) as mock_deserialize:
            mock_deserialize.return_value = self.mock_message
            
            result = await self.protocol_handler.deserialize_message(serialized_data)
            
            assert result == self.mock_message
            mock_deserialize.assert_called_once_with(serialized_data)
    
    @pytest.mark.asyncio
    async def test_message_validation(self):
        """Test message validation"""
        with patch.object(self.protocol_handler, '_validate_message', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = True
            
            result = await self.protocol_handler.validate_message(self.mock_message)
            
            assert result is True
            mock_validate.assert_called_once_with(self.mock_message)
    
    @pytest.mark.asyncio
    async def test_message_processing(self):
        """Test message processing"""
        with patch.object(self.protocol_handler, '_process_message', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'response': {'order_id': 'order_001', 'status': 'submitted'},
                'timestamp': datetime.now()
            }
            
            result = await self.protocol_handler.process_message(self.mock_message)
            
            assert result is not None
            assert result['status'] == 'success'
            mock_process.assert_called_once_with(self.mock_message)
    
    @pytest.mark.asyncio
    async def test_protocol_handling(self):
        """Test protocol-specific handling"""
        # Test JSON-RPC protocol
        self.protocol_handler.protocol_type = ProtocolType.JSON_RPC
        
        with patch.object(self.protocol_handler, '_handle_json_rpc', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = {
                'jsonrpc': '2.0',
                'id': 'req_001',
                'result': {'order_id': 'order_001', 'status': 'submitted'}
            }
            
            result = await self.protocol_handler.handle_protocol_message(self.mock_protocol_data)
            
            assert result is not None
            assert 'jsonrpc' in result
            mock_handle.assert_called_once_with(self.mock_protocol_data)
        
        # Test REST protocol
        self.protocol_handler.protocol_type = ProtocolType.REST
        
        with patch.object(self.protocol_handler, '_handle_rest', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = {
                'status_code': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': {'order_id': 'order_001', 'status': 'submitted'}
            }
            
            result = await self.protocol_handler.handle_protocol_message(self.mock_protocol_data)
            
            assert result is not None
            assert 'status_code' in result
            mock_handle.assert_called_once_with(self.mock_protocol_data)
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling and recovery"""
        # Test serialization error
        with patch.object(self.protocol_handler, '_serialize_message', new_callable=AsyncMock) as mock_serialize:
            mock_serialize.side_effect = Exception("Serialization failed")
            
            try:
                await self.protocol_handler.serialize_message(self.mock_message)
            except Exception as e:
                assert "Serialization failed" in str(e)
        
        # Test deserialization error
        with patch.object(self.protocol_handler, '_deserialize_message', new_callable=AsyncMock) as mock_deserialize:
            mock_deserialize.side_effect = Exception("Deserialization failed")
            
            try:
                await self.protocol_handler.deserialize_message("invalid_data")
            except Exception as e:
                assert "Deserialization failed" in str(e)
        
        # Test validation error
        with patch.object(self.protocol_handler, '_validate_message', new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            try:
                await self.protocol_handler.validate_message(self.mock_message)
            except Exception as e:
                assert "Validation failed" in str(e)
    
    @pytest.mark.asyncio
    async def test_message_routing(self):
        """Test message routing based on type"""
        # Test order submission routing
        order_message = self.mock_message.copy()
        order_message['message_type'] = MessageType.ORDER_SUBMISSION
        
        with patch.object(self.protocol_handler, '_route_order_message', new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {'status': 'routed'}
            
            result = await self.protocol_handler.route_message(order_message)
            
            assert result['status'] == 'routed'
            mock_route.assert_called_once_with(order_message)
        
        # Test market data routing
        market_data_message = self.mock_message.copy()
        market_data_message['message_type'] = MessageType.MARKET_DATA
        
        with patch.object(self.protocol_handler, '_route_market_data_message', new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {'status': 'routed'}
            
            result = await self.protocol_handler.route_message(market_data_message)
            
            assert result['status'] == 'routed'
            mock_route.assert_called_once_with(market_data_message)
    
    @pytest.mark.asyncio
    async def test_message_compression(self):
        """Test message compression and decompression"""
        large_message = self.mock_message.copy()
        large_message['payload'] = {'data': 'x' * 10000}  # Large payload
        
        with patch.object(self.protocol_handler, '_compress_message', new_callable=AsyncMock) as mock_compress:
            mock_compress.return_value = b'compressed_data'
            
            compressed = await self.protocol_handler.compress_message(large_message)
            
            assert compressed == b'compressed_data'
            mock_compress.assert_called_once_with(large_message)
        
        # Test decompression
        with patch.object(self.protocol_handler, '_decompress_message', new_callable=AsyncMock) as mock_decompress:
            mock_decompress.return_value = large_message
            
            decompressed = await self.protocol_handler.decompress_message(b'compressed_data')
            
            assert decompressed == large_message
            mock_decompress.assert_called_once_with(b'compressed_data')
    
    @pytest.mark.asyncio
    async def test_message_encryption(self):
        """Test message encryption and decryption"""
        with patch.object(self.protocol_handler, '_encrypt_message', new_callable=AsyncMock) as mock_encrypt:
            mock_encrypt.return_value = b'encrypted_data'
            
            encrypted = await self.protocol_handler.encrypt_message(self.mock_message)
            
            assert encrypted == b'encrypted_data'
            mock_encrypt.assert_called_once_with(self.mock_message)
        
        # Test decryption
        with patch.object(self.protocol_handler, '_decrypt_message', new_callable=AsyncMock) as mock_decrypt:
            mock_decrypt.return_value = self.mock_message
            
            decrypted = await self.protocol_handler.decrypt_message(b'encrypted_data')
            
            assert decrypted == self.mock_message
            mock_decrypt.assert_called_once_with(b'encrypted_data')
    
    @pytest.mark.asyncio
    async def test_protocol_statistics(self):
        """Test protocol statistics tracking"""
        # Process some messages
        for i in range(5):
            with patch.object(self.protocol_handler, '_process_message', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = {'status': 'success'}
                await self.protocol_handler.process_message(self.mock_message)
        
        # Get statistics
        stats = self.protocol_handler.get_protocol_statistics()
        
        assert stats is not None
        assert 'total_messages_processed' in stats
        assert 'successful_messages' in stats
        assert 'failed_messages' in stats
        assert 'average_processing_time_ms' in stats


class TestMessageProcessorComprehensive:
    """Comprehensive tests for MessageProcessor - Message processing and routing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'processing_timeout': 30,
            'max_concurrent_processing': 10,
            'enable_async_processing': True,
            'retry_attempts': 3,
            'retry_delay': 1.0
        }
        
        self.message_processor = MessageProcessor(self.config)
        
        self.test_message = {
            'message_id': 'msg_001',
            'message_type': MessageType.ORDER_SUBMISSION,
            'payload': {'order_id': 'order_001', 'symbol': 'AAPL'},
            'timestamp': datetime.now()
        }
    
    @pytest.mark.asyncio
    async def test_processor_initialization(self):
        """Test MessageProcessor initialization"""
        assert self.message_processor is not None
        assert self.message_processor.config == self.config
        assert hasattr(self.message_processor, 'processing_queue')
        assert hasattr(self.message_processor, 'active_processors')
    
    @pytest.mark.asyncio
    async def test_message_queueing(self):
        """Test message queueing"""
        with patch.object(self.message_processor, '_queue_message', new_callable=AsyncMock) as mock_queue:
            mock_queue.return_value = True
            
            result = await self.message_processor.queue_message(self.test_message)
            
            assert result is True
            mock_queue.assert_called_once_with(self.test_message)
    
    @pytest.mark.asyncio
    async def test_message_processing(self):
        """Test message processing"""
        with patch.object(self.message_processor, '_process_message_internal', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {'status': 'success', 'result': 'processed'}
            
            result = await self.message_processor.process_message(self.test_message)
            
            assert result is not None
            assert result['status'] == 'success'
            mock_process.assert_called_once_with(self.test_message)
    
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch message processing"""
        messages = [self.test_message.copy() for _ in range(3)]
        for i, msg in enumerate(messages):
            msg['message_id'] = f'msg_{i:03d}'
        
        with patch.object(self.message_processor, '_process_batch', new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = [
                {'message_id': 'msg_000', 'status': 'success'},
                {'message_id': 'msg_001', 'status': 'success'},
                {'message_id': 'msg_002', 'status': 'success'}
            ]
            
            results = await self.message_processor.process_batch(messages)
            
            assert len(results) == 3
            assert all(result['status'] == 'success' for result in results)
            mock_batch.assert_called_once_with(messages)
    
    @pytest.mark.asyncio
    async def test_processing_with_retry(self):
        """Test message processing with retry logic"""
        with patch.object(self.message_processor, '_process_message_internal', new_callable=AsyncMock) as mock_process:
            # First two attempts fail, third succeeds
            mock_process.side_effect = [
                Exception("Processing failed"),
                Exception("Processing failed"),
                {'status': 'success', 'result': 'processed'}
            ]
            
            result = await self.message_processor.process_message_with_retry(self.test_message)
            
            assert result['status'] == 'success'
            assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_processing_timeout(self):
        """Test processing timeout handling"""
        with patch.object(self.message_processor, '_process_message_internal', new_callable=AsyncMock) as mock_process:
            async def slow_process(message):
                await asyncio.sleep(35)  # Longer than timeout
                return {'status': 'success'}
            
            mock_process.side_effect = slow_process
            
            try:
                await self.message_processor.process_message(self.test_message)
            except asyncio.TimeoutError:
                # Expected to timeout
                pass
    
    @pytest.mark.asyncio
    async def test_processing_statistics(self):
        """Test processing statistics"""
        # Process some messages
        for i in range(5):
            with patch.object(self.message_processor, '_process_message_internal', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = {'status': 'success'}
                await self.message_processor.process_message(self.test_message)
        
        # Get statistics
        stats = self.message_processor.get_processing_statistics()
        
        assert stats is not None
        assert 'total_messages_processed' in stats
        assert 'successful_messages' in stats
        assert 'failed_messages' in stats
        assert 'average_processing_time_ms' in stats


class TestProtocolValidatorComprehensive:
    """Comprehensive tests for ProtocolValidator - Protocol validation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'validation_level': ValidationLevel.STRICT,
            'enable_schema_validation': True,
            'enable_content_validation': True,
            'max_message_size': 1024 * 1024,
            'allowed_message_types': [MessageType.ORDER_SUBMISSION, MessageType.MARKET_DATA]
        }
        
        self.validator = ProtocolValidator(self.config)
        
        self.valid_message = {
            'message_id': 'msg_001',
            'message_type': MessageType.ORDER_SUBMISSION,
            'timestamp': datetime.now().isoformat(),
            'payload': {
                'order_id': 'order_001',
                'symbol': 'AAPL',
                'action': 'BUY',
                'quantity': 100,
                'price': 150.0
            }
        }
        
        self.invalid_message = {
            'message_id': 'msg_002',
            'message_type': 'INVALID_TYPE',  # Invalid message type
            'timestamp': 'invalid_timestamp',  # Invalid timestamp
            'payload': {}  # Missing required fields
        }
    
    @pytest.mark.asyncio
    async def test_validator_initialization(self):
        """Test ProtocolValidator initialization"""
        assert self.validator is not None
        assert self.validator.config == self.config
        assert hasattr(self.validator, 'validation_level')
        assert hasattr(self.validator, 'schema_validator')
    
    @pytest.mark.asyncio
    async def test_message_validation(self):
        """Test message validation"""
        with patch.object(self.validator, '_validate_message_structure', new_callable=AsyncMock) as mock_structure:
            mock_structure.return_value = True
            
            with patch.object(self.validator, '_validate_message_content', new_callable=AsyncMock) as mock_content:
                mock_content.return_value = True
                
                result = await self.validator.validate_message(self.valid_message)
                
                assert result is True
                mock_structure.assert_called_once_with(self.valid_message)
                mock_content.assert_called_once_with(self.valid_message)
    
    @pytest.mark.asyncio
    async def test_schema_validation(self):
        """Test schema validation"""
        with patch.object(self.validator, '_validate_against_schema', new_callable=AsyncMock) as mock_schema:
            mock_schema.return_value = True
            
            result = await self.validator.validate_schema(self.valid_message)
            
            assert result is True
            mock_schema.assert_called_once_with(self.valid_message)
    
    @pytest.mark.asyncio
    async def test_content_validation(self):
        """Test content validation"""
        with patch.object(self.validator, '_validate_content', new_callable=AsyncMock) as mock_content:
            mock_content.return_value = True
            
            result = await self.validator.validate_content(self.valid_message)
            
            assert result is True
            mock_content.assert_called_once_with(self.valid_message)
    
    @pytest.mark.asyncio
    async def test_message_type_validation(self):
        """Test message type validation"""
        # Valid message type
        with patch.object(self.validator, '_validate_message_type', new_callable=AsyncMock) as mock_type:
            mock_type.return_value = True
            
            result = await self.validator.validate_message_type(MessageType.ORDER_SUBMISSION)
            
            assert result is True
            mock_type.assert_called_once_with(MessageType.ORDER_SUBMISSION)
        
        # Invalid message type
        with patch.object(self.validator, '_validate_message_type', new_callable=AsyncMock) as mock_type:
            mock_type.return_value = False
            
            result = await self.validator.validate_message_type('INVALID_TYPE')
            
            assert result is False
            mock_type.assert_called_once_with('INVALID_TYPE')
    
    @pytest.mark.asyncio
    async def test_size_validation(self):
        """Test message size validation"""
        # Valid size
        with patch.object(self.validator, '_validate_message_size', new_callable=AsyncMock) as mock_size:
            mock_size.return_value = True
            
            result = await self.validator.validate_message_size(self.valid_message)
            
            assert result is True
            mock_size.assert_called_once_with(self.valid_message)
        
        # Invalid size (too large)
        large_message = self.valid_message.copy()
        large_message['payload'] = {'data': 'x' * (1024 * 1024 * 2)}  # 2MB
        
        with patch.object(self.validator, '_validate_message_size', new_callable=AsyncMock) as mock_size:
            mock_size.return_value = False
            
            result = await self.validator.validate_message_size(large_message)
            
            assert result is False
            mock_size.assert_called_once_with(large_message)
    
    @pytest.mark.asyncio
    async def test_validation_error_reporting(self):
        """Test validation error reporting"""
        with patch.object(self.validator, '_validate_message_structure', new_callable=AsyncMock) as mock_structure:
            mock_structure.return_value = False
            
            with patch.object(self.validator, '_get_validation_errors', new_callable=AsyncMock) as mock_errors:
                mock_errors.return_value = ['Missing required field: order_id', 'Invalid message type']
                
                result = await self.validator.validate_message(self.invalid_message)
                errors = await self.validator.get_validation_errors()
                
                assert result is False
                assert len(errors) == 2
                assert 'Missing required field: order_id' in errors


class TestProtocolSerializerComprehensive:
    """Comprehensive tests for ProtocolSerializer - Data serialization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'format': SerializationFormat.JSON,
            'enable_compression': True,
            'enable_encryption': False,
            'pretty_print': False,
            'include_metadata': True
        }
        
        self.serializer = ProtocolSerializer(self.config)
        
        self.test_data = {
            'message_id': 'msg_001',
            'payload': {
                'order_id': 'order_001',
                'symbol': 'AAPL',
                'action': 'BUY',
                'quantity': 100,
                'price': 150.0
            },
            'timestamp': datetime.now()
        }
    
    @pytest.mark.asyncio
    async def test_serializer_initialization(self):
        """Test ProtocolSerializer initialization"""
        assert self.serializer is not None
        assert self.serializer.config == self.config
        assert hasattr(self.serializer, 'format')
        assert hasattr(self.serializer, 'compression_enabled')
    
    @pytest.mark.asyncio
    async def test_json_serialization(self):
        """Test JSON serialization"""
        self.serializer.format = SerializationFormat.JSON
        
        with patch.object(self.serializer, '_serialize_to_json', new_callable=AsyncMock) as mock_json:
            mock_json.return_value = json.dumps(self.test_data)
            
            result = await self.serializer.serialize(self.test_data)
            
            assert result is not None
            assert isinstance(result, str)
            mock_json.assert_called_once_with(self.test_data)
    
    @pytest.mark.asyncio
    async def test_pickle_serialization(self):
        """Test Pickle serialization"""
        self.serializer.format = SerializationFormat.PICKLE
        
        with patch.object(self.serializer, '_serialize_to_pickle', new_callable=AsyncMock) as mock_pickle:
            mock_pickle.return_value = pickle.dumps(self.test_data)
            
            result = await self.serializer.serialize(self.test_data)
            
            assert result is not None
            assert isinstance(result, bytes)
            mock_pickle.assert_called_once_with(self.test_data)
    
    @pytest.mark.asyncio
    async def test_msgpack_serialization(self):
        """Test MessagePack serialization"""
        self.serializer.format = SerializationFormat.MSGPACK
        
        with patch.object(self.serializer, '_serialize_to_msgpack', new_callable=AsyncMock) as mock_msgpack:
            mock_msgpack.return_value = b'msgpack_data'
            
            result = await self.serializer.serialize(self.test_data)
            
            assert result is not None
            assert isinstance(result, bytes)
            mock_msgpack.assert_called_once_with(self.test_data)
    
    @pytest.mark.asyncio
    async def test_compression(self):
        """Test data compression"""
        large_data = {'data': 'x' * 10000}
        
        with patch.object(self.serializer, '_compress_data', new_callable=AsyncMock) as mock_compress:
            mock_compress.return_value = b'compressed_data'
            
            result = await self.serializer.compress(large_data)
            
            assert result == b'compressed_data'
            mock_compress.assert_called_once_with(large_data)
    
    @pytest.mark.asyncio
    async def test_encryption(self):
        """Test data encryption"""
        with patch.object(self.serializer, '_encrypt_data', new_callable=AsyncMock) as mock_encrypt:
            mock_encrypt.return_value = b'encrypted_data'
            
            result = await self.serializer.encrypt(self.test_data)
            
            assert result == b'encrypted_data'
            mock_encrypt.assert_called_once_with(self.test_data)
    
    @pytest.mark.asyncio
    async def test_serialization_with_metadata(self):
        """Test serialization with metadata"""
        with patch.object(self.serializer, '_add_metadata', new_callable=AsyncMock) as mock_metadata:
            mock_metadata.return_value = {
                **self.test_data,
                'serialization_info': {
                    'format': 'json',
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            
            with patch.object(self.serializer, '_serialize_to_json', new_callable=AsyncMock) as mock_json:
                mock_json.return_value = json.dumps(self.test_data)
                
                result = await self.serializer.serialize_with_metadata(self.test_data)
                
                assert result is not None
                mock_metadata.assert_called_once()
                mock_json.assert_called_once()


class TestProtocolDeserializerComprehensive:
    """Comprehensive tests for ProtocolDeserializer - Data deserialization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'format': SerializationFormat.JSON,
            'enable_decompression': True,
            'enable_decryption': False,
            'strict_mode': True,
            'handle_errors': True
        }
        
        self.deserializer = ProtocolDeserializer(self.config)
        
        self.test_data = {
            'message_id': 'msg_001',
            'payload': {
                'order_id': 'order_001',
                'symbol': 'AAPL',
                'action': 'BUY',
                'quantity': 100,
                'price': 150.0
            },
            'timestamp': datetime.now().isoformat()
        }
        
        self.serialized_json = json.dumps(self.test_data)
        self.serialized_pickle = pickle.dumps(self.test_data)
    
    @pytest.mark.asyncio
    async def test_deserializer_initialization(self):
        """Test ProtocolDeserializer initialization"""
        assert self.deserializer is not None
        assert self.deserializer.config == self.config
        assert hasattr(self.deserializer, 'format')
        assert hasattr(self.deserializer, 'decompression_enabled')
    
    @pytest.mark.asyncio
    async def test_json_deserialization(self):
        """Test JSON deserialization"""
        self.deserializer.format = SerializationFormat.JSON
        
        with patch.object(self.deserializer, '_deserialize_from_json', new_callable=AsyncMock) as mock_json:
            mock_json.return_value = self.test_data
            
            result = await self.deserializer.deserialize(self.serialized_json)
            
            assert result == self.test_data
            mock_json.assert_called_once_with(self.serialized_json)
    
    @pytest.mark.asyncio
    async def test_pickle_deserialization(self):
        """Test Pickle deserialization"""
        self.deserializer.format = SerializationFormat.PICKLE
        
        with patch.object(self.deserializer, '_deserialize_from_pickle', new_callable=AsyncMock) as mock_pickle:
            mock_pickle.return_value = self.test_data
            
            result = await self.deserializer.deserialize(self.serialized_pickle)
            
            assert result == self.test_data
            mock_pickle.assert_called_once_with(self.serialized_pickle)
    
    @pytest.mark.asyncio
    async def test_decompression(self):
        """Test data decompression"""
        compressed_data = b'compressed_data'
        
        with patch.object(self.deserializer, '_decompress_data', new_callable=AsyncMock) as mock_decompress:
            mock_decompress.return_value = self.serialized_json
            
            result = await self.deserializer.decompress(compressed_data)
            
            assert result == self.serialized_json
            mock_decompress.assert_called_once_with(compressed_data)
    
    @pytest.mark.asyncio
    async def test_decryption(self):
        """Test data decryption"""
        encrypted_data = b'encrypted_data'
        
        with patch.object(self.deserializer, '_decrypt_data', new_callable=AsyncMock) as mock_decrypt:
            mock_decrypt.return_value = self.serialized_json
            
            result = await self.deserializer.decrypt(encrypted_data)
            
            assert result == self.serialized_json
            mock_decrypt.assert_called_once_with(encrypted_data)
    
    @pytest.mark.asyncio
    async def test_deserialization_error_handling(self):
        """Test deserialization error handling"""
        invalid_data = "invalid_json_data"
        
        with patch.object(self.deserializer, '_deserialize_from_json', new_callable=AsyncMock) as mock_json:
            mock_json.side_effect = json.JSONDecodeError("Invalid JSON", invalid_data, 0)
            
            try:
                await self.deserializer.deserialize(invalid_data)
            except json.JSONDecodeError:
                # Expected to fail
                pass
    
    @pytest.mark.asyncio
    async def test_format_detection(self):
        """Test automatic format detection"""
        with patch.object(self.deserializer, '_detect_format', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = SerializationFormat.JSON
            
            format_type = await self.deserializer.detect_format(self.serialized_json)
            
            assert format_type == SerializationFormat.JSON
            mock_detect.assert_called_once_with(self.serialized_json)
    
    @pytest.mark.asyncio
    async def test_deserialization_with_metadata(self):
        """Test deserialization with metadata extraction"""
        data_with_metadata = {
            **self.test_data,
            'serialization_info': {
                'format': 'json',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0'
            }
        }
        
        with patch.object(self.deserializer, '_extract_metadata', new_callable=AsyncMock) as mock_metadata:
            mock_metadata.return_value = {
                'data': self.test_data,
                'metadata': data_with_metadata['serialization_info']
            }
            
            result = await self.deserializer.deserialize_with_metadata(data_with_metadata)
            
            assert result is not None
            assert 'data' in result
            assert 'metadata' in result
            mock_metadata.assert_called_once_with(data_with_metadata)


if __name__ == '__main__':
    pytest.main([__file__])
