"""
Base Experiment Framework
=========================

Abstract base class for all backtest experiments.
Enforces consistent interface and zero re-implementation principle.

Author: StatArb_Gemini Core Engine
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Structured experiment result"""
    
    # Experiment metadata
    experiment_name: str
    experiment_type: str
    run_timestamp: datetime
    duration_seconds: float
    
    # Engine results (pass-through from InstitutionalBacktestEngine)
    engine_results: Dict[str, Any]
    
    # Performance summary (extracted from engine_results)
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    total_trades: int
    win_rate: float
    
    # Additional metrics (experiment-specific)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'experiment_name': self.experiment_name,
            'experiment_type': self.experiment_type,
            'run_timestamp': self.run_timestamp.isoformat(),
            'duration_seconds': self.duration_seconds,
            'performance': {
                'total_return_pct': self.total_return_pct,
                'sharpe_ratio': self.sharpe_ratio,
                'max_drawdown_pct': self.max_drawdown_pct,
                'total_trades': self.total_trades,
                'win_rate': self.win_rate,
            },
            'custom_metrics': self.custom_metrics,
            'engine_results': self.engine_results,
            'success': self.success,
            'error_message': self.error_message,
        }


class BaseExperiment(ABC):
    """
    Abstract base for all backtest experiments.
    
    Enforces:
    - Consistent interface
    - Zero re-implementation (use engine as black box)
    - Structured results
    - Config-driven execution
    """
    
    def __init__(self, config: Dict[str, Any], output_dir: str = "backtest/results"):
        """
        Initialize experiment.
        
        Args:
            config: Experiment configuration (loaded from YAML)
            output_dir: Directory for results output
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def run(self) -> ExperimentResult:
        """
        Run experiment.
        
        MUST:
        - Use InstitutionalBacktestEngine (import from backtest.engine)
        - Not re-implement any engine logic
        - Return ExperimentResult
        
        Returns:
            ExperimentResult with structured results
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get one-line experiment description.
        
        Returns:
            Human-readable description
        """
        pass
    
    def print_summary(self, result: ExperimentResult):
        """
        Print concise run summary to console.
        
        Args:
            result: Experiment result to summarize
        """
        print("\n" + "="*80)
        print(f"📊 EXPERIMENT SUMMARY: {result.experiment_name}")
        print("="*80)
        print(f"Type:           {result.experiment_type}")
        print(f"Status:         {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        print(f"Duration:       {result.duration_seconds:.2f}s")
        print()
        
        if result.success:
            print("Performance Metrics:")
            print(f"  Total Return:    {result.total_return_pct:>8.2f}%")
            print(f"  Sharpe Ratio:    {result.sharpe_ratio:>8.2f}")
            print(f"  Max Drawdown:    {result.max_drawdown_pct:>8.2f}%")
            print(f"  Total Trades:    {result.total_trades:>8}")
            print(f"  Win Rate:        {result.win_rate:>8.1f}%")
            
            if result.custom_metrics:
                print()
                print("Custom Metrics:")
                for key, value in result.custom_metrics.items():
                    if isinstance(value, float):
                        print(f"  {key:<20} {value:>10.4f}")
                    else:
                        print(f"  {key:<20} {value:>10}")
        else:
            print(f"❌ Error: {result.error_message}")
        
        print("="*80)
    
    def save_results(self, result: ExperimentResult):
        """
        Write structured results to disk.
        
        Saves:
        - JSON file with full results
        - CSV file with key metrics (if applicable)
        
        Args:
            result: Experiment result to save
        """
        timestamp = result.run_timestamp.strftime("%Y%m%d_%H%M%S")
        experiment_slug = result.experiment_name.replace(" ", "_").lower()
        
        # Save JSON
        json_path = self.output_dir / f"{experiment_slug}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        
        self.logger.info(f"Results saved to: {json_path}")
        
        # Save summary CSV (for easy comparison across runs)
        csv_path = self.output_dir / "experiment_summary.csv"
        self._append_to_summary_csv(result, csv_path)
    
    def _append_to_summary_csv(self, result: ExperimentResult, csv_path: Path):
        """Append result to summary CSV"""
        import csv
        
        # Check if file exists to determine if we need header
        file_exists = csv_path.exists()
        
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write header if new file
            if not file_exists:
                writer.writerow([
                    'timestamp', 'experiment_name', 'experiment_type',
                    'total_return_pct', 'sharpe_ratio', 'max_drawdown_pct',
                    'total_trades', 'win_rate', 'duration_seconds', 'success'
                ])
            
            # Write data row
            writer.writerow([
                result.run_timestamp.isoformat(),
                result.experiment_name,
                result.experiment_type,
                result.total_return_pct,
                result.sharpe_ratio,
                result.max_drawdown_pct,
                result.total_trades,
                result.win_rate,
                result.duration_seconds,
                result.success
            ])
    
    def _extract_performance_metrics(self, engine_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract standard performance metrics from engine results.
        
        Args:
            engine_results: Raw results from InstitutionalBacktestEngine
            
        Returns:
            Dict with standard metrics
        """
        # Extract from engine results structure
        # Adjust keys based on actual engine output
        performance = engine_results.get('performance', {})
        
        return {
            'total_return_pct': performance.get('total_return_pct', 0.0),
            'sharpe_ratio': performance.get('sharpe_ratio', 0.0),
            'max_drawdown_pct': performance.get('max_drawdown_pct', 0.0),
            'total_trades': performance.get('total_trades', 0),
            'win_rate': performance.get('win_rate', 0.0) * 100,  # Convert to percentage
        }

