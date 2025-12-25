"""
Unit tests for papertest.experiments.smoke_test
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from papertest.experiments.smoke_test import SmokeTest
from papertest.experiments.base_experiment import PapertestResult


class TestSmokeTest:
    def test_get_description(self):
        """Test getting experiment description"""
        config = {}
        experiment = SmokeTest(config)

        description = experiment.get_description()
        assert description == "Smoke test: single symbol streaming replay + basic pipeline wiring"

    @patch('papertest.engine.papertest_engine.PapertestEngine')
    @patch('papertest.experiments.smoke_test.time.perf_counter')
    @patch('papertest.experiments.smoke_test.datetime')
    async def test_run_success(self, mock_datetime, mock_perf_counter, mock_engine_class):
        """Test successful experiment run"""
        # Setup mocks
        mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_perf_counter.side_effect = [0.0, 10.5]  # start, end

        mock_engine = AsyncMock()
        mock_engine_class.return_value = mock_engine

        # Mock the run result
        mock_run_result = AsyncMock()
        mock_run_result.engine_stats = {"bars_processed": 100}
        mock_run_result.replay_stats = {"events_processed": 50}
        mock_run_result.bridge_stats = {"bars_enqueued": 100}
        mock_run_result.execution_history = []
        mock_run_result.account_info = {"cash": 100000.0}

        mock_engine.run.return_value = mock_run_result

        config = {"test": "config"}
        experiment = SmokeTest(config)

        result = await experiment.run()

        # Verify engine was created and methods called
        mock_engine_class.assert_called_once_with(config)
        mock_engine.initialize.assert_called_once()
        mock_engine.run.assert_called_once()

        # Verify result
        assert isinstance(result, PapertestResult)
        assert result.experiment_name == "Smoke_Test"
        assert result.experiment_type == "smoke_test"
        assert result.duration_seconds == 10.5
        assert result.success is True
        assert result.error_message is None
        assert result.engine_stats == {"bars_processed": 100}
        assert result.replay_stats == {"events_processed": 50}
        assert result.execution_stats == {
            "execution_history": [],
            "account_info": {"cash": 100000.0}
        }
        assert result.custom_metrics == {"bridge_stats": {"bars_enqueued": 100}}

    @patch('papertest.engine.papertest_engine.PapertestEngine')
    @patch('papertest.experiments.smoke_test.time.perf_counter')
    @patch('papertest.experiments.smoke_test.datetime')
    async def test_run_initialization_failure(self, mock_datetime, mock_perf_counter, mock_engine_class):
        """Test experiment run with initialization failure"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_perf_counter.side_effect = [0.0, 5.0]

        mock_engine = AsyncMock()
        mock_engine.initialize.side_effect = RuntimeError("Init failed")
        mock_engine_class.return_value = mock_engine

        config = {"test": "config"}
        experiment = SmokeTest(config)

        result = await experiment.run()

        # Verify result indicates failure
        assert isinstance(result, PapertestResult)
        assert result.success is False
        assert result.error_message == "Init failed"
        assert result.duration_seconds == 5.0

        # Engine run should not be called
        mock_engine.run.assert_not_called()

    @patch('papertest.engine.papertest_engine.PapertestEngine')
    @patch('papertest.experiments.smoke_test.time.perf_counter')
    @patch('papertest.experiments.smoke_test.datetime')
    async def test_run_execution_failure(self, mock_datetime, mock_perf_counter, mock_engine_class):
        """Test experiment run with execution failure"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_perf_counter.side_effect = [0.0, 8.0]

        mock_engine = AsyncMock()
        mock_engine.run.side_effect = ValueError("Run failed")
        mock_engine_class.return_value = mock_engine

        config = {"test": "config"}
        experiment = SmokeTest(config)

        result = await experiment.run()

        # Verify result indicates failure
        assert isinstance(result, PapertestResult)
        assert result.success is False
        assert result.error_message == "Run failed"
        assert result.duration_seconds == 8.0

    @patch('builtins.print')
    def test_print_summary_delegates_to_backtest_style(self, mock_print):
        """Test that print_summary delegates to backtest-style printing"""
        config = {}
        experiment = SmokeTest(config)

        result = PapertestResult(
            experiment_name="Test",
            experiment_type="test",
            run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            duration_seconds=10.0,
            success=True
        )

        experiment.print_summary(result)

        # Should delegate to the backtest-style print method
        assert mock_print.call_count > 0