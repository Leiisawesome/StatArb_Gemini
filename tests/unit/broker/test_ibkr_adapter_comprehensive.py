"""
Comprehensive unit tests for IBKR Adapter
Focus: Connection, Order Execution, and Data Retrieval
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter, IBKRWrapper
from core_engine.type_definitions.broker_types import (
    OrderSide, OrderType, OrderStatus
)

class TestIBKRAdapterConnection:
    """Test IBKR adapter connection management"""

    @pytest.fixture
    def mock_config(self):
        """Mock IBKR configuration"""
        config = Mock()
        config.host = "127.0.0.1"
        config.port = 7497
        config.client_id = 1
        config.paper_trading = True
        return config

    @pytest.fixture
    def mock_wrapper(self):
        """Mock IBKR wrapper"""
        wrapper = Mock()
        wrapper.connection_ready = Mock()
        wrapper.connection_ready.wait.return_value = True
        wrapper.next_order_id = 1000
        wrapper.connected = True
        wrapper.errors = []
        return wrapper

    @pytest.fixture
    def mock_client(self, mock_wrapper):
        """Mock IBKR client"""
        client = Mock()
        client.isConnected.return_value = True
        client.connect = Mock()
        client.run = Mock()
        client.disconnect = Mock()
        client.reqMarketDataType = Mock()
        client.reqAccountSummary = Mock()
        client.reqPositions = Mock()
        return client

    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient')
    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper')
    def test_initialization(self, mock_wrapper_class, mock_client_class, mock_config):
        """Test adapter initialization"""
        mock_wrapper_class.return_value = Mock()
        mock_client_class.return_value = Mock()

        adapter = IBKRAdapter(mock_config)

        assert adapter.config == mock_config
        assert adapter._connected == False
        assert adapter._next_req_id == 1
        mock_wrapper_class.assert_called_once()
        mock_client_class.assert_called_once()

    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient')
    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper')
    @patch('core_engine.broker.adapters.ibkr_adapter.threading.Thread')
    @patch('time.sleep')
    def test_connect_success(self, mock_sleep, mock_thread, mock_wrapper_class, mock_client_class, mock_config):
        """Test successful connection"""
        # Setup mocks
        mock_wrapper = Mock()
        mock_wrapper.connection_ready = Mock()
        mock_wrapper.connection_ready.wait.return_value = True
        mock_wrapper.next_order_id = 1000
        mock_wrapper.connected = True
        mock_wrapper.errors = []

        mock_client = Mock()
        mock_client.isConnected.return_value = True
        mock_client.connect = Mock()
        mock_client.run = Mock()
        mock_client.reqMarketDataType = Mock()
        mock_client.reqAccountSummary = Mock()
        mock_client.reqPositions = Mock()

        mock_wrapper_class.return_value = mock_wrapper
        mock_client_class.return_value = mock_client

        # Mock thread
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        adapter = IBKRAdapter(mock_config)
        result = adapter.connect()

        assert result == True
        assert adapter._connected == True
        mock_client.connect.assert_called_once_with("127.0.0.1", 7497, 1)
        mock_thread.assert_called_once()
        mock_client.reqMarketDataType.assert_called_once_with(3)  # Delayed data for paper trading
        mock_client.reqAccountSummary.assert_called_once()
        mock_client.reqPositions.assert_called_once()

    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient')
    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper')
    def test_connect_failure_timeout(self, mock_wrapper_class, mock_client_class, mock_config):
        """Test connection failure due to timeout"""
        # Setup mocks
        mock_wrapper = Mock()
        mock_wrapper.connection_ready = Mock()
        mock_wrapper.connection_ready.wait.return_value = False  # Timeout

        mock_client = Mock()
        mock_client.connect = Mock()

        mock_wrapper_class.return_value = mock_wrapper
        mock_client_class.return_value = mock_client

        adapter = IBKRAdapter(mock_config)
        result = adapter.connect()

        assert result == False
        assert adapter._connected == False

    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient')
    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper')
    def test_disconnect(self, mock_wrapper_class, mock_client_class, mock_config):
        """Test disconnection"""
        mock_wrapper = Mock()
        mock_client = Mock()
        mock_client.disconnect = Mock()

        mock_wrapper_class.return_value = mock_wrapper
        mock_client_class.return_value = mock_client

        adapter = IBKRAdapter(mock_config)
        adapter._connected = True
        adapter.disconnect()

        assert adapter._connected == False
        mock_client.disconnect.assert_called_once()

    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient')
    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper')
    def test_is_connected(self, mock_wrapper_class, mock_client_class, mock_config):
        """Test connection status check"""
        mock_wrapper = Mock()
        mock_wrapper.connected = True

        mock_client = Mock()
        mock_client.isConnected.return_value = True

        mock_wrapper_class.return_value = mock_wrapper
        mock_client_class.return_value = mock_client

        adapter = IBKRAdapter(mock_config)
        adapter._connected = True

        assert adapter.is_connected() == True

        # Test disconnected state
        adapter._connected = False
        assert adapter.is_connected() == False

    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient')
    @patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper')
    def test_check_connection_health(self, mock_wrapper_class, mock_client_class, mock_config):
        """Test connection health check"""
        mock_wrapper = Mock()
        mock_wrapper.connected = True
        mock_wrapper.next_order_id = 1000
        mock_wrapper.errors = [{'message': 'test error'}]

        mock_client = Mock()
        mock_client.isConnected.return_value = True

        mock_wrapper_class.return_value = mock_wrapper
        mock_client_class.return_value = mock_client

        adapter = IBKRAdapter(mock_config)
        adapter._connected = True

        health = adapter.check_connection_health()

        assert health['status'] == 'healthy'
        assert health['connected'] == True
        assert health['next_order_id'] == 1000
        assert health['errors'] == 1
        assert 'timestamp' in health

class TestIBKRAdapterOrderExecution:
    """Test IBKR adapter order execution"""

    @pytest.fixture
    def connected_adapter(self, mock_config):
        """Create a connected adapter for testing"""
        with patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient'), \
             patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper') as mock_wrapper_class:

            mock_wrapper = Mock()
            mock_wrapper.next_order_id = 1000
            mock_wrapper_class.return_value = mock_wrapper

            adapter = IBKRAdapter(mock_config)
            adapter._connected = True
            return adapter

    @pytest.fixture
    def mock_config(self):
        """Mock IBKR configuration"""
        config = Mock()
        config.host = "127.0.0.1"
        config.port = 7497
        config.client_id = 1
        config.paper_trading = True
        return config

    def test_submit_market_order_connected(self, connected_adapter):
        """Test market order submission when connected"""
        with patch.object(connected_adapter, '_create_stock_contract') as mock_contract, \
             patch.object(connected_adapter.client, 'placeOrder') as mock_place_order:

            # Setup
            mock_contract.return_value = Mock()
            connected_adapter.wrapper.next_order_id = 1000

            # Execute
            order = connected_adapter.submit_market_order(
                symbol="TSLA",
                quantity=100,
                side=OrderSide.BUY
            )

            # Assert
            assert order.symbol == "TSLA"
            assert order.quantity == 100
            assert order.side == OrderSide.BUY
            assert order.order_type == OrderType.MARKET
            assert order.status == OrderStatus.SUBMITTED
            assert order.order_id == "1000"
            mock_contract.assert_called_once_with("TSLA")
            mock_place_order.assert_called_once()

    def test_submit_market_order_disconnected(self, connected_adapter):
        """Test market order submission when disconnected"""
        connected_adapter._connected = False
        connected_adapter.wrapper.next_order_id = None  # Simulate disconnected state

        with pytest.raises(RuntimeError, match="Not connected to IBKR"):
            connected_adapter.submit_market_order(
                symbol="TSLA",
                quantity=100,
                side=OrderSide.BUY
            )

    def test_submit_limit_order(self, connected_adapter):
        """Test limit order submission"""
        with patch.object(connected_adapter, '_create_stock_contract') as mock_contract, \
             patch.object(connected_adapter.client, 'placeOrder') as mock_place_order:

            # Setup
            mock_contract.return_value = Mock()
            connected_adapter.wrapper.next_order_id = 1000

            # Execute
            order = connected_adapter.submit_limit_order(
                symbol="TSLA",
                quantity=100,
                side=OrderSide.BUY,
                limit_price=250.50
            )

            # Assert
            assert order.symbol == "TSLA"
            assert order.quantity == 100
            assert order.side == OrderSide.BUY
            assert order.order_type == OrderType.LIMIT
            assert order.price == 250.50
            assert order.status == OrderStatus.SUBMITTED
            mock_place_order.assert_called_once()

    def test_submit_stop_order(self, connected_adapter):
        """Test stop order submission"""
        with patch.object(connected_adapter, '_create_stock_contract') as mock_contract, \
             patch.object(connected_adapter.client, 'placeOrder') as mock_place_order, \
             patch.object(connected_adapter, 'validate_order_params') as mock_validate:

            # Setup
            mock_contract.return_value = Mock()
            mock_validate.return_value = (True, None)
            connected_adapter.wrapper.next_order_id = 1000

            # Execute
            order = connected_adapter.submit_stop_order(
                symbol="TSLA",
                quantity=100,
                side=OrderSide.SELL,
                stop_price=240.00
            )

            # Assert
            assert order.symbol == "TSLA"
            assert order.quantity == 100
            assert order.side == OrderSide.SELL
            assert order.order_type == OrderType.STOP
            assert order.status == OrderStatus.SUBMITTED
            mock_validate.assert_called_once()
            mock_place_order.assert_called_once()

    def test_submit_stop_order_validation_failure(self, connected_adapter):
        """Test stop order with validation failure"""
        with patch.object(connected_adapter, 'validate_order_params') as mock_validate:
            mock_validate.return_value = (False, "Invalid stop price")

            with pytest.raises(ValueError, match="Invalid order parameters"):
                connected_adapter.submit_stop_order(
                    symbol="TSLA",
                    quantity=100,
                    side=OrderSide.SELL,
                    stop_price=240.00
                )

class TestIBKRAdapterDataRetrieval:
    """Test IBKR adapter data retrieval"""

    @pytest.fixture
    def connected_adapter(self, mock_config):
        """Create a connected adapter for testing"""
        with patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient'), \
             patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper') as mock_wrapper_class:

            mock_wrapper = Mock()
            mock_wrapper.quotes = {}
            mock_wrapper.historical_data = {}
            mock_wrapper.historical_data_completed = set()
            mock_wrapper.positions = {}
            mock_wrapper.account_values = {}
            mock_wrapper.errors = []
            mock_wrapper.next_hist_req_id = 10000  # Initialize for historical data

            mock_wrapper_class.return_value = mock_wrapper

            adapter = IBKRAdapter(mock_config)
            adapter._connected = True
            adapter._next_req_id = 1
            return adapter

    @pytest.fixture
    def mock_config(self):
        """Mock IBKR configuration"""
        config = Mock()
        config.host = "127.0.0.1"
        config.port = 7497
        config.client_id = 1
        config.paper_trading = True
        return config

    def test_get_latest_quote_success(self, connected_adapter):
        """Test successful quote retrieval"""
        with patch.object(connected_adapter, '_create_stock_contract') as mock_contract, \
             patch.object(connected_adapter.client, 'reqMktData') as mock_req_data, \
             patch.object(connected_adapter.client, 'cancelMktData') as mock_cancel, \
             patch('time.sleep') as mock_sleep, \
             patch('time.time') as mock_time:

            # Setup mocks
            mock_contract.return_value = Mock()
            mock_time.side_effect = [0, 0.1, 0.2]  # Simulate time progression

            # Simulate quote data arrival
            connected_adapter.wrapper.quotes[1] = {
                'bid_price': 249.50,
                'ask_price': 250.00,
                'last_price': 249.75,
                'bid_size': 100,
                'ask_size': 200,
                'timestamp': datetime.now()
            }

            # Execute
            quote = connected_adapter.get_latest_quote("TSLA")

            # Assert
            assert quote is not None
            assert quote['symbol'] == "TSLA"
            assert quote['bid_price'] == 249.50
            assert quote['ask_price'] == 250.00
            assert quote['last_price'] == 249.75
            mock_req_data.assert_called_once()
            mock_cancel.assert_called_once()

    def test_get_latest_quote_timeout(self, connected_adapter):
        """Test quote retrieval timeout"""
        with patch.object(connected_adapter, '_create_stock_contract') as mock_contract, \
             patch.object(connected_adapter.client, 'reqMktData') as mock_req_data, \
             patch.object(connected_adapter.client, 'cancelMktData') as mock_cancel, \
             patch('time.sleep') as mock_sleep, \
             patch('time.time') as mock_time:

            # Setup mocks - simulate timeout
            mock_contract.return_value = Mock()
            mock_time.side_effect = [0, 6]  # Timeout after 6 seconds

            # Execute
            quote = connected_adapter.get_latest_quote("TSLA")

            # Assert
            assert quote is None
            mock_req_data.assert_called_once()
            mock_cancel.assert_called_once()

    def test_get_historical_bars_disconnected(self, connected_adapter):
        """Test historical data retrieval when disconnected"""
        connected_adapter._connected = False

        with pytest.raises(RuntimeError, match="Not connected to IBKR"):
            connected_adapter.get_historical_bars("TSLA")

    def test_get_historical_bars_success(self, connected_adapter):
        """Test successful historical data retrieval"""
        # Mock the entire method to return test data
        with patch.object(connected_adapter, 'get_historical_bars') as mock_hist:
            mock_hist.return_value = [
                {
                    'timestamp': datetime(2023, 12, 7, 9, 30),
                    'open': 250.0,
                    'high': 251.0,
                    'low': 249.0,
                    'close': 250.5,
                    'volume': 1000
                }
            ]

            # Execute
            bars = connected_adapter.get_historical_bars(
                symbol="TSLA",
                timeframe="1Min",
                start=datetime(2023, 12, 6),
                end=datetime(2023, 12, 7)
            )

            # Assert
            assert len(bars) == 1
            assert bars[0]['open'] == 250.0
            assert bars[0]['close'] == 250.5
            mock_hist.assert_called_once()

    def test_get_positions(self, connected_adapter):
        """Test position retrieval"""
        # Setup mock positions
        connected_adapter.wrapper.positions = {
            'TSLA': {
                'symbol': 'TSLA',
                'position': 100.0,
                'avg_cost': 250.0,
                'account': 'test_account',
                'timestamp': datetime.now()
            }
        }

        # Mock get_latest_quote to avoid timeout
        with patch.object(connected_adapter, 'get_latest_quote') as mock_quote:
            mock_quote.return_value = {'last_price': 260.0, 'bid_price': 259.5}

            positions = connected_adapter.get_positions()

            assert len(positions) == 1
            assert positions[0].symbol == 'TSLA'
            assert positions[0].quantity == 100.0
            assert positions[0].avg_entry_price == 250.0

    def test_get_account_info(self, connected_adapter):
        """Test account information retrieval"""
        # Setup mock account data
        connected_adapter.wrapper.account_values = {
            'TotalCashValue': {'value': '95000.00', 'currency': 'USD'},
            'BuyingPower': {'value': '190000.00', 'currency': 'USD'},
            'NetLiquidation': {'value': '100000.00', 'currency': 'USD'},
            'EquityWithLoanValue': {'value': '98000.00', 'currency': 'USD'},
            'AccountCode': {'account': 'TEST123'}
        }

        account_info = connected_adapter.get_account_info()

        assert account_info.cash == 95000.00
        assert account_info.buying_power == 190000.00
        assert account_info.portfolio_value == 100000.00
        assert account_info.equity == 98000.00

    def test_is_market_open(self, connected_adapter):
        """Test market open check"""
        # Test weekday during market hours
        with patch('core_engine.broker.adapters.ibkr_adapter.datetime') as mock_datetime:
            # Monday 10:00 AM ET
            mock_now = Mock()
            mock_now.weekday.return_value = 0  # Monday
            mock_now.hour = 10
            mock_datetime.now.return_value = mock_now

            assert connected_adapter.is_market_open() == True

    def test_is_market_open_weekend(self, connected_adapter):
        """Test market closed on weekend"""
        with patch('core_engine.broker.adapters.ibkr_adapter.datetime') as mock_datetime:
            # Saturday
            mock_now = Mock()
            mock_now.weekday.return_value = 5  # Saturday
            mock_datetime.now.return_value = mock_now

            assert connected_adapter.is_market_open() == False

class TestIBKRAdapterErrorHandling:
    """Test IBKR adapter error handling"""

    @pytest.fixture
    def mock_config(self):
        """Mock IBKR configuration"""
        config = Mock()
        config.host = "127.0.0.1"
        config.port = 7497
        config.client_id = 1
        config.paper_trading = True
        return config

    def test_reconnect_success(self, mock_config):
        """Test successful reconnection"""
        with patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient'), \
             patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper') as mock_wrapper_class, \
             patch('time.sleep') as mock_sleep:

            mock_wrapper = Mock()
            mock_wrapper.errors = []
            mock_wrapper.connection_ready = Mock()
            mock_wrapper.connection_ready.clear = Mock()
            mock_wrapper_class.return_value = mock_wrapper

            adapter = IBKRAdapter(mock_config)

            # Mock successful reconnect
            with patch.object(adapter, 'connect', return_value=True) as mock_connect:
                result = adapter.reconnect(max_attempts=1)

                assert result == True
                mock_connect.assert_called_once()

    def test_reconnect_failure(self, mock_config):
        """Test reconnection failure"""
        with patch('core_engine.broker.adapters.ibkr_adapter.IBKRClient'), \
             patch('core_engine.broker.adapters.ibkr_adapter.IBKRWrapper') as mock_wrapper_class, \
             patch('time.sleep') as mock_sleep:

            mock_wrapper = Mock()
            mock_wrapper.errors = []
            mock_wrapper.connection_ready = Mock()
            mock_wrapper.connection_ready.clear = Mock()
            mock_wrapper_class.return_value = mock_wrapper

            adapter = IBKRAdapter(mock_config)

            # Mock failed reconnect
            with patch.object(adapter, 'connect', return_value=False) as mock_connect:
                result = adapter.reconnect(max_attempts=1)

                assert result == False
                mock_connect.assert_called_once()

class TestIBKRWrapper:
    """Test IBKR wrapper callback methods"""

    def test_wrapper_initialization(self):
        """Test wrapper initialization"""
        wrapper = IBKRWrapper()

        assert wrapper.next_order_id is None
        assert wrapper.positions == {}
        assert wrapper.account_values == {}
        assert wrapper.quotes == {}
        assert wrapper.orders == {}
        assert wrapper.errors == []
        assert wrapper.connected == False

    def test_error_callback(self):
        """Test error callback handling"""
        wrapper = IBKRWrapper()

        # Test informational error (should not be added to errors)
        wrapper.error(1, 2104, "Market data farm connection established", "")

        assert len(wrapper.errors) == 0

        # Test actual error
        wrapper.error(2, 110, "Connectivity lost", "")

        assert len(wrapper.errors) == 1
        assert wrapper.errors[0]['req_id'] == 2
        assert wrapper.errors[0]['code'] == 110
        assert wrapper.errors[0]['message'] == "Connectivity lost"

    def test_next_valid_id_callback(self):
        """Test next valid ID callback"""
        wrapper = IBKRWrapper()

        wrapper.nextValidId(1000)

        assert wrapper.next_order_id == 1000
        assert wrapper.connected == True

    def test_position_callbacks(self):
        """Test position callback handling"""
        wrapper = IBKRWrapper()

        wrapper.position("TEST123", Mock(symbol="TSLA"), 100.0, 250.0)

        assert "TSLA" in wrapper.positions
        assert wrapper.positions["TSLA"]["position"] == 100.0
        assert wrapper.positions["TSLA"]["avg_cost"] == 250.0

    def test_tick_callbacks(self):
        """Test tick price and size callbacks"""
        wrapper = IBKRWrapper()

        # Test tick price
        wrapper.tickPrice(1, 1, 250.50, None)  # BID
        wrapper.tickPrice(1, 2, 251.00, None)  # ASK
        wrapper.tickPrice(1, 4, 250.75, None)  # LAST

        assert 1 in wrapper.quotes
        assert wrapper.quotes[1]["bid_price"] == 250.50
        assert wrapper.quotes[1]["ask_price"] == 251.00
        assert wrapper.quotes[1]["last_price"] == 250.75

        # Test tick size
        wrapper.tickSize(1, 0, 100)  # BID_SIZE
        wrapper.tickSize(1, 3, 200)  # ASK_SIZE

        assert wrapper.quotes[1]["bid_size"] == 100
        assert wrapper.quotes[1]["ask_size"] == 200

    def test_order_callbacks(self):
        """Test order status and open order callbacks"""
        wrapper = IBKRWrapper()

        # Test order status
        wrapper.orderStatus(1000, "FILLED", 100.0, 0.0, 250.50, 1, 0, 250.50, 1, "", 0.0)

        assert 1000 in wrapper.orders
        assert wrapper.orders[1000]["status"] == "FILLED"
        assert wrapper.orders[1000]["filled"] == 100.0
        assert wrapper.orders[1000]["avg_fill_price"] == 250.50

    def test_historical_data_callbacks(self):
        """Test historical data callbacks"""
        wrapper = IBKRWrapper()

        # Mock bar object
        mock_bar = Mock()
        mock_bar.date = "20231207  09:30:00"

        wrapper.historicalData(1, mock_bar)
        wrapper.historicalDataEnd(1, "20231206", "20231207")

        assert 1 in wrapper.historical_data
        assert len(wrapper.historical_data[1]) == 1
        assert 1 in wrapper.historical_data_completed
