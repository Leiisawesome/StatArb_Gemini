"""
Analysis of simpler vs. complex versions of the model.
"""
import copy
import pandas as pd
from structs import Config
from main import run_backtest
from evaluation.metrics import calculate_metrics
from typing import List, Tuple

def run_ablation_tests(base_config: Config, data: pd.DataFrame, pairs: List[Tuple[str, str]]):
    """
    Runs ablation tests by toggling features in the config and compares results.
    """
    print("\n--- Running Ablation Analysis ---")
    
    variants = {
        "Full Model": base_config,
        "No Classifier": Config(**{**base_config.__dict__, 'use_ensemble_classifier': False}),
        "No HMM": Config(**{**base_config.__dict__, 'use_hmm': False}),
        "Kalman Only": Config(**{**base_config.__dict__, 'use_hmm': False, 'use_ensemble_classifier': False}),
    }
    
    results = {}

    for name, config_variant in variants.items():
        print(f"\nRunning variant: {name}")
        trade_log = run_backtest(copy.deepcopy(config_variant), data, pairs)
        if trade_log is not None:
            results[name] = calculate_metrics(trade_log, config_variant)
        else:
            results[name] = calculate_metrics(pd.DataFrame(), config_variant)

    results_df = pd.DataFrame.from_dict(results, orient='index')
    print("\n--- Ablation Study Results ---")
    print(results_df.to_string(float_format="%.2f")) 