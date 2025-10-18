"""
Parameter Management Tests

Tests for CentralParameterRegistry and ConfigurationStore.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from backtest.optimization.config_management.parameter_registry import (
    CentralParameterRegistry,
    ParameterVersion
)
from backtest.optimization.config_management.configuration_store import ConfigurationStore


class TestCentralParameterRegistry:
    """Tests for CentralParameterRegistry"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.registry = CentralParameterRegistry()
        self.strategy_type = "momentum"
        self.test_params = {
            'lookback_period': 60,
            'momentum_threshold': 0.02,
            'adx_threshold': 25.0
        }
    
    def test_parameter_registry_initialization(self):
        """Test 1: Registry initializes correctly"""
        assert self.registry is not None
        assert isinstance(self.registry._parameters, dict)
        assert isinstance(self.registry._subscribers, dict)
        assert isinstance(self.registry._history, dict)
    
    def test_subscribe_to_updates(self):
        """Test 2: Subscribe to parameter updates"""
        callback_called = []
        
        def test_callback(strategy_type, symbol, parameters):
            callback_called.append((strategy_type, symbol, parameters))
        
        sub_id = self.registry.subscribe(self.strategy_type, test_callback)
        assert sub_id is not None
        assert len(self.registry._subscribers[self.strategy_type]) == 1
    
    def test_get_parameters_default(self):
        """Test 3: Get default parameters"""
        # Set parameters
        self.registry.update_parameters(self.strategy_type, self.test_params)
        
        # Get parameters
        params = self.registry.get_parameters(self.strategy_type)
        assert params == self.test_params
    
    def test_get_parameters_symbol_specific(self):
        """Test 4: Get symbol-specific parameters"""
        # Set default
        self.registry.update_parameters(self.strategy_type, self.test_params)
        
        # Set symbol-specific override
        symbol_params = {'momentum_threshold': 0.03}
        self.registry.update_parameters(self.strategy_type, symbol_params, symbol="NVDA")
        
        # Get symbol-specific (should merge)
        params = self.registry.get_parameters(self.strategy_type, "NVDA")
        assert params['lookback_period'] == 60  # From default
        assert params['momentum_threshold'] == 0.03  # Override
    
    def test_update_parameters_notifies_subscribers(self):
        """Test 5: Parameter updates notify subscribers"""
        callback_called = []
        
        def test_callback(strategy_type, symbol, parameters):
            callback_called.append((strategy_type, symbol, parameters))
        
        self.registry.subscribe(self.strategy_type, test_callback)
        
        # Update parameters
        self.registry.update_parameters(self.strategy_type, self.test_params)
        
        # Verify callback was called
        assert len(callback_called) == 1
        assert callback_called[0][0] == self.strategy_type
        assert callback_called[0][2] == self.test_params
    
    def test_parameter_versioning(self):
        """Test 6: Parameter versioning works"""
        # Update parameters twice
        self.registry.update_parameters(self.strategy_type, {'param1': 1})
        self.registry.update_parameters(self.strategy_type, {'param1': 2})
        
        # Check versions
        assert self.registry._version_counters[self.strategy_type][None] == 2
    
    def test_rollback_parameters(self):
        """Test 7: Parameter rollback works"""
        # Set initial parameters
        params_v1 = {'lookback_period': 30}
        params_v2 = {'lookback_period': 60}
        
        self.registry.update_parameters(self.strategy_type, params_v1)
        self.registry.update_parameters(self.strategy_type, params_v2)
        
        # Rollback to version 1
        success = self.registry.rollback_parameters(self.strategy_type, 1)
        assert success
        
        # Verify rollback
        current_params = self.registry.get_parameters(self.strategy_type)
        assert current_params['lookback_period'] == 30
    
    def test_parameter_validation(self):
        """Test 8: Parameter validation works"""
        # Valid parameters
        is_valid, error = self.registry.validate_parameters(
            self.strategy_type,
            self.test_params
        )
        assert is_valid
        assert error is None
        
        # Invalid parameters (not a dict)
        is_valid, error = self.registry.validate_parameters(
            self.strategy_type,
            "not_a_dict"
        )
        assert not is_valid
        assert error is not None
        
        # Empty parameters
        is_valid, error = self.registry.validate_parameters(
            self.strategy_type,
            {}
        )
        assert not is_valid
    
    def test_configuration_store_save_load(self):
        """Test 9: Configuration store saves and loads"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ConfigurationStore(tmpdir)
            
            # Save parameters
            success = store.save_parameters(
                self.strategy_type,
                self.test_params
            )
            assert success
            
            # Load parameters
            loaded_params = store.load_parameters(self.strategy_type)
            assert loaded_params == self.test_params
    
    def test_json_persistence(self):
        """Test 10: JSON persistence works correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ConfigurationStore(tmpdir)
            
            # Save and verify file exists
            store.save_parameters(self.strategy_type, self.test_params)
            
            file_path = Path(tmpdir) / self.strategy_type / "default.json"
            assert file_path.exists()
            
            # Verify JSON content
            import json
            with open(file_path) as f:
                data = json.load(f)
            
            assert 'parameters' in data
            assert data['parameters'] == self.test_params
    
    def test_parameter_history_tracking(self):
        """Test 11: Parameter history is tracked"""
        # Make multiple updates
        self.registry.update_parameters(self.strategy_type, {'param1': 1})
        self.registry.update_parameters(self.strategy_type, {'param1': 2})
        self.registry.update_parameters(self.strategy_type, {'param1': 3})
        
        # Get history
        history = self.registry.get_parameter_history(self.strategy_type)
        assert len(history) == 3
        assert all(isinstance(v, ParameterVersion) for v in history)
    
    def test_concurrent_updates(self):
        """Test 12: Concurrent updates are handled"""
        # Subscribe multiple callbacks
        callbacks_called = [[], []]
        
        def callback1(st, sym, params):
            callbacks_called[0].append(params)
        
        def callback2(st, sym, params):
            callbacks_called[1].append(params)
        
        self.registry.subscribe(self.strategy_type, callback1)
        self.registry.subscribe(self.strategy_type, callback2)
        
        # Update parameters
        self.registry.update_parameters(self.strategy_type, self.test_params)
        
        # Both callbacks should be called
        assert len(callbacks_called[0]) == 1
        assert len(callbacks_called[1]) == 1
    
    def test_error_handling(self):
        """Test 13: Error handling works correctly"""
        # Try to rollback non-existent version
        success = self.registry.rollback_parameters(self.strategy_type, 999)
        assert not success
        
        # Try to get parameters for non-existent strategy
        params = self.registry.get_parameters("non_existent_strategy")
        assert params == {}


