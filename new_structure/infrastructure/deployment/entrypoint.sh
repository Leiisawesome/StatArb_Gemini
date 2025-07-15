#!/bin/bash
set -e

echo "Starting StatArb Gemini Trading System..."

# Wait for dependencies to be ready
echo "Waiting for database connections..."

# Wait for ClickHouse
until curl -f "${CLICKHOUSE_HOST:-clickhouse}:8123" >/dev/null 2>&1; do
    echo "Waiting for ClickHouse..."
    sleep 2
done

# Wait for Redis
until redis-cli -h "${REDIS_HOST:-redis}" ping >/dev/null 2>&1; do
    echo "Waiting for Redis..."
    sleep 2
done

# Wait for PostgreSQL
until pg_isready -h "${POSTGRES_HOST:-postgres}" -U trader >/dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

echo "All dependencies are ready!"

# Run database migrations if needed
echo "Running database initialization..."
python -c "
from infrastructure.database.database_manager import DatabaseManager
import asyncio

async def init_db():
    db_manager = DatabaseManager()
    await db_manager.initialize()
    print('Database initialization complete')

asyncio.run(init_db())
"

# Start the main application
echo "Starting main application..."
exec "$@"
