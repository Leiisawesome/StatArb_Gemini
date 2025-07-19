# StatArb_Gemini Test Suite

Comprehensive test suite for the StatArb_Gemini trading system, organized by module for efficient testing and validation.

## Directory Structure

```
Tests/
├── __init__.py                    # Test package initialization
├── ClickHouse_Manager/            # ClickHouse database management toolkit
│   ├── clickhouse_manager.py     # Main management script
│   ├── quick_start.py            # Setup and initialization script
│   ├── configs/                  # Database configuration files
│   ├── schemas/                  # SQL schema definitions
│   └── sample_data/              # Sample data for testing
├── signal_generation/             # Signal generation and indicators
├── analytics/                    # Performance analytics tests
├── market_data/                  # Data processing tests
├── portfolio_management/         # Portfolio optimization tests
├── risk_management/              # Risk assessment tests
├── execution_engine/             # Order execution tests
├── strategy_engine/              # Trading strategy tests
├── ai_infrastructure/            # AI/ML component tests
├── benchmarks/                   # Performance benchmarks
└── integration_testing/          # End-to-end tests
```

## Quick Start

### Database Management
```bash
# Set up ClickHouse database and tables
cd Tests/ClickHouse_Manager
python quick_start.py

# Manage database interactively
python clickhouse_manager.py --interactive

# List all tables
python clickhouse_manager.py list-tables

# Create table from schema
python clickhouse_manager.py create-table market_data --schema schemas/market_data.sql
```

### Run All Tests
```bash
# Run complete test suite
python run_all_tests.py

# Run with coverage report
python run_all_tests.py --coverage

# Skip slow tests for quick validation
python run_all_tests.py --fast
```

### Run Module-Specific Tests
```bash
# Test signal generation module
python run_all_tests.py --module signal_generation

# Test specific module with coverage
python run_all_tests.py --module analytics --coverage

# List available modules
python run_all_tests.py --list-modules
```

### Using pytest Directly
```bash
# Run all tests with pytest
pytest Tests/ -v

# Run specific module
pytest Tests/signal_generation/ -v

# Run with coverage
pytest Tests/ --cov=core_structure --cov-report=html
```

## Test Categories

### Database Management
- **ClickHouse_Manager/**: Complete ClickHouse database management toolkit
  - Table creation, deletion, and schema management
  - Data operations (insert, query, delete) with safety features
  - Performance monitoring and database statistics
  - Interactive CLI for complex operations
  - Pre-defined schemas for trading data structures

### Unit Tests
- **signal_generation/**: Model ensemble, feature engineering, technical indicators
- **analytics/**: Performance metrics, monitoring systems, reporting
- **market_data/**: Data ingestion, processing, validation
- **portfolio_management/**: Allocation optimization, rebalancing
- **risk_management/**: Position sizing, risk metrics, constraints
- **execution_engine/**: Order routing, transaction cost optimization
- **strategy_engine/**: Trading strategies, signal processing
- **ai_infrastructure/**: ML models, agent systems, optimization

### Integration Tests  
- **integration_testing/**: End-to-end workflow validation
- Cross-module compatibility testing
- System performance under load
- Real-time data processing validation

### Performance Tests
- **benchmarks/**: System performance benchmarks
- Latency measurements
- Memory usage profiling
- Scalability testing

## Test Markers

Tests are categorized with markers for selective execution:

- `@pytest.mark.slow`: Long-running tests (skip with `-m "not slow"`)
- `@pytest.mark.integration`: Integration tests requiring external services
- `@pytest.mark.unit`: Fast unit tests
- `@pytest.mark.performance`: Performance benchmarks
- `@pytest.mark.ai`: AI/ML component tests

## Configuration

Test configuration is managed through `pytest.ini` in the root directory:

```ini
[pytest]
testpaths = Tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
```

## Coverage Reports

Coverage reports are generated in multiple formats:
- **Terminal**: Immediate feedback with missing lines
- **HTML**: Detailed interactive report in `htmlcov/`
- **XML**: CI/CD integration format

## Best Practices

### Writing Tests
1. Use descriptive test names that explain the scenario
2. Follow the Arrange-Act-Assert pattern
3. Use appropriate markers for test categorization
4. Mock external dependencies appropriately
5. Include both positive and negative test cases

### Test Organization
1. Group related tests in the same file
2. Use meaningful file names starting with `test_`
3. Place tests in the module directory they're testing
4. Include integration tests for cross-module functionality

### Continuous Integration
1. Run fast tests first for quick feedback
2. Use parallel execution for performance
3. Generate coverage reports for quality tracking
4. Fail builds on coverage regression

## Dependencies

Test dependencies are managed separately from production code:
- `pytest`: Test framework
- `pytest-cov`: Coverage reporting
- `pytest-asyncio`: Async test support
- `pytest-mock`: Enhanced mocking capabilities

## Troubleshooting

### Import Errors
- Ensure `PYTHONPATH` includes the project root
- Check that all `__init__.py` files are present
- Verify import paths are correct for the new structure

### Test Failures
- Run individual tests to isolate issues
- Check test data and mock configurations
- Ensure test environment matches requirements

### Performance Issues
- Use `--fast` flag to skip slow tests during development
- Profile test execution with `--duration=10`
- Consider parallel execution with `pytest-xdist`

## Contributing

When adding new tests:
1. Place tests in the appropriate module directory
2. Follow existing naming conventions
3. Add appropriate markers for categorization
4. Update this README if adding new test categories
5. Ensure tests pass in isolation and as part of the suite

For questions or issues with the test suite, refer to the project documentation or open an issue.