class TestConfigurationStore:
    """Tests for ConfigurationStore"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tmpdir = tempfile.mkdtemp()
        self.store = ConfigurationStore(self.tmpdir)
        self.strategy_type = "momentum"
        self.test_params = {
            'lookback_period': 60,
            'momentum_threshold': 0.02
        }
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_save_and_load_default_parameters(self):
        """Test: Save and load default parameters"""
        success = self.store.save_parameters(self.strategy_type, self.test_params)
        assert success
        
        loaded = self.store.load_parameters(self.strategy_type)
        assert loaded == self.test_params
    
    def test_save_and_load_symbol_specific(self):
        """Test: Save and load symbol-specific parameters"""
        success = self.store.save_parameters(
            self.strategy_type,
            self.test_params,
            symbol="NVDA"
        )
        assert success
        
        loaded = self.store.load_parameters(self.strategy_type, "NVDA")
        assert loaded == self.test_params
    
    def test_list_configurations(self):
        """Test: List configurations works"""
        # Save multiple configurations
        self.store.save_parameters(self.strategy_type, self.test_params)
        self.store.save_parameters(self.strategy_type, self.test_params, symbol="NVDA")
        self.store.save_parameters(self.strategy_type, self.test_params, symbol="TSLA")
        
        # List all
        configs = self.store.list_configurations()
        assert len(configs) >= 3
    
    def test_delete_configuration(self):
        """Test: Delete configuration works"""
        # Save then delete
        self.store.save_parameters(self.strategy_type, self.test_params)
        success = self.store.delete_configuration(self.strategy_type)
        assert success
        
        # Verify deleted
        loaded = self.store.load_parameters(self.strategy_type)
        assert loaded is None
    
    def test_version_history(self):
        """Test: Version history is saved"""
        # Save multiple versions
        self.store.save_parameters(self.strategy_type, {'param': 1})
        self.store.save_parameters(self.strategy_type, {'param': 2})
        self.store.save_parameters(self.strategy_type, {'param': 3})
        
        # Check versions directory exists
        versions_dir = Path(self.tmpdir) / self.strategy_type / "versions"
        assert versions_dir.exists()
        
        # Check version files exist
        version_files = list(versions_dir.glob("default_v*.json"))
        assert len(version_files) >= 2  # v1, v2 (v3 is current)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

