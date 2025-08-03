#!/usr/bin/env python3
"""
AI Infrastructure Analysis Script
================================

This script analyzes the AI infrastructure components in the core system:
- LLM Client availability and capabilities
- Knowledge Base availability and functionality
- Vector Database availability and performance
- AI Monitor availability and status
- Trading Agents availability and capabilities

Author: AI Integration Team
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

try:
    import openai
    import chromadb
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    import pandas as pd
    from langchain.llms import OpenAI
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.schema import Document
except ImportError as e:
    print(f"Warning: Some AI packages not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AIComponentStatus:
    """Status information for an AI component"""
    name: str
    available: bool
    version: Optional[str] = None
    capabilities: List[str] = None
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = None

@dataclass
class AIInfrastructureReport:
    """Complete AI infrastructure analysis report"""
    timestamp: str
    overall_status: str
    components: Dict[str, AIComponentStatus]
    recommendations: List[str]
    integration_readiness: float  # 0.0 to 1.0

class AIInfrastructureAnalyzer:
    """Analyzes AI infrastructure components in the core system"""
    
    def __init__(self):
        self.report = None
        self.components = {}
        
    async def analyze_all_components(self) -> AIInfrastructureReport:
        """Analyze all AI infrastructure components"""
        logger.info("Starting AI infrastructure analysis...")
        
        # Analyze each component
        await self._analyze_llm_client()
        await self._analyze_knowledge_base()
        await self._analyze_vector_database()
        await self._analyze_ai_monitor()
        await self._analyze_trading_agents()
        
        # Generate overall report
        self.report = self._generate_report()
        
        logger.info("AI infrastructure analysis completed")
        return self.report
    
    async def _analyze_llm_client(self):
        """Analyze LLM client availability and capabilities"""
        logger.info("Analyzing LLM client...")
        
        try:
            # Check if OpenAI is available
            if 'openai' in sys.modules:
                # Test basic functionality
                client = openai.OpenAI()
                
                # Check if API key is configured
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    capabilities = [
                        "Text generation",
                        "Chat completion",
                        "Embedding generation",
                        "Fine-tuning support"
                    ]
                    
                    # Test basic embedding generation
                    try:
                        response = client.embeddings.create(
                            model="text-embedding-ada-002",
                            input="test"
                        )
                        performance_metrics = {
                            "embedding_dimension": len(response.data[0].embedding),
                            "model": "text-embedding-ada-002"
                        }
                    except Exception as e:
                        performance_metrics = {"error": str(e)}
                    
                    self.components['llm_client'] = AIComponentStatus(
                        name="OpenAI LLM Client",
                        available=True,
                        version=openai.__version__,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics
                    )
                else:
                    self.components['llm_client'] = AIComponentStatus(
                        name="OpenAI LLM Client",
                        available=False,
                        error_message="OPENAI_API_KEY not configured"
                    )
            else:
                self.components['llm_client'] = AIComponentStatus(
                    name="OpenAI LLM Client",
                    available=False,
                    error_message="OpenAI package not available"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing LLM client: {e}")
            self.components['llm_client'] = AIComponentStatus(
                name="OpenAI LLM Client",
                available=False,
                error_message=str(e)
            )
    
    async def _analyze_knowledge_base(self):
        """Analyze Knowledge Base availability and functionality"""
        logger.info("Analyzing Knowledge Base...")
        
        try:
            # Check if knowledge base module exists
            knowledge_base_path = project_root / "core_structure" / "ai_infrastructure" / "knowledge" / "knowledge_base.py"
            
            if knowledge_base_path.exists():
                try:
                    # Try to import and test knowledge base
                    from core_structure.ai_infrastructure.knowledge.knowledge_base import KnowledgeBase
                    
                    # Test basic functionality
                    kb = KnowledgeBase()
                    
                    capabilities = [
                        "Knowledge storage",
                        "Knowledge retrieval",
                        "Pattern matching",
                        "Historical data access"
                    ]
                    
                    self.components['knowledge_base'] = AIComponentStatus(
                        name="Knowledge Base",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics={"status": "initialized"}
                    )
                    
                except Exception as e:
                    self.components['knowledge_base'] = AIComponentStatus(
                        name="Knowledge Base",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}"
                    )
            else:
                self.components['knowledge_base'] = AIComponentStatus(
                    name="Knowledge Base",
                    available=False,
                    error_message="Knowledge base module not found"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing Knowledge Base: {e}")
            self.components['knowledge_base'] = AIComponentStatus(
                name="Knowledge Base",
                available=False,
                error_message=str(e)
            )
    
    async def _analyze_vector_database(self):
        """Analyze Vector Database availability and performance"""
        logger.info("Analyzing Vector Database...")
        
        try:
            # Check if ChromaDB is available
            if 'chromadb' in sys.modules:
                try:
                    # Test ChromaDB functionality
                    client = chromadb.Client()
                    
                    # Test collection creation and embedding
                    collection = client.create_collection(
                        name="test_collection",
                        metadata={"description": "Test collection for analysis"}
                    )
                    
                    # Test embedding generation
                    if 'sentence_transformers' in sys.modules:
                        model = SentenceTransformer('all-MiniLM-L6-v2')
                        test_embeddings = model.encode(["test document"])
                        
                        collection.add(
                            embeddings=test_embeddings.tolist(),
                            documents=["test document"],
                            ids=["test_id"]
                        )
                        
                        # Test similarity search
                        results = collection.query(
                            query_embeddings=test_embeddings.tolist(),
                            n_results=1
                        )
                        
                        performance_metrics = {
                            "embedding_dimension": test_embeddings.shape[1],
                            "collection_created": True,
                            "similarity_search_working": len(results['ids'][0]) > 0
                        }
                    else:
                        performance_metrics = {
                            "embedding_dimension": "unknown",
                            "collection_created": True,
                            "similarity_search_working": False
                        }
                    
                    capabilities = [
                        "Vector storage",
                        "Similarity search",
                        "Collection management",
                        "Metadata storage"
                    ]
                    
                    self.components['vector_database'] = AIComponentStatus(
                        name="ChromaDB Vector Database",
                        available=True,
                        version=chromadb.__version__,
                        capabilities=capabilities,
                        performance_metrics=performance_metrics
                    )
                    
                    # Clean up test collection
                    client.delete_collection("test_collection")
                    
                except Exception as e:
                    self.components['vector_database'] = AIComponentStatus(
                        name="ChromaDB Vector Database",
                        available=False,
                        error_message=f"Functionality test failed: {str(e)}"
                    )
            else:
                self.components['vector_database'] = AIComponentStatus(
                    name="ChromaDB Vector Database",
                    available=False,
                    error_message="ChromaDB package not available"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing Vector Database: {e}")
            self.components['vector_database'] = AIComponentStatus(
                name="ChromaDB Vector Database",
                available=False,
                error_message=str(e)
            )
    
    async def _analyze_ai_monitor(self):
        """Analyze AI Monitor availability and status"""
        logger.info("Analyzing AI Monitor...")
        
        try:
            # Check if AI monitor module exists
            ai_monitor_path = project_root / "core_structure" / "ai_infrastructure" / "monitoring" / "ai_monitor.py"
            
            if ai_monitor_path.exists():
                try:
                    # Try to import and test AI monitor
                    from core_structure.ai_infrastructure.monitoring.ai_monitor import AIMonitor
                    
                    # Test basic functionality
                    monitor = AIMonitor()
                    
                    capabilities = [
                        "AI performance monitoring",
                        "Model health tracking",
                        "Alert generation",
                        "Metrics collection"
                    ]
                    
                    self.components['ai_monitor'] = AIComponentStatus(
                        name="AI Monitor",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics={"status": "initialized"}
                    )
                    
                except Exception as e:
                    self.components['ai_monitor'] = AIComponentStatus(
                        name="AI Monitor",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}"
                    )
            else:
                self.components['ai_monitor'] = AIComponentStatus(
                    name="AI Monitor",
                    available=False,
                    error_message="AI monitor module not found"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing AI Monitor: {e}")
            self.components['ai_monitor'] = AIComponentStatus(
                name="AI Monitor",
                available=False,
                error_message=str(e)
            )
    
    async def _analyze_trading_agents(self):
        """Analyze Trading Agents availability and capabilities"""
        logger.info("Analyzing Trading Agents...")
        
        try:
            # Check if trading agents module exists
            trading_agents_path = project_root / "core_structure" / "ai_infrastructure" / "agents" / "trading_agents.py"
            
            if trading_agents_path.exists():
                try:
                    # Try to import and test trading agents
                    from core_structure.ai_infrastructure.agents.trading_agents import TradingAgent
                    
                    # Test basic functionality
                    agent = TradingAgent()
                    
                    capabilities = [
                        "Trading decision making",
                        "Market analysis",
                        "Risk assessment",
                        "Portfolio management"
                    ]
                    
                    self.components['trading_agents'] = AIComponentStatus(
                        name="Trading Agents",
                        available=True,
                        capabilities=capabilities,
                        performance_metrics={"status": "initialized"}
                    )
                    
                except Exception as e:
                    self.components['trading_agents'] = AIComponentStatus(
                        name="Trading Agents",
                        available=False,
                        error_message=f"Import/initialization error: {str(e)}"
                    )
            else:
                self.components['trading_agents'] = AIComponentStatus(
                    name="Trading Agents",
                    available=False,
                    error_message="Trading agents module not found"
                )
                
        except Exception as e:
            logger.error(f"Error analyzing Trading Agents: {e}")
            self.components['trading_agents'] = AIComponentStatus(
                name="Trading Agents",
                available=False,
                error_message=str(e)
            )
    
    def _generate_report(self) -> AIInfrastructureReport:
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
        
        if not self.components.get('llm_client', {}).available:
            recommendations.append("Configure OpenAI API key for LLM functionality")
        
        if not self.components.get('vector_database', {}).available:
            recommendations.append("Install and configure ChromaDB for vector storage")
        
        if not self.components.get('knowledge_base', {}).available:
            recommendations.append("Implement Knowledge Base module")
        
        if not self.components.get('ai_monitor', {}).available:
            recommendations.append("Implement AI Monitor for performance tracking")
        
        if not self.components.get('trading_agents', {}).available:
            recommendations.append("Implement Trading Agents for AI-driven decisions")
        
        if integration_readiness < 0.6:
            recommendations.append("Focus on core AI components (LLM, Vector DB) first")
        
        return AIInfrastructureReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            components=self.components,
            recommendations=recommendations,
            integration_readiness=integration_readiness
        )
    
    def print_report(self):
        """Print formatted analysis report"""
        if not self.report:
            print("No report available. Run analyze_all_components() first.")
            return
        
        print("\n" + "="*80)
        print("🤖 AI INFRASTRUCTURE ANALYSIS REPORT")
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
            
            if component.error_message:
                print(f"   Error: {component.error_message}")
            
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
    print("🚀 Starting AI Infrastructure Analysis...")
    
    analyzer = AIInfrastructureAnalyzer()
    report = await analyzer.analyze_all_components()
    analyzer.print_report()
    
    # Save report to file
    report_file = project_root / "analysis" / "ai_infrastructure_report.json"
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
                "performance_metrics": comp.performance_metrics
            }
            for name, comp in report.components.items()
        },
        "recommendations": report.recommendations
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_dict, f, indent=2)
    
    print(f"📄 Report saved to: {report_file}")
    
    return report

if __name__ == "__main__":
    asyncio.run(main()) 