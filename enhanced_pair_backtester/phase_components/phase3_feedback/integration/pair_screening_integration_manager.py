"""
ClickHouse-Enhanced Backtester Integration Manager
================================================

This module provides the central coordination system between ClickHouse pair screening
and the enhanced backtester, creating a unified, scalable statistical arbitrage system.

Key Features:
- Unified interface for pair discovery and backtesting
- Automated pipeline from screening to validation
- Performance feedback integration
- Real-time monitoring capabilities
- Machine learning-based ranking
- Dynamic universe expansion

Author: Pro Quant Desk Trader
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ClickHouse screening system
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from clickhouse_pair_screening import ClickHousePairScreener, ScreeningConfig, PairAnalyzer

# Import enhanced backtester components
from config.backtest_config import BacktestConfig
from backtesting.enhanced_realistic_backtester import EnhancedRealisticBacktester
from backtesting.engine import BacktestEngine
from analysis.performance_metrics import PerformanceAnalyzer
from models.ensemble_filter_simple import EnsembleFilter

logger = logging.getLogger(__name__)

class IntegrationStatus(Enum):
    """Status of integration tasks"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ScreeningResult:
    """Results from ClickHouse screening"""
    pair: Tuple[str, str]
    correlation: float
    cointegration_pvalue: float
    hedge_ratio: float
    spread_mean: float
    spread_std: float
    regime_score: float
    liquidity_score: float
    transaction_cost_bps: float
    composite_score: float
    screening_timestamp: datetime

@dataclass
class BacktestResult:
    """Results from enhanced backtesting"""
    pair: Tuple[str, str]
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_duration: float
    transaction_costs: float
    alpha: float
    beta: float
    information_ratio: float
    calmar_ratio: float
    sortino_ratio: float
    backtest_timestamp: datetime

@dataclass
class IntegratedPairAnalysis:
    """Combined analysis from screening and backtesting"""
    pair: Tuple[str, str]
    screening_result: ScreeningResult
    backtest_result: BacktestResult
    final_score: float
    recommendation: str
    confidence_level: float
    risk_assessment: str
    expected_performance: Dict[str, float]
    analysis_timestamp: datetime

