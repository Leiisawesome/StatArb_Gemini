# ClickHouse Manager

Comprehensive database management toolkit for StatArb_Gemini's ClickHouse operations.

## Overview

The ClickHouse Manager provides a complete suite of tools for managing ClickHouse database operations including table management, data operations, system monitoring, and schema management specifically designed for the StatArb_Gemini trading system.

## Directory Structure

```
Tests/ClickHouse_Manager/
├── README.md                    # This documentation
├── clickhouse_manager.py        # Main management script
├── configs/                     # Configuration files
│   ├── clickhouse_config.json   # Default configuration
│   └── production_config.json   # Production settings (create as needed)
├── schemas/                     # SQL schema definitions
│   ├── market_data.sql          # Market data table schema
│   ├── trading_signals.sql      # Trading signals schema
│   ├── portfolio_positions.sql  # Portfolio positions schema
│   └── performance_analytics.sql # Performance metrics schema
└── sample_data/                 # Sample data files (create as needed)
```

## Features

### 🔧 Core Operations
- **Table Management**: Create, drop, list, and describe tables
- **Data Operations**: Insert, query, delete data with safety confirmations
- **Schema Management**: Apply pre-defined schemas optimized for trading data
- **Interactive Mode**: Command-line interface for complex operations

### 📊 Monitoring & Analytics
- **Database Statistics**: Comprehensive metrics and table sizes
- **Performance Monitoring**: Query execution times and system metrics
- **Partition Analysis**: Detailed partition information for optimized tables

### 🛡️ Safety Features
- **Confirmation Prompts**: Protection against accidental data loss
- **Connection Validation**: Automatic connection testing and error handling
- **Logging**: Comprehensive operation logging to file and console

## Quick Start

### 1. Installation Dependencies
```bash
# Install required packages
pip install clickhouse-driver pandas
```

### 2. Configure Connection
```bash
# Edit the configuration file
nano Tests/ClickHouse_Manager/configs/clickhouse_config.json
```

Update the configuration with your ClickHouse settings:
```json
{
  "host": "localhost",
  "port": 9000,
  "database": "trading",
  "user": "default",
  "password": "",
  "settings": {
    "max_execution_time": 300,
    "max_memory_usage": 10000000000
  }
}
```

### 3. Basic Usage

#### List All Tables
```bash
cd Tests/ClickHouse_Manager
python clickhouse_manager.py list-tables
```

#### Create a Table from Schema
```bash
python clickhouse_manager.py create-table market_data --schema schemas/market_data.sql
```

#### Query Data
```bash
python clickhouse_manager.py query "SELECT COUNT(*) FROM market_data"
```

#### Interactive Mode
```bash
python clickhouse_manager.py --interactive
```

## Command Reference

### Table Operations
```bash
# List all tables with statistics
python clickhouse_manager.py list-tables

# Describe table structure and partitions
python clickhouse_manager.py describe market_data

# Create table from schema file
python clickhouse_manager.py create-table signals --schema schemas/trading_signals.sql

# Create table with inline SQL
python clickhouse_manager.py create-table test --sql "CREATE TABLE test (id UInt32, name String) ENGINE=Memory"

# Drop table (with confirmation)
python clickhouse_manager.py drop-table old_table

# Force drop without confirmation
python clickhouse_manager.py drop-table old_table --force
```

### Data Operations
```bash
# Execute SELECT query with automatic limiting
python clickhouse_manager.py query "SELECT * FROM market_data WHERE symbol='AAPL'"

# Execute query with custom limit
python clickhouse_manager.py query "SELECT * FROM market_data" --limit 50

# Insert data from CSV file
python clickhouse_manager.py insert --table market_data --file data.csv

# Delete data with WHERE clause (with confirmation)
python clickhouse_manager.py delete --table market_data --where "timestamp < '2023-01-01'"

# Force delete without confirmation
python clickhouse_manager.py delete --table market_data --where "symbol='TEST'" --force
```

### System Operations
```bash
# Show database statistics and top tables
python clickhouse_manager.py stats

# Use custom configuration file
python clickhouse_manager.py --config /path/to/config.json list-tables

# Start interactive mode
python clickhouse_manager.py --interactive
```

## Interactive Mode Commands

Once in interactive mode (`python clickhouse_manager.py --interactive`):

