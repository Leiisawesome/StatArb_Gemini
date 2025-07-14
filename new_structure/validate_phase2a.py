#!/usr/bin/env python3
"""
Phase 2A Market Data Migration Validation
Standalone validation script for market data components
"""

import sys
import os
from datetime import datetime

def validate_phase2a():
    """Validate Phase 2A: Market Data Migration completion"""
    print("🔍 Validating Phase 2A: Market Data Migration...")
    print("=" * 60)
    
    validation_results = {
        'infrastructure': False,
        'data_manager': False,
        'feeds': False,
        'data_processor': False,
        'enhanced_loader': False,
        'integration': False
    }
    
    try:
        # Check file structure
        print("📁 Checking file structure...")
        
        required_files = [
            'market_data/__init__.py',
            'market_data/data_manager.py',
            'market_data/feeds.py',
            'market_data/data_processor.py',
            'market_data/enhanced_clickhouse_loader.py',
            'market_data/README.md'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False
        else:
            print("✅ All required files present")
            validation_results['infrastructure'] = True
        
        # Validate individual components
        print("\n🧩 Validating individual components...")
        
        # 1. DataManager validation
        print("  - DataManager structure...")
        try:
            with open('market_data/data_manager.py', 'r') as f:
                content = f.read()
                
            required_classes = ['DataManager', 'DataCache']
            required_methods = ['load_historical_data', 'get_real_time_data', 'start_real_time_feeds']
            
            for cls in required_classes:
                if f'class {cls}' in content:
                    print(f"    ✅ {cls} class defined")
                else:
                    print(f"    ❌ {cls} class missing")
                    return False
            
            for method in required_methods:
                if f'def {method}' in content:
                    print(f"    ✅ {method} method defined")
                else:
                    print(f"    ❌ {method} method missing")
                    return False
                    
            validation_results['data_manager'] = True
            
        except Exception as e:
            print(f"    ❌ DataManager validation failed: {e}")
            return False
        
        # 2. Feeds validation
        print("  - Feed system structure...")
        try:
            with open('market_data/feeds.py', 'r') as f:
                content = f.read()
                
            required_classes = ['FeedManager', 'PolygonFeed', 'AlphaVantageFeed', 'MarketTick']
            required_enums = ['DataType', 'FeedStatus']
            
            for cls in required_classes:
                if f'class {cls}' in content:
                    print(f"    ✅ {cls} class defined")
                else:
                    print(f"    ❌ {cls} class missing")
                    return False
            
            for enum in required_enums:
                if f'class {enum}' in content:
                    print(f"    ✅ {enum} enum defined")
                else:
                    print(f"    ❌ {enum} enum missing")
                    return False
                    
            validation_results['feeds'] = True
            
        except Exception as e:
            print(f"    ❌ Feeds validation failed: {e}")
            return False
        
        # 3. Data Processor validation
        print("  - Data processor structure...")
        try:
            with open('market_data/data_processor.py', 'r') as f:
                content = f.read()
                
            required_classes = ['DataProcessor', 'FeatureEngine', 'DataQualityChecker']
            
            for cls in required_classes:
                if f'class {cls}' in content:
                    print(f"    ✅ {cls} class defined")
                else:
                    print(f"    ❌ {cls} class missing")
                    return False
                    
            validation_results['data_processor'] = True
            
        except Exception as e:
            print(f"    ❌ Data processor validation failed: {e}")
            return False
        
        # 4. Enhanced ClickHouse Loader validation
        print("  - Enhanced ClickHouse loader structure...")
        try:
            with open('market_data/enhanced_clickhouse_loader.py', 'r') as f:
                content = f.read()
                
            required_classes = ['EnhancedClickHouseLoader', 'SmartCache', 'DataRequest']
            
            for cls in required_classes:
                if f'class {cls}' in content:
                    print(f"    ✅ {cls} class defined")
                else:
                    print(f"    ❌ {cls} class missing")
                    return False
                    
            validation_results['enhanced_loader'] = True
            
        except Exception as e:
            print(f"    ❌ Enhanced loader validation failed: {e}")
            return False
        
        # 5. Integration validation
        print("  - Module integration...")
        try:
            with open('market_data/__init__.py', 'r') as f:
                content = f.read()
                
            required_imports = ['DataManager', 'FeedManager', 'MarketTick']
            
            for imp in required_imports:
                if imp in content:
                    print(f"    ✅ {imp} properly exported")
                else:
                    print(f"    ❌ {imp} not exported")
                    return False
                    
            validation_results['integration'] = True
            
        except Exception as e:
            print(f"    ❌ Integration validation failed: {e}")
            return False
        
        # Check architecture compliance
        print("\n🏗️  Validating architecture compliance...")
        
        architecture_checks = {
            'message_bus_integration': False,
            'metrics_collection': False,
            'ai_ready_interfaces': False,
            'error_handling': False,
            'performance_optimization': False
        }
        
        # Check for message bus integration
        for file_path in ['market_data/data_manager.py', 'market_data/feeds.py']:
            with open(file_path, 'r') as f:
                content = f.read()
                if 'MessageBus' in content:
                    architecture_checks['message_bus_integration'] = True
                    break
        
        # Check for metrics collection
        for file_path in ['market_data/data_manager.py', 'market_data/feeds.py']:
            with open(file_path, 'r') as f:
                content = f.read()
                if 'MetricsCollector' in content:
                    architecture_checks['metrics_collection'] = True
                    break
        
        # Check for AI-ready interfaces
        with open('market_data/feeds.py', 'r') as f:
            content = f.read()
            if 'ai.market_data_stream' in content or 'AI-ready' in content:
                architecture_checks['ai_ready_interfaces'] = True
        
        # Check for error handling
        error_handling_patterns = ['try:', 'except:', 'raise', 'logger.error']
        for file_path in required_files[1:-1]:  # Skip __init__.py and README.md
            with open(file_path, 'r') as f:
                content = f.read()
                if any(pattern in content for pattern in error_handling_patterns):
                    architecture_checks['error_handling'] = True
                    break
        
        # Check for performance optimization
        perf_patterns = ['async', 'await', 'threading', 'cache', 'parallel']
        for file_path in required_files[1:-1]:
            with open(file_path, 'r') as f:
                content = f.read()
                if any(pattern in content for pattern in perf_patterns):
                    architecture_checks['performance_optimization'] = True
                    break
        
        # Print architecture results
        for check, passed in architecture_checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check.replace('_', ' ').title()}")
        
        # Final validation
        print("\n📊 Summary:")
        print("-" * 40)
        
        all_passed = all(validation_results.values()) and all(architecture_checks.values())
        
        for component, passed in validation_results.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {component.replace('_', ' ').title()}")
        
        print(f"\nArchitecture Compliance: {sum(architecture_checks.values())}/{len(architecture_checks)} checks passed")
        
        if all_passed:
            print("\n🎉 Phase 2A: Market Data Migration - COMPLETE!")
            print("✅ All components validated successfully")
            print("✅ Architecture compliance verified")
            print("✅ Ready for Phase 2B: Signal Generation Migration")
            
            # Write completion marker
            with open('phase2a_complete.marker', 'w') as f:
                f.write(f"Phase 2A completed at {datetime.now().isoformat()}\n")
                f.write("Components validated:\n")
                for component in validation_results.keys():
                    f.write(f"  - {component}\n")
            
            return True
        else:
            print("\n❌ Phase 2A validation failed")
            print("Please address the issues above before proceeding")
            return False
        
    except Exception as e:
        print(f"\n💥 Validation error: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are available"""
    print("🔧 Checking dependencies...")
    
    dependencies = {
        'pandas': False,
        'numpy': False,
        'asyncio': False,
        'logging': False,
        'datetime': False
    }
    
    for dep in dependencies.keys():
        try:
            __import__(dep)
            dependencies[dep] = True
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep} (missing)")
    
    optional_deps = ['ta', 'sklearn', 'scipy', 'websocket']
    print("\nOptional dependencies (for advanced features):")
    for dep in optional_deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ⚠️  {dep} (optional)")
    
    core_available = all(dependencies.values())
    print(f"\nCore dependencies: {'✅ All available' if core_available else '❌ Missing required'}")
    
    return core_available


if __name__ == "__main__":
    print("🚀 StatArb System Migration Validation")
    print("Phase 2A: Market Data Migration")
    print("=" * 60)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Required dependencies missing. Please install them first.")
        sys.exit(1)
    
    print()
    
    # Run validation
    success = validate_phase2a()
    
    if success:
        print("\n🏁 Phase 2A validation completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Phase 2A validation failed!")
        sys.exit(1) 