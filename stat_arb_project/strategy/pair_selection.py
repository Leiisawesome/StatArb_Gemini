"""
Dynamic pair selection based on cointegration and stationarity checks.
"""
from statsmodels.tsa.stattools import coint, adfuller
import pandas as pd
from typing import Tuple, List

def is_stationary(series: pd.Series, adf_p_value_threshold: float = 0.05) -> bool:
    """Checks if a series is stationary using the Augmented Dickey-Fuller test."""
    if series.empty: return False
    series = series.dropna()
    if len(series) < 20: return False
    try:
        adf_result = adfuller(series)
        return adf_result[1] < adf_p_value_threshold
    except Exception:
        return False

def is_cointegrated(series_a: pd.Series, series_b: pd.Series, coint_p_value_threshold: float = 0.05) -> bool:
    """Checks for cointegration between two series using the Engle-Granger test."""
    if series_a.empty or series_b.empty or len(series_a) < 20 or len(series_b) < 20:
        return False
    if series_a.nunique() == 1 or series_b.nunique() == 1:
        return False
    try:
        score, p_value, _ = coint(series_a, series_b, trend='c')
        return p_value < coint_p_value_threshold
    except Exception:
        return False

def dynamic_pair_selection(training_data: pd.DataFrame) -> List[Tuple[str, str]]:
    """Selects pairs of assets that are likely cointegrated based on training data."""
    from itertools import combinations
    
    tickers = training_data.columns
    print(f"Running dynamic pair selection on {len(tickers)} tickers...")
    
    potential_pairs: List[Tuple[str, str]] = []
    if len(tickers) < 2:
        print("Not enough tickers to form pairs.")
        return []

    for a, b in combinations(tickers, 2):
        if is_cointegrated(training_data[a], training_data[b]):
            potential_pairs.append((a, b))
            print(f"Found cointegrated pair: ({a}, {b})")

    return potential_pairs 