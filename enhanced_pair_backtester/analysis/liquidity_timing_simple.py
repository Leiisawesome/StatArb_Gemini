import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum

class MarketSession(Enum):
    PRE_MARKET = "pre_market"
    OPENING = "opening"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    CLOSING = "closing"
    AFTER_HOURS = "after_hours"

@dataclass
class LiquidityWindow:
    """Optimal execution window"""
    start_time: time
    end_time: time
    expected_cost: float
    volume_score: float
    session: MarketSession
    confidence: float

class LiquidityTimingOptimizer:
    """
    Simplified liquidity timing optimizer for pair execution
    
    Focuses on practical execution timing optimization based on:
    - Market session analysis
    - Volume patterns
    - Volatility timing
    - Transaction cost optimization
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Market session definitions (ET)
        self.session_times = {
            MarketSession.PRE_MARKET: (time(4, 0), time(9, 30)),
            MarketSession.OPENING: (time(9, 30), time(10, 30)),
            MarketSession.MORNING: (time(10, 30), time(12, 0)),
            MarketSession.MIDDAY: (time(12, 0), time(14, 0)),
            MarketSession.AFTERNOON: (time(14, 0), time(15, 30)),
            MarketSession.CLOSING: (time(15, 30), time(16, 0)),
            MarketSession.AFTER_HOURS: (time(16, 0), time(20, 0))
        }
        
        # Historical liquidity patterns (based on market microstructure research)
        self.session_liquidity_scores = {
            MarketSession.PRE_MARKET: 0.8,    # Lower liquidity
            MarketSession.OPENING: 0.6,       # High volatility, moderate liquidity
            MarketSession.MORNING: 0.9,       # Best liquidity
            MarketSession.MIDDAY: 0.7,        # Lunch hour effects
            MarketSession.AFTERNOON: 0.85,    # Good liquidity
            MarketSession.CLOSING: 0.5,       # High volatility, variable liquidity
            MarketSession.AFTER_HOURS: 0.3    # Lowest liquidity
        }
        
        # Day-of-week effects (Monday=0, Friday=4)
        self.day_of_week_adjustments = {
            0: 0.95,  # Monday - slightly lower liquidity
            1: 1.0,   # Tuesday - baseline
            2: 1.05,  # Wednesday - peak liquidity
            3: 1.0,   # Thursday - baseline
            4: 0.9    # Friday - lower liquidity
        }
        
    def classify_session(self, timestamp: datetime) -> MarketSession:
        """Classify timestamp into market session"""
        time_only = timestamp.time()
        
        for session, (start, end) in self.session_times.items():
            if start <= time_only < end:
                return session
        
        return MarketSession.AFTER_HOURS
    
    def calculate_execution_cost(self, 
                               timestamp: datetime,
                               trade_size: float,
                               volatility: float = 0.02) -> float:
        """Calculate expected execution cost for a trade"""
        session = self.classify_session(timestamp)
        day_of_week = timestamp.weekday()
        
        # Base cost components
        base_spread = 0.0005  # 5 bps base spread
        
        # Session-based cost adjustments
        session_multiplier = {
            MarketSession.PRE_MARKET: 2.0,
            MarketSession.OPENING: 1.5,
            MarketSession.MORNING: 1.0,
            MarketSession.MIDDAY: 1.2,
            MarketSession.AFTERNOON: 1.0,
            MarketSession.CLOSING: 1.8,
            MarketSession.AFTER_HOURS: 3.0
        }
        
        # Market impact (square root law)
        market_impact = volatility * 0.1 * np.sqrt(trade_size / 100000)
        
        # Day-of-week adjustment
        day_adjustment = self.day_of_week_adjustments.get(day_of_week, 1.0)
        
        # Total cost
        spread_cost = base_spread * session_multiplier[session] * day_adjustment
        total_cost = spread_cost + market_impact
        
        return total_cost
    
    def find_optimal_execution_windows(self, 
                                     trade_date: datetime,
                                     trade_size: float = 100000,
                                     volatility: float = 0.02) -> List[LiquidityWindow]:
        """Find optimal execution windows for a given date"""
        windows = []
        
        # Define candidate time windows (15-minute intervals during market hours)
        market_start = time(9, 30)
        market_end = time(16, 0)
        
        current_time = datetime.combine(trade_date.date(), market_start)
        end_time = datetime.combine(trade_date.date(), market_end)
        
        while current_time < end_time:
            window_end = current_time + timedelta(minutes=15)
            
            # Calculate cost for this window
            cost = self.calculate_execution_cost(current_time, trade_size, volatility)
            session = self.classify_session(current_time)
            
            # Volume score (higher is better)
            volume_score = self.session_liquidity_scores[session]
            day_adjustment = self.day_of_week_adjustments.get(current_time.weekday(), 1.0)
            volume_score *= day_adjustment
            
            # Confidence based on session stability
            confidence = {
                MarketSession.OPENING: 0.7,
                MarketSession.MORNING: 0.95,
                MarketSession.MIDDAY: 0.8,
                MarketSession.AFTERNOON: 0.9,
                MarketSession.CLOSING: 0.6
            }.get(session, 0.5)
            
            windows.append(LiquidityWindow(
                start_time=current_time.time(),
                end_time=window_end.time(),
                expected_cost=cost,
                volume_score=volume_score,
                session=session,
                confidence=confidence
            ))
            
            current_time = window_end
        
        # Sort by expected cost (lower is better)
        windows.sort(key=lambda w: w.expected_cost)
        
        return windows
    
    def get_best_execution_times(self, 
                               trade_date: datetime,
                               trade_size: float = 100000,
                               volatility: float = 0.02,
                               top_n: int = 3) -> List[LiquidityWindow]:
        """Get top N best execution times"""
        windows = self.find_optimal_execution_windows(trade_date, trade_size, volatility)
        return windows[:top_n]
    
    def optimize_pair_execution_timing(self, 
                                     trade_date: datetime,
                                     long_size: float,
                                     short_size: float,
                                     volatility_long: float = 0.02,
                                     volatility_short: float = 0.02) -> Dict:
        """Optimize execution timing for a pair trade"""
        
        # Find optimal windows for both legs
        long_windows = self.find_optimal_execution_windows(
            trade_date, long_size, volatility_long
        )
        short_windows = self.find_optimal_execution_windows(
            trade_date, short_size, volatility_short
        )
        
        # Find overlapping optimal windows
        optimal_pairs = []
        
        for long_window in long_windows[:5]:  # Top 5 for long leg
            for short_window in short_windows[:5]:  # Top 5 for short leg
                # Check if windows overlap or are close
                time_diff = abs(
                    datetime.combine(trade_date.date(), long_window.start_time) -
                    datetime.combine(trade_date.date(), short_window.start_time)
                ).total_seconds() / 60  # Minutes
                
                if time_diff <= 15:  # Within 15 minutes
                    combined_cost = long_window.expected_cost + short_window.expected_cost
                    combined_confidence = min(long_window.confidence, short_window.confidence)
                    
                    optimal_pairs.append({
                        'execution_time': min(long_window.start_time, short_window.start_time),
                        'long_window': long_window,
                        'short_window': short_window,
                        'combined_cost': combined_cost,
                        'combined_confidence': combined_confidence,
                        'time_diff_minutes': time_diff
                    })
        
        # Sort by combined cost
        optimal_pairs.sort(key=lambda x: x['combined_cost'])
        
        return {
            'optimal_pairs': optimal_pairs[:3],
            'best_execution_time': optimal_pairs[0]['execution_time'] if optimal_pairs else None,
            'expected_total_cost': optimal_pairs[0]['combined_cost'] if optimal_pairs else None
        }
    
    def generate_execution_schedule(self, 
                                  trade_date: datetime,
                                  total_quantity: float,
                                  max_slice_size: float = 50000,
                                  volatility: float = 0.02) -> List[Dict]:
        """Generate execution schedule for large orders"""
        
        if total_quantity <= max_slice_size:
            # Single execution
            best_windows = self.get_best_execution_times(trade_date, total_quantity, volatility, 1)
            return [{
                'execution_time': best_windows[0].start_time,
                'quantity': total_quantity,
                'expected_cost': best_windows[0].expected_cost,
                'session': best_windows[0].session.value
            }] if best_windows else []
        
        # Multiple executions
        num_slices = int(np.ceil(total_quantity / max_slice_size))
        slice_size = total_quantity / num_slices
        
        # Get best windows
        best_windows = self.get_best_execution_times(
            trade_date, slice_size, volatility, num_slices
        )
        
        schedule = []
        for i, window in enumerate(best_windows):
            quantity = slice_size if i < num_slices - 1 else total_quantity - (slice_size * i)
            
            schedule.append({
                'execution_time': window.start_time,
                'quantity': quantity,
                'expected_cost': window.expected_cost,
                'session': window.session.value,
                'confidence': window.confidence
            })
        
        return schedule
    
    def analyze_timing_impact(self, 
                            trade_date: datetime,
                            trade_size: float = 100000,
                            volatility: float = 0.02) -> Dict:
        """Analyze timing impact across different execution times"""
        
        windows = self.find_optimal_execution_windows(trade_date, trade_size, volatility)
        
        # Calculate statistics
        costs = [w.expected_cost for w in windows]
        best_cost = min(costs)
        worst_cost = max(costs)
        avg_cost = np.mean(costs)
        
        # Session analysis
        session_costs = {}
        for window in windows:
            session = window.session.value
            if session not in session_costs:
                session_costs[session] = []
            session_costs[session].append(window.expected_cost)
        
        session_summary = {
            session: {
                'avg_cost': np.mean(costs),
                'min_cost': min(costs),
                'max_cost': max(costs),
                'cost_bps': np.mean(costs) * 10000
            }
            for session, costs in session_costs.items()
        }
        
        return {
            'best_cost_bps': best_cost * 10000,
            'worst_cost_bps': worst_cost * 10000,
            'avg_cost_bps': avg_cost * 10000,
            'timing_impact_bps': (worst_cost - best_cost) * 10000,
            'session_analysis': session_summary,
            'optimal_sessions': sorted(session_summary.keys(), 
                                     key=lambda s: session_summary[s]['avg_cost'])[:2]
        }
    
    def generate_timing_report(self, 
                             trade_date: datetime,
                             trade_size: float = 100000,
                             volatility: float = 0.02) -> str:
        """Generate comprehensive timing analysis report"""
        
        analysis = self.analyze_timing_impact(trade_date, trade_size, volatility)
        best_windows = self.get_best_execution_times(trade_date, trade_size, volatility, 3)
        
        report = f"""
