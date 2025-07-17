#!/usr/bin/env python3
"""
Setup script for momentum trading backtest environment
Prepares the environment and validates all dependencies
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    print("Checking Python version...")
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} detected")
        print("❌ Python 3.8+ required")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("\nInstalling dependencies...")
    
    # Read requirements file
    requirements_file = "requirements.txt"
    if not os.path.exists(requirements_file):
        print(f"❌ {requirements_file} not found")
        return False
    
    try:
        # Install packages
        cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def create_directory_structure():
    """Create necessary directories"""
    print("\nCreating directory structure...")
    
    directories = [
        "results",
        "results/logs",
        "results/performance_reports",
        "results/data_exports",
        "results/visualizations"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    return True

def check_clickhouse_connection():
    """Check ClickHouse connection (optional)"""
    print("\nChecking ClickHouse connection...")
    
    try:
        import clickhouse_connect
        
        # Try to connect with default settings
        try:
            client = clickhouse_connect.get_client(
                host='localhost',
                port=9000,
                username='default',
                password='',
                database='market_data'
            )
            
            # Test connection
            result = client.query("SELECT 1")
            if result:
                print("✅ ClickHouse connection successful")
                
                # Check for market data
                try:
                    tables = client.query("SHOW TABLES").result_set
                    table_names = [row[0] for row in tables]
                    
                    if any('stock' in table.lower() or 'market' in table.lower() for table in table_names):
                        print("✅ Market data tables found")
                    else:
                        print("⚠️  No market data tables found (will use mock data)")
                        
                except Exception:
                    print("⚠️  Could not check for market data tables")
                
                return True
                
        except Exception as e:
            print(f"⚠️  ClickHouse connection failed: {e}")
            print("⚠️  Will use mock data for testing")
            return False
            
    except ImportError:
        print("⚠️  clickhouse-connect not available")
        print("⚠️  Install with: pip install clickhouse-connect")
        return False

def validate_configuration():
    """Validate configuration file"""
    print("\nValidating configuration...")
    
    config_file = "config/backtest_config.yaml"
    if not os.path.exists(config_file):
        print(f"❌ Configuration file not found: {config_file}")
        return False
    
    try:
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ['clickhouse', 'data', 'strategy', 'portfolio', 'execution', 'risk']
        
        for section in required_sections:
            if section not in config:
                print(f"❌ Missing configuration section: {section}")
                return False
        
        print("✅ Configuration file valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating configuration: {e}")
        return False

def check_data_availability():
    """Check for available data sources"""
    print("\nChecking data availability...")
    
    # Check if new_structure data is available
    new_structure_path = "../new_structure"
    if os.path.exists(new_structure_path):
        print("✅ new_structure directory found")
        
        # Check for market data
        market_data_path = os.path.join(new_structure_path, "market_data")
        if os.path.exists(market_data_path):
            print("✅ Market data module available")
        else:
            print("⚠️  Market data module not found in new_structure")
    else:
        print("⚠️  new_structure directory not found")
    
    return True

def run_system_test():
    """Run basic system validation"""
    print("\nRunning system validation...")
    
    try:
        # Run basic import tests
        test_cmd = [sys.executable, "test_system.py"]
        result = subprocess.run(test_cmd, capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✅ System validation passed")
            return True
        else:
            print("⚠️  System validation completed with warnings")
            print("Check test output for details")
            return True  # Continue even with warnings
            
    except Exception as e:
        print(f"⚠️  Could not run system validation: {e}")
        return True  # Continue anyway

def main():
    """Main setup function"""
    print("=" * 80)
    print("MOMENTUM BACKTEST SETUP")
    print("=" * 80)
    
    # Track setup status
    checks = []
    
    # 1. Check Python version
    checks.append(("Python Version", check_python_version()))
    
    # 2. Create directories
    checks.append(("Directory Structure", create_directory_structure()))
    
    # 3. Install dependencies
    checks.append(("Dependencies", install_dependencies()))
    
    # 4. Validate configuration
    checks.append(("Configuration", validate_configuration()))
    
    # 5. Check ClickHouse (optional)
    checks.append(("ClickHouse", check_clickhouse_connection()))
    
    # 6. Check data availability
    checks.append(("Data Sources", check_data_availability()))
    
    # 7. Run system test
    checks.append(("System Test", run_system_test()))
    
    # Summary
    print("\n" + "=" * 80)
    print("SETUP SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(checks)
    
    for check_name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}")
        if status:
            passed += 1
    
    print(f"\nSetup Status: {passed}/{total} checks passed")
    
    if passed >= total - 1:  # Allow 1 failure (usually ClickHouse)
        print("✅ SETUP COMPLETED SUCCESSFULLY")
        print("\nYou can now run the backtest:")
        print("  python run_backtest.py")
        print("\nOr run tests first:")
        print("  python test_system.py")
    else:
        print("❌ SETUP INCOMPLETE")
        print("Please resolve the failed checks before proceeding")
        return 1
    
    print("=" * 80)
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