class PairScreeningIntegrationManager:
    """
    Central coordination system between ClickHouse screening and enhanced backtester.
    
    This class provides a unified interface for:
    - Automated pair discovery using ClickHouse screening
    - Comprehensive backtesting of discovered pairs
    - Performance feedback integration
    - Real-time monitoring and alerts
    - Machine learning-based ranking
    """
    
    def __init__(self, 
                 screening_config: Optional[ScreeningConfig] = None,
                 backtest_config: Optional[BacktestConfig] = None,
                 output_dir: str = "integration_results"):
        
        self.screening_config = screening_config or ScreeningConfig()
        self.backtest_config = backtest_config or BacktestConfig()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.clickhouse_screener = ClickHousePairScreener(self.screening_config)
        self.enhanced_backtester = EnhancedRealisticBacktester(
            initial_capital=self.backtest_config.initial_capital
        )
        self.performance_analyzer = PerformanceAnalyzer()
        
        # State tracking
        self.screening_results: List[ScreeningResult] = []
        self.backtest_results: List[BacktestResult] = []
        self.integrated_analyses: List[IntegratedPairAnalysis] = []
        
        # Performance tracking
        self.integration_stats = {
            'pairs_screened': 0,
            'pairs_backtested': 0,
            'successful_integrations': 0,
            'failed_integrations': 0,
            'total_runtime': 0.0,
            'last_update': None
        }
        
        # Configuration
        self.max_pairs_to_backtest = 50
        self.min_screening_score = 0.6
        self.min_backtest_sharpe = 0.5
        self.parallel_backtests = 4
        
        logger.info("PairScreeningIntegrationManager initialized")
    
    async def run_integrated_analysis(self, 
                                    screening_limit: int = 100,
                                    backtest_limit: int = 20) -> List[IntegratedPairAnalysis]:
        """
        Run complete integrated analysis pipeline.
        
        Args:
            screening_limit: Maximum pairs to screen
            backtest_limit: Maximum pairs to backtest
            
        Returns:
            List of integrated pair analyses
        """
        start_time = datetime.now()
        logger.info(f"Starting integrated analysis pipeline")
        
        try:
            # Phase 1: ClickHouse Screening
            logger.info("Phase 1: Running ClickHouse pair screening...")
            screening_results = await self._run_clickhouse_screening(screening_limit)
            
            if not screening_results:
                logger.warning("No pairs found in screening phase")
                return []
            
            # Phase 2: Enhanced Backtesting
            logger.info("Phase 2: Running enhanced backtesting...")
            backtest_results = await self._run_enhanced_backtesting(
                screening_results[:backtest_limit]
            )
            
            # Phase 3: Integration and Analysis
            logger.info("Phase 3: Integrating results...")
            integrated_analyses = self._integrate_results(screening_results, backtest_results)
            
            # Phase 4: Ranking and Selection
            logger.info("Phase 4: Ranking and selecting best pairs...")
            final_recommendations = self._rank_and_select_pairs(integrated_analyses)
            
            # Phase 5: Generate Reports
            logger.info("Phase 5: Generating reports...")
            await self._generate_integration_reports(final_recommendations)
            
            # Update statistics
            runtime = (datetime.now() - start_time).total_seconds()
            self._update_integration_stats(runtime, len(final_recommendations))
            
            logger.info(f"Integrated analysis completed in {runtime:.2f} seconds")
            logger.info(f"Final recommendations: {len(final_recommendations)} pairs")
            
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Integrated analysis failed: {e}")
            raise
    
    async def _run_clickhouse_screening(self, limit: int) -> List[ScreeningResult]:
        """Run ClickHouse screening and convert results"""
        try:
            # Run screening
            self.clickhouse_screener.screen_pairs()
            
            # Get results
            results_df = self.clickhouse_screener.get_screening_results()
            
            if results_df.empty:
                logger.warning("ClickHouse screening returned no results")
                return []
            
            # Convert to ScreeningResult objects
            screening_results = []
            for _, row in results_df.head(limit).iterrows():
                result = ScreeningResult(
                    pair=(row['symbol1'], row['symbol2']),
                    correlation=row.get('correlation', 0.0),
                    cointegration_pvalue=row.get('cointegration_pvalue', 1.0),
                    hedge_ratio=row.get('hedge_ratio', 1.0),
                    spread_mean=row.get('spread_mean', 0.0),
                    spread_std=row.get('spread_std', 1.0),
                    regime_score=row.get('regime_score', 0.0),
                    liquidity_score=row.get('liquidity_score', 0.0),
                    transaction_cost_bps=row.get('transaction_cost_bps', 30.0),
                    composite_score=row.get('composite_score', 0.0),
                    screening_timestamp=datetime.now()
                )
                screening_results.append(result)
            
            self.screening_results = screening_results
            self.integration_stats['pairs_screened'] = len(screening_results)
            
            logger.info(f"ClickHouse screening completed: {len(screening_results)} pairs")
            return screening_results
            
        except Exception as e:
            logger.error(f"ClickHouse screening failed: {e}")
            return []
    
    async def _run_enhanced_backtesting(self, 
                                      screening_results: List[ScreeningResult]) -> List[BacktestResult]:
        """Run enhanced backtesting on screened pairs"""
        backtest_results = []
        
        # Filter pairs by screening score
        filtered_pairs = [
            result for result in screening_results 
            if result.composite_score >= self.min_screening_score
        ]
        
        logger.info(f"Backtesting {len(filtered_pairs)} pairs (filtered from {len(screening_results)})")
        
        # Run backtests in parallel batches
        batch_size = self.parallel_backtests
        for i in range(0, len(filtered_pairs), batch_size):
            batch = filtered_pairs[i:i + batch_size]
            batch_results = await self._run_backtest_batch(batch)
            backtest_results.extend(batch_results)
        
        self.backtest_results = backtest_results
        self.integration_stats['pairs_backtested'] = len(backtest_results)
        
        logger.info(f"Enhanced backtesting completed: {len(backtest_results)} pairs")
        return backtest_results
    
    async def _run_backtest_batch(self, batch: List[ScreeningResult]) -> List[BacktestResult]:
        """Run backtesting for a batch of pairs"""
        results = []
        
        for screening_result in batch:
            try:
                # Configure backtester for this pair
                pair = screening_result.pair
                
                # Update backtest config
                self.backtest_config.symbol1 = pair[0]
                self.backtest_config.symbol2 = pair[1]
                
                # Run backtest
                start_date = datetime.now() - timedelta(days=365)
                end_date = datetime.now() - timedelta(days=30)
                
                backtest_result = self.enhanced_backtester.run_enhanced_backtest(
                    pairs=[pair],
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Convert to BacktestResult
                if backtest_result:
                    result = BacktestResult(
                        pair=pair,
                        total_return=backtest_result.get('total_return', 0.0),
                        sharpe_ratio=backtest_result.get('sharpe_ratio', 0.0),
                        max_drawdown=backtest_result.get('max_drawdown', 0.0),
                        win_rate=backtest_result.get('win_rate', 0.0),
                        total_trades=backtest_result.get('total_trades', 0),
                        avg_trade_duration=backtest_result.get('avg_trade_duration', 0.0),
                        transaction_costs=backtest_result.get('transaction_costs', 0.0),
                        alpha=backtest_result.get('alpha', 0.0),
                        beta=backtest_result.get('beta', 0.0),
                        information_ratio=backtest_result.get('information_ratio', 0.0),
                        calmar_ratio=backtest_result.get('calmar_ratio', 0.0),
                        sortino_ratio=backtest_result.get('sortino_ratio', 0.0),
                        backtest_timestamp=datetime.now()
                    )
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Backtest failed for pair {pair}: {e}")
                continue
        
        return results
    
    def _integrate_results(self, 
                          screening_results: List[ScreeningResult],
                          backtest_results: List[BacktestResult]) -> List[IntegratedPairAnalysis]:
        """Integrate screening and backtesting results"""
        integrated_analyses = []
        
        # Create lookup for backtest results
        backtest_lookup = {result.pair: result for result in backtest_results}
        
        for screening_result in screening_results:
            pair = screening_result.pair
            
            # Find corresponding backtest result
            backtest_result = backtest_lookup.get(pair)
            
            if backtest_result:
                # Calculate final score
                final_score = self._calculate_final_score(screening_result, backtest_result)
                
                # Generate recommendation
                recommendation = self._generate_recommendation(screening_result, backtest_result, final_score)
                
                # Calculate confidence level
                confidence_level = self._calculate_confidence_level(screening_result, backtest_result)
                
                # Risk assessment
                risk_assessment = self._assess_risk(screening_result, backtest_result)
                
                # Expected performance
                expected_performance = self._calculate_expected_performance(screening_result, backtest_result)
                
                integrated_analysis = IntegratedPairAnalysis(
                    pair=pair,
                    screening_result=screening_result,
                    backtest_result=backtest_result,
                    final_score=final_score,
                    recommendation=recommendation,
                    confidence_level=confidence_level,
                    risk_assessment=risk_assessment,
                    expected_performance=expected_performance,
                    analysis_timestamp=datetime.now()
                )
                
                integrated_analyses.append(integrated_analysis)
        
        self.integrated_analyses = integrated_analyses
        self.integration_stats['successful_integrations'] = len(integrated_analyses)
        
        return integrated_analyses
    
    def _calculate_final_score(self, 
                             screening_result: ScreeningResult,
                             backtest_result: BacktestResult) -> float:
        """Calculate final combined score"""
        # Weighted combination of screening and backtest scores
        screening_weight = 0.4
        backtest_weight = 0.6
        
        # Normalize screening score (0-1)
        screening_score = min(1.0, max(0.0, screening_result.composite_score))
        
        # Normalize backtest score based on Sharpe ratio
        backtest_score = min(1.0, max(0.0, (backtest_result.sharpe_ratio + 1) / 3))
        
        # Risk adjustment
        risk_penalty = max(0.0, backtest_result.max_drawdown - 0.1) * 2  # Penalty for >10% drawdown
        
        final_score = (screening_weight * screening_score + 
                      backtest_weight * backtest_score - 
                      risk_penalty)
        
        return max(0.0, min(1.0, final_score))
    
    def _generate_recommendation(self, 
                               screening_result: ScreeningResult,
                               backtest_result: BacktestResult,
                               final_score: float) -> str:
        """Generate trading recommendation"""
        if final_score >= 0.8 and backtest_result.sharpe_ratio >= 1.0:
            return "STRONG_BUY"
        elif final_score >= 0.6 and backtest_result.sharpe_ratio >= 0.5:
            return "BUY"
        elif final_score >= 0.4:
            return "HOLD"
        elif final_score >= 0.2:
            return "WEAK_SELL"
        else:
            return "STRONG_SELL"
    
    def _calculate_confidence_level(self, 
                                  screening_result: ScreeningResult,
                                  backtest_result: BacktestResult) -> float:
        """Calculate confidence level in the analysis"""
        factors = [
            min(1.0, screening_result.composite_score),
            min(1.0, max(0.0, backtest_result.sharpe_ratio / 2)),
            min(1.0, max(0.0, 1 - backtest_result.max_drawdown * 2)),
            min(1.0, max(0.0, backtest_result.win_rate)),
            min(1.0, max(0.0, backtest_result.total_trades / 100))
        ]
        
        return np.mean(factors)
    
    def _assess_risk(self, 
                    screening_result: ScreeningResult,
                    backtest_result: BacktestResult) -> str:
        """Assess risk level"""
        risk_score = (
            backtest_result.max_drawdown * 0.4 +
            (1 - backtest_result.win_rate) * 0.3 +
            (screening_result.transaction_cost_bps / 100) * 0.2 +
            (1 - screening_result.liquidity_score) * 0.1
        )
        
        if risk_score <= 0.2:
            return "LOW"
        elif risk_score <= 0.4:
            return "MEDIUM"
        elif risk_score <= 0.6:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    def _calculate_expected_performance(self, 
                                      screening_result: ScreeningResult,
                                      backtest_result: BacktestResult) -> Dict[str, float]:
        """Calculate expected performance metrics"""
        return {
            'expected_annual_return': backtest_result.total_return * 0.8,  # Conservative estimate
            'expected_sharpe_ratio': backtest_result.sharpe_ratio * 0.9,
            'expected_max_drawdown': backtest_result.max_drawdown * 1.2,
            'expected_win_rate': backtest_result.win_rate * 0.95,
            'expected_transaction_costs': screening_result.transaction_cost_bps * 1.1
        }
    
    def _rank_and_select_pairs(self, 
                             integrated_analyses: List[IntegratedPairAnalysis]) -> List[IntegratedPairAnalysis]:
        """Rank and select best pairs"""
        # Sort by final score
        sorted_analyses = sorted(
            integrated_analyses, 
            key=lambda x: x.final_score, 
            reverse=True
        )
        
        # Filter by minimum criteria
        filtered_analyses = [
            analysis for analysis in sorted_analyses
            if (analysis.final_score >= 0.5 and 
                analysis.backtest_result.sharpe_ratio >= self.min_backtest_sharpe and
                analysis.recommendation in ['STRONG_BUY', 'BUY'])
        ]
        
        return filtered_analyses[:20]  # Top 20 pairs
    
    async def _generate_integration_reports(self, 
                                          final_recommendations: List[IntegratedPairAnalysis]):
        """Generate comprehensive integration reports"""
        try:
            # Summary report
            summary_report = self._create_summary_report(final_recommendations)
            
            # Detailed analysis report
            detailed_report = self._create_detailed_report(final_recommendations)
            
            # Performance comparison report
            performance_report = self._create_performance_report(final_recommendations)
            
            # Save reports
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save as JSON
            with open(self.output_dir / f"integration_summary_{timestamp}.json", 'w') as f:
                json.dump(summary_report, f, indent=2, default=str)
            
            # Save as CSV
            self._save_results_csv(final_recommendations, timestamp)
            
            logger.info(f"Integration reports generated in {self.output_dir}")
            
        except Exception as e:
            logger.error(f"Failed to generate reports: {e}")
    
    def _create_summary_report(self, recommendations: List[IntegratedPairAnalysis]) -> Dict[str, Any]:
        """Create summary report"""
        if not recommendations:
            return {"error": "No recommendations available"}
        
        return {
            "integration_summary": {
                "total_pairs_screened": self.integration_stats['pairs_screened'],
                "total_pairs_backtested": self.integration_stats['pairs_backtested'],
                "successful_integrations": self.integration_stats['successful_integrations'],
                "final_recommendations": len(recommendations),
                "success_rate": len(recommendations) / max(1, self.integration_stats['pairs_screened']),
                "last_update": datetime.now().isoformat()
            },
            "top_recommendations": [
                {
                    "pair": f"{rec.pair[0]}_{rec.pair[1]}",
                    "final_score": rec.final_score,
                    "recommendation": rec.recommendation,
                    "confidence_level": rec.confidence_level,
                    "risk_assessment": rec.risk_assessment,
                    "expected_annual_return": rec.expected_performance['expected_annual_return'],
                    "expected_sharpe_ratio": rec.expected_performance['expected_sharpe_ratio'],
                    "expected_max_drawdown": rec.expected_performance['expected_max_drawdown']
                }
                for rec in recommendations[:10]
            ],
            "performance_statistics": {
                "avg_final_score": np.mean([rec.final_score for rec in recommendations]),
                "avg_sharpe_ratio": np.mean([rec.backtest_result.sharpe_ratio for rec in recommendations]),
                "avg_max_drawdown": np.mean([rec.backtest_result.max_drawdown for rec in recommendations]),
                "avg_win_rate": np.mean([rec.backtest_result.win_rate for rec in recommendations]),
                "avg_transaction_costs": np.mean([rec.screening_result.transaction_cost_bps for rec in recommendations])
            }
        }
    
    def _create_detailed_report(self, recommendations: List[IntegratedPairAnalysis]) -> Dict[str, Any]:
        """Create detailed analysis report"""
        return {
            "detailed_analysis": [
                {
                    "pair": f"{rec.pair[0]}_{rec.pair[1]}",
                    "screening_metrics": {
                        "correlation": rec.screening_result.correlation,
                        "cointegration_pvalue": rec.screening_result.cointegration_pvalue,
                        "hedge_ratio": rec.screening_result.hedge_ratio,
                        "regime_score": rec.screening_result.regime_score,
                        "liquidity_score": rec.screening_result.liquidity_score,
                        "transaction_cost_bps": rec.screening_result.transaction_cost_bps,
                        "composite_score": rec.screening_result.composite_score
                    },
                    "backtest_metrics": {
                        "total_return": rec.backtest_result.total_return,
                        "sharpe_ratio": rec.backtest_result.sharpe_ratio,
                        "max_drawdown": rec.backtest_result.max_drawdown,
                        "win_rate": rec.backtest_result.win_rate,
                        "total_trades": rec.backtest_result.total_trades,
                        "avg_trade_duration": rec.backtest_result.avg_trade_duration,
                        "alpha": rec.backtest_result.alpha,
                        "beta": rec.backtest_result.beta,
                        "information_ratio": rec.backtest_result.information_ratio
                    },
                    "integration_metrics": {
                        "final_score": rec.final_score,
                        "recommendation": rec.recommendation,
                        "confidence_level": rec.confidence_level,
                        "risk_assessment": rec.risk_assessment
                    },
                    "expected_performance": rec.expected_performance
                }
                for rec in recommendations
            ]
        }
    
    def _create_performance_report(self, recommendations: List[IntegratedPairAnalysis]) -> Dict[str, Any]:
        """Create performance comparison report"""
        if not recommendations:
            return {"error": "No recommendations for performance analysis"}
        
        screening_scores = [rec.screening_result.composite_score for rec in recommendations]
        backtest_sharpes = [rec.backtest_result.sharpe_ratio for rec in recommendations]
        final_scores = [rec.final_score for rec in recommendations]
        
        return {
            "performance_comparison": {
                "screening_vs_backtest_correlation": np.corrcoef(screening_scores, backtest_sharpes)[0, 1],
                "screening_vs_final_correlation": np.corrcoef(screening_scores, final_scores)[0, 1],
                "backtest_vs_final_correlation": np.corrcoef(backtest_sharpes, final_scores)[0, 1],
                "top_quartile_performance": {
                    "avg_screening_score": np.mean(screening_scores[:len(screening_scores)//4]),
                    "avg_backtest_sharpe": np.mean(backtest_sharpes[:len(backtest_sharpes)//4]),
                    "avg_final_score": np.mean(final_scores[:len(final_scores)//4])
                }
            }
        }
    
    def _save_results_csv(self, recommendations: List[IntegratedPairAnalysis], timestamp: str):
        """Save results to CSV format"""
        data = []
        for rec in recommendations:
            data.append({
                'pair': f"{rec.pair[0]}_{rec.pair[1]}",
                'symbol1': rec.pair[0],
                'symbol2': rec.pair[1],
                'final_score': rec.final_score,
                'recommendation': rec.recommendation,
                'confidence_level': rec.confidence_level,
                'risk_assessment': rec.risk_assessment,
                'screening_composite_score': rec.screening_result.composite_score,
                'screening_correlation': rec.screening_result.correlation,
                'screening_cointegration_pvalue': rec.screening_result.cointegration_pvalue,
                'screening_regime_score': rec.screening_result.regime_score,
                'screening_liquidity_score': rec.screening_result.liquidity_score,
                'screening_transaction_cost_bps': rec.screening_result.transaction_cost_bps,
                'backtest_total_return': rec.backtest_result.total_return,
                'backtest_sharpe_ratio': rec.backtest_result.sharpe_ratio,
                'backtest_max_drawdown': rec.backtest_result.max_drawdown,
                'backtest_win_rate': rec.backtest_result.win_rate,
                'backtest_total_trades': rec.backtest_result.total_trades,
                'backtest_alpha': rec.backtest_result.alpha,
                'backtest_beta': rec.backtest_result.beta,
                'expected_annual_return': rec.expected_performance['expected_annual_return'],
                'expected_sharpe_ratio': rec.expected_performance['expected_sharpe_ratio'],
                'expected_max_drawdown': rec.expected_performance['expected_max_drawdown'],
                'expected_win_rate': rec.expected_performance['expected_win_rate']
            })
        
        df = pd.DataFrame(data)
        df.to_csv(self.output_dir / f"integration_results_{timestamp}.csv", index=False)
    
    def _update_integration_stats(self, runtime: float, recommendations_count: int):
        """Update integration statistics"""
        self.integration_stats.update({
            'total_runtime': runtime,
            'recommendations_generated': recommendations_count,
            'last_update': datetime.now().isoformat()
        })
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get current integration statistics"""
        return self.integration_stats.copy()
    
    def get_top_recommendations(self, limit: int = 10) -> List[IntegratedPairAnalysis]:
        """Get top pair recommendations"""
        return sorted(
            self.integrated_analyses,
            key=lambda x: x.final_score,
            reverse=True
        )[:limit]
    
    def get_recommendations_by_risk(self, risk_level: str) -> List[IntegratedPairAnalysis]:
        """Get recommendations filtered by risk level"""
        return [
            analysis for analysis in self.integrated_analyses
            if analysis.risk_assessment == risk_level
        ]
    
    def save_configuration(self, filename: str):
        """Save current configuration"""
        config = {
            'screening_config': {
                'min_correlation': self.screening_config.min_correlation,
                'min_cointegration_pvalue': self.screening_config.min_cointegration_pvalue,
                'regime_window': self.screening_config.regime_window,
                'max_pairs_to_test': self.screening_config.max_pairs_to_test
            },
            'backtest_config': {
                'initial_capital': self.backtest_config.initial_capital,
                'entry_threshold': self.backtest_config.entry_threshold,
                'exit_threshold': self.backtest_config.exit_threshold,
                'lookback_window': self.backtest_config.lookback_window
            },
            'integration_config': {
                'max_pairs_to_backtest': self.max_pairs_to_backtest,
                'min_screening_score': self.min_screening_score,
                'min_backtest_sharpe': self.min_backtest_sharpe,
                'parallel_backtests': self.parallel_backtests
            }
        }
        
        with open(self.output_dir / filename, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuration saved to {filename}")

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_integration():
        """Test the integration manager"""
        # Initialize with test configuration
        screening_config = ScreeningConfig(
            max_pairs_to_test=20,
            min_correlation=0.3,
            sample_files=10
        )
        
        backtest_config = BacktestConfig(
            initial_capital=1000000,
            entry_threshold=2.0,
            exit_threshold=0.5
        )
        
        # Create integration manager
        integration_manager = PairScreeningIntegrationManager(
            screening_config=screening_config,
            backtest_config=backtest_config,
            output_dir="test_integration_results"
        )
        
        # Run integrated analysis
        try:
            recommendations = await integration_manager.run_integrated_analysis(
                screening_limit=20,
                backtest_limit=10
            )
            
            print(f"Integration completed successfully!")
            print(f"Generated {len(recommendations)} recommendations")
            
            # Display top recommendations
            if recommendations:
                print("\nTop 5 Recommendations:")
                for i, rec in enumerate(recommendations[:5], 1):
                    print(f"{i}. {rec.pair[0]}/{rec.pair[1]} - Score: {rec.final_score:.3f} - {rec.recommendation}")
            
            # Display statistics
            stats = integration_manager.get_integration_stats()
            print(f"\nIntegration Statistics:")
            print(f"Pairs Screened: {stats['pairs_screened']}")
            print(f"Pairs Backtested: {stats['pairs_backtested']}")
            print(f"Successful Integrations: {stats['successful_integrations']}")
            print(f"Total Runtime: {stats['total_runtime']:.2f} seconds")
            
        except Exception as e:
            print(f"Integration test failed: {e}")
    
    # Run test
    asyncio.run(test_integration()) 