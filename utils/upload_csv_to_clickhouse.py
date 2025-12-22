#!/usr/bin/env python3
"""
CSV Upload Utility for ClickHouse
==================================

Utility script to upload compressed CSV files containing tick data
into the local ClickHouse database (polygon_data.ticks table).

Features:
- Supports compressed CSV files (.csv.gz, .csv.bz2, etc.)
- Batch insertion for performance
- Progress tracking
- Error handling and validation
- Command-line interface

Usage:
    python upload_csv_to_clickhouse.py file1.csv.gz file2.csv.gz --batch-size 10000

Author: StatArb_Gemini Utils
Version: 1.0.0
"""

import argparse
import gzip
import logging
import sys
from pathlib import Path
from typing import List, Optional
import pandas as pd
from glob import glob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import requests
    from dotenv import load_dotenv
    import os
except ImportError as e:
    logger.error(f"Missing required dependency: {e}")
    logger.error("Please install required packages: pip install requests python-dotenv")
    sys.exit(1)


class ClickHouseCSVUploader:
    """
    ClickHouse CSV Upload Handler

    Handles uploading CSV data to ClickHouse with proper error handling
    and performance optimizations.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        database: str = "polygon_data",
        table: str = "ticks",
        batch_size: int = 10000,
        clear_table: bool = False
    ):
        """
        Initialize the uploader.

        Args:
            host: ClickHouse host
            port: ClickHouse port
            database: Database name
            table: Table name
            batch_size: Batch size for insertions
            clear_table: Whether to clear the table before uploading
        """
        self.host = host
        self.port = port
        self.database = database
        self.table = table
        self.batch_size = batch_size
        self.clear_table = clear_table
        self.url = f"http://{host}:{port}"
        self.session = None

    def clear_table_data(self) -> bool:
        """
        Clear all data from the target table.

        Returns:
            True if successful, False otherwise
        """
        try:
            query = f"TRUNCATE TABLE {self.database}.{self.table}"
            resp = self.session.post(self.url, data=query)
            if resp.status_code == 200:
                logger.info(f"🗑️  Cleared all data from {self.database}.{self.table}")
                return True
            else:
                logger.error(f"❌ Failed to clear table: HTTP {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Error clearing table: {e}")
            return False

    def connect(self) -> bool:
        """
        Establish connection to ClickHouse.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.session = requests.Session()
            # Test connection
            resp = self.session.post(self.url, data="SELECT 1")
            if resp.status_code == 200:
                logger.info("✅ Connected to ClickHouse successfully")
                return True
            else:
                logger.error(f"❌ ClickHouse connection test failed: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to ClickHouse: {e}")
            return False

    def validate_csv_structure(self, df: pd.DataFrame) -> bool:
        """
        Validate CSV DataFrame structure matches expected schema.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        required_columns = {'ticker', 'window_start', 'open', 'high', 'low', 'close', 'volume'}

        if not required_columns.issubset(set(df.columns)):
            missing = required_columns - set(df.columns)
            logger.error(f"❌ Missing required columns: {missing}")
            return False

        # Validate data types
        try:
            # ticker should be string
            df['ticker'] = df['ticker'].astype(str)

            # window_start should be convertible to int64 (nanoseconds)
            df['window_start'] = df['window_start'].astype('int64')

            # OHLCV should be numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Check for NaN values
            if df[['open', 'high', 'low', 'close', 'volume']].isnull().any().any():
                logger.warning("⚠️  Found NaN values in OHLCV columns, they will be converted to 0")
                df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].fillna(0)

        except Exception as e:
            logger.error(f"❌ Data type validation failed: {e}")
            return False

        return True

    def read_csv_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """
        Read CSV file, handling compression automatically.

        Args:
            file_path: Path to CSV file

        Returns:
            DataFrame if successful, None otherwise
        """
        try:
            logger.info(f"📖 Reading CSV file: {file_path}")

            # pandas can handle compression automatically based on file extension
            df = pd.read_csv(file_path)

            if df.empty:
                logger.warning(f"⚠️  CSV file is empty: {file_path}")
                return None

            logger.info(f"✅ Read {len(df)} rows from {file_path}")
            return df

        except Exception as e:
            logger.error(f"❌ Failed to read CSV file {file_path}: {e}")
            return None

    def upload_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Upload DataFrame to ClickHouse.

        Args:
            df: DataFrame to upload

        Returns:
            True if successful, False otherwise
        """
        if not self.validate_csv_structure(df):
            return False

        try:
            # Convert to list of tuples for insertion
            data = df[['ticker', 'window_start', 'open', 'high', 'low', 'close', 'volume', 'transactions']].values.tolist()

            # Insert in batches
            total_rows = len(data)
            inserted = 0

            for i in range(0, total_rows, self.batch_size):
                batch = data[i:i + self.batch_size]

                # Format batch as VALUES string
                values = []
                for row in batch:
                    # Escape single quotes in ticker
                    ticker = str(row[0]).replace("'", "\\'")
                    values.append(f"('{ticker}', {row[1]}, {row[2]}, {row[3]}, {row[4]}, {row[5]}, {row[6]}, {row[7]})")

                values_str = ",\n".join(values)

                query = f"""
                INSERT INTO {self.database}.{self.table}
                (ticker, window_start, open, high, low, close, volume, transactions)
                VALUES
                {values_str}
                """

                resp = self.session.post(self.url, data=query)
                if resp.status_code != 200:
                    logger.error(f"❌ Insert failed for batch {i//self.batch_size + 1}: {resp.text}")
                    return False

                inserted += len(batch)
                logger.info(f"📤 Inserted batch {i//self.batch_size + 1}: {len(batch)} rows (total: {inserted}/{total_rows})")

            logger.info(f"✅ Successfully uploaded {total_rows} rows to {self.database}.{self.table}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to upload data: {e}")
            return False

    def upload_files(self, file_paths: List[Path]) -> bool:
        """
        Upload multiple CSV files.

        Args:
            file_paths: List of paths to CSV files

        Returns:
            True if all uploads successful, False otherwise
        """
        if not self.connect():
            return False

        # Clear table if requested
        if self.clear_table:
            if not self.clear_table_data():
                logger.error("❌ Failed to clear table, aborting upload")
                return False

        success_count = 0

        for file_path in file_paths:
            if not file_path.exists():
                logger.error(f"❌ File not found: {file_path}")
                continue

            df = self.read_csv_file(file_path)
            if df is None:
                continue

            if self.upload_dataframe(df):
                success_count += 1
            else:
                logger.error(f"❌ Failed to upload {file_path}")

        total_files = len(file_paths)
        logger.info(f"📊 Upload summary: {success_count}/{total_files} files successful")

        return success_count == total_files


