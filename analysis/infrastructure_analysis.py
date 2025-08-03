#!/usr/bin/env python3
"""
Infrastructure Analysis Script
==============================

This script analyzes the infrastructure components in the core system:
- ConfigManager availability and capabilities
- DatabaseManager availability and functionality
- MessageBus availability and performance
- MetricsCollector availability and status

Author: Infrastructure Integration Team
Date: 2025-01-27
"""

import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class InfrastructureComponentStatus:
    """Status information for an infrastructure component"""
    name: str
    available: bool
    version: Optional[str] = None
    capabilities: List[str] = None
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = None
    integration_points: List[str] = None

@dataclass
class InfrastructureReport:
    """Complete infrastructure analysis report"""
    timestamp: str
    overall_status: str
    components: Dict[str, InfrastructureComponentStatus]
    recommendations: List[str]
    integration_readiness: float  # 0.0 to 1.0
    system_orchestrator_requirements: Dict[str, Any]

class InfrastructureAnalyzer:
    """Analyzes infrastructure components in the core system"""
    
    def __init__(self):
        self.report = None
        self.components = {}
        
    async def analyze_all_components(self) -> InfrastructureReport:
        """Analyze all infrastructure components"""
        logger.info("Starting infrastructure analysis...")
        
        # Analyze each component
        await self._analyze_config_manager()
        await self._analyze_database_manager()
        await self._analyze_message_bus()
        await self._analyze_metrics_collector()
        
        # Generate overall report
        self.report = self._generate_report()
        
        logger.info("Infrastructure analysis completed")
        return self.report
    
    async def _analyze_config_manager(self):
        """Analyze ConfigManager availability and capabilities"""
        logger.info("Analyzing ConfigManager...")
        
        try:
            # Check if config manager module exists
            config_manager_path = project_root / "core_structure" / "infrastructure" / "config" / "config_manager.py"
            
            if config_manager_path.exists():
                try:
                    # Try to import and test config manager
                    from core_structure.infrastructure.config.config_manager import ConfigManager
                    
                    # Test basic functionality
                    config_manager = ConfigManager()
                    
                    capabilities = [
                        "Configuration loading",
                        "Configuration validation",
                        "Environment-based config",
                        "Configuration hot-reloading"
                    ]
                    
                    # Test configuration loading
                    try:
                        # Test loading a basic configuration
                        test_config = config_manager.get_config()
                        performance_metrics = {
                            "config_loaded": True,
                            "config_type": type(test_config).__name__ if test_config else "None"
                        }
                    except Exception as e:
                        performance_metrics = {"config_loaded": False, "error": str(e)}
                    
                    integration_points = [
                        "signal_generation",
                        "execution_engine", 
                        "risk_management",
                        "analytics",
                        "ai_infrastructure"
                    ]
                    
                    self.components['config_manager'] = InfrastructureComponentStatus(
                        name="ConfigManager",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics,
                        integration_points=integration_points
                    )
                    
                except Exception as e:
                    self.components['config_manager'] = InfrastructureComponentStatus(
                        name="ConfigManager",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}",
                        integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure"]
                    )
            else:
                self.components['config_manager'] = InfrastructureComponentStatus(
                    name="ConfigManager",
                    available=False,
                    error_message="ConfigManager module not found",
                    integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure"]
                )
                
        except Exception as e:
            logger.error(f"Error analyzing ConfigManager: {e}")
            self.components['config_manager'] = InfrastructureComponentStatus(
                name="ConfigManager",
                available=False,
                error_message=str(e),
                integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure"]
            )
    
    async def _analyze_database_manager(self):
        """Analyze DatabaseManager availability and functionality"""
        logger.info("Analyzing DatabaseManager...")
        
        try:
            # Check if database manager module exists
            database_manager_path = project_root / "core_structure" / "infrastructure" / "database" / "database_manager.py"
            
            if database_manager_path.exists():
                try:
                    # Try to import and test database manager
                    from core_structure.infrastructure.database.database_manager import DatabaseManager
                    
                    # Test basic functionality
                    db_manager = DatabaseManager()
                    
                    capabilities = [
                        "Database connection management",
                        "Query execution",
                        "Connection pooling",
                        "Transaction management"
                    ]
                    
                    # Test database connectivity
                    try:
                        # Test basic connectivity
                        connection_status = db_manager.is_connected()
                        performance_metrics = {
                            "connected": connection_status,
                            "connection_type": "mock" if not connection_status else "real"
                        }
                    except Exception as e:
                        performance_metrics = {"connected": False, "error": str(e)}
                    
                    integration_points = [
                        "market_data",
                        "analytics",
                        "risk_management",
                        "execution_engine",
                        "ai_infrastructure"
                    ]
                    
                    self.components['database_manager'] = InfrastructureComponentStatus(
                        name="DatabaseManager",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics,
                        integration_points=integration_points
                    )
                    
                except Exception as e:
                    self.components['database_manager'] = InfrastructureComponentStatus(
                        name="DatabaseManager",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}",
                        integration_points=["market_data", "analytics", "risk_management", "execution_engine", "ai_infrastructure"]
                    )
            else:
                self.components['database_manager'] = InfrastructureComponentStatus(
                    name="DatabaseManager",
                    available=False,
                    error_message="DatabaseManager module not found",
                    integration_points=["market_data", "analytics", "risk_management", "execution_engine", "ai_infrastructure"]
                )
                
        except Exception as e:
            logger.error(f"Error analyzing DatabaseManager: {e}")
            self.components['database_manager'] = InfrastructureComponentStatus(
                name="DatabaseManager",
                available=False,
                error_message=str(e),
                integration_points=["market_data", "analytics", "risk_management", "execution_engine", "ai_infrastructure"]
            )
    
    async def _analyze_message_bus(self):
        """Analyze MessageBus availability and performance"""
        logger.info("Analyzing MessageBus...")
        
        try:
            # Check if message bus module exists
            message_bus_path = project_root / "core_structure" / "infrastructure" / "messaging" / "message_bus.py"
            
            if message_bus_path.exists():
                try:
                    # Try to import and test message bus
                    from core_structure.infrastructure.messaging.message_bus import MessageBus
                    
                    # Test basic functionality
                    message_bus = MessageBus()
                    
                    capabilities = [
                        "Message publishing",
                        "Message subscription",
                        "Topic management",
                        "Message routing"
                    ]
                    
                    # Test message bus functionality
                    try:
                        # Test basic messaging
                        test_message = {"type": "test", "data": "test_data"}
                        message_bus.publish("test_topic", test_message)
                        
                        performance_metrics = {
                            "publish_working": True,
                            "message_bus_type": "mock"
                        }
                    except Exception as e:
                        performance_metrics = {"publish_working": False, "error": str(e)}
                    
                    integration_points = [
                        "signal_generation",
                        "execution_engine",
                        "risk_management",
                        "analytics",
                        "ai_infrastructure",
                        "market_data"
                    ]
                    
                    self.components['message_bus'] = InfrastructureComponentStatus(
                        name="MessageBus",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics,
                        integration_points=integration_points
                    )
                    
                except Exception as e:
                    self.components['message_bus'] = InfrastructureComponentStatus(
                        name="MessageBus",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}",
                        integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure", "market_data"]
                    )
            else:
                self.components['message_bus'] = InfrastructureComponentStatus(
                    name="MessageBus",
                    available=False,
                    error_message="MessageBus module not found",
                    integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure", "market_data"]
                )
                
        except Exception as e:
            logger.error(f"Error analyzing MessageBus: {e}")
            self.components['message_bus'] = InfrastructureComponentStatus(
                name="MessageBus",
                available=False,
                error_message=str(e),
                integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure", "market_data"]
            )
    
    async def _analyze_metrics_collector(self):
        """Analyze MetricsCollector availability and status"""
        logger.info("Analyzing MetricsCollector...")
        
        try:
            # Check if metrics collector module exists
            metrics_collector_path = project_root / "core_structure" / "infrastructure" / "monitoring" / "metrics_collector.py"
            
            if metrics_collector_path.exists():
                try:
                    # Try to import and test metrics collector
                    from core_structure.infrastructure.monitoring.metrics_collector import MetricsCollector
                    
                    # Test basic functionality
                    metrics_collector = MetricsCollector()
                    
                    capabilities = [
                        "Metrics collection",
                        "Performance monitoring",
                        "Health checks",
                        "Alert generation"
                    ]
                    
                    # Test metrics collection
                    try:
                        # Test basic metrics collection
                        metrics_collector.record_metric("test_metric", 1.0)
                        metrics = metrics_collector.get_metrics()
                        
                        performance_metrics = {
                            "metrics_collection_working": True,
                            "metrics_count": len(metrics) if metrics else 0
                        }
                    except Exception as e:
                        performance_metrics = {"metrics_collection_working": False, "error": str(e)}
                    
                    integration_points = [
                        "signal_generation",
                        "execution_engine",
                        "risk_management",
                        "analytics",
                        "ai_infrastructure",
                        "market_data"
                    ]
                    
                    self.components['metrics_collector'] = InfrastructureComponentStatus(
                        name="MetricsCollector",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics,
                        integration_points=integration_points
                    )
                    
                except Exception as e:
                    self.components['metrics_collector'] = InfrastructureComponentStatus(
                        name="MetricsCollector",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}",
                        integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure", "market_data"]
                    )
            else:
                self.components['metrics_collector'] = InfrastructureComponentStatus(
                    name="MetricsCollector",
                    available=False,
                    error_message="MetricsCollector module not found",
                    integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure", "market_data"]
                )
                
        except Exception as e:
            logger.error(f"Error analyzing MetricsCollector: {e}")
            self.components['metrics_collector'] = InfrastructureComponentStatus(
                name="MetricsCollector",
                available=False,
                error_message=str(e),
                integration_points=["signal_generation", "execution_engine", "risk_management", "analytics", "ai_infrastructure", "market_data"]
            )
    
    def _generate_report(self) -> InfrastructureReport:
        """Generate comprehensive analysis report"""
        from datetime import datetime
        
        # Calculate overall status
        available_components = sum(1 for comp in self.components.values() if comp.available)
        total_components = len(self.components)
        integration_readiness = available_components / total_components if total_components > 0 else 0.0
        
        if integration_readiness >= 0.8:
            overall_status = "EXCELLENT"
        elif integration_readiness >= 0.6:
            overall_status = "GOOD"
        elif integration_readiness >= 0.4:
            overall_status = "FAIR"
        else:
            overall_status = "POOR"
        
        # Generate recommendations
        recommendations = []
        
        if not self.components.get('config_manager', {}).available:
            recommendations.append("Implement ConfigManager for centralized configuration management")
        
        if not self.components.get('database_manager', {}).available:
            recommendations.append("Implement DatabaseManager for data persistence and access")
        
        if not self.components.get('message_bus', {}).available:
            recommendations.append("Implement MessageBus for inter-module communication")
        
        if not self.components.get('metrics_collector', {}).available:
            recommendations.append("Implement MetricsCollector for system monitoring")
        
        if integration_readiness < 0.6:
            recommendations.append("Focus on core infrastructure components first")
        
        # System Orchestrator requirements
        system_orchestrator_requirements = {
            "required_components": ["config_manager", "message_bus", "metrics_collector"],
            "optional_components": ["database_manager"],
            "integration_points": self._get_all_integration_points(),
            "messaging_requirements": {
                "publish_subscribe": True,
                "request_response": True,
                "broadcast": True
            },
            "monitoring_requirements": {
                "health_checks": True,
                "performance_metrics": True,
                "error_tracking": True
            }
        }
        
        return InfrastructureReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            components=self.components,
            recommendations=recommendations,
            integration_readiness=integration_readiness,
            system_orchestrator_requirements=system_orchestrator_requirements
        )
    
    def _get_all_integration_points(self) -> List[str]:
        """Get all unique integration points from components"""
        integration_points = set()
        for component in self.components.values():
            if component.integration_points:
                integration_points.update(component.integration_points)
        return list(integration_points)
    
    def print_report(self):
        """Print formatted analysis report"""
        if not self.report:
            print("No report available. Run analyze_all_components() first.")
            return
        
        print("\n" + "="*80)
        print("🏗️ INFRASTRUCTURE ANALYSIS REPORT")
        print("="*80)
        print(f"Timestamp: {self.report.timestamp}")
        print(f"Overall Status: {self.report.overall_status}")
        print(f"Integration Readiness: {self.report.integration_readiness:.1%}")
        print()
        
        print("📊 COMPONENT ANALYSIS:")
        print("-" * 50)
        
        for name, component in self.report.components.items():
            status_icon = "✅" if component.available else "❌"
            print(f"{status_icon} {component.name}")
            print(f"   Available: {component.available}")
            
            if component.version:
                print(f"   Version: {component.version}")
            
            if component.capabilities:
                print(f"   Capabilities: {', '.join(component.capabilities)}")
            
            if component.performance_metrics:
                print(f"   Performance: {component.performance_metrics}")
            
            if component.integration_points:
                print(f"   Integration Points: {', '.join(component.integration_points)}")
            
            if component.error_message:
                print(f"   Error: {component.error_message}")
            
            print()
        
        print("🎯 SYSTEM ORCHESTRATOR REQUIREMENTS:")
        print("-" * 50)
        requirements = self.report.system_orchestrator_requirements
        print(f"Required Components: {', '.join(requirements['required_components'])}")
        print(f"Optional Components: {', '.join(requirements['optional_components'])}")
        print(f"Integration Points: {', '.join(requirements['integration_points'])}")
        print(f"Messaging Requirements: {requirements['messaging_requirements']}")
        print(f"Monitoring Requirements: {requirements['monitoring_requirements']}")
        print()
        
        if self.report.recommendations:
            print("💡 RECOMMENDATIONS:")
            print("-" * 50)
            for i, rec in enumerate(self.report.recommendations, 1):
                print(f"{i}. {rec}")
            print()
        
        print("="*80)

async def main():
    """Main analysis function"""
    print("🚀 Starting Infrastructure Analysis...")
    
    analyzer = InfrastructureAnalyzer()
    report = await analyzer.analyze_all_components()
    analyzer.print_report()
    
    # Save report to file
    report_file = project_root / "analysis" / "infrastructure_report.json"
    import json
    from datetime import datetime
    
    report_dict = {
        "timestamp": report.timestamp,
        "overall_status": report.overall_status,
        "integration_readiness": report.integration_readiness,
        "components": {
            name: {
                "name": comp.name,
                "available": comp.available,
                "version": comp.version,
                "capabilities": comp.capabilities,
                "error_message": comp.error_message,
                "performance_metrics": comp.performance_metrics,
                "integration_points": comp.integration_points
            }
            for name, comp in report.components.items()
        },
        "recommendations": report.recommendations,
        "system_orchestrator_requirements": report.system_orchestrator_requirements
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_dict, f, indent=2)
    
    print(f"📄 Report saved to: {report_file}")
    
    return report

if __name__ == "__main__":
    asyncio.run(main()) 