=== LIQUIDITY TIMING ANALYSIS ===
Date: {trade_date.strftime('%Y-%m-%d')} ({trade_date.strftime('%A')})
Trade Size: ${trade_size:,.0f}
Volatility: {volatility:.2%}

=== TIMING IMPACT ANALYSIS ===
Best Execution Cost: {analysis['best_cost_bps']:.1f} bps
Worst Execution Cost: {analysis['worst_cost_bps']:.1f} bps
Average Cost: {analysis['avg_cost_bps']:.1f} bps
Timing Impact: {analysis['timing_impact_bps']:.1f} bps

=== OPTIMAL EXECUTION WINDOWS ===
"""
        
        for i, window in enumerate(best_windows, 1):
            report += f"""
Window {i}:
  Time: {window.start_time.strftime('%H:%M')} - {window.end_time.strftime('%H:%M')}
  Session: {window.session.value.replace('_', ' ').title()}
  Expected Cost: {window.expected_cost * 10000:.1f} bps
  Volume Score: {window.volume_score:.2f}
  Confidence: {window.confidence:.2f}
"""
        
        report += "\n=== SESSION ANALYSIS ===\n"
        for session in analysis['optimal_sessions']:
            session_data = analysis['session_analysis'][session]
            report += f"""
{session.replace('_', ' ').title()}:
  Average Cost: {session_data['cost_bps']:.1f} bps
  Cost Range: {session_data['min_cost']*10000:.1f} - {session_data['max_cost']*10000:.1f} bps
