#!/usr/bin/env python3
"""
Check market data prices for debugging
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate some sample market data to see typical prices
np.random.seed(42)
dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')

# Simulate realistic stock prices
for symbol, base_price in [('NVDA', 800), ('TSLA', 250)]:
    prices = []
    current_price = base_price
    for _ in range(len(dates)):
        # Random walk with some volatility
        change = np.random.normal(0, 0.02)  # 2% daily volatility
        current_price *= (1 + change)
        prices.append(current_price)

    print(f'{symbol} sample prices:')
    print(f'  Latest: ${prices[-1]:.2f}')
    print(f'  Min: ${min(prices):.2f}')
    print(f'  Max: ${max(prices):.2f}')
    print(f'  Cost for 10 shares: ${prices[-1] * 10:.2f}')
    print()