"""
Hybrid Strategy Discovery Main Orchestrator
Coordinates the entire strategy discovery and integration process
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import argparse

from academic_miner import AcademicStrategyMiner
from public_miner import PublicStrategyMiner
from enhancer import StrategyEnhancer
from integration import StrategyDiscoveryIntegration, DeploymentPipeline

class HybridStrategyDiscovery:
    """Main orchestrator for hybrid strategy discovery"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.academic_miner = AcademicStrategyMiner()
        self.public_miner = PublicStrategyMiner()
        self.enhancer = StrategyEnhancer()
        self.integrator = StrategyDiscoveryIntegration()
        self.deployment = DeploymentPipeline()
        
        # Strategy storage
        self.discovered_strategies = []
        self.enhanced_strategies = []
        self.integrated_strategies = []
    
    def run_discovery_pipeline(self, 
                              keywords: List[str],
                              date_range: tuple = ('2020-01-01', '2024-01-01'),
                              max_strategies: int = 50) -> Dict:
        """
        Run the complete strategy discovery pipeline
        
        Args:
            keywords: Search keywords for strategy discovery
            date_range: Date range for academic papers
            max_strategies: Maximum number of strategies to discover
            
        Returns:
            Pipeline results summary
        """
        self.logger.info("Starting Hybrid Strategy Discovery Pipeline")
        
        # Phase 1: Strategy Discovery
        self.logger.info("Phase 1: Strategy Discovery")
        academic_strategies = self.academic_miner.mine_strategies(
            keywords, date_range, max_strategies//2
        )
        public_strategies = self.public_miner.extract_strategies(max_strategies//2)
        
        self.discovered_strategies = academic_strategies + public_strategies
        self.logger.info(f"Discovered {len(self.discovered_strategies)} strategies")
        
        # Phase 2: Strategy Enhancement
        self.logger.info("Phase 2: Strategy Enhancement")
        self.enhanced_strategies = []
        for strategy in self.discovered_strategies:
            try:
                enhanced = self.enhancer.enhance_strategy(strategy)
                self.enhanced_strategies.append(enhanced)
            except Exception as e:
                self.logger.error(f"Error enhancing strategy {strategy.get('name', 'Unknown')}: {str(e)}")
        
        self.logger.info(f"Enhanced {len(self.enhanced_strategies)} strategies")
        
        # Phase 3: Strategy Integration
        self.logger.info("Phase 3: Strategy Integration")
        self.integrated_strategies = []
        for strategy in self.enhanced_strategies:
            try:
                integrated = self.integrator.integrate_strategy(strategy)
                self.integrated_strategies.append(integrated)
            except Exception as e:
                self.logger.error(f"Error integrating strategy {strategy.get('name', 'Unknown')}: {str(e)}")
        
        self.logger.info(f"Integrated {len(self.integrated_strategies)} strategies")
        
        # Generate summary
        summary = self.generate_pipeline_summary()
        
        self.logger.info("Hybrid Strategy Discovery Pipeline completed")
        return summary
    
    def generate_pipeline_summary(self) -> Dict:
        """Generate pipeline execution summary"""
        return {
            'pipeline_execution_date': datetime.now().isoformat(),
            'discovery_results': {
                'academic_strategies': len([s for s in self.discovered_strategies if s.get('source_type') == 'academic']),
                'public_strategies': len([s for s in self.discovered_strategies if s.get('source_type') == 'public']),
                'total_discovered': len(self.discovered_strategies)
            },
            'enhancement_results': {
                'enhanced_strategies': len(self.enhanced_strategies),
                'enhancement_success_rate': len(self.enhanced_strategies) / len(self.discovered_strategies) if self.discovered_strategies else 0
            },
            'integration_results': {
                'integrated_strategies': len(self.integrated_strategies),
                'integration_success_rate': len(self.integrated_strategies) / len(self.enhanced_strategies) if self.enhanced_strategies else 0
            },
            'strategy_types': self.get_strategy_type_distribution(),
            'quality_metrics': self.get_quality_metrics()
        }
    
    def get_strategy_type_distribution(self) -> Dict:
        """Get distribution of strategy types"""
        distribution = {}
        for strategy in self.integrated_strategies:
            strategy_type = strategy['strategy'].get('strategy_type', 'unknown')
            distribution[strategy_type] = distribution.get(strategy_type, 0) + 1
        return distribution
    
    def get_quality_metrics(self) -> Dict:
        """Get quality metrics for discovered strategies"""
        if not self.integrated_strategies:
            return {}
        
        sharpe_ratios = []
        max_drawdowns = []
        annual_returns = []
        
        for strategy in self.integrated_strategies:
            performance = strategy['strategy'].get('performance_metrics', {})
            if 'sharpe_ratio' in performance:
                sharpe_ratios.append(performance['sharpe_ratio'])
            if 'max_drawdown' in performance:
                max_drawdowns.append(performance['max_drawdown'])
            if 'annual_return' in performance:
                annual_returns.append(performance['annual_return'])
        
        return {
            'avg_sharpe_ratio': sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0,
            'avg_max_drawdown': sum(max_drawdowns) / len(max_drawdowns) if max_drawdowns else 0,
            'avg_annual_return': sum(annual_returns) / len(annual_returns) if annual_returns else 0,
            'strategies_with_performance': len([s for s in self.integrated_strategies if 'performance_metrics' in s['strategy']])
        }
    
    def deploy_strategies(self, strategies: List[Dict], stage: str = 'paper_trading') -> List[Dict]:
        """
        Deploy strategies to specified stage
        
        Args:
            strategies: List of strategies to deploy
            stage: Deployment stage (validation, backtesting, paper_trading, live_trading)
            
        Returns:
            List of deployment results
        """
        deployment_results = []
        
        for strategy in strategies:
            try:
                result = self.deployment.deploy_strategy(strategy['strategy'], stage)
                deployment_results.append(result)
                self.logger.info(f"Deployed strategy {strategy['strategy'].get('name', 'Unknown')} to {stage}")
            except Exception as e:
                self.logger.error(f"Error deploying strategy {strategy['strategy'].get('name', 'Unknown')}: {str(e)}")
                deployment_results.append({
                    'strategy_id': strategy['strategy'].get('strategy_id'),
                    'deployment_stage': stage,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return deployment_results
    
    def save_results(self, output_file: str):
        """Save discovery results to file"""
        results = {
            'discovered_strategies': self.discovered_strategies,
            'enhanced_strategies': self.enhanced_strategies,
            'integrated_strategies': self.integrated_strategies,
            'summary': self.generate_pipeline_summary()
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to {output_file}")
    
    def load_results(self, input_file: str):
        """Load discovery results from file"""
        with open(input_file, 'r') as f:
            results = json.load(f)
        
        self.discovered_strategies = results.get('discovered_strategies', [])
        self.enhanced_strategies = results.get('enhanced_strategies', [])
        self.integrated_strategies = results.get('integrated_strategies', [])
        
        self.logger.info(f"Results loaded from {input_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Hybrid Strategy Discovery System')
    parser.add_argument('--keywords', nargs='+', default=['momentum', 'mean reversion', 'arbitrage'],
                       help='Search keywords for strategy discovery')
    parser.add_argument('--date-range', nargs=2, default=['2020-01-01', '2024-01-01'],
                       help='Date range for academic papers (start_date end_date)')
    parser.add_argument('--max-strategies', type=int, default=50,
                       help='Maximum number of strategies to discover')
    parser.add_argument('--output-file', default='strategy_discovery_results.json',
                       help='Output file for results')
    parser.add_argument('--deploy-stage', default='paper_trading',
                       choices=['validation', 'backtesting', 'paper_trading', 'live_trading'],
                       help='Deployment stage for strategies')
    parser.add_argument('--deploy', action='store_true',
                       help='Deploy strategies after discovery')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize discovery system
    discovery = HybridStrategyDiscovery()
    
    # Run discovery pipeline
    summary = discovery.run_discovery_pipeline(
        keywords=args.keywords,
        date_range=tuple(args.date_range),
        max_strategies=args.max_strategies
    )
    
    # Save results
    discovery.save_results(args.output_file)
    
    # Deploy strategies if requested
    if args.deploy:
        deployment_results = discovery.deploy_strategies(
            discovery.integrated_strategies,
            args.deploy_stage
        )
        print(f"Deployed {len(deployment_results)} strategies to {args.deploy_stage}")
    
    # Print summary
    print("\n" + "="*50)
    print("HYBRID STRATEGY DISCOVERY SUMMARY")
    print("="*50)
    print(f"Total strategies discovered: {summary['discovery_results']['total_discovered']}")
    print(f"Strategies enhanced: {summary['enhancement_results']['enhanced_strategies']}")
    print(f"Strategies integrated: {summary['integration_results']['integrated_strategies']}")
    print(f"Strategy types: {summary['strategy_types']}")
    
    if summary['quality_metrics']:
        print(f"Average Sharpe ratio: {summary['quality_metrics']['avg_sharpe_ratio']:.3f}")
        print(f"Average max drawdown: {summary['quality_metrics']['avg_max_drawdown']:.3f}")
        print(f"Average annual return: {summary['quality_metrics']['avg_annual_return']:.3f}")


if __name__ == "__main__":
    main() 