def load_config_from_env():
    """
    Load ClickHouse configuration from environment variables.

    Returns:
        Dict with configuration values
    """
    load_dotenv()

    return {
        'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
        'port': int(os.getenv('CLICKHOUSE_PORT', '8123')),
        'database': os.getenv('CLICKHOUSE_DATABASE', 'polygon_data'),
        'table': os.getenv('CLICKHOUSE_TABLE', 'ticks')
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload compressed CSV files to ClickHouse polygon_data.ticks table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upload_csv_to_clickhouse.py data/ticks_2024.csv.gz
  python upload_csv_to_clickhouse.py D:\\dbticks\\*.csv.gz --batch-size 50000
  python upload_csv_to_clickhouse.py file1.csv.gz file2.csv.gz --clear-table
  python upload_csv_to_clickhouse.py file1.csv.gz file2.csv.gz --host 192.168.1.100
        """
    )

    parser.add_argument(
        'files',
        nargs='+',
        type=Path,
        help='CSV files to upload (supports compressed files)'
    )

    parser.add_argument(
        '--host',
        default=None,
        help='ClickHouse host (default: localhost or CLICKHOUSE_HOST env var)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='ClickHouse port (default: 8123 or CLICKHOUSE_PORT env var)'
    )

    parser.add_argument(
        '--database',
        default=None,
        help='ClickHouse database (default: polygon_data or CLICKHOUSE_DATABASE env var)'
    )

    parser.add_argument(
        '--table',
        default=None,
        help='ClickHouse table (default: ticks or CLICKHOUSE_TABLE env var)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=10000,
        help='Batch size for insertions (default: 10000)'
    )

    parser.add_argument(
        '--clear-table',
        action='store_true',
        help='Clear the target table before uploading data'
    )

    args = parser.parse_args()

    # Load config from env
    config = load_config_from_env()

    # Override with command line args
    config.update({
        k: v for k, v in {
            'host': args.host,
            'port': args.port,
            'database': args.database,
            'table': args.table
        }.items() if v is not None
    })

    logger.info("🚀 Starting CSV upload to ClickHouse")
    logger.info(f"📍 Target: {config['host']}:{config['port']}/{config['database']}.{config['table']}")
    # Expand glob patterns in file arguments
    expanded_files = []
    for file_pattern in args.files:
        matches = glob(str(file_pattern))
        if matches:
            expanded_files.extend([Path(match) for match in matches])
        else:
            # If no matches, treat as literal path
            expanded_files.append(Path(file_pattern))

    if not expanded_files:
        logger.error("❌ No files found matching the specified patterns")
        sys.exit(1)

    logger.info(f"📁 Found {len(expanded_files)} files to process")
    logger.info(f"🔢 Batch size: {args.batch_size}")

    # Create uploader
    uploader = ClickHouseCSVUploader(
        host=config['host'],
        port=config['port'],
        database=config['database'],
        table=config['table'],
        batch_size=args.batch_size,
        clear_table=args.clear_table
    )

    # Upload files
    success = uploader.upload_files(expanded_files)

    if success:
        logger.info("🎉 All uploads completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Some uploads failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()