"""
        
        return report

# Integration with existing system
class LiquidityTimingIntegrator:
    """Integrates liquidity timing with existing execution system"""
    
    def __init__(self):
        self.optimizer = LiquidityTimingOptimizer()
        self.logger = logging.getLogger(__name__)
    
    def enhance_execution_decision(self, 
                                 timestamp: datetime,
                                 trade_size: float,
                                 volatility: float = 0.02) -> Dict:
        """Enhance execution decision with timing analysis"""
        
        # Get current session
        session = self.optimizer.classify_session(timestamp)
        
        # Calculate execution cost
        current_cost = self.optimizer.calculate_execution_cost(
            timestamp, trade_size, volatility
        )
        
        # Find better alternatives
        best_windows = self.optimizer.get_best_execution_times(
            timestamp, trade_size, volatility, 3
        )
        
        # Timing recommendation
        if best_windows:
            best_cost = best_windows[0].expected_cost
            potential_savings = (current_cost - best_cost) * 10000  # bps
            
            recommendation = "EXECUTE_NOW" if potential_savings < 1.0 else "DELAY"
            
            return {
                'current_cost_bps': current_cost * 10000,
                'optimal_cost_bps': best_cost * 10000,
                'potential_savings_bps': potential_savings,
                'recommendation': recommendation,
                'current_session': session.value,
                'optimal_time': best_windows[0].start_time,
                'confidence': best_windows[0].confidence
            }
        
        return {
            'current_cost_bps': current_cost * 10000,
            'recommendation': "EXECUTE_NOW",
            'current_session': session.value,
            'confidence': 0.5
        }

# Example usage
if __name__ == "__main__":
    optimizer = LiquidityTimingOptimizer()
    
    # Test with sample date
    test_date = datetime(2024, 1, 15)  # Monday
    
    # Generate timing report
    report = optimizer.generate_timing_report(test_date, 100000, 0.025)
    print(report)
    
    # Test pair execution optimization
    pair_result = optimizer.optimize_pair_execution_timing(
        test_date, 100000, 100000, 0.025, 0.025
    )
    
    print("\n=== PAIR EXECUTION OPTIMIZATION ===")
    if pair_result['optimal_pairs']:
        best_pair = pair_result['optimal_pairs'][0]
        print(f"Best Execution Time: {best_pair['execution_time']}")
        print(f"Combined Cost: {best_pair['combined_cost']*10000:.1f} bps")
        print(f"Confidence: {best_pair['combined_confidence']:.2f}") 