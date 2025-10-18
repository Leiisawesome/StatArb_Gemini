"""
Period Scanner Base Class
=========================

Abstract base class for implementing period scanners that analyze
historical market conditions and identify optimal trading periods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class PeriodAnalysisResult:
    """Results from analyzing a specific period"""
    
    symbol: str
    start_date: str
    end_date: str
    period_label: str  # e.g., "2023 Q1"
    score: float
    metrics: Dict[str, float]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'period': self.period_label,
            'score': self.score,
            'metrics': self.metrics,
            'metadata': self.metadata or {}
        }


class PeriodScannerBase(ABC):
    """
    Abstract base class for period scanners.
    
    Provides common functionality for:
    - Loading and resampling data
    - Calculating technical indicators
    - Scoring periods
    - Generating reports
    """
    
    def __init__(self, symbols: List[str], start_year: int, end_year: int):
        """
        Initialize period scanner.
        
        Args:
            symbols: List of symbols to analyze
            start_year: Starting year for analysis
            end_year: Ending year for analysis
        """
        self.symbols = symbols
        self.start_year = start_year
        self.end_year = end_year
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Standard quarters for analysis
        self.quarters = [
            ('Q1', '-01-01', '-03-31'),
            ('Q2', '-04-01', '-06-30'),
            ('Q3', '-07-01', '-09-30'),
            ('Q4', '-10-01', '-12-31'),
        ]
    
    @abstractmethod
    def analyze_period(self, symbol: str, start_date: str, end_date: str) -> Optional[PeriodAnalysisResult]:
        """
        Analyze a specific period for a symbol.
        
        Args:
            symbol: Symbol to analyze
            start_date: Period start date (YYYY-MM-DD)
            end_date: Period end date (YYYY-MM-DD)
            
        Returns:
            PeriodAnalysisResult or None if analysis fails
        """
        pass
    
    @abstractmethod
    def calculate_period_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate score for a period based on metrics.
        
        Args:
            metrics: Dictionary of calculated metrics
            
        Returns:
            Score for the period
        """
        pass
    
    def scan_all_periods(self) -> List[PeriodAnalysisResult]:
        """
        Scan all quarters for all symbols.
        
        Returns:
            List of PeriodAnalysisResult objects
        """
        self.logger.info("=" * 80)
        self.logger.info(f"🔍 {self.__class__.__name__.upper()} - Starting comprehensive scan")
        self.logger.info("=" * 80)
        self.logger.info(f"Symbols: {', '.join(self.symbols)}")
        self.logger.info(f"Period: {self.start_year} - {self.end_year}")
        self.logger.info("")
        
        all_results = []
        total_periods = len(self.symbols) * len(self.quarters) * (self.end_year - self.start_year + 1)
        current = 0
        
        for year in range(self.start_year, self.end_year + 1):
            for quarter_name, start_suffix, end_suffix in self.quarters:
                for symbol in self.symbols:
                    current += 1
                    
                    start_date = f"{year}{start_suffix}"
                    end_date = f"{year}{end_suffix}"
                    period_label = f"{year} {quarter_name}"
                    
                    self.logger.info(f"[{current}/{total_periods}] Analyzing {symbol} {period_label}...")
                    
                    result = self.analyze_period(symbol, start_date, end_date)
                    
                    if result:
                        self.logger.info(f"  ✅ Score: {result.score:.2f}")
                        all_results.append(result)
                    else:
                        self.logger.info(f"  ⚠️ No data available")
        
        self.logger.info("")
        self.logger.info(f"✅ Scan complete: {len(all_results)}/{total_periods} periods analyzed")
        self.logger.info("")
        
        return all_results
    
    def generate_report(self, results: List[PeriodAnalysisResult]) -> Dict[str, Any]:
        """
        Generate comprehensive report from scan results.
        
        Args:
            results: List of PeriodAnalysisResult objects
            
        Returns:
            Dictionary containing report data
        """
        if not results:
            return {}
        
        # Sort by score (descending)
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        
        # Calculate symbol-specific statistics
        symbol_stats = {}
        for symbol in self.symbols:
            symbol_results = [r for r in results if r.symbol == symbol]
            if symbol_results:
                scores = [r.score for r in symbol_results]
                symbol_stats[symbol] = {
                    'avg_score': np.mean(scores),
                    'best_period': max(symbol_results, key=lambda x: x.score).period_label,
                    'best_score': max(scores),
                    'total_periods': len(symbol_results)
                }
        
        report = {
            'scan_date': datetime.now().isoformat(),
            'scanner_type': self.__class__.__name__,
            'total_periods_analyzed': len(results),
            'symbols_analyzed': self.symbols,
            'year_range': f"{self.start_year}-{self.end_year}",
            'top_periods': [r.to_dict() for r in sorted_results[:15]],
            'bottom_periods': [r.to_dict() for r in sorted_results[-10:]],
            'symbol_statistics': symbol_stats,
            'recommendations': self._generate_recommendations(sorted_results),
            'all_results': [r.to_dict() for r in sorted_results]
        }
        
        return report
    
    def _generate_recommendations(self, sorted_results: List[PeriodAnalysisResult]) -> Dict[str, Any]:
        """
        Generate testing recommendations based on results.
        
        Args:
            sorted_results: Results sorted by score (descending)
            
        Returns:
            Dictionary of recommendations
        """
        if not sorted_results:
            return {}
        
        best_period = sorted_results[0]
        
        # Find secondary and validation periods
        secondary = None
        validation = None
        
        for result in sorted_results[1:]:
            if not secondary and result.symbol == best_period.symbol:
                secondary = result
            elif not validation and result.symbol != best_period.symbol:
                validation = result
            
            if secondary and validation:
                break
        
        return {
            'primary_test_period': {
                'symbol': best_period.symbol,
                'period': best_period.period_label,
                'start_date': best_period.start_date,
                'end_date': best_period.end_date,
                'score': best_period.score,
                'reason': 'Highest overall score'
            },
            'secondary_test_period': {
                'symbol': secondary.symbol if secondary else best_period.symbol,
                'period': secondary.period_label if secondary else 'N/A',
                'start_date': secondary.start_date if secondary else 'N/A',
                'end_date': secondary.end_date if secondary else 'N/A',
                'score': secondary.score if secondary else 0.0
            } if secondary else None,
            'validation_period': {
                'symbol': validation.symbol if validation else 'N/A',
                'period': validation.period_label if validation else 'N/A',
                'start_date': validation.start_date if validation else 'N/A',
                'end_date': validation.end_date if validation else 'N/A',
                'score': validation.score if validation else 0.0
            } if validation else None,
            'avoid_periods': [
                {
                    'symbol': r.symbol,
                    'period': r.period_label,
                    'score': r.score,
                    'reason': 'Low score'
                }
                for r in sorted_results[-3:]
            ]
        }
    
    def calculate_momentum(self, data: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calculate momentum as percentage change over period"""
        return data['close'].pct_change(period) * 100
    
    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average Directional Index (ADX) with proper error handling.
        
        ADX measures trend strength (not direction):
        - ADX < 25: Weak/no trend
        - ADX 25-50: Moderate to strong trend
        - ADX > 50: Very strong trend
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        # Use pandas Series directly instead of numpy where to maintain index
        plus_dm = pd.Series(0.0, index=data.index)
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
        
        minus_dm = pd.Series(0.0, index=data.index)
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]
        
        # Smooth with EMA
        atr = tr.ewm(span=period, adjust=False).mean()
        
        # Avoid division by zero in ATR
        atr = atr.replace(0, np.nan)
        
        plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
        minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr
        
        # Calculate ADX with division by zero protection
        di_sum = plus_di + minus_di
        di_diff = abs(plus_di - minus_di)
        
        # Initialize DX as a Series with zeros and the same index
        dx = pd.Series(0.0, index=data.index)
        # Only calculate DX where di_sum is significant (> 0.01)
        mask = di_sum > 0.01
        dx[mask] = 100 * di_diff[mask] / di_sum[mask]
        
        # Calculate ADX
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return adx
    
    def calculate_volatility(self, data: pd.DataFrame, period: int = 20) -> float:
        """Calculate annualized volatility"""
        returns = data['close'].pct_change()
        return returns.std() * np.sqrt(252)
    
    def save_report(self, report: Dict[str, Any], filename: str):
        """
        Save report to JSON file with proper numpy type handling.
        
        Args:
            report: Report dictionary
            filename: Output filename
        """
        import json
        from pathlib import Path
        
        def convert_numpy_types(obj):
            """Convert numpy types to Python native types for JSON serialization"""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                # Handle NaN, inf, -inf
                if np.isnan(obj):
                    return None
                elif np.isinf(obj):
                    return None
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        # Convert all numpy types before saving
        serializable_report = convert_numpy_types(report)
        
        output_path = Path('backtest/optimization') / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(serializable_report, f, indent=2)
        
        self.logger.info(f"📄 Report saved to: {output_path}")


