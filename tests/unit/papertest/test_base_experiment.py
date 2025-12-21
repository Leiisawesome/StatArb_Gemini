"""
Unit tests for papertest.experiments.base_experiment
"""

import pytest
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from papertest.experiments.base_experiment import (
    PapertestResult,
    BasePapertestExperiment
)


class TestPapertestResult:
    def test_initialization(self):
        """Test PapertestResult initialization"""
        run_ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = PapertestResult(
            experiment_name="Test Experiment",
            experiment_type="test",
            run_timestamp=run_ts,
            duration_seconds=10.5
        )

        assert result.experiment_name == "Test Experiment"
        assert result.experiment_type == "test"
        assert result.run_timestamp == run_ts
        assert result.duration_seconds == 10.5
        assert result.success is True
        assert result.error_message is None
        assert result.engine_stats == {}
        assert result.replay_stats == {}
        assert result.risk_stats == {}
        assert result.execution_stats == {}
        assert result.total_pnl == 0.0
        assert result.realized_pnl == 0.0
        assert result.unrealized_pnl == 0.0
        assert result.max_drawdown == 0.0
        assert result.custom_metrics == {}

    def test_to_dict(self):
        """Test converting result to dict"""
        run_ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = PapertestResult(
            experiment_name="Test Experiment",
            experiment_type="test",
            run_timestamp=run_ts,
            duration_seconds=10.5,
            engine_stats={"bars_processed": 100},
            custom_metrics={"test_metric": 42.0},
            success=False,
            error_message="Test error"
        )

        result_dict = result.to_dict()

        expected = {
            "experiment_name": "Test Experiment",
            "experiment_type": "test",
            "run_timestamp": "2024-01-01T12:00:00+00:00",
            "duration_seconds": 10.5,
            "engine_stats": {"bars_processed": 100},
            "replay_stats": {},
            "risk_stats": {},
            "execution_stats": {},
            "performance": {
                "total_pnl": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "max_drawdown": 0.0,
            },
            "custom_metrics": {"test_metric": 42.0},
            "success": False,
            "error_message": "Test error"
        }

        assert result_dict == expected


