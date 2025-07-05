"""
Robustness checks like Cross-Validation and Monte Carlo simulations.
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from structs import Config
from strategy import pair_selection, trading
from evaluation.metrics import calculate_metrics
from typing import List, Tuple
from main import run_backtest

def run_cross_validation(config: Config, data: pd.DataFrame, pairs: List[Tuple[str, str]]):
    """Runs k-fold time-series cross-validation on the dataset."""
    print("\n--- Running Time-Series Cross-Validation ---")
    
    tscv = TimeSeriesSplit(n_splits=config.cross_validation_slices)
    results = []

    for fold, (train_index, test_index) in enumerate(tscv.split(data)):
        print(f"\nProcessing Fold {fold + 1}/{config.cross_validation_slices}...")
        
        train_data = data.iloc[train_index]
        test_data = data.iloc[test_index]
        
        if len(train_data) < config.training_window_bars:
            print("Skipping fold due to insufficient training data.")
            continue
            
        fold_pairs = pair_selection.dynamic_pair_selection(train_data) if config.use_dynamic_pairs else pairs
        if not fold_pairs:
            print("No pairs found in this fold. Skipping.")
            continue
            
        all_trades = []
        for pair in fold_pairs:
            if not all(p in train_data.columns for p in pair): continue
            if not pair_selection.is_cointegrated(train_data[pair[0]], train_data[pair[1]]): continue

            trade_log = trading.simulate_trading(pair, train_data, test_data, config)
            if trade_log is not None and not trade_log.empty:
                all_trades.append(trade_log)

        if all_trades:
            fold_trade_log = pd.concat(all_trades).sort_values(by='entry_date').reset_index(drop=True)
            results.append(calculate_metrics(fold_trade_log, config))
        
    if results:
        results_df = pd.DataFrame(results)
        print("\n--- Cross-Validation Results ---")
        print(results_df.to_string(float_format="%.2f"))
        print("\n--- Cross-Validation Summary (Mean) ---")
        print(results_df.mean().to_string(float_format="%.2f"))

def run_monte_carlo_backtests(config: Config, data: pd.DataFrame, pairs: List[Tuple[str, str]]):
    """Runs backtests on resampled data paths."""
    print("\n--- Running Monte Carlo Simulation ---")
    
    # Resample bar returns, not daily returns, for higher frequency strategies
    bar_returns = data.pct_change().dropna()
    results = []

    for i in range(config.monte_carlo_simulations):
        print(f"Running simulation {i + 1}/{config.monte_carlo_simulations}...", end='\r')
        
        # Create a new synthetic dataset via bootstrap
        synthetic_returns = bar_returns.sample(n=len(bar_returns), replace=True)
        synthetic_prices = (1 + synthetic_returns).cumprod() * data.iloc[0]
        
        trade_log = run_backtest(config, synthetic_prices, pairs)
        if trade_log is not None:
            results.append(calculate_metrics(trade_log, config))

    if results:
        results_df = pd.DataFrame(results)
        print("\n\n--- Monte Carlo Results Summary ---")
        print(results_df[['Total PnL', 'Annualized Sharpe Ratio', 'Max Drawdown']].describe().to_string(float_format="%.2f")) 