"""
Unit tests for papertest.engine.papertest_engine
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from core_engine.data.replay.engine import ReplayStatus
from papertest.engine.papertest_engine import PapertestEngine, PapertestRunResult


class TestPapertestRunResult:
    def test_initialization(self):
        """Test PapertestRunResult initialization"""
        result = PapertestRunResult(
            engine_stats={"bars": 100},
            replay_stats={"events": 50},
            bridge_stats={"enqueued": 100},
            execution_history=[{"symbol": "AAPL"}],
            account_info={"cash": 100000.0}
        )

        assert result.engine_stats == {"bars": 100}
        assert result.replay_stats == {"events": 50}
        assert result.bridge_stats == {"enqueued": 100}
        assert result.execution_history == [{"symbol": "AAPL"}]
        assert result.account_info == {"cash": 100000.0}


class TestPapertestEngine:
    def test_initialization(self):
        """Test PapertestEngine initialization"""
        config = {"papertest": {"data": {"symbols": ["AAPL"]}}}
        engine = PapertestEngine(config)

        assert engine.config == config
        assert engine.wired is None
        assert engine._bridge is None
        assert engine._run_task is None

    @patch('papertest.engine.papertest_engine.ComponentFactory')
    @patch('papertest.engine.papertest_engine.ReplayToDispatcherBridge')
    async def test_initialize_success(self, mock_bridge_class, mock_factory_class):
        """Test successful initialization"""
        config = {
            "papertest": {
                "data": {"symbols": ["AAPL"]},
                "debug": {"start_at_time": "09:30"}
            }
        }

        # Mock factory
        mock_wired = Mock()
        mock_wired.replay_adapter = Mock()
        mock_wired.replay_adapter.connect = AsyncMock(return_value=True)
        mock_wired.replay_adapter.subscribe = AsyncMock()
        mock_wired.engine = Mock()
        mock_wired.engine.initialize = AsyncMock(return_value=True)
        mock_wired.engine.warmup = AsyncMock()
        mock_wired.components = {
            "strategy_manager": Mock()
        }
        mock_wired.components["strategy_manager"].add_strategy = AsyncMock(return_value=True)

        mock_factory = Mock()
        mock_factory.build.return_value = mock_wired
        mock_factory_class.return_value = mock_factory

        # Mock bridge
        mock_bridge = Mock()
        mock_bridge_class.return_value = mock_bridge

        engine = PapertestEngine(config)
        await engine.initialize()

        # Verify initialization steps
        mock_factory_class.assert_called_once_with(config)
        mock_factory.build.assert_called_once()
        mock_wired.replay_adapter.connect.assert_called_once()
        mock_wired.replay_adapter.subscribe.assert_called_once_with(["AAPL"], ["bar", "quote", "trade"])
        mock_wired.engine.initialize.assert_called_once()
        mock_wired.engine.warmup.assert_called_once_with(["AAPL"])

        assert engine.wired == mock_wired
        assert engine._bridge == mock_bridge

    async def test_initialize_replay_connect_fails(self):
        """Test initialization failure when replay connect fails"""
        config = {"papertest": {"data": {"symbols": ["AAPL"]}}}

        with patch('papertest.engine.papertest_engine.ComponentFactory') as mock_factory_class:
            mock_wired = Mock()
            mock_wired.replay_adapter = Mock()
            mock_wired.replay_adapter.connect = AsyncMock(return_value=False)

            mock_factory = Mock()
            mock_factory.build.return_value = mock_wired
            mock_factory_class.return_value = mock_factory

            engine = PapertestEngine(config)

            with pytest.raises(RuntimeError, match="Replay adapter connect failed"):
                await engine.initialize()

    async def test_initialize_engine_init_fails(self):
        """Test initialization failure when engine init fails"""
        config = {"papertest": {"data": {"symbols": ["AAPL"]}}}

        with patch('papertest.engine.papertest_engine.ComponentFactory') as mock_factory_class:
            mock_wired = Mock()
            mock_wired.replay_adapter = Mock()
            mock_wired.replay_adapter.connect = AsyncMock(return_value=True)
            mock_wired.replay_adapter.subscribe = AsyncMock()
            mock_wired.engine = Mock()
            mock_wired.engine.initialize = AsyncMock(return_value=False)

            mock_factory = Mock()
            mock_factory.build.return_value = mock_wired
            mock_factory_class.return_value = mock_factory

            engine = PapertestEngine(config)

            with pytest.raises(RuntimeError, match="PaperTradingEngine.initialize failed"):
                await engine.initialize()

    async def test_run_without_initialization(self):
        """Test run fails without initialization"""
        config = {}
        engine = PapertestEngine(config)

        with pytest.raises(RuntimeError, match="Call initialize\\(\\) first"):
            await engine.run()

    @patch('papertest.engine.papertest_engine._time')
    async def test_run_success(self, mock_time):
        """Test successful run"""
        mock_time.time.side_effect = [0.0, 1.0, 2.1]  # For sleep timing

        config = {"papertest": {"data": {"symbols": ["AAPL"]}}}
        engine = PapertestEngine(config)

        # Mock wired system
        mock_wired = Mock()
        mock_wired.replay_adapter = Mock()
        mock_wired.replay_adapter.start_replay = AsyncMock(return_value=True)
        mock_wired.replay_adapter.get_replay_statistics = Mock(return_value={"events": 100})
        mock_wired.engine = Mock()
        mock_wired.engine.run = AsyncMock()
        mock_wired.engine.get_stats = Mock(return_value={"bars_processed": 50})
        mock_wired.engine.get_state = Mock(return_value=Mock(name="RUNNING"))
        mock_wired.engine.stop = Mock()

        # Mock bridge
        mock_bridge = Mock()
        mock_bridge.stats = {"bars_enqueued": 50}

        # Mock components for account info
        mock_broker = Mock()
        mock_broker.get_account_info = Mock(return_value=Mock(
            cash=95000.0,
            equity=100000.0,
            portfolio_value=100000.0
        ))
        mock_wired.components = {"paper_broker": mock_broker}

        engine.wired = mock_wired
        engine._bridge = mock_bridge

        # Mock replay completion
        with patch.object(engine, '_wait_for_replay_completion', new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = None

            result = await engine.run()

        # Verify result
        assert isinstance(result, PapertestRunResult)
        assert result.engine_stats["bars_processed"] == 50
        assert result.replay_stats == {"events": 100}
        assert result.bridge_stats == {"bars_enqueued": 50}
        assert result.account_info["cash"] == 95000.0

        # Verify calls
        mock_wired.replay_adapter.start_replay.assert_called_once()
        mock_wired.engine.run.assert_called_once()
        mock_wired.engine.stop.assert_called_once()

    async def test_run_replay_start_fails(self):
        """Test run fails when replay start fails"""
        config = {"papertest": {"data": {"symbols": ["AAPL"]}}}
        engine = PapertestEngine(config)

        mock_wired = Mock()
        mock_wired.replay_adapter = Mock()
        mock_wired.replay_adapter.start_replay = AsyncMock(return_value=False)

        engine.wired = mock_wired
        engine._bridge = Mock()

        with pytest.raises(RuntimeError, match="Replay start failed"):
            await engine.run()

    @patch('papertest.engine.papertest_engine._time')
    async def test_run_with_execution_history_from_engine(self, mock_time):
        """Test run with execution history from engine stats"""
        mock_time.time.side_effect = [0.0, 1.0, 2.1]

        config = {"papertest": {"data": {"symbols": ["AAPL"]}}}
        engine = PapertestEngine(config)

        mock_wired = Mock()
        mock_wired.replay_adapter = Mock()
        mock_wired.replay_adapter.start_replay = AsyncMock(return_value=True)
        mock_wired.replay_adapter.get_replay_statistics = Mock(return_value={})
        mock_wired.engine = Mock()
        mock_wired.engine.run = AsyncMock()
        mock_wired.engine.get_stats = Mock(return_value={
            "bars_processed": 50,
            "execution_history": [
                {"symbol": "AAPL", "action": "BUY", "quantity": 100, "price": 100.0}
            ]
        })
        mock_wired.engine.get_state = Mock(return_value=Mock(name="RUNNING"))
        mock_wired.engine.stop = Mock()

        mock_bridge = Mock()
        mock_bridge.stats = {}

        mock_wired.components = {}

        engine.wired = mock_wired
        engine._bridge = mock_bridge

        with patch.object(engine, '_wait_for_replay_completion', new_callable=AsyncMock):
            result = await engine.run()

        assert result.execution_history == []

    @patch('papertest.engine.papertest_engine.Path')
    @patch('core_engine.system.event_journal.EventJournal.read_journal')
    async def test_extract_execution_history_from_journal(self, mock_read_journal, mock_path):
        """Test extracting execution history from journal"""
        config = {}
        engine = PapertestEngine(config)

        # Mock journal file exists
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)  # Support / operator
        mock_path.return_value = mock_path_instance

        # Mock journal events
        mock_events = [
            Mock(to_dict=Mock(return_value={
                "category": "SIGNAL",
                "event_type": "signal_generated",
                "symbol": "AAPL",
                "data": {"signal_strength": 0.8}
            })),
            Mock(to_dict=Mock(return_value={
                "category": "FILL",
                "event_type": "fill",
                "symbol": "AAPL",
                "data": {
                    "side": "buy",
                    "quantity": 100.0,
                    "price": 100.0,
                    "fill_timestamp": "2024-01-01 09:30:00"
                }
            }))
        ]
        mock_read_journal.return_value = mock_events

        result = engine._extract_execution_history_from_journal(
            journal_dir="/tmp",
            session_id="test_session"
        )

        expected = [{
            "timestamp": "2024-01-01 09:30:00",
            "symbol": "AAPL",
            "action": "buy",
            "quantity": 100.0,
            "price": 100.0,
            "signal_strength": 0.8,
            "confidence": 0.0
        }]

        assert result == expected

    async def test_wait_for_replay_completion(self):
        """Test waiting for replay completion"""
        config = {}
        engine = PapertestEngine(config)

        mock_wired = Mock()
        mock_replay_engine = Mock()
        mock_replay_engine.status = ReplayStatus.COMPLETED
        mock_wired.replay_adapter = Mock()
        mock_wired.replay_adapter.replay_engine = mock_replay_engine
        mock_wired.engine = Mock()
        mock_wired.engine.get_state = Mock(return_value=Mock(name="RUNNING"))

        engine.wired = mock_wired

        await engine._wait_for_replay_completion()

        # Should complete immediately since status is COMPLETED

    @patch('papertest.engine.papertest_engine._time')
    async def test_configure_strategy_manager(self, mock_time):
        """Test configuring strategy manager"""
        mock_time.time.return_value = 1234567890.0

        config = {
            "papertest": {
                "data": {"symbols": ["AAPL"]},
                "strategies": [
                    {"name": "test_strategy", "type": "momentum", "active": True}
                ]
            }
        }
        engine = PapertestEngine(config)

        mock_wired = Mock()
        mock_strategy_manager = Mock()
        mock_strategy_manager.add_strategy = AsyncMock(return_value=True)
        mock_wired.components = {"strategy_manager": mock_strategy_manager}

        engine.wired = mock_wired

        await engine._configure_strategy_manager()

        mock_strategy_manager.add_strategy.assert_called_once()
        call_args = mock_strategy_manager.add_strategy.call_args[0][0]
        assert call_args["name"] == "test_strategy"
        assert call_args["type"] == "momentum"
        assert call_args["symbols"] == ["AAPL"]

    async def test_configure_strategy_manager_no_strategies(self):
        """Test configuring strategy manager with no strategies (uses default)"""
        config = {
            "papertest": {
                "data": {"symbols": ["AAPL", "MSFT"]}
            }
        }
        engine = PapertestEngine(config)

        mock_wired = Mock()
        mock_strategy_manager = Mock()
        mock_strategy_manager.add_strategy = AsyncMock(return_value=True)
        mock_wired.components = {"strategy_manager": mock_strategy_manager}

        engine.wired = mock_wired

        await engine._configure_strategy_manager()

        # Should add default momentum strategy
        mock_strategy_manager.add_strategy.assert_called_once()
        call_args = mock_strategy_manager.add_strategy.call_args[0][0]
        assert call_args["name"] == "momentum_default"
        assert call_args["type"] == "momentum"
        assert call_args["symbols"] == ["AAPL", "MSFT"]