#!/usr/bin/env python3
"""
ClickHouse Database Management Script
====================================

Comprehensive command-line tool for managing ClickHouse database operations
including table management, data operations, and system monitoring.

Features:
- List, create, drop, describe tables
- Insert, query, delete data
- Database statistics and monitoring
- Backup and restore operations
- Configuration management
- Interactive mode for complex operations

Usage:
    python clickhouse_manager.py --help
    python clickhouse_manager.py list-tables
    python clickhouse_manager.py create-table market_data --schema schema.sql
    python clickhouse_manager.py query "SELECT COUNT(*) FROM market_data"
    python clickhouse_manager.py --interactive

Author: StatArb_Gemini Team
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

try:
    from clickhouse_driver import Client
    from clickhouse_driver.errors import ServerException, NetworkError
except ImportError:
    print("❌ clickhouse-driver not installed. Run: pip install clickhouse-driver")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('clickhouse_manager.log')
    ]
)
logger = logging.getLogger(__name__)

class ClickHouseManager:
    """Comprehensive ClickHouse database management system"""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize ClickHouse manager with configuration"""
        self.config = self._load_config(config_file)
        self.client = None
        self._connect()
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            'host': 'localhost',
            'port': 9000,
            'database': 'polygon_data',
            'user': 'default',
            'password': '',
            'settings': {
                'max_execution_time': 300,
                'max_memory_usage': 10000000000,
                'send_progress_in_http_headers': 1
            }
        }
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                default_config.update(file_config)
                logger.info(f"✅ Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load config file: {e}. Using defaults.")
        
        return default_config
    
    def _connect(self) -> bool:
        """Establish connection to ClickHouse"""
        try:
            # First try to connect without specifying database to check server connectivity
            test_client = Client(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                settings=self.config['settings']
            )
            
            # Test basic connectivity
            result = test_client.execute("SELECT version()")
            logger.info(f"✅ Connected to ClickHouse server {result[0][0]} at {self.config['host']}:{self.config['port']}")
            
            # Check if database exists, create if not
            databases = test_client.execute("SHOW DATABASES")
            db_names = [db[0] for db in databases]
            
            if self.config['database'] not in db_names:
                logger.info(f"📦 Database '{self.config['database']}' does not exist. Creating...")
                test_client.execute(f"CREATE DATABASE {self.config['database']}")
                logger.info(f"✅ Created database '{self.config['database']}'")
            
            # Now connect to the specific database
            self.client = Client(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                settings=self.config['settings']
            )
            
            # Test database connection
            self.client.execute("SELECT 1")
            logger.info(f"✅ Connected to database '{self.config['database']}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to ClickHouse: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Tuple]:
        """Execute a query and return results"""
        try:
            start_time = time.perf_counter()
            result = self.client.execute(query, params or {})
            duration = (time.perf_counter() - start_time) * 1000
            
            logger.info(f"⚡ Query executed in {duration:.2f}ms")
            return result
            
        except ServerException as e:
            logger.error(f"❌ Server error: {e}")
            raise
        except NetworkError as e:
            logger.error(f"❌ Network error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            raise
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List all tables in the database"""
        query = """
        SELECT 
            name,
            engine,
            total_rows,
            total_bytes,
            formatReadableSize(total_bytes) as size_readable,
            comment
        FROM system.tables 
        WHERE database = currentDatabase()
        ORDER BY total_bytes DESC
        """
        
        try:
            result = self.execute_query(query)
            tables = []
            
            print("\n📊 DATABASE TABLES")
            print("=" * 80)
            print(f"{'Table Name':<25} {'Engine':<15} {'Rows':<12} {'Size':<10} {'Comment':<20}")
            print("-" * 80)
            
            for row in result:
                name, engine, total_rows, total_bytes, size_readable, comment = row
                tables.append({
                    'name': name,
                    'engine': engine,
                    'rows': total_rows,
                    'bytes': total_bytes,
                    'size': size_readable,
                    'comment': comment or ''
                })
                
                print(f"{name:<25} {engine:<15} {total_rows:<12,} {size_readable:<10} {comment or '':<20}")
            
            print(f"\n📈 Total tables: {len(tables)}")
            return tables
            
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Get detailed table schema and statistics"""
        try:
            # Get table structure
            structure_query = f"DESCRIBE TABLE {table_name}"
            structure = self.execute_query(structure_query)
            
            # Get table info
            info_query = f"""
            SELECT 
                engine,
                total_rows,
                total_bytes,
                formatReadableSize(total_bytes) as size_readable,
                comment
            FROM system.tables 
            WHERE name = '{table_name}' AND database = currentDatabase()
            """
            info = self.execute_query(info_query)
            
            # Get partition info if applicable
            try:
                partition_query = f"""
                SELECT 
                    partition,
                    count() as parts,
                    sum(rows) as rows,
                    formatReadableSize(sum(bytes_on_disk)) as size
                FROM system.parts 
                WHERE table = '{table_name}' AND database = currentDatabase()
                GROUP BY partition
                ORDER BY partition
                """
                partitions = self.execute_query(partition_query)
            except:
                partitions = []
            
            table_info = {
                'name': table_name,
                'structure': structure,
                'info': info[0] if info else None,
                'partitions': partitions
            }
            
            # Display table information
            print(f"\n🔍 TABLE: {table_name}")
            print("=" * 60)
            
            if info:
                engine, total_rows, total_bytes, size_readable, comment = info[0]
                print(f"Engine: {engine}")
                print(f"Rows: {total_rows:,}")
                print(f"Size: {size_readable}")
                print(f"Comment: {comment or 'None'}")
            
            print(f"\n📋 SCHEMA:")
            print("-" * 60)
            print(f"{'Column':<25} {'Type':<20} {'Default':<15} {'Comment':<20}")
            print("-" * 60)
            
            for col in structure:
                name, type_name, default_type, default_expr, comment, codec_expr, ttl_expr = col
                print(f"{name:<25} {type_name:<20} {default_expr or '':<15} {comment or '':<20}")
            
            if partitions:
                print(f"\n🗂️  PARTITIONS:")
                print("-" * 60)
                print(f"{'Partition':<20} {'Parts':<10} {'Rows':<12} {'Size':<10}")
                print("-" * 60)
                for partition, parts, rows, size in partitions:
                    print(f"{partition:<20} {parts:<10} {rows:<12,} {size:<10}")
            
            return table_info
            
        except Exception as e:
            logger.error(f"Failed to describe table {table_name}: {e}")
            return {}
    
    def create_table(self, table_name: str, schema_file: Optional[str] = None, schema_sql: Optional[str] = None) -> bool:
        """Create a new table from schema file or SQL"""
        try:
            if schema_file and Path(schema_file).exists():
                with open(schema_file, 'r') as f:
                    create_sql = f.read()
            elif schema_sql:
                create_sql = schema_sql
            else:
                # Default market data table schema
                create_sql = f"""
                CREATE TABLE {table_name} (
                    timestamp DateTime64(3),
                    symbol String,
                    open Float64,
                    high Float64,
                    low Float64,
                    close Float64,
                    volume UInt64,
                    vwap Float64,
                    trade_count UInt32,
                    updated_at DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                PARTITION BY toYYYYMM(timestamp)
                ORDER BY (symbol, timestamp)
                """
            
            self.execute_query(create_sql)
            logger.info(f"✅ Table '{table_name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create table '{table_name}': {e}")
            return False
    
    def drop_table(self, table_name: str, confirm: bool = False) -> bool:
        """Drop a table (with confirmation)"""
        if not confirm:
            response = input(f"⚠️  Are you sure you want to drop table '{table_name}'? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Operation cancelled")
                return False
        
        try:
            self.execute_query(f"DROP TABLE IF EXISTS {table_name}")
            logger.info(f"✅ Table '{table_name}' dropped successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to drop table '{table_name}': {e}")
            return False
    
    def query_data(self, query: str, format_output: bool = True, limit: int = 100) -> Optional[pd.DataFrame]:
        """Execute a SELECT query and display results"""
        try:
            # Add LIMIT if not present and format_output is True
            if format_output and 'LIMIT' not in query.upper():
                query = f"{query.rstrip(';')} LIMIT {limit}"
            
            result = self.execute_query(query)
            
            if not result:
                print("📭 No results found")
                return None
            
            # Try to get column names
            try:
                columns_query = f"SELECT * FROM ({query}) LIMIT 0"
                self.client.execute(columns_query, columnar=True)
                # This is a simplified approach - in practice, you'd need to parse the query
                # or use a different method to get column names
            except:
                pass
            
            if format_output:
                print(f"\n📊 QUERY RESULTS ({len(result)} rows)")
                print("=" * 80)
                
                # Simple tabular display
                if result:
                    # Display first few rows
                    for i, row in enumerate(result[:20]):  # Show max 20 rows
                        print(f"Row {i+1}: {row}")
                    
                    if len(result) > 20:
                        print(f"... and {len(result) - 20} more rows")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return None
    
    def insert_data(self, table_name: str, data_file: Optional[str] = None, data: Optional[List[Dict]] = None) -> bool:
        """Insert data from file or direct data"""
        try:
            if data_file and Path(data_file).exists():
                if data_file.endswith('.csv'):
                    df = pd.read_csv(data_file)
                    data = df.to_dict('records')
                elif data_file.endswith('.json'):
                    with open(data_file, 'r') as f:
                        data = json.load(f)
                else:
                    logger.error("❌ Unsupported file format. Use CSV or JSON.")
                    return False
            
            if not data:
                logger.error("❌ No data provided for insertion")
                return False
            
            # Simple insert - this is a basic implementation
            # In practice, you'd want to use batch inserts for large datasets
            columns = list(data[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            
            insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES"
            
            # Batch insert
            values = []
            for row in data:
                values.append(tuple(row[col] for col in columns))
            
            self.client.execute(f"{insert_query} VALUES", values)
            logger.info(f"✅ Inserted {len(data)} rows into '{table_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to insert data into '{table_name}': {e}")
            return False
    
    def delete_data(self, table_name: str, where_clause: str, confirm: bool = False) -> bool:
        """Delete data from table with WHERE clause"""
        if not confirm:
            response = input(f"⚠️  Are you sure you want to delete from '{table_name}' WHERE {where_clause}? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Operation cancelled")
                return False
        
        try:
            delete_query = f"ALTER TABLE {table_name} DELETE WHERE {where_clause}"
            self.execute_query(delete_query)
            logger.info(f"✅ Deleted data from '{table_name}' WHERE {where_clause}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete data from '{table_name}': {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            # Database size
            size_query = """
            SELECT 
                formatReadableSize(sum(total_bytes)) as total_size,
                sum(total_rows) as total_rows,
                count() as table_count
            FROM system.tables 
            WHERE database = currentDatabase()
            """
            size_result = self.execute_query(size_query)
            
            # Top tables by size
            top_tables_query = """
            SELECT 
                name,
                formatReadableSize(total_bytes) as size,
                total_rows
            FROM system.tables 
            WHERE database = currentDatabase()
            ORDER BY total_bytes DESC
            LIMIT 10
            """
            top_tables = self.execute_query(top_tables_query)
            
            # System metrics
            system_query = """
            SELECT 
                metric,
                value,
                description
            FROM system.metrics 
            WHERE metric IN ('Query', 'Merge', 'NetworkReceive', 'NetworkSend')
            """
            system_metrics = self.execute_query(system_query)
            
            stats = {
                'database_size': size_result[0] if size_result else None,
                'top_tables': top_tables,
                'system_metrics': system_metrics
            }
            
            # Display stats
            print("\n📊 DATABASE STATISTICS")
            print("=" * 60)
            
            if size_result:
                total_size, total_rows, table_count = size_result[0]
                print(f"Total Size: {total_size}")
                print(f"Total Rows: {total_rows:,}")
                print(f"Table Count: {table_count}")
            
            print("\n🏆 TOP TABLES BY SIZE:")
            print("-" * 40)
            for name, size, rows in top_tables:
                print(f"{name:<20} {size:<12} {rows:,} rows")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            return {}
    
    def interactive_mode(self):
        """Interactive command mode"""
        print("\n🚀 ClickHouse Interactive Manager")
        print("Type 'help' for commands, 'exit' to quit")
        print("=" * 50)
        
        while True:
            try:
                command = input("\nClickHouse> ").strip()
                
                if command.lower() in ['exit', 'quit']:
                    print("👋 Goodbye!")
                    break
                elif command.lower() == 'help':
                    self._show_help()
                elif command.lower() == 'tables':
                    self.list_tables()
                elif command.lower() == 'stats':
                    self.get_database_stats()
                elif command.startswith('desc '):
                    table_name = command[5:].strip()
                    self.describe_table(table_name)
                elif command.lower().startswith('select'):
                    self.query_data(command)
                else:
                    # Try to execute as raw SQL
                    try:
                        result = self.execute_query(command)
                        print(f"✅ Query executed. Affected/returned rows: {len(result) if result else 0}")
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _show_help(self):
        """Show interactive mode help"""
        print("""
📖 AVAILABLE COMMANDS:
─────────────────────
  tables              - List all tables
  desc <table>        - Describe table structure
  stats               - Show database statistics
  SELECT ...          - Execute SELECT query
  CREATE TABLE ...    - Create new table
  DROP TABLE ...      - Drop table
  help                - Show this help
  exit/quit           - Exit interactive mode
  
💡 Examples:
  desc market_data
  SELECT COUNT(*) FROM market_data
  SELECT * FROM market_data LIMIT 5
        """)

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="ClickHouse Database Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list-tables
  %(prog)s describe market_data
  %(prog)s query "SELECT COUNT(*) FROM market_data"
  %(prog)s create-table new_table --schema schema.sql
  %(prog)s insert --table market_data --file data.csv
  %(prog)s stats
  %(prog)s --interactive
        """
    )
    
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--interactive', '-i', action='store_true', help='Start interactive mode')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List tables
    subparsers.add_parser('list-tables', help='List all tables')
    
    # Describe table
    desc_parser = subparsers.add_parser('describe', help='Describe table structure')
    desc_parser.add_argument('table', help='Table name')
    
    # Create table
    create_parser = subparsers.add_parser('create-table', help='Create new table')
    create_parser.add_argument('table', help='Table name')
    create_parser.add_argument('--schema', help='Schema file path')
    create_parser.add_argument('--sql', help='Direct SQL for table creation')
    
    # Drop table
    drop_parser = subparsers.add_parser('drop-table', help='Drop table')
    drop_parser.add_argument('table', help='Table name')
    drop_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Query
    query_parser = subparsers.add_parser('query', help='Execute SQL query')
    query_parser.add_argument('sql', help='SQL query to execute')
    query_parser.add_argument('--limit', type=int, default=100, help='Result limit')
    
    # Insert data
    insert_parser = subparsers.add_parser('insert', help='Insert data')
    insert_parser.add_argument('--table', required=True, help='Target table')
    insert_parser.add_argument('--file', help='Data file (CSV/JSON)')
    
    # Delete data
    delete_parser = subparsers.add_parser('delete', help='Delete data')
    delete_parser.add_argument('--table', required=True, help='Target table')
    delete_parser.add_argument('--where', required=True, help='WHERE clause')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Database stats
    subparsers.add_parser('stats', help='Show database statistics')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = ClickHouseManager(args.config)
    
    if args.interactive:
        manager.interactive_mode()
        return
    
    # Execute commands
    if args.command == 'list-tables':
        manager.list_tables()
    elif args.command == 'describe':
        manager.describe_table(args.table)
    elif args.command == 'create-table':
        manager.create_table(args.table, args.schema, args.sql)
    elif args.command == 'drop-table':
        manager.drop_table(args.table, args.force)
    elif args.command == 'query':
        manager.query_data(args.sql, limit=args.limit)
    elif args.command == 'insert':
        manager.insert_data(args.table, args.file)
    elif args.command == 'delete':
        manager.delete_data(args.table, args.where, args.force)
    elif args.command == 'stats':
        manager.get_database_stats()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
