# =====================================================
# Polygon L1 PDE Alpha v3 Multi-Day Validation Script
# Uses polygon_rest.py for RTH (09:30–16:00 ET) L1 data
# Author: StatArb_Gemini - March 2026
# =====================================================

import asyncio
import os
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from core_engine.data.feeds.polygon_rest import create_polygon_rest_service

warnings.filterwarnings("ignore")

ET = ZoneInfo("America/New_York")
UTC = timezone.utc

# ================== USER CONFIG ==================
API_KEY = os.getenv("POLYGON_API_KEY", "").strip()
if not API_KEY:
    raise ValueError("POLYGON_API_KEY environment variable is required.")

TICKER = "TSLA"
START_DATE = "2024-12-16"
END_DATE = "2024-12-20"
MAX_DAYS = 5
OUTPUT_DIR = _PROJECT_ROOT / "tsla_pde_v3_multi_day_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# v3 parameters (thesis-aligned with relaxed thresholds for validation)
SIGNAL_THRESH = 0.5
MAX_HOLD_BASE = 15
REPLEN_MIN = 0.02            # thesis §5: |δ| > threshold (0.02 allows more setups)
ETA_DELTA = 0.5

print(f"Starting multi-day validation for {TICKER} {START_DATE} to {END_DATE}")

# ================== FETCH (unchanged) ==================
async def fetch_l1_day_rth(service, ticker: str, day_str: str) -> pd.DataFrame:
    print(f"  Fetching RTH L1 for {day_str}...")
    year, month, day = map(int, day_str.split("-"))
    base_date = datetime(year, month, day, tzinfo=ET)
    start_et = base_date.replace(hour=9, minute=30, second=0)
    end_et = base_date.replace(hour=16, minute=0, second=0)
    start = start_et.astimezone(UTC)
    end = end_et.astimezone(UTC)

    df = await service.get_trade_quote_snapshots_1s(
        symbol=ticker, start=start, end=end,
        forward_fill_quotes=True, forward_fill_trades=False,
        limit=50000, max_pages=100,
    )

    if df.empty:
        return df

    df = df.reset_index()
    if "trade_size" not in df.columns:
        df["trade_size"] = 0
    df["trade_size"] = df["trade_size"].fillna(0)
    df["trade_price"] = df["trade_price"].astype(float)

    # Explicit spread (safety)
    if "spread" not in df.columns:
        df["spread"] = df["quote_ask"] - df["quote_bid"]

    df = df.dropna(subset=["quote_bid", "quote_ask"])
    df["quote_age_ms"] = df["quote_age_ms"].fillna(0)
    print(f"    → {len(df)} clean 1s RTH L1 bars")
    return df

