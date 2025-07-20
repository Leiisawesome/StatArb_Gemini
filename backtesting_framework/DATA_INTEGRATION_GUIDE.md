# 📊 Simplified Data Integration Guide for Backtesting Framework

## 🎯 **Overview**

The data integration has been **simplified** to focus exclusively on ClickHouse data access through the core system's DataManager. This provides a clean, focused approach for backtesting with your existing data infrastructure.

## 🚀 **What's Implemented**

### **1. Simplified DataIntegrationManager Class**

Located in `utils/data_integration.py`, this class provides:

- ✅ **ClickHouse Integration**: Uses core system DataManager
- ✅ **Data Validation**: Comprehensive quality checks
- ✅ **Caching System**: Improves performance with data caching
- ✅ **Error Handling**: Robust error management
- ✅ **Health Monitoring**: System status checking

### **2. Single Data Source**

**ClickHouse via Core System DataManager**:
- Uses your existing ClickHouse database infrastructure
- Leverages the enhanced ClickHouse loader
- Provides high-performance data access
- Supports multiple timeframes and data types

## 🔧 **How to Use**

### **Basic Usage**

```python
from utils.data_integration import DataIntegrationManager

# Initialize data integration manager
data_manager = DataIntegrationManager(cache_data=True)

# Load data from ClickHouse
data = data_manager.load_historical_data(
    symbols=["AAPL", "MSFT", "GOOGL"],
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```

### **Data Validation**

```python
# Validate loaded data
validation = data_manager._validate_data(data)

if validation['errors']:
    print("Data errors:", validation['errors'])

if validation['warnings']:
    print("Data warnings:", validation['warnings'])

# Get data information
info = data_manager._get_data_info(data)
print(f"Loaded {info['total_symbols']} symbols")
```

### **Health Status**

```python
# Check system health
health_status = data_manager.get_health_status()
print(f"Core system available: {health_status['core_system_available']}")
print(f"DataManager initialized: {health_status['data_manager_initialized']}")
```

## 🧪 **Testing the Integration**

Run the test script to verify everything works:

```bash
cd backtesting_framework
python test_data_integration.py
```

This will test:
- ✅ ClickHouse data loading
- ✅ Data validation
- ✅ Caching functionality
- ✅ Error handling
- ✅ Health status monitoring

## 📊 **Data Format**

All data is returned in standardized format:

```python
{
    'AAPL': pd.DataFrame({
        'open': [150.0, 151.0, ...],
        'high': [152.0, 153.0, ...],
        'low': [149.0, 150.0, ...],
        'close': [151.0, 152.0, ...],
        'volume': [1000000, 1100000, ...]
    }, index=pd.DatetimeIndex([...]))
}
```

## 🔄 **Integration with Experiment Runner**

The `ExperimentRunner` uses the simplified `DataIntegrationManager`:

```python
# In experiment_runner.py
def _load_data(self, config: ExperimentConfig) -> Dict[str, pd.DataFrame]:
    # Uses simplified data integration manager
    data = self.data_integration.load_historical_data(
        symbols=config.symbols,
        start_date=config.start_date,
        end_date=config.end_date
    )
    
    # Validates data quality
    validation_results = self.data_integration._validate_data(data)
    
    return data
```

## 🎯 **Strategy Usage**

Your strategies work with ClickHouse data:

```python
# In your strategy
def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
    # data contains ClickHouse market data
    for symbol, df in data.items():
        current_price = df['close'].iloc[-1]
        # Your strategy logic here
```

## 📈 **Data Quality Features**

### **Automatic Validation**

- ✅ **Required Columns**: Ensures OHLCV data present
- ✅ **Price Relationships**: Validates high ≥ open/close ≥ low
- ✅ **Missing Data**: Detects and reports data gaps
- ✅ **Negative Prices**: Flags invalid price data

### **Data Processing**

- ✅ **Date Standardization**: Converts all dates to datetime
- ✅ **Duplicate Removal**: Removes duplicate timestamps
- ✅ **Missing Value Handling**: Forward/backward fill
- ✅ **Column Standardization**: Lowercase column names

## 🚨 **Important Notes**

### **Core System Dependency**

The simplified integration **requires** the core system to be available:

```python
# Will raise RuntimeError if core system not available
data_manager = DataIntegrationManager()
```

### **ClickHouse Data Source**

All data comes from your ClickHouse database:
- ✅ **High Performance**: Optimized queries and caching
- ✅ **Data Quality**: Professional-grade data validation
- ✅ **Scalability**: Handles large datasets efficiently
- ✅ **Reliability**: Robust error handling and recovery

## 🔧 **Configuration Options**

### **DataIntegrationManager Parameters**

```python
data_manager = DataIntegrationManager(
    cache_data=True    # Enable data caching for performance
)
```

### **load_historical_data Parameters**

```python
data = data_manager.load_historical_data(
    symbols=["AAPL", "MSFT"],           # List of symbols
    start_date="2023-01-01",           # Start date
    end_date="2023-12-31",             # End date
    interval="1d",                     # Data interval (daily)
    include_volume=True                # Include volume data
)
```

## 📊 **Performance Monitoring**

### **Cache Statistics**

```python
stats = data_manager.get_cache_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Cached symbols: {stats['cached_symbols']}")
```

### **Health Status**

```python
health = data_manager.get_health_status()
print(f"Core system available: {health['core_system_available']}")
print(f"DataManager initialized: {health['data_manager_initialized']}")
print(f"Cache enabled: {health['cache_enabled']}")
```

## 🎯 **Next Steps**

1. **Test the Integration**:
   ```bash
   python test_data_integration.py
   ```

2. **Run Your Strategies**:
   ```bash
   python run_momentum_example.py
   ```

3. **Check Data Quality**:
   - Review validation results
   - Monitor data completeness
   - Verify price relationships

4. **Optimize Performance**:
   - Enable caching for repeated runs
   - Use appropriate date ranges
   - Monitor cache statistics

## ✅ **Summary**

The simplified data integration provides:

- ✅ **Focused Approach**: Only ClickHouse data access
- ✅ **High Performance**: Optimized for your existing infrastructure
- ✅ **Data Quality**: Comprehensive validation and processing
- ✅ **Reliability**: Robust error handling and monitoring
- ✅ **Simplicity**: Clean, maintainable codebase

Your backtesting framework now has **streamlined, professional-grade data integration** that works seamlessly with your ClickHouse infrastructure!

---

**Ready to run your strategies with ClickHouse data! 🚀** 