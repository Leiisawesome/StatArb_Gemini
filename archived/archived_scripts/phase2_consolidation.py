#!/usr/bin/env python3
"""
Phase 2: Order Types Consolidation
==================================

Continue eliminating duplicate Order implementations across execution modules.
Current status: 4 remaining duplicate implementations to consolidate.
"""

import os
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def analyze_order_type_usage():
    """Analyze which files use Order types and how"""
    
    order_files = [
        "core_structure/execution_engine/order_manager.py",
        "core_structure/execution_engine/enhanced_execution_engine.py", 
        "core_structure/broker_integration/base_broker.py",
        "core_structure/risk/risk_manager.py"
    ]
    
    usage_analysis = {}
    
    for file_path in order_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Count Order-related class definitions
            order_classes = re.findall(r'class\s+(Order\w*|.*Order)\s*\(', content)
            enum_classes = re.findall(r'class\s+(Order\w*)\s*\(Enum\)', content)
            
            usage_analysis[file_path] = {
                'order_classes': order_classes,
                'enum_classes': enum_classes,
                'lines': len(content.splitlines()),
                'has_order_import': 'from' in content and 'Order' in content
            }
    
    return usage_analysis

def main():
    logger.info("🔍 Phase 2: Order Types Consolidation Analysis")
    logger.info("=" * 60)
    
    usage = analyze_order_type_usage()
    
    for file_path, info in usage.items():
        logger.info(f"\n📁 {file_path}:")
        logger.info(f"   • Order classes: {info['order_classes']}")
        logger.info(f"   • Enum classes: {info['enum_classes']}")
        logger.info(f"   • File size: {info['lines']} lines")
        logger.info(f"   • Has imports: {info['has_order_import']}")
    
    logger.info("\n🎯 CONSOLIDATION PLAN:")
    logger.info("1. Update order_manager.py to use canonical types")
    logger.info("2. Update enhanced_execution_engine.py to use canonical types")
    logger.info("3. Update base_broker.py to use canonical types")
    logger.info("4. Update risk_manager.py to use canonical types")
    logger.info("5. Remove duplicate enum/class definitions")
    logger.info("6. Test system after each change")

if __name__ == "__main__":
    main()
