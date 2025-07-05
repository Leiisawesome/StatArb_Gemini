"""
Spread computation: price or return based.
"""
import numpy as np

def compute_spread(y: float, x: float, state: np.ndarray, spread_type: str, 
                   y_prev: float | None = None, x_prev: float | None = None) -> float:
    """Computes the spread between two series."""
    beta, alpha = state
    if spread_type == 'price':
        return y - (beta * x + alpha)
    elif spread_type == 'return':
        if y_prev is None or x_prev is None or y_prev <= 0 or x_prev <= 0:
            return 0.0
        return np.log(y / y_prev) - beta * np.log(x / x_prev)
    return 0.0 