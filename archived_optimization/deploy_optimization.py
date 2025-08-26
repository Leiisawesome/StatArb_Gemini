#!/usr/bin/env python3
"""
OPTIMIZATION DEPLOYMENT CLI
==========================

Simple command-line interface for deploying optimization to your existing system.

Usage:
    python deploy_optimization.py --mode conservative
    python deploy_optimization.py --mode balanced --symbols AAPL MSFT GOOGL
    python deploy_optimization.py --mode aggressive --symbols AAPL MSFT GOOGL TSLA --percentage 100

Examples:
    # Quick test with default settings
    python deploy_optimization.py
    
    # Conservative deployment for production
    python deploy_optimization.py --mode conservative
    
    # Balanced deployment with custom symbols
    python deploy_optimization.py --mode balanced --symbols AAPL MSFT GOOGL NVDA
    
    # Maximum performance test
    python deploy_optimization.py --mode aggressive --percentage 100

Author: Pro Quant Desk Trader
"""

import argparse
import asyncio
import logging
import sys
from typing import List

# Import deployment modules
from production_optimization_launcher import (
    deploy_conservative, 
    deploy_balanced, 
    deploy_aggressive,
    deploy_multi_symbol_test
)
from direct_integration_wrapper import (
    run_conservative_optimization,
    run_balanced_optimization,
    run_aggressive_optimization,
    quick_performance_test
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizationCLI:
    """Command-line interface for optimization deployment"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self):
        """Create command-line argument parser"""
        parser = argparse.ArgumentParser(
            description="Deploy optimization to existing trading system",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s                                    # Quick test
  %(prog)s --mode conservative                # 25%% optimization  
  %(prog)s --mode balanced --symbols AAPL MSFT GOOGL  # 50%% optimization
  %(prog)s --mode aggressive --percentage 100 # Maximum performance
            """
        )
        
        parser.add_argument(
            '--mode', 
            choices=['test', 'conservative', 'balanced', 'aggressive', 'multi'],
            default='test',
            help='Deployment mode (default: test)'
        )
        
        parser.add_argument(
            '--symbols', 
            nargs='+',
            default=['AAPL', 'MSFT'],
            help='Trading symbols (default: AAPL MSFT)'
        )
        
        parser.add_argument(
            '--percentage', 
            type=float,
            help='Optimization percentage (overrides mode default)'
        )
        
        parser.add_argument(
            '--launcher',
            choices=['direct', 'production'],
            default='direct',
            help='Deployment launcher type (default: direct)'
        )
        
        parser.add_argument(
            '--export-metrics',
            action='store_true',
            help='Export detailed performance metrics'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        
        return parser
    
    async def deploy(self, args):
        """Deploy optimization based on arguments"""
        
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        print("🚀 OPTIMIZATION DEPLOYMENT CLI")
        print("="*50)
        print(f"Mode: {args.mode}")
        print(f"Symbols: {', '.join(args.symbols)}")
        print(f"Launcher: {args.launcher}")
        print("="*50)
        
        try:
            if args.launcher == 'direct':
                await self._deploy_direct(args)
            else:
                await self._deploy_production(args)
                
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            sys.exit(1)
    
    async def _deploy_direct(self, args):
        """Deploy using direct integration wrapper"""
        
        if args.mode == 'test':
            print("🧪 Running quick performance test...")
            await quick_performance_test()
            
        elif args.mode == 'conservative':
            print("🛡️ Running conservative deployment (25% optimization)...")
            await run_conservative_optimization()
            
        elif args.mode == 'balanced':
            print("⚖️ Running balanced deployment (50% optimization)...")
            await run_balanced_optimization()
            
        elif args.mode == 'aggressive':
            print("🚀 Running aggressive deployment (100% optimization)...")
            await run_aggressive_optimization()
            
        else:
            logger.error(f"❌ Unknown mode for direct launcher: {args.mode}")
    
    async def _deploy_production(self, args):
        """Deploy using production launcher"""
        
        symbols = args.symbols
        
        if args.mode == 'test':
            print("🧪 Running multi-symbol test...")
            await deploy_multi_symbol_test()
            
        elif args.mode == 'conservative':
            print("🛡️ Running conservative deployment...")
            await deploy_conservative(symbols)
            
        elif args.mode == 'balanced':
            print("⚖️ Running balanced deployment...")
            await deploy_balanced(symbols)
            
        elif args.mode == 'aggressive':
            print("🚀 Running aggressive deployment...")
            await deploy_aggressive(symbols)
            
        elif args.mode == 'multi':
            print("📊 Running multi-symbol test...")
            await deploy_multi_symbol_test()
            
        else:
            logger.error(f"❌ Unknown mode for production launcher: {args.mode}")
    
    def run(self):
        """Run the CLI"""
        args = self.parser.parse_args()
        asyncio.run(self.deploy(args))

def main():
    """Main entry point"""
    cli = OptimizationCLI()
    cli.run()

if __name__ == "__main__":
    main()
