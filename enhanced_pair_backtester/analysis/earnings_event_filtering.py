#!/usr/bin/env python3
"""
Earnings Event Filtering and Risk Management System
Integrates earnings calendar data and provides event-driven risk management for pairs trading
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Set
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import warnings
import yfinance as yf
import requests
from concurrent.futures import ThreadPoolExecutor
import json
import re
warnings.filterwarnings('ignore')

class EarningsEventType(Enum):
    """Types of earnings events"""
    EARNINGS_ANNOUNCEMENT = "Earnings Announcement"
    GUIDANCE_UPDATE = "Guidance Update"
    CONFERENCE_CALL = "Conference Call"
    ANALYST_DAY = "Analyst Day"
    DIVIDEND_ANNOUNCEMENT = "Dividend Announcement"
    SPECIAL_EVENT = "Special Event"

class EarningsImpactLevel(Enum):
    """Expected impact levels for earnings events"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    EXTREME = "Extreme"

class RiskAction(Enum):
    """Risk management actions"""
    MONITOR = "Monitor"
    REDUCE_POSITION = "Reduce Position"
    HEDGE_POSITION = "Hedge Position"
    CLOSE_POSITION = "Close Position"
    AVOID_ENTRY = "Avoid Entry"

@dataclass
class EarningsEvent:
    """Individual earnings event data"""
    symbol: str
    date: datetime
    event_type: EarningsEventType
    time_of_day: str  # "BMO" (before market open), "AMC" (after market close), "DMT" (during market)
    eps_estimate: Optional[float]
    eps_actual: Optional[float]
    revenue_estimate: Optional[float]
    revenue_actual: Optional[float]
    surprise_percent: Optional[float]
    impact_level: EarningsImpactLevel
    confidence: float
    
@dataclass
class PairEarningsRisk:
    """Earnings risk assessment for a trading pair"""
    pair: Tuple[str, str]
    upcoming_events: List[EarningsEvent]
    days_to_next_event: int
    risk_level: EarningsImpactLevel
    recommended_action: RiskAction
    position_adjustment: float  # Multiplier for position size (0.0 to 1.0)
    hedge_ratio: Optional[float]
    monitoring_period: int  # Days to monitor around event
    
@dataclass
class EarningsCalendar:
    """Comprehensive earnings calendar"""
    events: List[EarningsEvent]
    last_updated: datetime
    data_source: str
    coverage_period: Tuple[datetime, datetime]
    
