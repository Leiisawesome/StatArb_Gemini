#!/usr/bin/env python3
"""
Streamlined Functional Test Runner

This is the single entry point for all functional testing in the StatArb_Gemini core engine.
Provides comprehensive testing across all 6 layers with real data integration.
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import test modules
from tests.functional.comprehensive_layer_tests import run_comprehensive_tests, ComprehensiveTestResult
from tests.functional.layer1_system_orchestration_tests import run_layer1_tests
from tests.functional.layer2_governance_tests import run_layer2_tests
from tests.functional.layer3_data_management_tests import run_layer3_tests
from tests.functional.layer4_core_processing_tests import run_layer4_tests
from tests.functional.layer5_analytics_strategy_tests import run_layer5_tests
from tests.functional.layer6_trading_execution_tests import run_layer6_tests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_single_layer_test(layer: int) -> dict:
    """Run tests for a specific layer"""
    
    layer_runners = {
        1: run_layer1_tests,
        2: run_layer2_tests, 
        3: run_layer3_tests,
        4: run_layer4_tests,
        5: run_layer5_tests,
        6: run_layer6_tests
    }
    
    if layer not in layer_runners:
        raise ValueError(f"Invalid layer: {layer}. Must be 1-6.")
    
    logger.info(f"🚀 Running Layer {layer} Tests...")
    result = await layer_runners[layer]()
    
    return {
        'layer': layer,
        'score': result.overall_score,
        'success': getattr(result, 'success', result.overall_score >= 70.0),
        'details': result
    }

async def run_multiple_layers(layers: List[int]) -> dict:
    """Run tests for multiple specific layers"""
    
    results = {}
    for layer in layers:
        try:
            results[f'layer{layer}'] = await run_single_layer_test(layer)
        except Exception as e:
            logger.error(f"Layer {layer} test failed: {e}")
            results[f'layer{layer}'] = {
                'layer': layer,
                'score': 0.0,
                'success': False,
                'error': str(e)
            }
    
    return results

async def run_all_layers() -> ComprehensiveTestResult:
    """Run comprehensive tests across all 6 layers"""
    
    logger.info("🚀 Running Comprehensive Layer-by-Layer Tests...")
    return await run_comprehensive_tests()

def print_test_summary(results: dict):
    """Print a summary of test results"""
    
    print("\n" + "="*60)
    print("📊 FUNCTIONAL TEST RESULTS SUMMARY")
    print("="*60)
    
    if isinstance(results, ComprehensiveTestResult):
        # Comprehensive test results
        print(f"🎯 Overall Score: {results.overall_score:.1f}%")
        print(f"✅ Success: {results.success}")
        print(f"⏱️  Duration: {results.duration_seconds:.1f}s")
        
        print(f"\n📋 Layer Scores:")
        print(f"  Layer 1 (System Orchestration): {results.layer1_score:.1f}%")
        print(f"  Layer 2 (Governance): {results.layer2_score:.1f}%")
        print(f"  Layer 3 (Data Management): {results.layer3_score:.1f}%")
        print(f"  Layer 4 (Core Processing): {results.layer4_score:.1f}%")
        print(f"  Layer 5 (Analytics & Strategy): {results.layer5_score:.1f}%")
        print(f"  Layer 6 (Trading & Execution): {results.layer6_score:.1f}%")
        
        if hasattr(results, 'end_to_end_score') and results.end_to_end_score:
            print(f"  End-to-End Integration: {results.end_to_end_score:.1f}%")
        if hasattr(results, 'production_readiness_score') and results.production_readiness_score:
            print(f"  Production Readiness: {results.production_readiness_score:.1f}%")
            
    else:
        # Individual layer results
        for layer_key, layer_result in results.items():
            if isinstance(layer_result, dict) and 'layer' in layer_result:
                layer_num = layer_result['layer']
                score = layer_result.get('score', 0.0)
                success = layer_result.get('success', False)
                print(f"  Layer {layer_num}: {score:.1f}% {'✅' if success else '❌'}")
    
    print("="*60)

async def main():
    """Main function to run functional tests"""
    
    parser = argparse.ArgumentParser(description="StatArb_Gemini Functional Test Runner")
    parser.add_argument('--layers', nargs='+', type=int, choices=range(1, 7), 
                       help='Specific layers to test (1-6)')
    parser.add_argument('--all', action='store_true', 
                       help='Run all 6 layers (comprehensive test)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick test (layers 1-4 only)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🚀 StatArb_Gemini Functional Test Runner")
    print("=" * 50)
    
    start_time = datetime.now()
    
    try:
        if args.all or (not args.layers and not args.quick):
            # Run comprehensive tests (all layers)
            results = await run_all_layers()
            
        elif args.quick:
            # Run quick test (layers 1-4)
            results = await run_multiple_layers([1, 2, 3, 4])
            
        elif args.layers:
            # Run specific layers
            results = await run_multiple_layers(args.layers)
            
        else:
            # Default: run all layers
            results = await run_all_layers()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_test_summary(results)
        
        # Save report if comprehensive test
        if isinstance(results, ComprehensiveTestResult):
            report_path = Path("reports/functional_test_report.md")
            report_path.parent.mkdir(exist_ok=True)
            
            # Generate simple report
            report_content = f"""# Functional Test Report

**Test Date:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {duration:.1f}s
**Overall Score:** {results.overall_score:.1f}%
**Success:** {results.success}

## Layer Scores
- Layer 1 (System Orchestration): {results.layer1_score:.1f}%
- Layer 2 (Governance): {results.layer2_score:.1f}%
- Layer 3 (Data Management): {results.layer3_score:.1f}%
- Layer 4 (Core Processing): {results.layer4_score:.1f}%
- Layer 5 (Analytics & Strategy): {results.layer5_score:.1f}%
- Layer 6 (Trading & Execution): {results.layer6_score:.1f}%

## Summary
{'✅ All tests passed successfully!' if results.success else '❌ Some tests failed - see details above.'}
"""
            
            report_path.write_text(report_content)
            print(f"\n📄 Test report saved to: {report_path}")
        
        # Exit with appropriate code
        if isinstance(results, ComprehensiveTestResult):
            sys.exit(0 if results.success else 1)
        else:
            all_success = all(
                layer_result.get('success', False) 
                for layer_result in results.values() 
                if isinstance(layer_result, dict)
            )
            sys.exit(0 if all_success else 1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
