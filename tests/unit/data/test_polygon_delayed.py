"""
Unit tests for Polygon Delayed Feed Adapter
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

from core_engine.data.feeds.polygon_delayed import (
    PolygonDelayedFeedAdapter,
    PolygonDelayedFeedConfig,
)
from core_engine.data.feeds.adapters import FeedProvider

class TestPolygonDelayedFeedAdapter:
    """Test cases for PolygonDelayedFeedAdapter"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return PolygonDelayedFeedConfig(
            provider=FeedProvider.POLYGON,
            name="test_polygon_delayed",
            api_key="test_api_key",
            symbols=["AAPL", "TSLA"],
        )

    @pytest.fixture
    def adapter(self, config):
        """Test adapter instance"""
        return PolygonDelayedFeedAdapter(config)

    @pytest.mark.asyncio
    async def test_initialization(self, adapter, config):
        """Test adapter initialization"""
        assert adapter.config == config
        assert adapter.websocket is None
        assert not adapter._connected
        assert len(adapter._subscribed_symbols) == 0
        assert adapter._reconnect_task is None
        assert adapter._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_is_connected_property(self, adapter):
        """Test is_connected property"""
        assert not adapter.is_connected

        # Simulate connection
        adapter._connected = True
        adapter.websocket = Mock()
        assert adapter.is_connected

        # Simulate disconnection
        adapter._connected = False
        assert not adapter.is_connected

    @pytest.mark.asyncio
    async def test_connect_success(self, adapter):
        """Test successful connection"""
        with patch('websockets.connect', new_callable=AsyncMock) as mock_ws_connect, \
             patch.object(adapter, '_authenticate', return_value=True) as mock_auth:

            mock_websocket = AsyncMock()
            mock_ws_connect.return_value = mock_websocket

            result = await adapter.connect()

            assert result is True
            assert adapter._connected is True
            assert adapter.websocket == mock_websocket
            mock_ws_connect.assert_called_once()
            mock_auth.assert_called_once()
            # Heartbeat task should be created
            assert adapter._heartbeat_task is not None

    @pytest.mark.asyncio
    async def test_connect_websocket_failure(self, adapter):
        """Test connection failure due to WebSocket error"""
        with patch('websockets.connect', side_effect=Exception("Connection failed")):
            result = await adapter.connect()

            assert result is False
            assert adapter._connected is False
            assert adapter.websocket is None

    @pytest.mark.asyncio
    async def test_connect_authentication_failure(self, adapter):
        """Test connection failure due to authentication error"""
        with patch('websockets.connect', new_callable=AsyncMock) as mock_ws_connect, \
             patch.object(adapter, '_authenticate', return_value=False) as mock_auth:

            mock_websocket = AsyncMock()
            mock_ws_connect.return_value = mock_websocket

            result = await adapter.connect()

            assert result is False
            assert adapter._connected is False
            mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        """Test disconnect functionality"""
        # Setup mock websocket and tasks
        mock_websocket = AsyncMock()
        adapter.websocket = mock_websocket
        adapter._connected = True

        # Create separate mock tasks (use regular Mock, not AsyncMock, since cancel() is synchronous)
        heartbeat_task = Mock()
        reconnect_task = Mock()
        adapter._heartbeat_task = heartbeat_task
        adapter._reconnect_task = reconnect_task

        await adapter.disconnect()

        assert adapter._connected is False
        assert adapter.websocket is None
        assert adapter._heartbeat_task is None
        assert adapter._reconnect_task is None
        heartbeat_task.cancel.assert_called_once()
        reconnect_task.cancel.assert_called_once()
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_success(self, adapter):
        """Test successful authentication"""
        mock_websocket = AsyncMock()
        adapter.websocket = mock_websocket

        # Mock successful auth response
        auth_response = json.dumps([{"ev": "status", "status": "auth_success"}])
        mock_websocket.recv = AsyncMock(return_value=auth_response)

        result = await adapter._authenticate()
        assert result is True

        # Check that auth message was sent
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message["action"] == "auth"
        assert sent_message["params"] == adapter.config.api_key

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, adapter):
        """Test authentication failure"""
        mock_websocket = AsyncMock()
        adapter.websocket = mock_websocket

        # Mock failed auth response
        auth_response = json.dumps([{"ev": "status", "status": "auth_failed"}])
        mock_websocket.recv = AsyncMock(return_value=auth_response)

        result = await adapter._authenticate()
        assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_timeout(self, adapter):
        """Test authentication timeout"""
        mock_websocket = AsyncMock()
        adapter.websocket = mock_websocket

        # Mock timeout
        mock_websocket.recv = AsyncMock(side_effect=asyncio.TimeoutError())

        result = await adapter._authenticate()
        assert result is False

    @pytest.mark.asyncio
    async def test_subscribe_success(self, adapter):
        """Test successful subscription"""
        mock_websocket = AsyncMock()
        adapter.websocket = mock_websocket
        adapter._connected = True

        result = await adapter.subscribe(["AAPL"], ["second_agg", "trade"])

        assert result is True
        assert "AAPL" in adapter._subscribed_symbols

        # Check subscription message
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message["action"] == "subscribe"
        assert "A.AAPL" in sent_message["params"]
        assert "T.AAPL" in sent_message["params"]

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, adapter):
        """Test subscription when not connected"""
        adapter._connected = False

        result = await adapter.subscribe(["AAPL"], ["second_agg"])

        assert result is False

    @pytest.mark.asyncio
    async def test_subscribe_invalid_data_types(self, adapter):
        """Test subscription with invalid data types"""
        mock_websocket = AsyncMock()
        adapter.websocket = mock_websocket
        adapter._connected = True

        result = await adapter.subscribe(["AAPL"], ["invalid_type"])

        assert result is False
        mock_websocket.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_success(self, adapter):
        """Test successful unsubscription"""
        mock_websocket = AsyncMock()
        adapter.websocket = mock_websocket
        adapter._connected = True
        adapter._subscribed_symbols.add("AAPL")

        result = await adapter.unsubscribe(["AAPL"], ["second_agg", "trade"])

        assert result is True
        assert "AAPL" not in adapter._subscribed_symbols

        # Check unsubscription message
        mock_websocket.send.assert_called_once()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message["action"] == "unsubscribe"
        assert "A.AAPL" in sent_message["params"]
        assert "T.AAPL" in sent_message["params"]

    @pytest.mark.asyncio
    async def test_unsubscribe_not_connected(self, adapter):
        """Test unsubscription when not connected"""
        adapter._connected = False

        result = await adapter.unsubscribe(["AAPL"], ["second_agg"])

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_aggregate_message(self, adapter):
        """Test handling of aggregate bar messages"""
        mock_handler = Mock()
        adapter.add_message_handler(mock_handler)

        # Second aggregate message
        agg_msg = {
            "ev": "A",
            "sym": "AAPL",
            "o": 150.0,
            "h": 151.0,
            "l": 149.0,
            "c": 150.5,
            "v": 1000,
            "vw": 150.25,
            "s": 1609459200000,  # 2021-01-01 00:00:00 UTC in milliseconds
            "e": 1609459260000,  # 2021-01-01 00:01:00 UTC in milliseconds
            "n": 100,
            "av": 500
        }

        await adapter._handle_message(json.dumps(agg_msg))

        mock_handler.assert_called_once()
        feed_message = mock_handler.call_args[0][0]
        assert feed_message.provider == FeedProvider.POLYGON
        assert feed_message.symbol == "AAPL"
        assert feed_message.message_type == "second_agg"
        assert hasattr(feed_message.data, 'symbol')
        assert feed_message.data.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_handle_minute_aggregate_message(self, adapter):
        """Test handling of minute aggregate bar messages"""
        mock_handler = Mock()
        adapter.add_message_handler(mock_handler)

        # Minute aggregate message
        agg_msg = {
            "ev": "AM",
            "sym": "TSLA",
            "o": 700.0,
            "h": 710.0,
            "l": 695.0,
            "c": 705.0,
            "v": 5000,
            "vw": 702.5,
            "s": 1609459200000,
            "e": 1609459560000,  # 5 minutes later
            "n": 500,
            "av": 2500
        }

        await adapter._handle_message(json.dumps(agg_msg))

        mock_handler.assert_called_once()
        feed_message = mock_handler.call_args[0][0]
        assert feed_message.message_type == "minute_agg"
        assert feed_message.data.symbol == "TSLA"

    @pytest.mark.asyncio
    async def test_handle_trade_message(self, adapter):
        """Test handling of trade messages"""
        mock_handler = Mock()
        adapter.add_message_handler(mock_handler)

        trade_msg = {
            "ev": "T",
            "sym": "AAPL",
            "p": 150.25,
            "s": 100,
            "t": 1609459200000000000,  # nanoseconds
            "c": [1, 2],
            "x": 4,
            "z": 3,
            "i": "12345"
        }

        await adapter._handle_message(json.dumps(trade_msg))

        mock_handler.assert_called_once()
        feed_message = mock_handler.call_args[0][0]
        assert feed_message.provider == FeedProvider.POLYGON
        assert feed_message.symbol == "AAPL"
        assert feed_message.message_type == "trade"
        assert feed_message.data.symbol == "AAPL"
        assert feed_message.data.price == 150.25
        assert feed_message.data.size == 100

    @pytest.mark.asyncio
    async def test_handle_status_message(self, adapter):
        """Test handling of status messages"""
        # Test connected status
        status_msg = {"ev": "status", "status": "connected", "message": "Connected successfully"}
        await adapter._handle_message(json.dumps(status_msg))

        # Test auth_success status
        auth_msg = {"ev": "status", "status": "auth_success", "message": "Authentication successful"}
        await adapter._handle_message(json.dumps(auth_msg))

        # Test error status
        error_msg = {"ev": "status", "status": "error", "message": "Connection error"}
        await adapter._handle_message(json.dumps(error_msg))

        # Test unknown status
        unknown_msg = {"ev": "status", "status": "unknown", "message": "Unknown status"}
        await adapter._handle_message(json.dumps(unknown_msg))

    @pytest.mark.asyncio
    async def test_handle_invalid_json(self, adapter):
        """Test handling of invalid JSON messages"""
        with patch.object(adapter.logger, 'warning') as mock_warning:
            await adapter._handle_message("invalid json")
            mock_warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, adapter):
        """Test handling of unknown message types"""
        unknown_msg = {"ev": "UNKNOWN", "data": "test"}
        await adapter._handle_message(json.dumps(unknown_msg))
        # Should not raise an exception

    @pytest.mark.asyncio
    async def test_start_listening_not_connected(self, adapter):
        """Test start_listening when not connected"""
        with pytest.raises(RuntimeError, match="Not connected to WebSocket"):
            await adapter.start_listening()

    @pytest.mark.asyncio
    async def test_heartbeat_functionality(self, adapter):
        """Test heartbeat functionality"""
        mock_websocket = AsyncMock()
        adapter.websocket = mock_websocket
        adapter._connected = True

        # Run heartbeat for a short time
        heartbeat_task = asyncio.create_task(adapter._heartbeat())
        await asyncio.sleep(0.1)  # Let it run briefly

        # Stop the heartbeat
        adapter._connected = False
        await heartbeat_task

        # Verify ping was called
        mock_websocket.ping.assert_called()

    @pytest.mark.asyncio
    async def test_reconnect_functionality(self, adapter):
        """Test reconnection functionality"""
        adapter.config.max_reconnect_attempts = 2

        with patch.object(adapter, 'connect', return_value=True) as mock_connect, \
             patch.object(adapter, 'subscribe') as mock_subscribe, \
             patch.object(adapter, 'start_listening') as mock_start_listening, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:

            # Add a subscribed symbol
            adapter._subscribed_symbols.add("AAPL")

            await adapter._reconnect()

            # Should attempt to connect
            mock_connect.assert_called_once()
            # Should re-subscribe
            mock_subscribe.assert_called_once_with(list({"AAPL"}), ["second_agg", "minute_agg", "trade"])
            # Should start listening
            mock_start_listening.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_max_attempts_exceeded(self, adapter):
        """Test reconnection when max attempts exceeded"""
        adapter.config.max_reconnect_attempts = 1

        with patch.object(adapter, 'connect', return_value=False) as mock_connect, \
             patch('asyncio.sleep', new_callable=AsyncMock):

            await adapter._reconnect()

            # Should attempt to connect max_reconnect_attempts times
            assert mock_connect.call_count == 1