class EarningsDataProvider:
    """Base class for earnings data providers"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_earnings_calendar(self, symbols: List[str], 
                            start_date: datetime, 
                            end_date: datetime) -> EarningsCalendar:
        """Get earnings calendar for symbols"""
        raise NotImplementedError
        
class YahooFinanceEarningsProvider(EarningsDataProvider):
    """Yahoo Finance earnings data provider"""
    
    def get_earnings_calendar(self, symbols: List[str], 
                            start_date: datetime, 
                            end_date: datetime) -> EarningsCalendar:
        """Get earnings calendar from Yahoo Finance"""
        
        events = []
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                
                # Get earnings calendar
                calendar = ticker.calendar
                
                if calendar is not None and not calendar.empty:
                    for index, row in calendar.iterrows():
                        event_date = pd.to_datetime(index).to_pydatetime()
                        
                        if start_date <= event_date <= end_date:
                            event = EarningsEvent(
                                symbol=symbol,
                                date=event_date,
                                event_type=EarningsEventType.EARNINGS_ANNOUNCEMENT,
                                time_of_day="Unknown",
                                eps_estimate=row.get('Earnings Estimate', None),
                                eps_actual=None,
                                revenue_estimate=row.get('Revenue Estimate', None),
                                revenue_actual=None,
                                surprise_percent=None,
                                impact_level=EarningsImpactLevel.MEDIUM,
                                confidence=0.7
                            )
                            events.append(event)
                
                # Get earnings history for impact assessment
                earnings_history = ticker.earnings_dates
                
                if earnings_history is not None and not earnings_history.empty:
                    # Use historical data to assess impact levels
                    for index, row in earnings_history.tail(4).iterrows():  # Last 4 quarters
                        event_date = pd.to_datetime(index).to_pydatetime()
                        
                        if start_date <= event_date <= end_date:
                            surprise = row.get('Surprise(%)', 0)
                            
                            # Determine impact level based on surprise
                            if abs(surprise) > 20:
                                impact_level = EarningsImpactLevel.EXTREME
                            elif abs(surprise) > 10:
                                impact_level = EarningsImpactLevel.HIGH
                            elif abs(surprise) > 5:
                                impact_level = EarningsImpactLevel.MEDIUM
                            else:
                                impact_level = EarningsImpactLevel.LOW
                            
                            event = EarningsEvent(
                                symbol=symbol,
                                date=event_date,
                                event_type=EarningsEventType.EARNINGS_ANNOUNCEMENT,
                                time_of_day=row.get('Time', 'Unknown'),
                                eps_estimate=row.get('EPS Estimate', None),
                                eps_actual=row.get('Reported EPS', None),
                                revenue_estimate=None,
                                revenue_actual=None,
                                surprise_percent=surprise,
                                impact_level=impact_level,
                                confidence=0.8
                            )
                            
                            # Only add if not already present
                            if not any(e.symbol == symbol and e.date.date() == event_date.date() for e in events):
                                events.append(event)
                            
            except Exception as e:
                self.logger.warning(f"Failed to get earnings data for {symbol}: {e}")
                
                # Create default event for risk management
                next_earnings = start_date + timedelta(days=90)  # Assume quarterly
                if next_earnings <= end_date:
                    event = EarningsEvent(
                        symbol=symbol,
                        date=next_earnings,
                        event_type=EarningsEventType.EARNINGS_ANNOUNCEMENT,
                        time_of_day="Unknown",
                        eps_estimate=None,
                        eps_actual=None,
                        revenue_estimate=None,
                        revenue_actual=None,
                        surprise_percent=None,
                        impact_level=EarningsImpactLevel.MEDIUM,
                        confidence=0.5
                    )
                    events.append(event)
        
        return EarningsCalendar(
            events=events,
            last_updated=datetime.now(),
            data_source="Yahoo Finance",
            coverage_period=(start_date, end_date)
        )

class MockEarningsProvider(EarningsDataProvider):
    """Mock earnings provider for testing"""
    
    def get_earnings_calendar(self, symbols: List[str], 
                            start_date: datetime, 
                            end_date: datetime) -> EarningsCalendar:
        """Generate mock earnings calendar"""
        
        events = []
        
        for symbol in symbols:
            # Generate realistic earnings dates (quarterly)
            current_date = start_date
            
            while current_date <= end_date:
                # Add some randomness to dates
                earnings_date = current_date + timedelta(days=np.random.randint(0, 30))
                
                if earnings_date <= end_date:
                    # Generate realistic event
                    surprise = np.random.normal(0, 10)  # Mean 0, std 10%
                    
                    if abs(surprise) > 15:
                        impact_level = EarningsImpactLevel.EXTREME
                    elif abs(surprise) > 8:
                        impact_level = EarningsImpactLevel.HIGH
                    elif abs(surprise) > 3:
                        impact_level = EarningsImpactLevel.MEDIUM
                    else:
                        impact_level = EarningsImpactLevel.LOW
                    
                    event = EarningsEvent(
                        symbol=symbol,
                        date=earnings_date,
                        event_type=EarningsEventType.EARNINGS_ANNOUNCEMENT,
                        time_of_day=np.random.choice(["BMO", "AMC", "DMT"]),
                        eps_estimate=np.random.uniform(0.5, 3.0),
                        eps_actual=None,
                        revenue_estimate=np.random.uniform(1000, 10000),
                        revenue_actual=None,
                        surprise_percent=surprise,
                        impact_level=impact_level,
                        confidence=0.8
                    )
                    
                    events.append(event)
                
                # Move to next quarter
                current_date += timedelta(days=90)
        
        return EarningsCalendar(
            events=events,
            last_updated=datetime.now(),
            data_source="Mock Provider",
            coverage_period=(start_date, end_date)
        )

class EarningsEventFilter:
    """
    Comprehensive earnings event filtering and risk management system
    
    Features:
    - Earnings calendar integration
    - Event impact assessment
    - Pair-specific risk analysis
    - Automated risk controls
    - Position sizing adjustments
    - Hedging recommendations
    """
    
    def __init__(self, data_provider: Optional[EarningsDataProvider] = None):
        self.data_provider = data_provider or MockEarningsProvider()
        self.logger = logging.getLogger(__name__)
        
        # Risk parameters
        self.risk_windows = {
            EarningsImpactLevel.LOW: 2,      # 2 days around event
            EarningsImpactLevel.MEDIUM: 3,   # 3 days around event
            EarningsImpactLevel.HIGH: 5,     # 5 days around event
            EarningsImpactLevel.EXTREME: 7   # 7 days around event
        }
        
        self.position_adjustments = {
            EarningsImpactLevel.LOW: 0.9,      # 10% reduction
            EarningsImpactLevel.MEDIUM: 0.7,   # 30% reduction
            EarningsImpactLevel.HIGH: 0.5,     # 50% reduction
            EarningsImpactLevel.EXTREME: 0.2   # 80% reduction
        }
        
        # Cache for earnings data
        self.earnings_cache = {}
        
    def get_earnings_calendar(self, symbols: List[str], 
                            start_date: datetime, 
                            end_date: datetime) -> EarningsCalendar:
        """Get earnings calendar with caching"""
        
        cache_key = f"{'-'.join(sorted(symbols))}_{start_date.date()}_{end_date.date()}"
        
        if cache_key in self.earnings_cache:
            cached_calendar = self.earnings_cache[cache_key]
            # Check if cache is still valid (within 24 hours)
            if (datetime.now() - cached_calendar.last_updated).total_seconds() < 86400:
                return cached_calendar
        
        # Get fresh data
        calendar = self.data_provider.get_earnings_calendar(symbols, start_date, end_date)
        self.earnings_cache[cache_key] = calendar
        
        return calendar
    
    def assess_earnings_impact(self, event: EarningsEvent, 
                             historical_data: Optional[pd.DataFrame] = None) -> EarningsImpactLevel:
        """Assess expected impact of earnings event"""
        
        # If we have historical data, use it for better assessment
        if historical_data is not None and event.symbol in historical_data.columns:
            symbol_data = historical_data[event.symbol]
            
            # Calculate historical volatility around earnings
            returns = symbol_data.pct_change().dropna()
            
            # Look for patterns around similar dates (quarterly earnings)
            earnings_vol = returns.rolling(window=5).std().mean()
            normal_vol = returns.rolling(window=21).std().mean()
            
            vol_ratio = earnings_vol / normal_vol if normal_vol > 0 else 1.0
            
            # Adjust impact based on volatility
            if vol_ratio > 2.0:
                return EarningsImpactLevel.EXTREME
            elif vol_ratio > 1.5:
                return EarningsImpactLevel.HIGH
            elif vol_ratio > 1.2:
                return EarningsImpactLevel.MEDIUM
            else:
                return EarningsImpactLevel.LOW
        
        # Default to event's impact level
        return event.impact_level
    
    def analyze_pair_earnings_risk(self, pair: Tuple[str, str], 
                                 calendar: EarningsCalendar,
                                 current_date: datetime) -> PairEarningsRisk:
        """Analyze earnings risk for a specific pair"""
        
        symbol1, symbol2 = pair
        
        # Get upcoming events for both symbols
        upcoming_events = []
        for event in calendar.events:
            if event.symbol in [symbol1, symbol2] and event.date >= current_date:
                upcoming_events.append(event)
        
        # Sort by date
        upcoming_events.sort(key=lambda x: x.date)
        
        if not upcoming_events:
            # No upcoming events - low risk
            return PairEarningsRisk(
                pair=pair,
                upcoming_events=[],
                days_to_next_event=999,
                risk_level=EarningsImpactLevel.LOW,
                recommended_action=RiskAction.MONITOR,
                position_adjustment=1.0,
                hedge_ratio=None,
                monitoring_period=0
            )
        
        # Find next event
        next_event = upcoming_events[0]
        days_to_next = (next_event.date - current_date).days
        
        # Determine overall risk level
        risk_level = self._calculate_pair_risk_level(upcoming_events, current_date)
        
        # Generate recommendations
        recommended_action = self._generate_risk_action(risk_level, days_to_next)
        position_adjustment = self._calculate_position_adjustment(risk_level, days_to_next)
        hedge_ratio = self._calculate_hedge_ratio(pair, upcoming_events, current_date)
        monitoring_period = self.risk_windows[risk_level]
        
        return PairEarningsRisk(
            pair=pair,
            upcoming_events=upcoming_events,
            days_to_next_event=days_to_next,
            risk_level=risk_level,
            recommended_action=recommended_action,
            position_adjustment=position_adjustment,
            hedge_ratio=hedge_ratio,
            monitoring_period=monitoring_period
        )
    
    def _calculate_pair_risk_level(self, events: List[EarningsEvent], 
                                 current_date: datetime) -> EarningsImpactLevel:
        """Calculate overall risk level for pair"""
        
        if not events:
            return EarningsImpactLevel.LOW
        
        # Find events within next 7 days
        near_events = [e for e in events if (e.date - current_date).days <= 7]
        
        if not near_events:
            return EarningsImpactLevel.LOW
        
        # Get maximum impact level
        max_impact = max(e.impact_level for e in near_events)
        
        # Check if both symbols have events close together
        symbols_with_events = set(e.symbol for e in near_events)
        
        if len(symbols_with_events) > 1:
            # Both symbols have events - increase risk
            impact_levels = [EarningsImpactLevel.LOW, EarningsImpactLevel.MEDIUM, 
                           EarningsImpactLevel.HIGH, EarningsImpactLevel.EXTREME]
            
            current_index = impact_levels.index(max_impact)
            if current_index < len(impact_levels) - 1:
                return impact_levels[current_index + 1]
        
        return max_impact
    
    def _generate_risk_action(self, risk_level: EarningsImpactLevel, 
                            days_to_event: int) -> RiskAction:
        """Generate recommended risk action"""
        
        if days_to_event > 7:
            return RiskAction.MONITOR
        
        if risk_level == EarningsImpactLevel.LOW:
            return RiskAction.MONITOR
        elif risk_level == EarningsImpactLevel.MEDIUM:
            if days_to_event <= 2:
                return RiskAction.REDUCE_POSITION
            else:
                return RiskAction.MONITOR
        elif risk_level == EarningsImpactLevel.HIGH:
            if days_to_event <= 3:
                return RiskAction.HEDGE_POSITION
            else:
                return RiskAction.REDUCE_POSITION
        else:  # EXTREME
            if days_to_event <= 2:
                return RiskAction.CLOSE_POSITION
            else:
                return RiskAction.HEDGE_POSITION
    
    def _calculate_position_adjustment(self, risk_level: EarningsImpactLevel, 
                                     days_to_event: int) -> float:
        """Calculate position size adjustment"""
        
        base_adjustment = self.position_adjustments[risk_level]
        
        # Adjust based on time to event
        if days_to_event <= 1:
            return base_adjustment * 0.5  # More aggressive reduction
        elif days_to_event <= 3:
            return base_adjustment * 0.7
        elif days_to_event <= 7:
            return base_adjustment
        else:
            return 1.0  # No adjustment
    
    def _calculate_hedge_ratio(self, pair: Tuple[str, str], 
                             events: List[EarningsEvent], 
                             current_date: datetime) -> Optional[float]:
        """Calculate hedge ratio for pair"""
        
        symbol1, symbol2 = pair
        
        # Check which symbol has earnings
        symbol1_events = [e for e in events if e.symbol == symbol1 and (e.date - current_date).days <= 7]
        symbol2_events = [e for e in events if e.symbol == symbol2 and (e.date - current_date).days <= 7]
        
        if symbol1_events and not symbol2_events:
            # Symbol1 has earnings - hedge with symbol2
            return 0.8  # 80% hedge ratio
        elif symbol2_events and not symbol1_events:
            # Symbol2 has earnings - hedge with symbol1
            return 0.8
        elif symbol1_events and symbol2_events:
            # Both have earnings - no hedge recommended
            return None
        else:
            # No near-term events
            return None
    
    def filter_pairs_by_earnings(self, pairs: List[Tuple[str, str]], 
                               current_date: datetime,
                               lookforward_days: int = 30) -> Dict[str, PairEarningsRisk]:
        """Filter pairs based on earnings events"""
        
        self.logger.info(f"Filtering {len(pairs)} pairs for earnings events")
        
        # Get all symbols
        all_symbols = set()
        for pair in pairs:
            all_symbols.update(pair)
        
        # Get earnings calendar
        end_date = current_date + timedelta(days=lookforward_days)
        calendar = self.get_earnings_calendar(list(all_symbols), current_date, end_date)
        
        # Analyze each pair
        pair_risks = {}
        
        for pair in pairs:
            try:
                risk_analysis = self.analyze_pair_earnings_risk(pair, calendar, current_date)
                pair_key = f"{pair[0]}_{pair[1]}"
                pair_risks[pair_key] = risk_analysis
                
            except Exception as e:
                self.logger.warning(f"Error analyzing pair {pair}: {e}")
                continue
        
        return pair_risks
    
    def generate_earnings_alerts(self, pair_risks: Dict[str, PairEarningsRisk]) -> List[Dict[str, any]]:
        """Generate earnings-based alerts"""
        
        alerts = []
        
        for pair_key, risk in pair_risks.items():
            if risk.recommended_action != RiskAction.MONITOR:
                alert = {
                    'pair': f"{risk.pair[0]}/{risk.pair[1]}",
                    'alert_type': 'EARNINGS_RISK',
                    'risk_level': risk.risk_level.value,
                    'days_to_event': risk.days_to_next_event,
                    'recommended_action': risk.recommended_action.value,
                    'position_adjustment': risk.position_adjustment,
                    'message': self._generate_alert_message(risk),
                    'timestamp': datetime.now()
                }
                alerts.append(alert)
        
        return alerts
    
    def _generate_alert_message(self, risk: PairEarningsRisk) -> str:
        """Generate alert message"""
        
        pair_str = f"{risk.pair[0]}/{risk.pair[1]}"
        
        if risk.days_to_next_event <= 1:
            time_str = "TODAY"
        elif risk.days_to_next_event <= 2:
            time_str = "TOMORROW"
        else:
            time_str = f"in {risk.days_to_next_event} days"
        
        if risk.upcoming_events:
            symbols_with_events = set(e.symbol for e in risk.upcoming_events if (e.date - datetime.now()).days <= 7)
            symbols_str = ", ".join(symbols_with_events)
        else:
            symbols_str = "unknown"
        
        return f"EARNINGS ALERT: {pair_str} - {symbols_str} earnings {time_str}. " \
               f"Risk level: {risk.risk_level.value}. " \
               f"Recommended action: {risk.recommended_action.value}. " \
               f"Position adjustment: {risk.position_adjustment:.0%}"
    
    def run_earnings_risk_analysis(self, pairs: List[Tuple[str, str]], 
                                 current_date: Optional[datetime] = None) -> Dict[str, any]:
        """Run comprehensive earnings risk analysis"""
        
        if current_date is None:
            current_date = datetime.now()
        
        self.logger.info(f"Running earnings risk analysis for {len(pairs)} pairs")
        
        # Filter pairs by earnings
        pair_risks = self.filter_pairs_by_earnings(pairs, current_date)
        
        # Generate alerts
        alerts = self.generate_earnings_alerts(pair_risks)
        
        # Generate summary statistics
        summary = self._generate_earnings_summary(pair_risks, alerts)
        
        return {
            'pair_risks': pair_risks,
            'alerts': alerts,
            'summary': summary,
            'analysis_date': current_date,
            'total_pairs': len(pairs)
        }
    
    def _generate_earnings_summary(self, pair_risks: Dict[str, PairEarningsRisk], 
                                 alerts: List[Dict[str, any]]) -> Dict[str, any]:
        """Generate earnings analysis summary"""
        
        if not pair_risks:
            return {'error': 'No pair risks available'}
        
        risks = list(pair_risks.values())
        
        # Risk level distribution
        risk_levels = [r.risk_level for r in risks]
        risk_distribution = {
            level.value: sum(1 for r in risk_levels if r == level)
            for level in EarningsImpactLevel
        }
        
        # Action distribution
        actions = [r.recommended_action for r in risks]
        action_distribution = {
            action.value: sum(1 for a in actions if a == action)
            for action in RiskAction
        }
        
        # Days to next event statistics
        days_to_events = [r.days_to_next_event for r in risks if r.days_to_next_event < 999]
        
        # Position adjustment statistics
        adjustments = [r.position_adjustment for r in risks]
        
        return {
            'total_pairs_analyzed': len(risks),
            'pairs_with_upcoming_events': len(days_to_events),
            'risk_level_distribution': risk_distribution,
            'action_distribution': action_distribution,
            'alerts_generated': len(alerts),
            'average_days_to_event': np.mean(days_to_events) if days_to_events else 0,
            'min_days_to_event': min(days_to_events) if days_to_events else 0,
            'average_position_adjustment': np.mean(adjustments),
            'pairs_requiring_action': len([r for r in risks if r.recommended_action != RiskAction.MONITOR]),
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def generate_earnings_report(self, analysis_results: Dict[str, any]) -> str:
        """Generate comprehensive earnings risk report"""
        
        report = f"""