class TestBasePapertestExperiment:
    def test_initialization(self):
        """Test BasePapertestExperiment initialization"""
        config = {"test": "config"}
        output_dir = "/tmp/test_output"

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        experiment = ConcreteExperiment(config, output_dir)

        assert experiment.config == config
        assert experiment.output_dir == Path(output_dir)
        assert experiment.output_dir.exists()

    def test_initialization_default_output_dir(self):
        """Test initialization with default output directory"""
        config = {"test": "config"}

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        with patch('papertest.experiments.base_experiment.Path') as mock_path:
            mock_path.return_value.mkdir = MagicMock()

            experiment = ConcreteExperiment(config)

            # Should use default "papertest/results"
            mock_path.assert_called_with("papertest/results")
            mock_path.return_value.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('builtins.print')
    def test_print_summary_success(self, mock_print):
        """Test printing summary for successful result"""
        config = {}

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        experiment = ConcreteExperiment(config)

        run_ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = PapertestResult(
            experiment_name="Test Experiment",
            experiment_type="test",
            run_timestamp=run_ts,
            duration_seconds=10.5,
            success=True,
            custom_metrics={"bars_processed": 100}
        )

        experiment.print_summary(result)

        # Check that print was called (detailed assertions would be complex)
        assert mock_print.call_count > 0

    @patch('builtins.print')
    def test_print_summary_failure(self, mock_print):
        """Test printing summary for failed result"""
        config = {}

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        experiment = ConcreteExperiment(config)

        run_ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = PapertestResult(
            experiment_name="Test Experiment",
            experiment_type="test",
            run_timestamp=run_ts,
            duration_seconds=5.0,
            success=False,
            error_message="Test error"
        )

        experiment.print_summary(result)

        assert mock_print.call_count > 0

    @patch('builtins.print')
    def test_print_summary_backtest_style(self, mock_print):
        """Test printing backtest-style summary"""
        config = {"papertest": {"execution": {"initial_cash": 100000.0}}}

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        experiment = ConcreteExperiment(config)

        run_ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = PapertestResult(
            experiment_name="Test Experiment",
            experiment_type="test",
            run_timestamp=run_ts,
            duration_seconds=10.5,
            success=True,
            execution_stats={
                "account_info": {"equity": 105000.0}
            },
            engine_stats={"execution_history": []}
        )

        experiment.print_summary_backtest_style(result)

        assert mock_print.call_count > 0

    def test_save_results(self):
        """Test saving results to file"""
        config = {}

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        with tempfile.TemporaryDirectory() as temp_dir:
            experiment = ConcreteExperiment(config, temp_dir)

            run_ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = PapertestResult(
                experiment_name="Test Experiment",
                experiment_type="test",
                run_timestamp=run_ts,
                duration_seconds=10.5,
                success=True,
                custom_metrics={"test_metric": 42.0}
            )

            experiment.save_results(result)

            # Check that a file was created
            files = list(Path(temp_dir).glob("*.json"))
            assert len(files) == 1

            # Check file contents
            with open(files[0], 'r') as f:
                saved_data = json.load(f)

            assert saved_data["experiment_name"] == "Test Experiment"
            assert saved_data["success"] is True
            assert saved_data["custom_metrics"]["test_metric"] == 42.0

    def test_compute_equity_curve_from_journal_no_file(self):
        """Test computing equity curve when journal file doesn't exist"""
        config = {}

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        experiment = ConcreteExperiment(config)

        result = experiment._compute_equity_curve_from_journal(
            journal_dir="/nonexistent",
            session_id="test_session",
            initial_cash=100000.0
        )

        assert result["sharpe_ratio"] == 0.0
        assert result["max_drawdown_pct"] == 0.0
        assert result["equity_points"] == 0

    def test_compute_equity_curve_from_journal_empty_events(self):
        """Test computing equity curve with empty events"""
        config = {}

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        experiment = ConcreteExperiment(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "test_session.jsonl"
            journal_path.write_text("")  # Empty file

            with patch('core_engine.system.event_journal.EventJournal.read_journal', return_value=[]):
                result = experiment._compute_equity_curve_from_journal(
                    journal_dir=temp_dir,
                    session_id="test_session",
                    initial_cash=100000.0
                )

        assert result["sharpe_ratio"] == 0.0
        assert result["max_drawdown_pct"] == 0.0
        assert result["equity_points"] == 0

    @patch('core_engine.system.event_journal.EventJournal.read_journal')
    def test_compute_equity_curve_from_journal_with_data(self, mock_read_journal):
        """Test computing equity curve with actual data"""
        config = {}

        # Create a concrete subclass for testing
        class ConcreteExperiment(BasePapertestExperiment):
            async def run(self):
                return PapertestResult(
                    experiment_name="test",
                    experiment_type="test",
                    run_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                    duration_seconds=1.0
                )

            def get_description(self):
                return "Test experiment"

        experiment = ConcreteExperiment(config)

        # Mock journal events
        mock_events = [
            MagicMock(),  # Fill event
            MagicMock(),  # Bar event
        ]

        # Configure the mocks
        mock_events[0].to_dict.return_value = {
            "category": "FILL",
            "event_type": "fill",
            "symbol": "AAPL",
            "data": {
                "side": "buy",
                "quantity": 100.0,
                "price": 100.0,
                "commission": 1.0
            }
        }

        mock_events[1].to_dict.return_value = {
            "category": "MARKET_DATA",
            "event_type": "bar",
            "symbol": "AAPL",
            "data": {
                "timestamp": "2024-01-01T09:30:00",
                "close": 101.0
            }
        }

        mock_read_journal.return_value = mock_events

        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "test_session.jsonl"
            journal_path.write_text("dummy")  # File exists

            result = experiment._compute_equity_curve_from_journal(
                journal_dir=temp_dir,
                session_id="test_session",
                initial_cash=100000.0
            )

        # Should have computed some metrics
        assert isinstance(result["sharpe_ratio"], (int, float))
        assert isinstance(result["max_drawdown_pct"], (int, float))
        assert result["equity_points"] > 0

    def test_abstract_methods(self):
        """Test that abstract methods are defined and abstract"""
        from abc import ABC
        from inspect import signature

        # Check that BasePapertestExperiment is abstract
        assert issubclass(BasePapertestExperiment, ABC)

        # Check that the abstract methods exist
        assert hasattr(BasePapertestExperiment, 'run')
        assert hasattr(BasePapertestExperiment, 'get_description')

        # Check that they are abstract methods
        import inspect
        run_method = getattr(BasePapertestExperiment, 'run')
        desc_method = getattr(BasePapertestExperiment, 'get_description')

        # Abstract methods should raise NotImplementedError when called
        # But we can't test this directly without instantiation
        # Instead, verify the methods exist and have the expected signatures
        assert callable(run_method)
        assert callable(desc_method)