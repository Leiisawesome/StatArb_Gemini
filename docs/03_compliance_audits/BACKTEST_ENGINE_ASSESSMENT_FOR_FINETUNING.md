# Assessment: Institutional Backtest Engine for Strategy Fine-Tuning
**Target Objective:** Single source for simulating Stocks, ETFs, and Cryptos using real ClickHouse data for strategy fine-tuning.

**Date:** November 23, 2025  
**Reviewer:** AI Architecture Compliance System

---

## Executive Summary

The `InstitutionalBacktestEngine` is a robust **Event-Driven Backtester** designed for high-fidelity simulation of US Equities. However, for the specific objective of being a **multi-asset fine-tuning platform**, it currently has significant gaps in **performance**, **instrument handling**, and **optimization workflows**.

| Capability | Status | Readiness for Objective |
|------------|--------|-------------------------|
| **US Equities Simulation** | ✅ Ready | High-fidelity, production-aligned |
| **Crypto/ETF Simulation** | ⚠️ Gaps | Hardcoded market hours, missing funding rates |
| **Strategy Fine-Tuning** | ❌ Missing | No optimization loop, too slow for iterations |
| **Data Handling** | ✅ Good | ClickHouse integration is solid |

---

## 1. Trading Logic Gaps (Asset Class Specifics)

To support **Stocks, ETFs, and Cryptos** uniformly, the engine needs to abstract "Instrument Properties".

### A. Hardcoded Market Hours (Critical)
*   **Current State:** The engine explicitly hardcodes US Market Hours (09:30 - 16:00) in `_load_historical_data`.
    ```python
    # backtest/engine/institutional_backtest_engine.py
    start_dt = start_dt.replace(hour=9, minute=30, second=0)  # Hardcoded!
    end_dt = end_dt.replace(hour=16, minute=0, second=0)      # Hardcoded!
    ```
*   **Gap:** This makes **Crypto backtesting impossible** (requires 24/7 data) and breaks international ETFs.
*   **Recommendation:** Implement `MarketCalendar` or `InstrumentDefinition` class that defines trading hours per symbol/exchange.

### B. Missing Asset-Specific Cost Models
*   **Current State:** Uses generic commission (`commission_per_share`) and spread models.
*   **Gap:**
    *   **Cryptos:** Fees are often % of notional (bps), not per-share. Funding rates (for perps) are missing.
    *   **ETFs:** May have different liquidity profiles/impact models.
*   **Recommendation:** Enhance `HistoricalExecutionSimulator` to accept `FeeModel` strategies (e.g., `PerShareFee`, `PercentageFee`, `MakerTakerFee`).

### C. Corporate Actions & Funding Rates
*   **Current State:** No visible handling of dividends, splits, or crypto funding rates.
*   **Gap:** Long-term ETF/Stock backtests will be inaccurate without total return adjustments. Crypto perp strategies will miss significant P&L components (funding).
*   **Recommendation:** Add `CorporateActionHandler` and `FundingRateManager` components.

---

## 2. System Architectural Gaps (Fine-Tuning & Performance)

"Fine-tuning" implies running thousands of variations. The current architecture is optimized for **fidelity**, not **speed**.

### A. Python Event Loop Bottleneck (Critical for Fine-Tuning)
*   **Current State:** `process_bar` iterates row-by-row in Python `async` loop.
*   **Gap:** This is **orders of magnitude too slow** for parameter optimization (grid search/genetic algos). A single 1-year, 1-minute backtest could take minutes. Fine-tuning requires seconds.
*   **Recommendation:**
    *   **Vectorized Backtester:** Create a parallel `VectorizedBacktestEngine` for rapid signal generation and initial filtering.
    *   **Hybrid Approach:** Use Vectorized for broad optimization → Event-Driven (current engine) for final verification.

### B. Missing Optimization Framework
*   **Current State:** The engine runs *one* configuration per execution.
*   **Gap:** No built-in support for:
    *   Grid Search / Random Search
    *   Walk-Forward Analysis
    *   Parameter Stability Tests
*   **Recommendation:** Create an `OptimizationOrchestrator` that wraps the backtest engine, manages parameter spaces, and aggregates results.

### C. Data Granularity for Fine-Tuning
*   **Current State:** Loads data into Pandas DataFrame.
*   **Gap:** Large-scale fine-tuning (e.g., 5-year, 100-symbol, tick-data) will hit memory limits.
*   **Recommendation:** Implement "Chunked Processing" or "Streaming Data" for large optimizations, or leverage ClickHouse for server-side signal calculation (offloading logic to DB).

---

## 3. Roadmap to "Single Source" Objective

To achieve the goal of a unified simulation & fine-tuning platform, we suggest this roadmap:

### Phase 1: Multi-Asset Abstraction (Weeks 1-2)
1.  **Instrument Registry:** Create `InstrumentDefinition` (symbol, type, exchange, trading_hours, fee_model).
2.  **Dynamic Calendars:** Replace hardcoded 9:30-16:00 logic with `calendar.is_open(timestamp)`.
3.  **Fee Model Factory:** Support `bps` fees (Crypto) vs `$/share` fees (Stocks).

### Phase 2: Optimization Layer (Weeks 3-4)
1.  **Vectorized Core:** Implement `VectorizedStrategy` interface using Pandas/Numpy/Polars for rapid signal calculation.
2.  **Optimization Loop:** Build `StrategyOptimizer` to run vectorized backtests in parallel.

### Phase 3: Institutional Logic (Weeks 5-6)
1.  **Funding & Dividends:** Add support for cash flow adjustments.
2.  **Margin Engine:** Enhance `CentralRiskManager` to handle different margin requirements per asset class (e.g., Crypto leverage vs Reg T).

---

### Conclusion

The current engine is an **excellent final verification tool** for US Equities but is **currently unsuited** for rapid multi-asset fine-tuning. It needs abstraction for asset classes and a high-performance vectorized mode to meet the "fine-tune" objective.