=== EARNINGS EVENT RISK ANALYSIS REPORT ===

Analysis Date: {analysis_results['analysis_date'].strftime('%Y-%m-%d %H:%M:%S')}

EXECUTIVE SUMMARY:
- Total Pairs Analyzed: {analysis_results['total_pairs']}
- Pairs with Upcoming Events: {analysis_results['summary']['pairs_with_upcoming_events']}
- Alerts Generated: {analysis_results['summary']['alerts_generated']}
- Pairs Requiring Action: {analysis_results['summary']['pairs_requiring_action']}
- Average Days to Next Event: {analysis_results['summary']['average_days_to_event']:.1f}
- Average Position Adjustment: {analysis_results['summary']['average_position_adjustment']:.1%}

RISK LEVEL DISTRIBUTION:
"""
        
        for level, count in analysis_results['summary']['risk_level_distribution'].items():
            report += f"  {level}: {count} pairs\n"
        
        report += f"""
RECOMMENDED ACTIONS:
"""
        
        for action, count in analysis_results['summary']['action_distribution'].items():
            report += f"  {action}: {count} pairs\n"
        
        if analysis_results['alerts']:
            report += f"""
ACTIVE ALERTS:
"""
            for alert in analysis_results['alerts'][:10]:  # Top 10 alerts
                report += f"  {alert['message']}\n"
        
        report += f"""
DETAILED PAIR ANALYSIS:
"""
        
        for pair_key, risk in list(analysis_results['pair_risks'].items())[:10]:  # Top 10
            report += f"""
Pair: {risk.pair[0]}/{risk.pair[1]}
  Risk Level: {risk.risk_level.value}
  Days to Next Event: {risk.days_to_next_event}
  Recommended Action: {risk.recommended_action.value}
  Position Adjustment: {risk.position_adjustment:.1%}
  Monitoring Period: {risk.monitoring_period} days
"""
            
            if risk.upcoming_events:
                report += f"  Upcoming Events:\n"
                for event in risk.upcoming_events[:3]:  # Top 3 events
                    report += f"    {event.symbol}: {event.date.strftime('%Y-%m-%d')} ({event.event_type.value})\n"
        
        return report 