"""
Unit tests for the spread calculation logic.
"""
import pytest
import numpy as np
from strategy.spread import compute_spread

def test_compute_price_spread():
    """Tests spread calculation in 'price' mode."""
    state = (1.5, 0.5) # beta, alpha
    y, x = 101.0, 67.0
    expected_spread = 101.0 - (1.5 * 67.0 + 0.5)
    assert compute_spread(y, x, state, 'price') == pytest.approx(expected_spread)

def test_compute_return_spread():
    """Tests spread calculation in 'return' mode."""
    state = (1.0, 0.0)
    y, x = 110.0, 55.0
    y_prev, x_prev = 100.0, 50.0
    expected_spread = np.log(1.1) - 1.0 * np.log(1.1)
    spread = compute_spread(y, x, state, 'return', y_prev, x_prev)
    assert spread == pytest.approx(expected_spread)

def test_return_spread_zero_division():
    """Tests that return spread handles zero prices gracefully."""
    state = (1.0, 0.0)
    y, x = 110.0, 55.0
    y_prev, x_prev = 100.0, 0
    spread = compute_spread(y, x, state, 'return', y_prev, x_prev)
    assert spread == 0 