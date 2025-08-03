#!/usr/bin/env python3
"""
StatArb_Gemini Codebase Cleanup Script

This script performs comprehensive cleanup of the codebase:
1. Organizes files and directories
2. Removes temporary files
3. Updates documentation
4. Validates code quality
"""

import os
import shutil
import glob
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CodebaseCleanup:
    """Comprehensive codebase cleanup utility"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.cleanup_report = {
            'timestamp': datetime.now().isoformat(),
            'files_removed': [],
            'files_moved': [],
            'directories_created': [],
            'errors': []
        }
    
    def cleanup_validation_reports(self) -> None:
        """Clean up old validation reports, keep only latest"""
        logger.info("Cleaning up validation reports...")
        
        # Find all validation report files
        report_patterns = [
            "**/*validation_report*.json",
            "**/*_validation_report_*.json"
        ]
        
        for pattern in report_patterns:
            reports = list(self.project_root.glob(pattern))
            
            # Group by base name (without timestamp)
            report_groups = {}
            for report in reports:
                base_name = report.stem.split('_2025')[0] if '_2025' in report.stem else report.stem
                if base_name not in report_groups:
                    report_groups[base_name] = []
                report_groups[base_name].append(report)
            
            # Keep only the latest report from each group
            for base_name, reports in report_groups.items():
                if len(reports) > 1:
                    # Sort by modification time, keep the latest
                    reports.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    
                    # Remove older reports
                    for old_report in reports[1:]:
                        try:
                            old_report.unlink()
                            self.cleanup_report['files_removed'].append(str(old_report))
                            logger.info(f"Removed old report: {old_report}")
                        except Exception as e:
                            self.cleanup_report['errors'].append(f"Failed to remove {old_report}: {e}")
    
    def cleanup_test_artifacts(self) -> None:
        """Remove test artifacts and temporary files"""
        logger.info("Cleaning up test artifacts...")
        
        # Files and directories to remove
        artifacts = [
            ".pytest_cache",
            "htmlcov",
            ".coverage",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".DS_Store",
            "Thumbs.db"
        ]
        
        for artifact in artifacts:
            if artifact.startswith('.'):
                # Directory
                artifact_path = self.project_root / artifact
                if artifact_path.exists():
                    try:
                        shutil.rmtree(artifact_path)
                        self.cleanup_report['files_removed'].append(str(artifact_path))
                        logger.info(f"Removed directory: {artifact_path}")
                    except Exception as e:
                        self.cleanup_report['errors'].append(f"Failed to remove {artifact_path}: {e}")
            else:
                # File pattern
                for file_path in self.project_root.glob(f"**/{artifact}"):
                    try:
                        file_path.unlink()
                        self.cleanup_report['files_removed'].append(str(file_path))
                        logger.info(f"Removed file: {file_path}")
                    except Exception as e:
                        self.cleanup_report['errors'].append(f"Failed to remove {file_path}: {e}")
    
    def organize_directories(self) -> None:
        """Organize project directories"""
        logger.info("Organizing project directories...")
        
        # Create organized directory structure
        directories = [
            "docs/architecture",
            "docs/api", 
            "docs/examples",
            "results/validation_reports",
            "results/performance",
            "results/backtests",
            "scripts",
            "configs",
            "logs"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.cleanup_report['directories_created'].append(str(dir_path))
                    logger.info(f"Created directory: {dir_path}")
                except Exception as e:
                    self.cleanup_report['errors'].append(f"Failed to create {dir_path}: {e}")
    
    def move_files_to_organized_locations(self) -> None:
        """Move files to their organized locations"""
        logger.info("Moving files to organized locations...")
        
        # Move validation reports to results/validation_reports
        validation_reports = list(self.project_root.glob("**/*validation_report*.json"))
        for report in validation_reports:
            if "results/validation_reports" not in str(report):
                try:
                    new_location = self.project_root / "results" / "validation_reports" / report.name
                    shutil.move(str(report), str(new_location))
                    self.cleanup_report['files_moved'].append({
                        'from': str(report),
                        'to': str(new_location)
                    })
                    logger.info(f"Moved: {report} -> {new_location}")
                except Exception as e:
                    self.cleanup_report['errors'].append(f"Failed to move {report}: {e}")
        
        # Move configuration files to configs directory
        config_files = list(self.project_root.glob("**/*.yaml")) + list(self.project_root.glob("**/*.yml"))
        for config in config_files:
            if "configs" not in str(config) and "backtesting_framework/configs" not in str(config):
                try:
                    new_location = self.project_root / "configs" / config.name
                    shutil.move(str(config), str(new_location))
                    self.cleanup_report['files_moved'].append({
                        'from': str(config),
                        'to': str(new_location)
                    })
                    logger.info(f"Moved: {config} -> {new_location}")
                except Exception as e:
                    self.cleanup_report['errors'].append(f"Failed to move {config}: {e}")
    
    def validate_code_quality(self) -> Dict[str, Any]:
        """Validate code quality and report issues"""
        logger.info("Validating code quality...")
        
        quality_report = {
            'python_files': 0,
            'files_with_docstrings': 0,
            'files_with_type_hints': 0,
            'files_with_imports': 0,
            'issues': []
        }
        
        # Find all Python files
        python_files = list(self.project_root.glob("**/*.py"))
        quality_report['python_files'] = len(python_files)
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for docstrings
                if '"""' in content or "'''" in content:
                    quality_report['files_with_docstrings'] += 1
                else:
                    quality_report['issues'].append(f"Missing docstring: {py_file}")
                
                # Check for type hints
                if 'from typing import' in content or 'import typing' in content:
                    quality_report['files_with_type_hints'] += 1
                else:
                    quality_report['issues'].append(f"Missing type hints: {py_file}")
                
                # Check for imports
                if 'import ' in content or 'from ' in content:
                    quality_report['files_with_imports'] += 1
                
            except Exception as e:
                quality_report['issues'].append(f"Error reading {py_file}: {e}")
        
        return quality_report
    
    def generate_cleanup_report(self) -> None:
        """Generate cleanup report"""
        logger.info("Generating cleanup report...")
        
        # Add quality validation to report
        quality_report = self.validate_code_quality()
        self.cleanup_report['quality_validation'] = quality_report
        
        # Save report
        report_path = self.project_root / "results" / "cleanup_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.cleanup_report, f, indent=2, default=str)
        
        logger.info(f"Cleanup report saved to: {report_path}")
    
    def run_full_cleanup(self) -> None:
        """Run complete cleanup process"""
        logger.info("Starting comprehensive codebase cleanup...")
        
        try:
            # Step 1: Clean up validation reports
            self.cleanup_validation_reports()
            
            # Step 2: Clean up test artifacts
            self.cleanup_test_artifacts()
            
            # Step 3: Organize directories
            self.organize_directories()
            
            # Step 4: Move files to organized locations
            self.move_files_to_organized_locations()
            
            # Step 5: Generate cleanup report
            self.generate_cleanup_report()
            
            logger.info("✅ Codebase cleanup completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            self.cleanup_report['errors'].append(f"Cleanup failed: {e}")
            raise


def main():
    """Main cleanup function"""
    # Get project root (assuming script is run from project root)
    project_root = os.getcwd()
    
    # Create cleanup instance
    cleanup = CodebaseCleanup(project_root)
    
    # Run full cleanup
    cleanup.run_full_cleanup()
    
    # Print summary
    print("\n" + "="*60)
    print("🧹 CLEANUP SUMMARY")
    print("="*60)
    print(f"Files removed: {len(cleanup.cleanup_report['files_removed'])}")
    print(f"Files moved: {len(cleanup.cleanup_report['files_moved'])}")
    print(f"Directories created: {len(cleanup.cleanup_report['directories_created'])}")
    print(f"Errors: {len(cleanup.cleanup_report['errors'])}")
    
    if cleanup.cleanup_report['errors']:
        print("\n❌ ERRORS:")
        for error in cleanup.cleanup_report['errors']:
            print(f"  - {error}")
    
    print(f"\n📊 CODE QUALITY:")
    quality = cleanup.cleanup_report['quality_validation']
    print(f"  Python files: {quality['python_files']}")
    print(f"  Files with docstrings: {quality['files_with_docstrings']}")
    print(f"  Files with type hints: {quality['files_with_type_hints']}")
    
    print(f"\n📄 Report saved to: results/cleanup_report.json")
    print("="*60)


if __name__ == "__main__":
    main() 