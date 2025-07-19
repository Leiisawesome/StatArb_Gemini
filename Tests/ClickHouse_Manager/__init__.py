"""
ClickHouse Manager Package
=========================

Comprehensive database management toolkit for StatArb_Gemini's ClickHouse operations.

This package provides:
- Database connection management
- Table schema management
- Data operations (CRUD)
- Performance monitoring
- Interactive CLI interface

Components:
- clickhouse_manager.py: Main management script
- configs/: Configuration files
- schemas/: SQL schema definitions

Usage:
    from Tests.ClickHouse_Manager.clickhouse_manager import ClickHouseManager
    
    manager = ClickHouseManager('configs/clickhouse_config.json')
    manager.list_tables()
"""

__version__ = "1.0.0"
__author__ = "StatArb_Gemini Team"

# Package metadata
PACKAGE_INFO = {
    "name": "ClickHouse Manager",
    "version": __version__,
    "description": "Database management toolkit for ClickHouse operations",
    "features": [
        "Table management",
        "Data operations", 
        "Schema management",
        "Performance monitoring",
        "Interactive CLI"
    ]
}
