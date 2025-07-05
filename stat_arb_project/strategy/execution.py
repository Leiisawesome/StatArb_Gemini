"""
Simulates order execution, including different order types and slippage.
"""
from structs import Config

def simulate_execution(price: float, direction: str, config: Config) -> float:
    """
    Simulates the execution of a trade, applying slippage.
    """
    slippage = config.slippage_pct
    if direction in ['LONG', 'SHORT_CLOSE']: # Buying
        return price * (1 + slippage)
    elif direction in ['SHORT', 'LONG_CLOSE']: # Selling
        return price * (1 - slippage)
    return price 