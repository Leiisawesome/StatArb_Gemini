"""
Risk scoring, neutrality checks, and other diagnostic tools.
"""
import pandas as pd
import matplotlib.pyplot as plt
from structs import Config

def run_diagnostics(trade_log: pd.DataFrame, config: Config):
    """Runs diagnostic checks on the trading performance."""
    if trade_log.empty:
        return
        
    print("\n--- Strategy Diagnostics ---")
    
    # Trade Type Distribution
    trade_types = trade_log['type'].value_counts()
    print("Trade Type Distribution:")
    print(trade_types)
    
    # Average PnL by Trade Type
    avg_pnl_by_type = trade_log.groupby('type')['pnl'].mean()
    print("\nAverage PnL by Trade Type:")
    print(avg_pnl_by_type.to_string(float_format="%.2f"))
    
    # Trade Duration Analysis
    trade_log['duration'] = pd.to_datetime(trade_log['exit_date']) - pd.to_datetime(trade_log['entry_date'])
    avg_duration_in_minutes = trade_log['duration'].mean().total_seconds() / 60
    
    bar_interval_minutes = int(config.data_interval[:-1]) if 'm' in config.data_interval else 60
    avg_duration_in_bars = avg_duration_in_minutes / bar_interval_minutes
    
    print("\nTrade Duration Analysis:")
    print(f"  Average Trade Duration (minutes): {avg_duration_in_minutes:.2f}")
    print(f"  Average Trade Duration (bars): {avg_duration_in_bars:.2f}")

    # PnL Distribution Plot
    plt.figure(figsize=(10, 6))
    trade_log['pnl'].hist(bins=50, color='skyblue', edgecolor='black')
    plt.title('Distribution of Trade P&L')
    plt.xlabel('P&L ($)')
    plt.ylabel('Frequency')
    plt.grid(axis='y', alpha=0.75)
    plt.savefig('pnl_distribution.png')
    print("\nPnL distribution plot saved to pnl_distribution.png")
    plt.close() 