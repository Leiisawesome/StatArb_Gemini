# Institutional-Grade Quant Desk: Intraday Pair Trading Platform

This project is a complete, production-ready statistical arbitrage trading strategy backtester and live simulation dashboard, specifically enhanced for **intraday pair trading**. The primary implemented and tested use case is for **Leveraged ETF (LETF) pairs** like TQQQ/SQQQ.

## Key Enhancements in This Version

-   **High-Frequency Capability:** The backtesting engine operates on intraday bar data (e.g., 1-minute, 5-minute).
-   **Instrument-Agnostic Design:** The core logic is structured to be extended to various financial instruments.
-   **Structured Configuration:** Type-safe configuration and data structures prevent common errors.
-   **Performance Optimization:** Key calculations are vectorized with pandas for high-speed backtesting.
-   **Full Robustness Suite:** Includes Time-Series Cross-Validation, Monte Carlo simulations (on bar returns), and advanced metrics like the **Sortino Ratio**.
-   **Containerization:** Ready for scalable deployment with Docker.

## Project Structure

```
stat_arb_project/
├── config.py                 # Configuration parameters
├── structs.py               # Type-safe data structures
├── main.py                  # Main entry point
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── README.md               # This file
├── data/
│   └── data_loader.py      # Data loading and preprocessing
├── model/
│   ├── kalman.py           # Kalman Filter for hedge ratios
│   ├── hmm.py              # Hidden Markov Models
│   └── ensemble.py         # Ensemble classifiers
├── strategy/
│   ├── spread.py           # Spread computation
│   ├── execution.py        # Order execution simulation
│   ├── pair_selection.py   # Dynamic pair selection
│   └── trading.py          # Main trading logic
├── evaluation/
│   ├── metrics.py          # Performance metrics
│   ├── diagnostics.py      # Risk diagnostics
│   ├── ablation.py         # Model ablation studies
│   └── robustness.py       # Cross-validation & Monte Carlo
├── dashboard/
│   └── live_dashboard.py   # Streamlit dashboard
├── utils/
│   └── helpers.py          # Utility functions
└── tests/
    ├── test_spread.py      # Unit tests
    └── test_metrics.py     # Performance test
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd stat_arb_project
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

### 1. Run the Intraday LETF Backtest
```bash
python main.py
```

### 2. Launch the Interactive Dashboard
```bash
streamlit run dashboard/live_dashboard.py
```

### 3. Run Unit Tests
```bash
pytest
```

### 4. Run with Docker
```bash
docker build -t stat-arb .
docker run stat-arb
```

---
### **IMPORTANT NOTE ON INTRADAY DATA**

The current implementation uses the `yfinance` library. For institutional-grade research, it is **strongly recommended** to integrate a professional data provider (e.g., Polygon.io, Alpaca, Bloomberg). The `data_loader.py` module is designed to be easily adapted for this.
---

## Trading Strategy Overview

The system implements a sophisticated statistical arbitrage strategy:

1. **Pair Selection**: Uses cointegration tests to find pairs of assets that move together
2. **Dynamic Hedge Ratios**: Kalman Filter estimates time-varying hedge ratios (beta)
3. **Regime Detection**: Hidden Markov Models identify different market regimes
4. **Signal Generation**: Z-score based entry/exit signals with ensemble confirmation
5. **Risk Management**: Stop-losses, position limits, and maximum holding periods

## Configuration

Key parameters in `config.py`:

- **Tickers**: Default is TQQQ/SQQQ (leveraged ETF pair)
- **Data Interval**: 5-minute bars (configurable to 1m, 15m, 1h)
- **Entry/Exit Thresholds**: Z-score based (entry: 2.0, exit: 0.5)
- **Position Sizing**: $10,000 per trade
- **Risk Management**: 3x stop-loss, 96-bar max hold

## Performance Metrics

The system calculates comprehensive performance metrics:

- **Sharpe Ratio**: Risk-adjusted returns
- **Sortino Ratio**: Downside risk-adjusted returns
- **Calmar Ratio**: Return to maximum drawdown
- **Profit Factor**: Gross profit to gross loss ratio
- **Win Rate**: Percentage of profitable trades
- **Maximum Drawdown**: Largest peak-to-trough decline

## Future Extensions

The robust and modular design of this platform allows for several future extensions:

-   **Live Trading Integration:** Connect the signal generation logic to a broker API (e.g., Interactive Brokers, Alpaca) for live order execution.
-   **New Instrument Types:** Create new classes that inherit from a base `Instrument` class to handle the unique characteristics of options (e.g., greeks, expiry) or futures (e.g., rollovers, margin).
-   **Advanced Risk Management:** Implement a more sophisticated portfolio-level risk management module that considers factor exposures, VaR (Value at Risk), and overall portfolio leverage.
-   **Alternative Models:** Integrate other time-series models (e.g., GARCH for volatility, LSTMs for prediction) into the ensemble framework.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. It is not intended for live trading without proper testing and risk management. The authors are not responsible for any financial losses incurred from using this software. 