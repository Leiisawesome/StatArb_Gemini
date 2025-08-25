# Timestamp Format Documentation
## Critical Infrastructure Requirements

**⚠️ CRITICAL: This document defines the timestamp format requirements for the entire trading system. Any deviation from these requirements will cause system-wide failures.**

---

## 📊 **Data Source: ClickHouse `polygon_data.ticks` Table**

### **Timestamp Storage Format**
- **Column**: `window_start` 
- **Type**: `UInt64`
- **Format**: **Nanoseconds since Unix epoch**
- **Example**: `1735885800000000000` = January 3, 2025 14:30:00 UTC

### **Conversion Requirements**

#### ✅ **CORRECT Conversion (MANDATORY)**
```sql
-- Convert nanoseconds to datetime
toDateTime(window_start / 1000000000)

-- Example query
SELECT 
    toDateTime(window_start / 1000000000) as timestamp,
    open, high, low, close, volume
FROM polygon_data.ticks 
WHERE ticker = 'TSLA' 
  AND toDate(toDateTime(window_start / 1000000000)) = '2025-01-03'
```

#### ❌ **INCORRECT Conversions (WILL CAUSE FAILURES)**
```sql
-- These will produce wrong dates (2106-02-07 instead of 2025-01-03)
toDateTime(window_start)           -- ❌ Wrong: treats nanoseconds as seconds
toDateTime(window_start / 1000)    -- ❌ Wrong: treats nanoseconds as milliseconds  
toDateTime(window_start / 1000000) -- ❌ Wrong: treats nanoseconds as microseconds
```

---

## 🏗️ **System Architecture Components**

### **1. Enhanced ClickHouse Loader** ✅ **FIXED**
- **File**: `core_structure/market_data/enhanced_clickhouse_loader.py`
- **Status**: ✅ Uses correct conversion (`window_start / 1000000000`)
- **Validation**: ✅ Integrated with `DataValidationMonitor`

### **2. Data Manager** ✅ **VERIFIED**
- **File**: `core_structure/market_data/data_manager.py`
- **Status**: ✅ Uses `EnhancedClickHouseLoader` (correct conversion)
- **Method**: `load_historical_data()` → `load_pair_data()` → `enhanced_loader.load_symbol_data()`

### **3. Backtesting Data Provider** ✅ **VERIFIED**
- **File**: `core_structure/market_data/backtesting_data_provider.py`
- **Status**: ✅ Uses `EnhancedClickHouseLoader` via `DataRequest`
- **Integration**: ✅ Properly integrated with backtesting system

### **4. Multi-Strategy Backtester** ✅ **VERIFIED**
- **File**: `testing_framework/multi_strategy_backtest_real_data.py`
- **Status**: ✅ Uses `core_engine.data_manager.load_historical_data()`
- **Data Flow**: ✅ Confirmed to access $415.12 high prices correctly

---

## 🔍 **Data Validation System**

### **Automatic Validation** ✅ **IMPLEMENTED**
- **File**: `core_structure/market_data/data_validation_monitor.py`
- **Features**:
  - ✅ Timestamp format detection and validation
  - ✅ Date range verification (prevents 2106-02-07 errors)
  - ✅ OHLC data validation
  - ✅ Volume and completeness checks
  - ✅ Outlier detection
  - ✅ Real-time monitoring and alerting

### **Validation Integration**
- **Enhanced ClickHouse Loader**: ✅ Validates all loaded data
- **Error Logging**: ✅ Critical errors logged with details
- **Performance Impact**: ✅ Minimal (can be disabled if needed)

---

## 📈 **Verified Data Availability**

### **TSLA January 3, 2025 Data** ✅ **CONFIRMED**
- **Total Records**: 1,103 (full day coverage)
- **Time Range**: 00:00:00 to 23:59:00
- **Highest Price**: **$415.12** at **15:21:00**
- **High Price Records**: 28 records with prices ≥ $410

### **Sample High Prices**
```
Timestamp               High     Close    Volume
2025-01-03 15:21:00    $415.12  $414.40  286,632
2025-01-03 15:26:00    $414.77  $412.95  341,446
2025-01-03 15:22:00    $414.40  $409.49  345,584
2025-01-03 15:32:00    $413.91  $412.25  305,682
2025-01-03 15:38:00    $413.72  $412.74  266,483
```

---

## 🧪 **Testing and Verification**

### **Data Loading Tests** ✅ **PASSED**
```bash
# Test current data loading system
python test_current_data_loading.py
# Result: ✅ SUCCESS - Can access $410+ prices

# Test backtesting data flow  
python debug_backtest_data_flow.py
# Result: ✅ SUCCESS - Backtest system has correct data
```

### **Validation Tests** ✅ **IMPLEMENTED**
- **Timestamp Format Detection**: ✅ Detects nanoseconds correctly
- **Date Range Validation**: ✅ Prevents future/past date errors
- **Data Quality Checks**: ✅ OHLC, volume, completeness validation
- **Performance Monitoring**: ✅ Query time and error tracking

---

## 🚨 **Critical Failure Points (RESOLVED)**

### **❌ Previous Issue: Wrong Timestamp Conversion**
- **Problem**: Using `toDateTime(window_start)` instead of `toDateTime(window_start / 1000000000)`
- **Result**: Dates showed as 2106-02-07 instead of 2025-01-03
- **Impact**: System couldn't access any real market data
- **Status**: ✅ **RESOLVED** - All components now use correct conversion

### **✅ Current Status: Infrastructure Working**
- **Data Loading**: ✅ All paths use correct timestamp conversion
- **Validation**: ✅ Automatic detection prevents future issues
- **Monitoring**: ✅ Real-time validation and error reporting
- **Testing**: ✅ Comprehensive test coverage

---

## 📋 **Maintenance Checklist**

### **For Developers**
- [ ] Always use `toDateTime(window_start / 1000000000)` for ClickHouse queries
- [ ] Test timestamp conversion with sample queries before deployment
- [ ] Monitor validation logs for data quality issues
- [ ] Run data loading tests after any infrastructure changes

### **For Operations**
- [ ] Monitor validation error logs daily
- [ ] Check data quality metrics in system dashboards
- [ ] Verify timestamp ranges in loaded data
- [ ] Alert on validation failures or data gaps

### **For New Components**
- [ ] Use `EnhancedClickHouseLoader` for all data loading
- [ ] Integrate with `DataValidationMonitor` for quality checks
- [ ] Follow established data loading patterns
- [ ] Test with real data before production deployment

---

## 🔗 **Related Files**

### **Core Infrastructure**
- `core_structure/market_data/enhanced_clickhouse_loader.py` - Main data loader
- `core_structure/market_data/data_manager.py` - Data management layer
- `core_structure/market_data/data_validation_monitor.py` - Validation system
- `core_structure/market_data/backtesting_data_provider.py` - Backtesting integration

### **Testing and Debugging**
- `test_current_data_loading.py` - Data loading verification
- `debug_backtest_data_flow.py` - Backtesting data flow debugging
- `check_high_prices_corrected.py` - High price data verification

### **Configuration**
- `core_structure/infrastructure/config/` - System configuration
- `core_structure/infrastructure/database/clickhouse_client.py` - Database client

---

**📝 Document Version**: 1.0  
**📅 Last Updated**: August 23, 2025  
**👤 Author**: Pro Quant Infrastructure Team  
**🔄 Review Cycle**: Monthly or after any timestamp-related changes
