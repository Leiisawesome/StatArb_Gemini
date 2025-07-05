"""
Global configuration parameters for the Stat-Arb trading strategy.
This dictionary is parsed into a type-safe Config object in `structs.py`.
The default configuration is now set for intraday LETF pair trading.
"""

CONFIG_DICT = {
    # Data and Pair Selection Configuration
    'tickers': ["TQQQ", "SQQQ"], # Classic LETF pair
    'use_dynamic_pairs': False, # For specific LETF pairs, we often pre-define them
    'spread_type': 'price',
    
    # Intraday Time Window Configuration
    'data_interval': '5m', # e.g., '1m', '5m', '15m', '1h'
    'history_duration_days': 59, # Max for < 1h intervals on yfinance is 60 days
    'training_window_bars': 2000, # Number of bars for initial model training
    'sample_window_bars': 500,    # Number of bars for out-of-sample testing

    # Model Configuration
    'num_regimes': 3,
    'use_hmm': True,
    'use_ensemble_classifier': True,

    # Trading Strategy Configuration
    'entry_z': 2.0,
    'exit_z': 0.5,
    'stop_loss_mult': 3.0,
    'max_hold_bars': 96, # e.g., 8 hours of 5-minute bars

    # Execution and Risk Configuration
    'trade_size_dollars': 10000,
    'slippage_pct': 0.0005,

    # Evaluation and Robustness Configuration
    'monte_carlo_simulations': 50,
    'cross_validation_slices': 5,
    'perform_ablation': True,
    'risk_free_rate': 0.02
} 