#!/usr/bin/env python3
"""
Simple Batch 5 Test - Quick Validation
"""

import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)
sys.path.insert(0, os.getcwd())

def test_batch5():
    """Quick validation of Batch 5 components"""
    print("🧪 Quick Batch 5 Validation...")
    
    try:
        # Test imports
        from backtesting_framework.monitoring.performance_monitor import PerformanceMonitor, PerformanceMetrics
        from backtesting_framework.monitoring.reporting_engine import ReportGenerator
        print("✅ All imports successful")
        
        # Test basic initialization
        monitor = PerformanceMonitor(initial_capital=100000)
        report_gen = ReportGenerator()
        print("✅ Component initialization successful")
        
        # Test basic functionality
        monitor.update_performance(105000, 0.05)  # 5% gain
        summary = monitor.get_performance_summary()
        print(f"✅ Performance monitoring working: {summary['total_return']:.2%} return")
        
        # Test report generation
        report = report_gen.generate_performance_report({
            'total_return': 0.05,
            'sharpe_ratio': 1.2,
            'max_drawdown': -0.02
        })
        print(f"✅ Report generation working: {report['report_id']}")
        
        print("\n🎉 Batch 5 validation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Batch 5 validation failed: {e}")
        return False

if __name__ == "__main__":
    success = test_batch5()
    sys.exit(0 if success else 1) 