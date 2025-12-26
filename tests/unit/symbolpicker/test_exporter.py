import pytest
import os
import json
import shutil
from datetime import datetime
from symbolpicker.exporter import ArtifactExporter

@pytest.fixture
def sample_config(tmp_path):
    output_dir = tmp_path / "symbolpicks"
    return {
        'output': {
            'directory': str(output_dir),
            'filename_format': "universe_{date}_{regime}.json"
        }
    }

def test_exporter_basic(sample_config):
    exporter = ArtifactExporter(sample_config)
    
    universe = {
        'AAPL': {'rank': 1, 'score': 0.9},
        'MSFT': {'rank': 2, 'score': 0.8}
    }
    regime_data = {'label': 'BULL', 'confidence': 0.7}
    asof_date = datetime(2023, 1, 1)
    
    file_path = exporter.export(universe, regime_data, asof_date)
    
    assert os.path.exists(file_path)
    assert "universe_2023-01-01_BULL.json" in file_path
    
    with open(file_path, 'r') as f:
        data = json.load(f)
        assert data['asof_date'] == '2023-01-01'
        assert data['universe_size'] == 2
        assert 'AAPL' in data['symbols']
        assert 'checksum' in data

def test_exporter_unknown_regime(sample_config):
    exporter = ArtifactExporter(sample_config)
    universe = {'AAPL': {'rank': 1}}
    regime_data = {} # No label
    asof_date = datetime(2023, 1, 1)
    
    file_path = exporter.export(universe, regime_data, asof_date)
    assert "UNKNOWN" in file_path
