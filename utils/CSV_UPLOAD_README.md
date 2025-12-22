# CSV Upload Utility for ClickHouse

This utility script uploads offline compressed CSV files containing tick data into the local ClickHouse database.

## Features

- **Compressed CSV Support**: Automatically handles compressed files (.csv.gz, .csv.bz2, etc.)
- **Batch Processing**: Configurable batch size for optimal performance
- **Data Validation**: Validates CSV structure and data types
- **Progress Tracking**: Shows detailed progress during upload
- **Error Handling**: Comprehensive error handling and logging
- **Command-line Interface**: Easy-to-use CLI with flexible options

## Prerequisites

- Python 3.8+
- ClickHouse server running on localhost:8123 (or configured host/port)
- Required Python packages: `requests`, `python-dotenv`, `pandas`

## Installation

The required packages are included in the project's `requirements.txt`. Install with:

```bash
pip install -r requirements.txt
```

## Database Setup

The script expects a ClickHouse database named `polygon_data` with a table `ticks` having the following schema:

```sql
CREATE TABLE polygon_data.ticks (
    ticker String,
    window_start UInt64,  -- Nanosecond timestamp
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64
) ENGINE = MergeTree()
ORDER BY (ticker, window_start);
```

## Usage

### Basic Usage

Upload a single CSV file:
```bash
python utils/upload_csv_to_clickhouse.py data/ticks_2024.csv.gz
```

Upload multiple files:
```bash
python utils/upload_csv_to_clickhouse.py file1.csv.gz file2.csv.gz file3.csv.gz
```

Upload all CSV files in a directory:
```bash
python utils/upload_csv_to_clickhouse.py data/*.csv.gz
```

### Advanced Options

Specify custom ClickHouse connection:
```bash
python utils/upload_csv_to_clickhouse.py data/ticks.csv.gz --host 192.168.1.100 --port 8123 --database mydb --table myticks
```

Adjust batch size for performance:
```bash
python utils/upload_csv_to_clickhouse.py data/ticks.csv.gz --batch-size 50000
```

Clear table before uploading (fresh import):
```bash
python utils/upload_csv_to_clickhouse.py D:\dbticks\*.csv.gz --clear-table
```

### Command Line Options

- `files`: CSV files to upload (supports wildcards and compressed files)
- `--host`: ClickHouse host (default: localhost)
- `--port`: ClickHouse port (default: 8123)
- `--database`: ClickHouse database (default: polygon_data)
- `--table`: ClickHouse table (default: ticks)
- `--batch-size`: Batch size for insertions (default: 10000)
- `--clear-table`: Clear the target table before uploading data

### Environment Variables

You can set default values using environment variables in your `.env` file:

```env
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=polygon_data
CLICKHOUSE_TABLE=ticks
```

## CSV Format

The CSV files should have the following columns (headers required):

```csv
ticker,window_start,open,high,low,close,volume
AAPL,1735689600000000000,150.25,151.00,149.50,150.75,1000000
MSFT,1735689600000000000,280.50,282.00,279.00,281.25,500000
```

### Column Descriptions

- `ticker`: Stock symbol (String)
- `window_start`: Window start time in nanoseconds since epoch (UInt64)
- `open`: Opening price (Float64)
- `high`: High price (Float64)
- `low`: Low price (Float64)
- `close`: Closing price (Float64)
- `volume`: Trading volume (UInt64)

## Data Location

In this project, offline CSV files are typically located in `D:\dbticks\`. The upload script can handle files from any location.

### Convenience Script

For easy uploads from `D:\dbticks`, use the provided batch script:

```bash
# Upload all files with default batch size (10,000)
upload_dbticks.bat

# Upload with custom batch size
upload_dbticks.bat 50000

# Upload with custom batch size and clear table first
upload_dbticks.bat 50000 clear
```

This script automatically activates the virtual environment and uploads all `.csv.gz` files from `D:\dbticks`.

### Bulk Upload

For large datasets, use larger batch sizes and monitor memory usage:

```bash
# Upload with larger batches for better performance
python utils/upload_csv_to_clickhouse.py large_dataset.csv.gz --batch-size 100000
```

## Troubleshooting

### Connection Issues

If you get connection errors:
1. Ensure ClickHouse is running: `sudo systemctl status clickhouse-server`
2. Check the host and port settings
3. Verify firewall settings allow connections to ClickHouse port

### Data Format Issues

If uploads fail due to data format:
1. Check CSV headers match expected columns
2. Ensure numeric columns contain valid numbers
3. Check for special characters in ticker symbols
4. Verify timestamps are in nanoseconds

### Performance Issues

For large files:
1. Increase batch size: `--batch-size 50000`
2. Monitor ClickHouse server resources
3. Consider splitting large files into smaller chunks

## Logging

The script provides detailed logging including:
- Connection status
- File reading progress
- Batch insertion progress
- Error messages with context
- Final upload summary

## Error Handling

The script handles various error conditions:
- Missing or invalid CSV files
- ClickHouse connection failures
- Data validation errors
- Insertion failures with rollback information

Failed uploads are logged with specific error messages to help diagnose issues.