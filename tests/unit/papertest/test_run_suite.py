"""
Unit tests for papertest.run_suite
"""

import pytest
import sys
from unittest.mock import MagicMock, patch, AsyncMock
from papertest.run_suite import main, run_experiment, list_experiments, EXPERIMENTS

class TestRunSuite:
    def test_list_experiments(self, capsys):
        list_experiments()
        captured = capsys.readouterr()
        assert "AVAILABLE PAPERTEST EXPERIMENTS" in captured.out
        for name in EXPERIMENTS:
            assert name in captured.out

    @patch('papertest.run_suite.load_config')
    @patch('papertest.run_suite.EXPERIMENTS')
    async def test_run_experiment_success(self, mock_experiments, mock_load_config):
        # Setup mock experiment
        mock_exp_class = MagicMock()
        mock_exp_instance = MagicMock()
        mock_exp_class.return_value = mock_exp_instance
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_exp_instance.run = AsyncMock(return_value=mock_result)
        
        mock_experiments.__getitem__.return_value = {
            "class": mock_exp_class,
            "default_config": "config.yaml",
            "description": "Test experiment"
        }
        mock_experiments.__contains__.return_value = True

        result = await run_experiment("test_exp")
        
        assert result is True
        mock_load_config.assert_called_once()
        mock_exp_class.assert_called_once()
        mock_exp_instance.run.assert_called_once()
        mock_exp_instance.print_summary.assert_called_once()
        mock_exp_instance.save_results.assert_called_once()

    @patch('papertest.run_suite.EXPERIMENTS')
    async def test_run_experiment_unknown(self, mock_experiments):
        mock_experiments.__contains__.return_value = False
        result = await run_experiment("unknown_exp")
        assert result is False

    @patch('papertest.run_suite.load_config')
    @patch('papertest.run_suite.EXPERIMENTS')
    async def test_run_experiment_failure(self, mock_experiments, mock_load_config):
        mock_load_config.side_effect = Exception("Config error")
        mock_experiments.__contains__.return_value = True
        mock_experiments.__getitem__.return_value = {
            "default_config": "config.yaml"
        }

        result = await run_experiment("test_exp")
        assert result is False

    @patch('papertest.run_suite.run_experiment')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_run_experiment_success(self, mock_parse_args, mock_run_experiment):
        mock_args = MagicMock()
        mock_args.list = False
        mock_args.experiment = "smoke_test"
        mock_args.config = None
        mock_args.base_config = "base.yaml"
        mock_parse_args.return_value = mock_args

        mock_run_experiment.return_value = True # AsyncMock not needed as main calls asyncio.run

        # We need to patch asyncio.run because main calls it
        with patch('asyncio.run', return_value=True) as mock_asyncio_run:
            ret = main()
            assert ret == 0
            mock_asyncio_run.assert_called_once()

    @patch('papertest.run_suite.run_experiment')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_run_experiment_failure(self, mock_parse_args, mock_run_experiment):
        mock_args = MagicMock()
        mock_args.list = False
        mock_args.experiment = "smoke_test"
        mock_args.config = None
        mock_args.base_config = "base.yaml"
        mock_parse_args.return_value = mock_args

        with patch('asyncio.run', return_value=False):
            ret = main()
            assert ret == 1

    @patch('papertest.run_suite.list_experiments')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_list(self, mock_parse_args, mock_list_experiments):
        mock_args = MagicMock()
        mock_args.list = True
        mock_parse_args.return_value = mock_args

        ret = main()
        assert ret == 0
        mock_list_experiments.assert_called_once()

    @patch('argparse.ArgumentParser.parse_args')
    @patch('argparse.ArgumentParser.print_help')
    def test_main_no_args(self, mock_print_help, mock_parse_args):
        mock_args = MagicMock()
        mock_args.list = False
        mock_args.experiment = None
        mock_parse_args.return_value = mock_args

        ret = main()
        assert ret == 0
        mock_print_help.assert_called_once()
