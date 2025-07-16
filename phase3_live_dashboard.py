#!/usr/bin/env python3
"""
PHASE 3 LIVE TRADING DASHBOARD
=============================

A simple command-line dashboard for monitoring live trading performance.

Features:
✅ Real-time performance monitoring
✅ Position tracking
✅ Signal history
✅ Risk metrics
✅ Alert system
"""

import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import logging

class LiveTradingDashboard:
    """Command-line dashboard for live trading monitoring"""
    
    def __init__(self, refresh_interval: int = 5):
        self.refresh_interval = refresh_interval
        self.running = False
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def format_currency(self, amount: float) -> str:
        """Format currency with color coding"""
        if amount > 0:
            return f"\033[92m${amount:,.2f}\033[0m"  # Green
        elif amount < 0:
            return f"\033[91m${amount:,.2f}\033[0m"  # Red
        else:
            return f"${amount:,.2f}"
    
    def format_percentage(self, pct: float) -> str:
        """Format percentage with color coding"""
        if pct > 0:
            return f"\033[92m{pct:+.2%}\033[0m"  # Green
        elif pct < 0:
            return f"\033[91m{pct:+.2%}\033[0m"  # Red
        else:
            return f"{pct:.2%}"
    
    def display_header(self):
        """Display dashboard header"""
        print("🚀 LIVE STATISTICAL ARBITRAGE TRADING DASHBOARD")
        print("=" * 60)
        print(f"⏰ Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def display_performance_summary(self, status: Dict):
        """Display performance summary"""
        print("📊 PERFORMANCE SUMMARY")
        print("-" * 30)
        
        initial = status.get('initial_capital', 0)
        current = status.get('current_capital', 0)
        unrealized = status.get('unrealized_pnl', 0)
        total = status.get('total_capital', 0)
        total_return = status.get('total_return', 0)
        
        print(f"Initial Capital:     {self.format_currency(initial)}")
        print(f"Current Capital:     {self.format_currency(current)}")
        print(f"Unrealized P&L:      {self.format_currency(unrealized)}")
        print(f"Total Capital:       {self.format_currency(total)}")
        print(f"Total Return:        {self.format_percentage(total_return)}")
        print()
    
    def display_positions(self, status: Dict):
        """Display current positions"""
        positions = status.get('positions', [])
        
        print(f"🔄 ACTIVE POSITIONS ({len(positions)})")
        print("-" * 30)
        
        if not positions:
            print("No active positions")
        else:
            for pos in positions:
                symbol_pair = f"{pos['symbol_pair'][0]}/{pos['symbol_pair'][1]}"
                pos_type = pos['position_type']
                unrealized = pos.get('unrealized_pnl', 0)
                size = pos.get('position_size', 0)
                entry_time = pos.get('entry_time', '')
                
                # Calculate holding time
                if entry_time:
                    try:
                        entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                        holding_time = datetime.now() - entry_dt.replace(tzinfo=None)
                        hours = holding_time.total_seconds() / 3600
                        time_str = f"{hours:.1f}h"
                    except:
                        time_str = "Unknown"
                else:
                    time_str = "Unknown"
                
                print(f"{symbol_pair:12} {pos_type:5} Size:{size:6.1%} "
                      f"P&L:{self.format_currency(unrealized):>12} Time:{time_str}")
        print()
    
    def display_recent_signals(self, status: Dict):
        """Display recent trading signals"""
        signals = status.get('recent_signals', [])
        
        print(f"🎯 RECENT SIGNALS ({len(signals)})")
        print("-" * 30)
        
        if not signals:
            print("No recent signals")
        else:
            for signal in signals[-5:]:  # Show last 5 signals
                symbol_pair = f"{signal['symbol_pair'][0]}/{signal['symbol_pair'][1]}"
                signal_type = signal['signal_type']
                confidence = signal.get('confidence', 0)
                z_score = signal.get('spread_z_score', 0)
                timestamp = signal.get('timestamp', '')
                
                # Format timestamp
                if timestamp:
                    try:
                        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = ts.strftime('%H:%M:%S')
                    except:
                        time_str = "Unknown"
                else:
                    time_str = "Unknown"
                
                print(f"{time_str} {symbol_pair:12} {signal_type:5} "
                      f"Conf:{confidence:5.2f} Z:{z_score:+6.2f}")
        print()
    
    def display_risk_metrics(self, status: Dict):
        """Display risk metrics"""
        print("⚠️  RISK METRICS")
        print("-" * 30)
        
        total_return = status.get('total_return', 0)
        num_positions = status.get('num_positions', 0)
        
        # Calculate some basic risk metrics
        if total_return < -0.05:
            drawdown_status = "🔴 High"
        elif total_return < -0.02:
            drawdown_status = "🟡 Medium"
        else:
            drawdown_status = "🟢 Low"
        
        if num_positions > 5:
            exposure_status = "🔴 High"
        elif num_positions > 2:
            exposure_status = "🟡 Medium"
        else:
            exposure_status = "🟢 Low"
        
        print(f"Drawdown Risk:       {drawdown_status}")
        print(f"Position Exposure:   {exposure_status}")
        print(f"Active Positions:    {num_positions}")
        print()
    
    def display_controls(self):
        """Display control instructions"""
        print("🎮 CONTROLS")
        print("-" * 30)
        print("Ctrl+C : Stop monitoring")
        print("Enter  : Force refresh")
        print()
    
    async def monitor_trading(self, status_file: str = "live_trading_status.json"):
        """Monitor live trading status"""
        
        self.running = True
        
        while self.running:
            try:
                self.clear_screen()
                
                # Load current status
                if os.path.exists(status_file):
                    with open(status_file, 'r') as f:
                        status = json.load(f)
                else:
                    # Mock status for testing
                    status = {
                        'timestamp': datetime.now().isoformat(),
                        'initial_capital': 1000000,
                        'current_capital': 1025000,
                        'unrealized_pnl': 5000,
                        'total_capital': 1030000,
                        'total_return': 0.03,
                        'num_positions': 2,
                        'positions': [
                            {
                                'symbol_pair': ['QQQ', 'TQQQ'],
                                'position_type': 'LONG',
                                'position_size': 0.08,
                                'unrealized_pnl': 3000,
                                'entry_time': (datetime.now() - timedelta(hours=2)).isoformat()
                            },
                            {
                                'symbol_pair': ['SPY', 'ARKK'],
                                'position_type': 'SHORT',
                                'position_size': 0.05,
                                'unrealized_pnl': 2000,
                                'entry_time': (datetime.now() - timedelta(minutes=45)).isoformat()
                            }
                        ],
                        'recent_signals': [
                            {
                                'symbol_pair': ['QQQ', 'TQQQ'],
                                'signal_type': 'LONG',
                                'confidence': 0.75,
                                'spread_z_score': -2.3,
                                'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat()
                            },
                            {
                                'symbol_pair': ['SPY', 'ARKK'],
                                'signal_type': 'SHORT',
                                'confidence': 0.68,
                                'spread_z_score': 2.1,
                                'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat()
                            }
                        ]
                    }
                
                # Display dashboard
                self.display_header()
                self.display_performance_summary(status)
                self.display_positions(status)
                self.display_recent_signals(status)
                self.display_risk_metrics(status)
                self.display_controls()
                
                # Check for alerts
                self.check_alerts(status)
                
                await asyncio.sleep(self.refresh_interval)
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"Dashboard error: {e}")
                await asyncio.sleep(5)
    
    def check_alerts(self, status: Dict):
        """Check for alert conditions"""
        alerts = []
        
        total_return = status.get('total_return', 0)
        num_positions = status.get('num_positions', 0)
        
        # Drawdown alert
        if total_return < -0.1:
            alerts.append("🚨 CRITICAL: Drawdown exceeds 10%")
        elif total_return < -0.05:
            alerts.append("⚠️  WARNING: Drawdown exceeds 5%")
        
        # Position count alert
        if num_positions > 5:
            alerts.append("⚠️  WARNING: High number of positions")
        
        # Profit alert
        if total_return > 0.2:
            alerts.append("🎉 SUCCESS: Return exceeds 20%")
        
        if alerts:
            print("🔔 ALERTS")
            print("-" * 30)
            for alert in alerts:
                print(alert)
            print()

def main():
    """Main dashboard function"""
    
    print("🚀 STARTING LIVE TRADING DASHBOARD")
    print("=" * 40)
    print("This dashboard will monitor your live trading performance.")
    print("Make sure the live trading system is running in another terminal.")
    print("\nPress Ctrl+C to exit at any time.")
    input("\nPress Enter to start monitoring...")
    
    dashboard = LiveTradingDashboard(refresh_interval=5)
    
    try:
        asyncio.run(dashboard.monitor_trading())
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard stopped")
    except Exception as e:
        print(f"\n\n❌ Dashboard error: {e}")

if __name__ == "__main__":
    main()
