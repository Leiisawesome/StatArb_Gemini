"""
Session Management Mixin for InstitutionalBacktestEngine
=========================================================

Contains methods for intraday session isolation, day-boundary resets,
warmup replay, RTH filtering, pre-calculation routing, and price updates.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SessionManagementMixin:
    """Session lifecycle methods for InstitutionalBacktestEngine."""

    def _is_before_simulation_start(self, timestamp: Any) -> bool:
        """Return True when timestamp is before configured simulation start date."""
        if not hasattr(self, 'simulation_start_dt'):
            return False

        ts_compare = pd.Timestamp(timestamp)
        sim_start_compare = pd.Timestamp(self.simulation_start_dt)

        if ts_compare.tzinfo is not None:
            ts_compare_normalized = ts_compare.tz_localize(None)
        else:
            ts_compare_normalized = ts_compare

        if sim_start_compare.tzinfo is not None:
            sim_start_compare_normalized = sim_start_compare.tz_localize(None)
        else:
            sim_start_compare_normalized = sim_start_compare

        return ts_compare_normalized.date() < sim_start_compare_normalized.date()

    def _is_within_rth(self, timestamp: Any, bar_index: int) -> bool:
        """Defensive RTH gate with cached calendar and asset-class lookup."""
        try:
            from core_engine.data.market_calendar import MarketCalendar

            if self._market_calendar is None:
                self._market_calendar = MarketCalendar()

            cal = self._market_calendar
            if self._rth_asset_class is None:
                primary_symbol = self.config.symbols[0] if self.config.symbols else "SPY"
                self._rth_asset_class = cal.get_asset_class(primary_symbol)

            ts_time = pd.Timestamp(timestamp)
            session_cfg = cal.sessions.get(self._rth_asset_class)
            if session_cfg:
                self._rth_tz_name = session_cfg.timezone

            if ts_time.tzinfo is None:
                ts_local = ts_time.tz_localize(self._rth_tz_name)
            else:
                ts_local = ts_time.tz_convert(self._rth_tz_name)

            session_open, session_close = cal.get_session_times(ts_local.to_pydatetime(), self._rth_asset_class)
            return session_open.time() <= ts_local.time() < session_close.time()
        except Exception as e:
            if bar_index == 0:
                logger.debug(f"RTH gate check skipped (non-fatal): {e}")
            return True

    # ================================================================
    # INTRADAY SESSION ISOLATION — Helper Methods
    # ================================================================

    async def _pre_calculate_per_session(
        self,
        raw_data_per_symbol: Dict[str, pd.DataFrame],
    ) -> None:
        """Compute features per trading day for session-isolated backtests.

        Each day's features are computed from a data window of
        ``warmup_bars`` prior bars + the day's bars.  Between days we reset
        the pipeline orchestrator's cache and the regime engine so that no
        state leaks between per-session pipeline calls.
        """
        warmup_cap = int(getattr(self.config, 'warmup_bars', 200) or 200)
        sim_start = None
        if hasattr(self, 'simulation_start_dt'):
            sim_start = pd.Timestamp(self.simulation_start_dt).date()

        for sym, full_df in raw_data_per_symbol.items():
            if full_df.empty:
                continue

            # Identify unique trading dates
            ts_col = full_df['timestamp'] if 'timestamp' in full_df.columns else full_df.index
            dates_series = pd.to_datetime(ts_col)
            full_df = full_df.copy()
            full_df['_ts_date'] = dates_series.dt.date.values

            if sim_start is not None:
                sim_dates = sorted(set(d for d in full_df['_ts_date'].unique() if d >= sim_start))
            else:
                sim_dates = sorted(full_df['_ts_date'].unique())

            if not sim_dates:
                logger.warning(f"   ⚠️ No simulation dates for {sym}")
                continue

            all_day_indicators = []
            all_day_features = []

            # Save the real regime engine and restore after the loop
            saved_regime_engine = getattr(self.pipeline_orchestrator, 'regime_engine', None)
            regime_config = None
            if saved_regime_engine is not None:
                cfg_obj = getattr(saved_regime_engine, 'config', None)
                if cfg_obj is not None and hasattr(cfg_obj, '__dict__'):
                    regime_config = cfg_obj.__dict__

            for day in sim_dates:
                day_mask = full_df['_ts_date'] == day
                before_mask = full_df['_ts_date'] < day

                before_bars = full_df[before_mask]
                day_bars = full_df[day_mask]

                if len(before_bars) > warmup_cap:
                    before_bars = before_bars.iloc[-warmup_cap:]

                window_df = pd.concat([before_bars, day_bars], ignore_index=True)
                window_df_clean = window_df.drop(columns=['_ts_date'], errors='ignore')

                # ── Reset ALL inter-call state so each day is independent ──
                # 1. Clear pipeline cache (keyed by symbol)
                if hasattr(self.pipeline_orchestrator, '_cache_entries'):
                    self.pipeline_orchestrator._cache_entries.clear()
                # 2. Install a BRAND NEW regime engine for each day so that
                #    regime detection starts with zero state (identical to a
                #    freshly-created engine in an individual-day run).
                if regime_config is not None:
                    try:
                        from core_engine.regime.engine import RealTimeRegimeSensor
                        fresh_regime = RealTimeRegimeSensor(regime_config)
                        fresh_regime.is_initialized = True
                        fresh_regime.is_operational = True
                        self.pipeline_orchestrator.regime_engine = fresh_regime
                    except Exception as exc:
                        logger.debug(f"Fresh regime creation failed: {exc}")
                elif saved_regime_engine is not None:
                    if hasattr(saved_regime_engine, 'reset_intraday_state'):
                        saved_regime_engine.reset_intraday_state()
                    saved_regime_engine.current_regime = None

                window_data = {sym: window_df_clean}
                try:
                    enriched_results = await self.pipeline_orchestrator.process_preloaded_data(
                        raw_data_per_symbol=window_data,
                        timeframe=self.config.interval,
                    )

                    if sym in enriched_results:
                        enriched = enriched_results[sym]
                        feat_df = enriched.features.copy()
                        ind_df = enriched.indicators.copy()

                        # Keep only the day's rows (tail = day bars)
                        n_day = len(day_bars)
                        if len(feat_df) > n_day:
                            feat_df = feat_df.iloc[-n_day:].reset_index(drop=True)
                        if len(ind_df) > n_day:
                            ind_df = ind_df.iloc[-n_day:].reset_index(drop=True)

                        all_day_features.append(feat_df)
                        all_day_indicators.append(ind_df)
                except Exception as e:
                    logger.warning(f"   ⚠️ Per-session pre-calc failed for {sym} on {day}: {e}")

            # Restore the original regime engine for bar-loop processing
            if saved_regime_engine is not None:
                self.pipeline_orchestrator.regime_engine = saved_regime_engine

            if all_day_features:
                combined_features = pd.concat(all_day_features, ignore_index=True)
                combined_indicators = pd.concat(all_day_indicators, ignore_index=True)
                self.pre_calculated_features_per_symbol[sym] = combined_features
                self.pre_calculated_indicators_per_symbol[sym] = combined_indicators
                logger.info(
                    f"   ✅ {sym}: {len(combined_features)} bars "
                    f"(per-session, {len(sim_dates)} days)"
                )

    def _reset_session_state(self) -> None:
        """Reset all runtime state that leaks across trading-day boundaries.

        Called at each new trading-day open when ``intraday_session_isolation``
        is enabled.  Resets *observation* / *decision* state AND portfolio
        cash so that position sizing on each day is independent of prior
        days' PnL (required for strict intraday additivity).
        """
        # 1. CentralRiskManager — price history, cooldowns, exit-in-flight,
        #    trade outcomes, and portfolio HWM
        if self.risk_manager and hasattr(self.risk_manager, 'reset_intraday_state'):
            self.risk_manager.reset_intraday_state()

        # 2. Regime engine — EWMA state, regime sequence, buffers
        if self.regime_engine and hasattr(self.regime_engine, 'reset_intraday_state'):
            self.regime_engine.reset_intraday_state()

        # 3. Strategy state — ALL per-symbol caches, counters, queues
        if self.strategy_manager and hasattr(self.strategy_manager, 'active_strategies'):
            for _name, strategy in self.strategy_manager.active_strategies.items():
                # Pending signal queue
                if hasattr(strategy, 'pending_signals') and hasattr(strategy.pending_signals, 'clear'):
                    strategy.pending_signals.clear()
                # State machine
                if hasattr(strategy, 'state_machine') and hasattr(strategy.state_machine, 'states'):
                    strategy.state_machine.states.clear()
                # Per-symbol indicators & momentum data
                for attr in ('indicators', 'momentum_data'):
                    container = getattr(strategy, attr, None)
                    if isinstance(container, dict):
                        container.clear()
                # ADS regime vector cache
                ads_cache = getattr(strategy, '_ads_regime_cache', None)
                if ads_cache is not None:
                    if hasattr(ads_cache, 'clear'):
                        ads_cache.clear()
                    elif hasattr(ads_cache, '_cache'):
                        ads_cache._cache.clear()
                # Scalar counters → reset to defaults
                if hasattr(strategy, '_sm_entries_triggered'):
                    strategy._sm_entries_triggered = 0
                if hasattr(strategy, '_sm_entry_reasons'):
                    strategy._sm_entry_reasons.clear()
                if hasattr(strategy, '_current_mqs'):
                    strategy._current_mqs = 1.0
                if hasattr(strategy, '_current_mqs_penalty'):
                    strategy._current_mqs_penalty = 1.0

        # 4. Engine-level pending signals (next-bar execution queue)
        self.pending_signals.clear()

        # 5. On-the-fly historical market data accumulator
        self.historical_market_data.clear()

        # 6. EOD guard — reset liquidation tracking for new day
        if hasattr(self.eod_guard, '_liquidated_dates'):
            self.eod_guard._liquidated_dates.clear()

        # 7. Portfolio cash — carry forward (compound across sessions).
        #    Positions should be flat from EOD liquidation. Cash reflects
        #    realised PnL from prior days, exactly as in live trading.
        #    (No cash reset — position sizing uses current equity.)

        # 8. RealTimePnLTracker — position cost basis, entry times, PnL
        pnl_tracker = getattr(self, 'pnl_tracker', None)
        if pnl_tracker:
            for attr in ('position_cost_basis', 'position_pnl',
                         'position_entry_time', 'position_sizes',
                         'daily_pnl', 'trade_history'):
                container = getattr(pnl_tracker, attr, None)
                if container is not None and hasattr(container, 'clear'):
                    container.clear()

        logger.debug("Session state reset complete")

    def _warmup_replay(self, warmup_bars: List) -> None:
        """Replay prior-day bars through stateful components in read-only mode.

        This primes price-history (for vol-stop σ_eff / Δρ) and regime EWMA
        so the new trading day starts with context, without leaking any
        trading decisions from the prior day.

        No signals are generated, no trades are executed.
        """
        if not warmup_bars:
            return

        n = len(warmup_bars)
        logger.info(f"   Replaying {n} prior-day bars for session warmup...")

        for bar in warmup_bars:
            bar_dict = self._bar_to_dict(bar) if hasattr(bar, 'to_dict') else dict(bar)
            timestamp = bar.get('timestamp', None) or bar.name if hasattr(bar, 'name') else None

            # Price history → feeds vol-stop computation
            if self.risk_manager and hasattr(self.risk_manager, 'update_market_prices'):
                prices = {}
                for sym in self.config.symbols:
                    close = bar_dict.get('close') or bar_dict.get('Close')
                    if close is not None:
                        try:
                            prices[sym] = float(close)
                        except (ValueError, TypeError):
                            pass
                if prices:
                    import asyncio
                    # update_market_prices is async; run synchronously in warmup
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # We're already in an async context — use create_task workaround
                            # Simpler: directly update the deque (same effect as the async method)
                            for symbol, price in prices.items():
                                p = float(price)
                                if p > 0:
                                    self.risk_manager._price_history[symbol].append(p)
                                    self.risk_manager.current_prices[symbol] = p
                        else:
                            loop.run_until_complete(
                                self.risk_manager.update_market_prices(prices, timestamp)
                            )
                    except Exception:
                        # Direct fallback
                        for symbol, price in prices.items():
                            p = float(price)
                            if p > 0:
                                self.risk_manager._price_history[symbol].append(p)
                                self.risk_manager.current_prices[symbol] = p

            # Regime engine — feed bar for EWMA state priming
            if self.regime_engine and hasattr(self.regime_engine, 'process_market_data'):
                regime_bar = dict(bar_dict)
                if timestamp is not None:
                    regime_bar['timestamp'] = timestamp
                try:
                    self.regime_engine.process_market_data(regime_bar)
                except Exception:
                    pass  # Non-fatal during warmup

        logger.info(f"   Session warmup complete ({n} bars replayed)")

    def _collect_warmup_bars_before_date(self, target_date) -> List:
        """Collect bars before ``target_date`` for session warmup.

        Scans ``self.historical_data`` for all bars whose date is strictly
        before ``target_date``, then returns the **last N** bars (where N
        is ``warmup_bars`` from config, default 200).  Taking from the tail
        ensures that multi-day and individual-day runs replay the *same*
        bars — the most recent history before the target date — even if the
        multi-day run has more historical data loaded.
        """
        if self.historical_data is None or self.historical_data.empty:
            return []

        all_prior = []
        for _idx, row in self.historical_data.iterrows():
            ts = row.get('timestamp', _idx)
            try:
                row_date = pd.Timestamp(ts).date()
            except Exception:
                continue
            if row_date >= target_date:
                break
            all_prior.append(row)

        # Cap to warmup_bars from config (deterministic, same in both paths)
        warmup_cap = int(getattr(self.config, 'warmup_bars', 200) or 200)
        if len(all_prior) > warmup_cap:
            all_prior = all_prior[-warmup_cap:]

        return all_prior

    def _update_current_prices_from_market_data(self, timestamp: Any) -> None:
        """Update risk-manager mark-to-market prices for all symbols."""
        if not (self.risk_manager and hasattr(self.risk_manager, 'current_prices')):
            return

        bar_ts = pd.Timestamp(timestamp)
        tz_align_cache = {} if self._use_fast_tz_alignment else None
        for sym, sym_df in self.market_data.items():
            try:
                if sym_df.empty:
                    continue

                fast_close = self._get_latest_close_price_fast(sym, sym_df, bar_ts, tz_align_cache=tz_align_cache)
                if fast_close is not None:
                    self.risk_manager.current_prices[sym] = fast_close
                    continue

                if isinstance(sym_df.index, pd.DatetimeIndex):
                    idx_obj = sym_df.index
                elif 'timestamp' in sym_df.columns:
                    idx_obj = pd.DatetimeIndex(sym_df['timestamp'])
                else:
                    continue

                ts_cmp = self._align_timestamp_to_index_tz(
                    bar_ts,
                    getattr(idx_obj, 'tz', None),
                    cache=tz_align_cache,
                )

                mask = idx_obj <= ts_cmp
                if mask.any():
                    last_idx = mask[::-1].idxmax() if isinstance(mask.index, pd.RangeIndex) else mask.values.nonzero()[0][-1]
                    close_col = 'close' if 'close' in sym_df.columns else 'Close'
                    if close_col in sym_df.columns:
                        self.risk_manager.current_prices[sym] = float(sym_df[close_col].iloc[last_idx])
            except Exception as price_err:
                logger.debug(f"Per-bar price update for {sym}: {price_err}")

    def _get_latest_close_price_fast(
        self,
        symbol: str,
        sym_df: pd.DataFrame,
        bar_ts: pd.Timestamp,
        tz_align_cache: Optional[Dict[Any, pd.Timestamp]] = None,
    ) -> Optional[float]:
        """Fast latest-close lookup using cached datetime index + searchsorted."""
        if not self._use_fast_price_update:
            return None

        cache = self._price_lookup_cache.get(symbol)
        if cache is None:
            cache = self._build_price_lookup_cache(sym_df)
            # Store sentinel to avoid rebuilding unsupported symbols each bar
            self._price_lookup_cache[symbol] = cache if cache is not None else {'disabled': True}
            cache = self._price_lookup_cache[symbol]

        if cache.get('disabled', False):
            return None

        idx_obj = cache['idx_obj']
        idx_tz = cache['idx_tz']
        ts_cmp = self._align_timestamp_to_index_tz(
            bar_ts,
            idx_tz,
            cache=tz_align_cache,
        )

        pos = int(idx_obj.searchsorted(ts_cmp, side='right')) - 1
        if pos < 0:
            return None

        value = cache['close_values'][pos]
        if pd.isna(value):
            return None
        return float(value)

    def _build_price_lookup_cache(self, sym_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Build cache for fast latest-close lookup; returns None if unsupported."""
        if sym_df is None or sym_df.empty:
            return None

        if isinstance(sym_df.index, pd.DatetimeIndex):
            idx_obj = sym_df.index
        elif 'timestamp' in sym_df.columns:
            idx_obj = pd.DatetimeIndex(sym_df['timestamp'])
        else:
            return None

        close_col = 'close' if 'close' in sym_df.columns else 'Close'
        if close_col not in sym_df.columns:
            return None

        if not getattr(idx_obj, 'is_monotonic_increasing', False):
            return None

        return {
            'idx_obj': idx_obj,
            'idx_tz': getattr(idx_obj, 'tz', None),
            'close_values': sym_df[close_col].to_numpy(copy=False),
        }

