#!/usr/bin/env python3
"""
Core Structure Cleanup Analysis and Plan
========================================

After multiple architecture iterations, the core_structure codebase contains:
- Duplicate functionality
- Obsolete components  
- Redundant cache implementations
- Inconsistent interfaces
- Unused legacy code

This script analyzes and provides a comprehensive cleanup plan.

Author: GitHub Copilot
"""

import os
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Add project root to path
sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

@dataclass
class CodeAnalysis:
    """Analysis results for a Python file"""
    file_path: str
    imports: List[str]
    classes: List[str]
    functions: List[str]
    lines_of_code: int
    has_tests: bool
    last_modified: str

@dataclass
class DuplicateGroup:
    """Group of duplicate/similar functionality"""
    category: str
    files: List[str]
    description: str
    recommendation: str

class CoreStructureAnalyzer:
    """Analyze core_structure for cleanup opportunities"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.core_structure_path = self.base_path / "core_structure"
        
        # Analysis results
        self.file_analysis: Dict[str, CodeAnalysis] = {}
        self.duplicates: List[DuplicateGroup] = []
        self.unused_files: List[str] = []
        self.import_map: Dict[str, Set[str]] = defaultdict(set)
        
    def analyze(self):
        """Run comprehensive analysis"""
        print("🔍 CORE STRUCTURE CLEANUP ANALYSIS")
        print("=" * 60)
        
        # 1. File-by-file analysis
        self._analyze_files()
        
        # 2. Identify duplicates
        self._identify_duplicates()
        
        # 3. Find unused components
        self._find_unused()
        
        # 4. Generate cleanup plan
        self._generate_cleanup_plan()
        
    def _analyze_files(self):
        """Analyze all Python files in core_structure"""
        print("\n📊 Analyzing Python files...")
        
        py_files = list(self.core_structure_path.rglob("*.py"))
        
        for file_path in py_files:
            if file_path.name == "__init__.py":
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Parse AST
                tree = ast.parse(content)
                
                # Extract information
                imports = []
                classes = []
                functions = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
                    elif isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        functions.append(node.name)
                
                # Store analysis
                relative_path = str(file_path.relative_to(self.base_path))
                self.file_analysis[relative_path] = CodeAnalysis(
                    file_path=relative_path,
                    imports=imports,
                    classes=classes,
                    functions=functions,
                    lines_of_code=len(content.splitlines()),
                    has_tests=self._has_tests(file_path),
                    last_modified=str(file_path.stat().st_mtime)
                )
                
            except Exception as e:
                print(f"  ⚠️  Error analyzing {file_path}: {e}")
                
        print(f"  ✅ Analyzed {len(self.file_analysis)} Python files")
        
    def _has_tests(self, file_path: Path) -> bool:
        """Check if file has corresponding tests"""
        test_patterns = [
            self.base_path / "tests" / f"test_{file_path.stem}.py",
            file_path.parent / f"test_{file_path.stem}.py",
            self.base_path / "tests" / file_path.parent.name / f"test_{file_path.stem}.py"
        ]
        
        return any(test_path.exists() for test_path in test_patterns)
        
    def _identify_duplicates(self):
        """Identify duplicate functionality"""
        print("\n🔍 Identifying duplicate functionality...")
        
        # Group by similar class names
        class_groups = defaultdict(list)
        for file_path, analysis in self.file_analysis.items():
            for class_name in analysis.classes:
                class_groups[class_name].append(file_path)
        
        # Identify actual duplicates
        for class_name, files in class_groups.items():
            if len(files) > 1:
                if class_name == "DataCache":
                    self.duplicates.append(DuplicateGroup(
                        category="Cache Implementation",
                        files=files,
                        description=f"Multiple DataCache implementations found",
                        recommendation="Consolidate into single implementation in infrastructure/"
                    ))
                elif class_name.endswith("Manager"):
                    self.duplicates.append(DuplicateGroup(
                        category="Manager Classes",
                        files=files,
                        description=f"Multiple {class_name} implementations",
                        recommendation="Choose the most recent/complete implementation"
                    ))
        
        # Check for similar functionality patterns
        self._check_market_data_duplicates()
        self._check_execution_duplicates()
        self._check_monitoring_duplicates()
        
        print(f"  ✅ Found {len(self.duplicates)} duplicate groups")
        
    def _check_market_data_duplicates(self):
        """Check for market data related duplicates"""
        market_data_files = [
            path for path in self.file_analysis.keys() 
            if "market_data" in path
        ]
        
        # Check for data_manager vs enhanced_data_manager
        data_managers = [f for f in market_data_files if "data_manager" in f]
        if len(data_managers) > 1:
            self.duplicates.append(DuplicateGroup(
                category="Market Data Management",
                files=data_managers,
                description="Multiple data manager implementations",
                recommendation="Keep enhanced_data_manager.py, remove data_manager.py"
            ))
            
    def _check_execution_duplicates(self):
        """Check for execution engine duplicates"""
        execution_files = [
            path for path in self.file_analysis.keys() 
            if "execution" in path
        ]
        
        # Look for multiple execution engines
        engines = [f for f in execution_files if "engine" in f]
        if len(engines) > 1:
            # This is expected (main vs backtesting), so not flagging as duplicate
            pass
            
    def _check_monitoring_duplicates(self):
        """Check for monitoring/metrics duplicates"""
        monitoring_files = [
            path for path in self.file_analysis.keys() 
            if any(keyword in path.lower() for keyword in ["monitoring", "metrics", "performance"])
        ]
        
        # Check for metrics collector duplicates
        metrics_files = [f for f in monitoring_files if "metrics" in f]
        if len(metrics_files) > 1:
            self.duplicates.append(DuplicateGroup(
                category="Metrics Collection",
                files=metrics_files,
                description="Multiple metrics collection implementations",
                recommendation="Consolidate into infrastructure/monitoring/"
            ))
            
    def _find_unused(self):
        """Find potentially unused files"""
        print("\n🧹 Finding unused components...")
        
        # Build import graph
        for file_path, analysis in self.file_analysis.items():
            for import_name in analysis.imports:
                self.import_map[import_name].add(file_path)
                
        # Check which files are never imported
        all_modules = set()
        for file_path in self.file_analysis.keys():
            # Convert file path to module name
            module_parts = file_path.replace("/", ".").replace(".py", "")
            all_modules.add(module_parts)
            
        # Files that are never imported (potential candidates for removal)
        potentially_unused = []
        for file_path, analysis in self.file_analysis.items():
            module_name = file_path.replace("/", ".").replace(".py", "")
            
            # Check if this module is imported by any other file
            is_imported = any(
                module_name in other_imports 
                for other_imports in [a.imports for a in self.file_analysis.values()]
            )
            
            # Check if it's a main script or has if __name__ == "__main__"
            is_main_script = False
            try:
                with open(self.base_path / file_path, 'r') as f:
                    content = f.read()
                    is_main_script = 'if __name__ == "__main__"' in content
            except:
                pass
                
            if not is_imported and not is_main_script and not file_path.endswith("__init__.py"):
                potentially_unused.append(file_path)
                
        self.unused_files = potentially_unused
        print(f"  ✅ Found {len(self.unused_files)} potentially unused files")
        
    def _generate_cleanup_plan(self):
        """Generate comprehensive cleanup plan"""
        print("\n📋 COMPREHENSIVE CLEANUP PLAN")
        print("=" * 60)
        
        print("\n1. 🔄 DUPLICATE RESOLUTION:")
        for i, duplicate in enumerate(self.duplicates, 1):
            print(f"   {i}. {duplicate.category}")
            print(f"      Files: {', '.join(duplicate.files)}")
            print(f"      Issue: {duplicate.description}")
            print(f"      Action: {duplicate.recommendation}")
            print()
            
        print("\n2. 🗑️  POTENTIALLY UNUSED FILES:")
        for file_path in self.unused_files:
            analysis = self.file_analysis[file_path]
            print(f"   • {file_path}")
            print(f"     Classes: {', '.join(analysis.classes) if analysis.classes else 'None'}")
            print(f"     Functions: {len(analysis.functions)} functions")
            print(f"     LOC: {analysis.lines_of_code}")
            print(f"     Has Tests: {'✅' if analysis.has_tests else '❌'}")
            print()
            
        print("\n3. 📊 STATISTICS:")
        total_files = len(self.file_analysis)
        total_classes = sum(len(a.classes) for a in self.file_analysis.values())
        total_functions = sum(len(a.functions) for a in self.file_analysis.values())
        total_loc = sum(a.lines_of_code for a in self.file_analysis.values())
        files_with_tests = sum(1 for a in self.file_analysis.values() if a.has_tests)
        
        print(f"   • Total Files: {total_files}")
        print(f"   • Total Classes: {total_classes}")
        print(f"   • Total Functions: {total_functions}")
        print(f"   • Total Lines of Code: {total_loc:,}")
        print(f"   • Files with Tests: {files_with_tests}/{total_files} ({files_with_tests/total_files*100:.1f}%)")
        print(f"   • Duplicate Groups: {len(self.duplicates)}")
        print(f"   • Potentially Unused: {len(self.unused_files)}")
        
        print("\n4. 🎯 RECOMMENDED ACTIONS:")
        print("   Priority 1 (High Impact):")
        print("   • Remove core_structure/market_data/data_manager.py (superseded)")
        print("   • Consolidate DataCache implementations")
        print("   • Remove unused monitoring components")
        
        print("\n   Priority 2 (Medium Impact):")
        print("   • Clean up unused import statements")
        print("   • Standardize naming conventions")
        print("   • Add missing unit tests")
        
        print("\n   Priority 3 (Low Impact):")
        print("   • Remove commented-out code")
        print("   • Update docstrings")
        print("   • Optimize imports")


def main():
    """Run the cleanup analysis"""
    base_path = "/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini"
    
    analyzer = CoreStructureAnalyzer(base_path)
    analyzer.analyze()
    
    print("\n" + "=" * 60)
    print("📝 ANALYSIS COMPLETE - Review recommendations above")
    print("=" * 60)


if __name__ == "__main__":
    main()