# ================== FIXED v3.1 BACKTEST ENGINE (with debug) ==================
def run_v3_backtest(df: pd.DataFrame, date_str: str):
    df = df.copy()
    size_sum = (df["quote_bid_size"] + df["quote_ask_size"]).replace(0, np.nan)
    df["microprice"] = (df["quote_bid"] * df["quote_ask_size"] + df["quote_ask"] * df["quote_bid_size"]) / size_sum
    df["imbalance"] = (df["quote_bid_size"] - df["quote_ask_size"]) / size_sum
    df["replen_delta"] = (df["quote_bid_size"].diff() - df["quote_ask_size"].diff()) / size_sum
    df["norm_spread"] = df["spread"] / df["spread"].rolling(600).median().replace(0, np.nan).fillna(1)
    df["regime"] = (df["spread"] > df["spread"].rolling(600).median()).astype(int)
    df["trade_aggr"] = np.sign(df["trade_price"] - df["quote_ask"].shift(1)).fillna(0)
    
    trades = []
    i = 0
    n = len(df)
    filter_stats = {"total": n, "sig_fail": 0, "age_fail": 0, "replen_fail": 0, "spread_fail": 0, "trade_fail": 0, "aggr_fail": 0}

    while i < n:
        row = df.iloc[i]
        i_val = row["imbalance"]
        s = row["norm_spread"]
        if s <= 0 or np.isnan(s):
            i += 1
            continue
        delta = row["replen_delta"] if pd.notna(row["replen_delta"]) else 0.0

        sig = (i_val / s) * (1.0 - abs(i_val)) + ETA_DELTA * delta

        rolling_med = df["spread"].rolling(600).median().iloc[i]
        trade_window = df["trade_aggr"].iloc[max(0, i-3):i+1]
        
        # FIXED filters with debug
        if abs(sig) < SIGNAL_THRESH:
            filter_stats["sig_fail"] += 1
            i += 1; continue
        if row["quote_age_ms"] > 0 and row["quote_age_ms"] < 200:   # FIXED: only positive small ages
            filter_stats["age_fail"] += 1
            i += 1; continue
        if abs(delta) < REPLEN_MIN:
            filter_stats["replen_fail"] += 1
            i += 1; continue
        if not np.isnan(rolling_med) and row["spread"] > 1.5 * rolling_med:
            filter_stats["spread_fail"] += 1
            i += 1; continue
        if trade_window.abs().sum() == 0:
            filter_stats["trade_fail"] += 1
            i += 1
            continue
        # Aggressive-trade confirmation: require net flow to align with signal direction
        trade_sum = trade_window.sum()
        needs_buy = sig > 0
        if not ((trade_sum > 0 and needs_buy) or (trade_sum < 0 and not needs_buy)):
            filter_stats["aggr_fail"] += 1
            i += 1
            continue

        # === ENTRY ===
        side = 1 if sig > 0 else -1
        entry_m = row["microprice"]
        entry_spread = row["spread"]
        entry_bid_size = row["quote_bid_size"]
        entry_ask_size = row["quote_ask_size"]

        max_hold = MAX_HOLD_BASE if row["regime"] == 0 else MAX_HOLD_BASE // 2
        exit_i = min(i + max_hold, n-1)
        entry_regime = row["regime"]
        for j in range(i+1, exit_i+1):
            rj = df.iloc[j]
            if np.sign(rj["imbalance"]) != np.sign(sig) or rj["regime"] != entry_regime:
                exit_i = j
                break

        exit_m = df.iloc[exit_i]["microprice"]
        gross_bps = side * (exit_m - entry_m) / entry_m * 10000
        half_spread_bps = (entry_spread / entry_m) * 5000
        side_size = entry_bid_size if side == -1 else entry_ask_size
        fill_prob = side_size / (side_size + 100)
        slippage_bps = 0.2 * (entry_spread / entry_m * 10000) * (1 - fill_prob)
        net_bps = gross_bps - side * (half_spread_bps + slippage_bps)

        trades.append({
            "date": date_str,
            "entry_time": df.iloc[i]["timestamp"],
            "side": "Long" if side > 0 else "Short",
            "entry_microprice": round(entry_m, 4),
            "signal_V": round(sig, 4),
            "regime": "tight" if row["regime"] == 0 else "wide",
            "replen_delta": round(delta, 4),
            "exit_time": df.iloc[exit_i]["timestamp"],
            "exit_microprice": round(exit_m, 4),
            "gross_bps": round(gross_bps, 2),
            "net_bps": round(net_bps, 2),
            "fill_prob": round(fill_prob, 4),
            "hold_seconds": (
                df.iloc[exit_i]["timestamp"] - df.iloc[i]["timestamp"]
            ).total_seconds(),
        })

        i = exit_i + 1

    trade_df = pd.DataFrame(trades)
    if not trade_df.empty:
        trade_df.to_csv(OUTPUT_DIR / f"{date_str}_trade_log_v3.csv", index=False)

    if n > 0:
        print(
            f"    Filter stats: sig_fail={filter_stats['sig_fail']} | replen_fail={filter_stats['replen_fail']} | "
            f"trade_fail={filter_stats['trade_fail']} | aggr_fail={filter_stats['aggr_fail']}"
        )

    summary = {
        "date": date_str,
        "trades": len(trade_df),
        "mean_net_bps": trade_df["net_bps"].mean() if not trade_df.empty else 0,
        "win_rate": (trade_df["net_bps"] > 0).mean() if not trade_df.empty else 0,
        "total_net_bps": trade_df["net_bps"].sum() if not trade_df.empty else 0,
    }
    return trade_df, summary

# ================== MAIN ==================
async def main():
    service = await create_polygon_rest_service(api_key=API_KEY)
    try:
        all_summaries = []
        current_date = datetime.strptime(START_DATE, "%Y-%m-%d")
        end_dt = datetime.strptime(END_DATE, "%Y-%m-%d")
        day_count = 0

        while current_date <= end_dt and day_count < MAX_DAYS:
            day_str = current_date.strftime("%Y-%m-%d")
            df_day = await fetch_l1_day_rth(service, TICKER, day_str)
            if len(df_day) < 1000:
                print(f"  Skipping {day_str} (insufficient data)")
                current_date += timedelta(days=1)
                continue

            trade_df, summary = run_v3_backtest(df_day, day_str)
            all_summaries.append(summary)
            print(
                f"  {day_str} → {summary['trades']} trades | "
                f"mean net {summary['mean_net_bps']:.3f} bps | "
                f"win {summary['win_rate']:.1%}"
            )

            current_date += timedelta(days=1)
            day_count += 1

        summary_df = pd.DataFrame(all_summaries)
        summary_df.to_csv(OUTPUT_DIR / "multi_day_summary_v3.csv", index=False)
        print("\n=== CROSS-DAY VALIDATION COMPLETE ===")
        print(summary_df[["date", "trades", "mean_net_bps", "win_rate", "total_net_bps"]])
        print(f"\nResults saved to {OUTPUT_DIR}")
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())