# Data Configuration Guide

This guide explains how to configure the statistical arbitrage system to use your Polygon.io CSV files from any directory on your system.

## 🎯 Current Configuration

The system is currently configured to load data from:
```
/Users/lei/Documents/data/polygon
```

## 📁 Supported File Formats

The system supports these Polygon.io file formats:

### Daily Aggregate Format (Recommended)
```
/Users/lei/Documents/data/polygon/
├── 2023-01-03.csv.gz
├── 2023-01-04.csv.gz
├── 2023-01-05.csv.gz
└── ...
```

### Symbol-Based Format
```
/Users/lei/Documents/data/polygon/
├── AAPL_1m_2023.csv
├── AAPL_1m_2024.csv
├── MSFT_1m_2023.csv
└── ...
```

## ⚙️ Configuration Methods

### Method 1: Environment Variables (Recommended for Production)

Set environment variables in your shell:

```bash
# Data directory
export POLYGON_DATA_DIR="/Users/lei/Documents/data/polygon"

# Optional settings
export DATA_SOURCE="polygon_offline"
export CACHE_ENABLED="true"
export VALIDATE_QUALITY="true"
export FILTER_MARKET_HOURS="true"
```

### Method 2: Configuration File

Edit `stat_arb_project/config/data_config.yaml`:

```yaml
data:
  source: "polygon_offline"
  data_directory: "/Users/lei/Documents/data/polygon"
  cache_enabled: true
  validate_quality: true
  filter_market_hours: true
```

### Method 3: Code Configuration

```python
from stat_arb_project.data.data_config import DataConfig, DataSource

config = DataConfig(
    source=DataSource.POLYGON_OFFLINE,
    data_directory="/Users/lei/Documents/data/polygon",
    validate_quality=True
)
```

## 🧪 Testing Your Configuration

Run the test script to verify your configuration:

```bash
python test_data_loading.py
```

This will:
- Test data loading with default configuration
- Test data loading with custom configuration
- Test data loading with environment variables
- Check your directory structure
- Verify file availability

## 🔧 Changing the Data Directory

### Option 1: Change Default Directory

Edit `stat_arb_project/data/data_config.py`:

```python
@dataclass
class DataConfig:
    data_directory: str = "/path/to/your/new/directory"
```

### Option 2: Use Environment Variable

```bash
export POLYGON_DATA_DIR="/path/to/your/new/directory"
```

### Option 3: Use Configuration File

Edit `stat_arb_project/config/data_config.yaml`:

```yaml
data:
  data_directory: "/path/to/your/new/directory"
```

## 📊 Data Quality Settings

### Validation Options

```yaml
data:
  validate_quality: true      # Enable data quality checks
  filter_market_hours: true   # Only use market hours data
  handle_outliers: true       # Handle price outliers
```

### Cache Settings

```yaml
data:
  cache_enabled: true         # Enable data caching
  cache_directory: "data/cache"  # Cache directory
```

## 🚀 Usage Examples

### Basic Usage

```python
from stat_arb_project.data.unified_data_loader import load_intraday_data

# Load data using default configuration
data = load_intraday_data(
    tickers=['AAPL', 'MSFT'],
    duration_days=30,
    interval='1m',
    data_source='polygon_offline'
)
```

### Advanced Usage

```python
from stat_arb_project.data.unified_data_loader import UnifiedDataLoader
from stat_arb_project.data.data_config import DataConfig, DataSource

# Create custom configuration
config = DataConfig(
    source=DataSource.POLYGON_OFFLINE,
    data_directory="/Users/lei/Documents/data/polygon",
    validate_quality=True,
    filter_market_hours=True
)

# Use the loader
loader = UnifiedDataLoader(config)
data = loader.load_data(
    symbols=['AAPL', 'MSFT'],
    start_date='2023-01-01',
    end_date='2023-12-31',
    interval='1m',
    data_type='close'
)
```

## 🔍 Troubleshooting

### Common Issues

1. **"Data directory does not exist"**
   - Verify the path exists: `ls /Users/lei/Documents/data/polygon`
   - Check permissions: `ls -la /Users/lei/Documents/data/polygon`

2. **"No data files found"**
   - Ensure files have correct extensions: `.csv` or `.csv.gz`
   - Check file naming convention

3. **"No symbols available"**
   - Verify files contain the expected symbols
   - Check file format and schema

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Tips

1. **Use compressed files**: `.csv.gz` files load faster
2. **Enable caching**: Reduces repeated file reads
3. **Filter market hours**: Reduces data size and improves quality
4. **Use appropriate date ranges**: Load only needed data

## 🔄 Migration from Other Directories

If you need to change from the current directory:

1. **Backup your data**
2. **Update configuration** using one of the methods above
3. **Test the new configuration** with `python test_data_loading.py`
4. **Update documentation** if needed

## 📝 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `POLYGON_DATA_DIR` | `/Users/lei/Documents/data/polygon` | Data directory path |
| `DATA_SOURCE` | `polygon_offline` | Data source type |
| `CACHE_ENABLED` | `true` | Enable data caching |
| `CACHE_DIRECTORY` | `data/cache` | Cache directory |
| `VALIDATE_QUALITY` | `true` | Enable data validation |
| `FILTER_MARKET_HOURS` | `true` | Filter to market hours |
| `HANDLE_OUTLIERS` | `true` | Handle price outliers |
| `MAX_RETRIES` | `3` | Maximum retry attempts |
| `RETRY_DELAY` | `1.0` | Retry delay in seconds |

---

**Note**: The system is designed to be flexible. You can store your data anywhere on your system and configure the system to load from that location. 