```
ClickHouse> tables                              # List all tables
ClickHouse> desc market_data                    # Describe table
ClickHouse> stats                               # Database statistics
ClickHouse> SELECT COUNT(*) FROM market_data   # Execute query
ClickHouse> CREATE TABLE test (id UInt32) ENGINE=Memory  # Create table
ClickHouse> help                                # Show commands
ClickHouse> exit                                # Exit interactive mode
```

## Schema Templates

### Market Data Table
Optimized for high-frequency market data storage:
- **Compression**: DoubleDelta + LZ4 for timestamps, T64 + LZ4 for prices
- **Partitioning**: Monthly partitions by timestamp
- **Indexing**: Ordered by (symbol, timestamp) for fast lookups
- **TTL**: 2-year retention policy

### Trading Signals Table
Designed for signal storage and analysis:
- **Features**: Map type for flexible feature storage
- **Metadata**: Extensible metadata storage
- **Tracking**: Execution tracking and PnL calculation
- **Partitioning**: By month and signal type

### Portfolio Positions Table
For position tracking and portfolio management:
- **Engine**: ReplacingMergeTree for position updates
- **Risk Metrics**: Map storage for flexible risk data
- **Relationships**: Links to entry signals
- **Status Tracking**: Position lifecycle management

### Performance Analytics Table
For comprehensive performance tracking:
- **Multi-Entity**: Support for portfolios, strategies, and models
- **Period Analysis**: Daily, weekly, monthly, yearly metrics
- **Risk Metrics**: Comprehensive risk and return calculations
- **Benchmarking**: Alpha, beta, tracking error analysis

## Configuration Management

### Default Configuration
The default configuration (`configs/clickhouse_config.json`) includes:
- Local ClickHouse connection settings
- Optimized query settings for trading workloads
- Connection pooling configuration
- Compression settings

### Production Configuration
For production environments, create a separate configuration file:
```json
{
  "host": "production-clickhouse.company.com",
  "port": 9000,
  "database": "trading_prod",
  "user": "trading_user",
  "password": "secure_password",
  "settings": {
    "max_execution_time": 600,
    "max_memory_usage": 50000000000,
    "max_threads": 16
  },
  "pool_size": 10,
  "compression": "zstd"
}
```

## Best Practices

### Table Design
1. **Use appropriate engines**: MergeTree for analytics, ReplacingMergeTree for updates
2. **Optimize partitioning**: Monthly partitions for time-series data
3. **Choose correct data types**: Use specific types (DateTime64, LowCardinality)
4. **Apply compression**: Use codec specifications for better storage efficiency

### Query Optimization
1. **Use proper ORDER BY**: Leverage sorting keys for fast queries
2. **Filter early**: Apply WHERE clauses on indexed columns
3. **Limit results**: Always use LIMIT for exploratory queries
4. **Batch operations**: Use batch inserts for large datasets

### Data Management
1. **Regular maintenance**: Monitor partition sizes and merge performance
2. **TTL policies**: Implement data retention policies
3. **Backup strategy**: Regular backups of critical tables
4. **Monitoring**: Track query performance and resource usage

## Troubleshooting

### Connection Issues
```bash
# Test basic connectivity
python clickhouse_manager.py query "SELECT version()"

# Check configuration
python clickhouse_manager.py --config configs/clickhouse_config.json stats
```

### Performance Issues
```bash
# Check database statistics
python clickhouse_manager.py stats

# Analyze table partitions
python clickhouse_manager.py describe your_table_name
```

### Data Issues
```bash
# Check table structure
python clickhouse_manager.py describe problematic_table

# Verify data integrity
python clickhouse_manager.py query "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM market_data"
```

## Logging

All operations are logged to:
- **Console**: Real-time operation feedback
- **File**: `clickhouse_manager.log` in the current directory

Log levels include:
- **INFO**: Successful operations and connection status
- **WARNING**: Non-critical issues and fallback actions
- **ERROR**: Failed operations and critical issues

## Security Considerations

1. **Configuration Files**: Never commit passwords to version control
2. **Access Control**: Use dedicated database users with minimal privileges
3. **Network Security**: Use SSL/TLS for production connections
4. **Audit Logging**: Enable ClickHouse query logging for compliance

## Extension Points

The ClickHouse Manager can be extended with:
- **Custom schemas**: Add new table definitions in the schemas/ directory
- **Data validators**: Implement data quality checks before insertion
- **Backup utilities**: Add automated backup and restore functions
- **Monitoring dashboards**: Integrate with monitoring systems

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the ClickHouse documentation
3. Examine the log files for detailed error information
4. Test with simplified queries in interactive mode
