#!/usr/bin/env python3
"""
Deep Core Structure Analysis
============================

Comprehensive analysis tool for identifying:
- Duplicate functionality across modules
- Unused/obsolete code patterns
- Inconsistent naming conventions
- Import dependency issues
- Dead code and redundant implementations
- Architecture violations and coupling issues
"""

import os
import ast
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DeepCodeAnalyzer:
    def __init__(self, base_path: str = "core_structure"):
        self.base_path = Path(base_path)
        self.files = []
        self.classes = defaultdict(list)  # class_name -> [(file, line_no)]
        self.functions = defaultdict(list)  # func_name -> [(file, line_no)]
        self.imports = defaultdict(set)  # file -> set of imports
        self.exports = defaultdict(set)  # file -> set of exports
        self.file_stats = {}  # file -> {lines, classes, functions, imports}
        self.dependencies = defaultdict(set)  # file -> set of files it depends on
        self.dead_code_candidates = []
        self.naming_issues = []
        self.architectural_issues = []
        
    def analyze(self):
        """Run comprehensive analysis"""
        logger.info("🔍 Starting Deep Core Structure Analysis")
        logger.info("=" * 60)
        
        # Phase 1: Collect all Python files
        self._collect_files()
        
        # Phase 2: Parse AST and extract metadata
        self._parse_files()
        
        # Phase 3: Analyze duplicates and patterns
        self._analyze_duplicates()
        
        # Phase 4: Find dead code
        self._find_dead_code()
        
        # Phase 5: Check naming conventions
        self._check_naming_conventions()
        
        # Phase 6: Analyze architecture
        self._analyze_architecture()
        
        # Phase 7: Generate report
        self._generate_report()
    
    def _collect_files(self):
        """Collect all Python files"""
        for root, dirs, files in os.walk(self.base_path):
            # Skip __pycache__ and other non-essential directories
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__')]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('.'):
                    file_path = Path(root) / file
                    self.files.append(file_path)
        
        logger.info(f"📁 Found {len(self.files)} Python files")
    
    def _parse_files(self):
        """Parse each file and extract metadata"""
        for file_path in self.files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST
                tree = ast.parse(content)
                
                # Initialize stats
                stats = {
                    'lines': len(content.splitlines()),
                    'classes': [],
                    'functions': [],
                    'imports': set(),
                    'has_main': False,
                    'docstring': ast.get_docstring(tree) is not None
                }
                
                # Extract information
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        self.classes[class_name].append((str(file_path), node.lineno))
                        stats['classes'].append(class_name)
                    
                    elif isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        self.functions[func_name].append((str(file_path), node.lineno))
                        stats['functions'].append(func_name)
                        
                        if func_name == 'main':
                            stats['has_main'] = True
                    
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                stats['imports'].add(alias.name)
                        else:  # ImportFrom
                            module = node.module or ''
                            for alias in node.names:
                                stats['imports'].add(f"{module}.{alias.name}")
                
                self.file_stats[str(file_path)] = stats
                
            except Exception as e:
                logger.warning(f"⚠️ Could not parse {file_path}: {e}")
    
    def _analyze_duplicates(self):
        """Find duplicate classes and functions"""
        logger.info("\n🔍 Analyzing Duplicates...")
        
        # Find duplicate classes
        duplicate_classes = {name: files for name, files in self.classes.items() if len(files) > 1}
        
        # Find duplicate functions (excluding common ones like __init__)
        common_functions = {'__init__', '__str__', '__repr__', 'main', 'run', 'setup', 'cleanup'}
        duplicate_functions = {
            name: files for name, files in self.functions.items() 
            if len(files) > 1 and name not in common_functions
        }
        
        self.duplicate_classes = duplicate_classes
        self.duplicate_functions = duplicate_functions
        
        logger.info(f"📊 Found {len(duplicate_classes)} duplicate class names")
        logger.info(f"📊 Found {len(duplicate_functions)} duplicate function names")
    
    def _find_dead_code(self):
        """Identify potentially dead code"""
        logger.info("\n🔍 Finding Dead Code...")
        
        # Files that are never imported
        imported_modules = set()
        for file_path, stats in self.file_stats.items():
            for imp in stats['imports']:
                # Extract module path from import
                parts = imp.split('.')
                if parts[0] in ['core_structure', '..', '.']:
                    imported_modules.add(imp)
        
        # Check for files that might be unused
        for file_path in self.files:
            rel_path = str(file_path.relative_to(self.base_path))
            module_path = rel_path.replace('/', '.').replace('.py', '')
            
            stats = self.file_stats[str(file_path)]
            
            # Criteria for potentially dead code:
            is_potentially_dead = (
                not stats['has_main'] and  # No main function
                len(stats['classes']) == 0 and  # No classes
                len(stats['functions']) < 3 and  # Few functions
                not any(module_path in imp for imp in imported_modules) and  # Not imported
                '__init__.py' not in str(file_path)  # Not an init file
            )
            
            if is_potentially_dead:
                self.dead_code_candidates.append(file_path)
    
    def _check_naming_conventions(self):
        """Check for naming convention issues"""
        logger.info("\n🔍 Checking Naming Conventions...")
        
        for file_path in self.files:
            stats = self.file_stats[str(file_path)]
            
            # Check for inconsistent naming
            for class_name in stats['classes']:
                if not class_name[0].isupper():
                    self.naming_issues.append(f"Class {class_name} in {file_path} should be PascalCase")
                
                if '_' in class_name and not class_name.isupper():
                    self.naming_issues.append(f"Class {class_name} in {file_path} mixes snake_case with PascalCase")
            
            for func_name in stats['functions']:
                if func_name[0].isupper() and not func_name.startswith('__'):
                    self.naming_issues.append(f"Function {func_name} in {file_path} should be snake_case")
    
    def _analyze_architecture(self):
        """Analyze architectural issues"""
        logger.info("\n🔍 Analyzing Architecture...")
        
        # Check for circular dependencies
        for file_path, stats in self.file_stats.items():
            for imp in stats['imports']:
                if 'core_structure' in imp:
                    # This is an internal import
                    target = imp.replace('core_structure.', '').replace('..', '').replace('.', '')
                    if target and target in str(file_path):
                        self.architectural_issues.append(f"Potential circular import in {file_path}: {imp}")
        
        # Check for files with too many responsibilities
        for file_path, stats in self.file_stats.items():
            if len(stats['classes']) > 5:
                self.architectural_issues.append(f"High class count in {file_path}: {len(stats['classes'])} classes")
            
            if stats['lines'] > 1000:
                self.architectural_issues.append(f"Large file {file_path}: {stats['lines']} lines")
    
    def _generate_report(self):
        """Generate comprehensive analysis report"""
        logger.info("\n📋 Generating Deep Analysis Report...")
        
        total_lines = sum(stats['lines'] for stats in self.file_stats.values())
        total_classes = sum(len(stats['classes']) for stats in self.file_stats.values())
        total_functions = sum(len(stats['functions']) for stats in self.file_stats.values())
        
        print("\n" + "="*80)
        print("🔍 DEEP CORE STRUCTURE ANALYSIS REPORT")
        print("="*80)
        
        print(f"\n📊 CODEBASE OVERVIEW:")
        print(f"  • Total Files: {len(self.files)}")
        print(f"  • Total Lines: {total_lines:,}")
        print(f"  • Total Classes: {total_classes}")
        print(f"  • Total Functions: {total_functions}")
        print(f"  • Average File Size: {total_lines // len(self.files)} lines")
        
        print(f"\n🔄 DUPLICATE ANALYSIS:")
        print(f"  • Duplicate Classes: {len(self.duplicate_classes)}")
        for name, locations in list(self.duplicate_classes.items())[:10]:  # Show top 10
            print(f"    - {name}: {len(locations)} implementations")
            for file_path, line_no in locations:
                print(f"      → {file_path}:{line_no}")
        
        print(f"  • Duplicate Functions: {len(self.duplicate_functions)}")
        for name, locations in list(self.duplicate_functions.items())[:5]:  # Show top 5
            print(f"    - {name}: {len(locations)} implementations")
        
        print(f"\n💀 DEAD CODE CANDIDATES:")
        print(f"  • Potentially Unused Files: {len(self.dead_code_candidates)}")
        for file_path in self.dead_code_candidates[:10]:  # Show first 10
            stats = self.file_stats[str(file_path)]
            print(f"    - {file_path} ({stats['lines']} lines, {len(stats['functions'])} functions)")
        
        print(f"\n📝 NAMING ISSUES:")
        print(f"  • Convention Violations: {len(self.naming_issues)}")
        for issue in self.naming_issues[:10]:  # Show first 10
            print(f"    - {issue}")
        
        print(f"\n🏗️ ARCHITECTURAL ISSUES:")
        print(f"  • Architecture Violations: {len(self.architectural_issues)}")
        for issue in self.architectural_issues[:10]:  # Show first 10
            print(f"    - {issue}")
        
        # File size distribution
        size_buckets = defaultdict(int)
        for stats in self.file_stats.values():
            lines = stats['lines']
            if lines < 100:
                size_buckets['<100'] += 1
            elif lines < 300:
                size_buckets['100-300'] += 1
            elif lines < 500:
                size_buckets['300-500'] += 1
            elif lines < 1000:
                size_buckets['500-1000'] += 1
            else:
                size_buckets['>1000'] += 1
        
        print(f"\n📏 FILE SIZE DISTRIBUTION:")
        for bucket, count in size_buckets.items():
            print(f"  • {bucket} lines: {count} files")
        
        # Largest files
        largest_files = sorted(
            [(path, stats['lines']) for path, stats in self.file_stats.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        print(f"\n📈 LARGEST FILES:")
        for file_path, lines in largest_files:
            print(f"  • {file_path}: {lines} lines")
        
        # Files with most classes
        class_heavy_files = sorted(
            [(path, len(stats['classes'])) for path, stats in self.file_stats.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        print(f"\n🏛️ CLASS-HEAVY FILES:")
        for file_path, class_count in class_heavy_files:
            if class_count > 0:
                print(f"  • {file_path}: {class_count} classes")
        
        print("\n" + "="*80)
        print("🎯 CLEANUP RECOMMENDATIONS:")
        print("="*80)
        
        print("\n1. 🔄 IMMEDIATE DUPLICATES TO RESOLVE:")
        critical_duplicates = {k: v for k, v in self.duplicate_classes.items() if len(v) > 2}
        for name, locations in list(critical_duplicates.items())[:5]:
            print(f"   • {name}: {len(locations)} implementations - CONSOLIDATE")
        
        print("\n2. 💀 FILES TO CONSIDER REMOVING:")
        for file_path in self.dead_code_candidates[:5]:
            print(f"   • {file_path} - appears unused")
        
        print("\n3. 📏 FILES TO SPLIT:")
        for file_path, lines in largest_files[:3]:
            if lines > 800:
                print(f"   • {file_path} ({lines} lines) - consider splitting")
        
        print("\n4. 🏗️ ARCHITECTURE IMPROVEMENTS:")
        if self.architectural_issues:
            print(f"   • Fix {len(self.architectural_issues)} architectural violations")
            print(f"   • Address circular imports and large files")
        
        print("\n✅ Analysis complete! Review recommendations above.")

def main():
    analyzer = DeepCodeAnalyzer()
    analyzer.analyze()

if __name__ == "__main__":
    main()
