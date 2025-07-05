"""
Calculates and visualizes performance metrics, adapted for intraday timeframes.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from structs import Config
from typing import Dict, Any

def calculate_metrics(trade_log: pd.DataFrame, config: Config) -> Dict[str, Any]:
    """Calculates a dictionary of performance metrics."""
    if trade_log.empty:
        return {
            'Total PnL': 0.0, 'Annualized Sharpe Ratio': 0.0, 'Annualized Sortino Ratio': 0.0, 'Max Drawdown': 0.0, 
            'Calmar Ratio': 0.0, 'Profit Factor': 0.0, 'Win Rate': 0.0, 'Total Trades': 0
        }

    trade_log['cumulative_pnl'] = trade_log['pnl'].cumsum()
    total_pnl = trade_log['cumulative_pnl'].iloc[-1]
    
    equity_curve = trade_log['cumulative_pnl']
    running_max = equity_curve.cummax()
    drawdown = running_max - equity_curve
    max_drawdown = drawdown.max()
    
    trade_log['exit_date'] = pd.to_datetime(trade_log['exit_date'])
    
    # Calculate returns based on the actual bar interval
    try:
        freq_str = config.data_interval.replace('m', 'T')
        all_bars = pd.date_range(start=trade_log['exit_date'].min().floor('h'), end=trade_log['exit_date'].max().ceil('h'), freq=freq_str)
        bar_returns = trade_log.set_index('exit_date')['pnl'].reindex(all_bars, fill_value=0) / (config.trade_size_dollars * 2)
    except Exception:
        bar_returns = trade_log.set_index('exit_date')['pnl']

    sharpe_ratio = 0.0
    sortino_ratio = 0.0
    if len(bar_returns) > 1 and bar_returns.std() > 0:
      bars_per_day = (6.5 * 60) / int(config.data_interval[:-1]) if 'm' in config.data_interval else 6.5
      bars_per_year = bars_per_day * 252
      
      # Sharpe Ratio
      excess_bar_returns = bar_returns - (config.risk_free_rate / bars_per_year)
      sharpe_ratio = np.sqrt(bars_per_year) * (excess_bar_returns.mean() / excess_bar_returns.std())
      
      # Sortino Ratio
      downside_returns = excess_bar_returns[excess_bar_returns < 0]
      downside_std = downside_returns.std()
      if downside_std > 0:
          sortino_ratio = np.sqrt(bars_per_year) * (excess_bar_returns.mean() / downside_std)

    num_trades = len(trade_log)
    wins = trade_log[trade_log['pnl'] > 0]
    gross_profit = wins['pnl'].sum()
    gross_loss = abs(trade_log[trade_log['pnl'] <= 0]['pnl'].sum())
    
    return {
        'Total PnL': total_pnl,
        'Annualized Sharpe Ratio': sharpe_ratio,
        'Annualized Sortino Ratio': sortino_ratio,
        'Max Drawdown': max_drawdown,
        'Calmar Ratio': total_pnl / max_drawdown if max_drawdown > 0 else np.inf,
        'Profit Factor': gross_profit / gross_loss if gross_loss > 0 else np.inf,
        'Win Rate': len(wins) / num_trades if num_trades > 0 else 0.0,
        'Total Trades': num_trades
    }

def calculate_and_plot_metrics(trade_log: pd.DataFrame, config: Config, plot_filename: str):
    """Generates equity curves, drawdown plots, and prints key metrics."""
    metrics_dict = calculate_metrics(trade_log, config)
    if metrics_dict['Total Trades'] == 0:
        print("No trades to evaluate.")
        return

    print("\n--- Performance Evaluation ---")
    for key, value in metrics_dict.items():
        print(f"{key+':':<25} {value:,.2f}" if isinstance(value, (float, int)) else f"{key+':':<25} {value}")

    trade_log['cumulative_pnl'] = trade_log['pnl'].cumsum()
    equity_curve = trade_log['cumulative_pnl']
    running_max = equity_curve.cummax()
    drawdown = running_max - equity_curve
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    trade_log['exit_date'] = pd.to_datetime(trade_log['exit_date'])
    ax1.plot(trade_log['exit_date'], trade_log['cumulative_pnl'], label='Cumulative PnL', color='blue')
    ax1.set_title("Portfolio Equity Curve & Drawdown")
    ax1.set_ylabel("Cumulative PnL ($)")
    ax1.grid(True)
    ax2.fill_between(trade_log['exit_date'], -drawdown, 0, color='red', alpha=0.5, label='Drawdown')
    ax2.set_ylabel("Drawdown ($)")
    ax2.set_xlabel("Date")
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig(plot_filename)
    print(f"\nPerformance summary plot saved to {plot_filename}")
    plt.close() 