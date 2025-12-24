import pytest
import yaml
from pathlib import Path
from livepapertest.utils.config_loader import load_yaml

def test_load_yaml_success(tmp_path):
    config_data = {"key": "value", "nested": {"a": 1}}
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    
    loaded_data = load_yaml(str(config_file))
    assert loaded_data == config_data

def test_load_yaml_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_yaml("non_existent_file.yaml")

def test_load_yaml_invalid_type(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    with open(config_file, "w") as f:
        f.write("- item1\n- item2") # This is a list, not a dict
    
    with pytest.raises(ValueError, match="Config root must be a mapping/dict"):
        load_yaml(str(config_file))

def test_load_yaml_empty_file(tmp_path):
    config_file = tmp_path / "empty.yaml"
    config_file.touch()
    
    loaded_data = load_yaml(str(config_file))
    assert loaded_data == {}
