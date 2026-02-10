# Phase 0: Propagation Backscan — Engineering Plan

**Version:** 1.0
**Date:** February 10, 2026
**Status:** READY FOR IMPLEMENTATION
**Objective:** Determine whether propagation is a statistically distinct, economically tradable market state — or noise.
**Time Budget:** 48-72 hours of computation. Decision within one week.

---

## 0. Research Charter (Non-Negotiable Preamble)

### Hypothesis

> Markets occasionally enter a propagation state characterized by high directional
> transmission efficiency, failing opposition, stored volatility release, and
> accelerating structure. This state should exhibit superior trade geometry
> (lower MAE, better skew, improved follow-through) relative to non-propagation periods.

### Objective

**Detect the state — NOT optimize returns.**

Returns are validation evidence. State detection is the objective function.
If features are tuned to maximize return prediction, the project is already dead.

### Kill Criteria (Written Before Code Exists)

All four must pass. No committee debates later.

| # | Criterion | Test | Threshold |
|---|-----------|------|-----------|
| 1 | **Statistical** | Q5 vs Q1 direction-adjusted forward returns, permutation test | p < 0.05 post-cost, in ≥ 3 vol regimes |
| 2 | **Economic** | Risk-adjusted return per trade improvement | ≥ 15% vs random-entry baseline |
| 3 | **Stability** | First-half vs second-half of sample | Quintile ordering preserved in both halves |
| 4 | **Monotonicity** | Q1 through Q5 forward returns | Clean gradient (≤ 1 adjacent inversion allowed) |
| 5 | **Left-Tail** | MAE 95th percentile, high-PS vs low-PS | ≥ 15% reduction in 95th-pctile MAE |

### Decision Tree

```
IF 3+ kill criteria fail → TERMINATE. No tweaks. No rescue.
IF statistical passes but economic weak → EXIT-ONLY deployment (Phase 3).
IF all pass → Proceed to Phase 1 (Feature Pipeline).
```

---

## 1. Data Specification

### Source

Use `ClickHouseDataManager.load_market_data()` from `core_engine/data/manager.py`.

```python
from core_engine.data.manager import ClickHouseDataManager
from core_engine.data.rth_filter import filter_bars_to_rth

data_manager = ClickHouseDataManager(config)
await data_manager.initialize()

raw_data = await data_manager.load_market_data(
    symbols=UNIVERSE,
    start_time=START_DATE,
    end_time=END_DATE,
    interval="1min"
)
```

### Universe

```python
# Structurally liquid, no cherry-picking
# Includes market proxy for RPS computation
UNIVERSE = [
    # Core equity (high-ADV, institutional flow)
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
    # Market proxy (REQUIRED for RPS decomposition)
    'SPY', 'QQQ',
]

# Minimum: 6 months. Preferred: 9-12 months.
# Must span multiple volatility regimes.
START_DATE = datetime(2025, 2, 1)   # Adjust to available data
END_DATE   = datetime(2025, 12, 31) # Adjust to available data
```

### RTH Filtering (Mandatory)

All features computed on RTH bars only. Overnight gaps are NOT part of propagation paths.

```python
from core_engine.data.market_calendar import MarketCalendar
calendar = MarketCalendar()

for symbol in UNIVERSE:
    symbol_data = raw_data[raw_data['symbol'] == symbol].copy()
    symbol_data = filter_bars_to_rth(symbol_data, symbol=symbol, calendar=calendar)
```

### Data Integrity Checks (Run Before Any Feature Computation)

```python
def validate_data(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Must pass before feature computation begins."""
    report = {
        'symbol': symbol,
        'total_bars': len(df),
        'date_range': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
        'trading_days': df['timestamp'].dt.date.nunique(),
        'missing_rate': _compute_missing_rate(df),  # gaps in expected 1-min sequence
        'zero_volume_rate': (df['volume'] == 0).mean(),
        'duplicate_timestamps': df['timestamp'].duplicated().sum(),
        'price_anomalies': _detect_price_anomalies(df),  # >10% 1-bar moves
    }
    
    # Hard gates
    assert report['missing_rate'] < 0.005, f"{symbol}: Missing rate {report['missing_rate']:.4f} > 0.5%"
    assert report['duplicate_timestamps'] == 0, f"{symbol}: {report['duplicate_timestamps']} duplicate timestamps"
    assert report['trading_days'] >= 120, f"{symbol}: Only {report['trading_days']} trading days (need ≥120)"
    
    return report

def _compute_missing_rate(df: pd.DataFrame) -> float:
    """Compute fraction of expected 1-min bars that are missing within RTH sessions."""
    expected_bars_per_day = 390  # 9:30 AM to 4:00 PM = 390 minutes
    trading_days = df['timestamp'].dt.date.nunique()
    expected_total = trading_days * expected_bars_per_day
    return 1.0 - len(df) / max(expected_total, 1)

def _detect_price_anomalies(df: pd.DataFrame) -> int:
    """Count bars with >10% price change (likely data errors or splits)."""
    returns = df['close'].pct_change().abs()
    return (returns > 0.10).sum()
```

**Print and log:**
```
Data Coverage: X bars per symbol (avg)
Symbols: N
Date Range: YYYY-MM-DD to YYYY-MM-DD
Trading Days: N
Missing Rate: X.XX%
Zero-Volume Rate: X.XX%
```

If missing > 0.5% for any symbol: fix or exclude that symbol before proceeding.

### Session Boundary Handling (Critical for Path Features)

Features that measure path structure (PathEff, CounterFail) must NOT span overnight gaps.

```python
def add_session_boundaries(df: pd.DataFrame) -> pd.DataFrame:
    """Mark session starts for feature computation boundaries."""
    df = df.sort_values('timestamp').copy()
    df['date'] = df['timestamp'].dt.date
    df['session_bar_num'] = df.groupby('date').cumcount()
    df['is_session_start'] = df['session_bar_num'] == 0
    # Time gap > 5 minutes between consecutive bars = session break
    df['time_gap'] = df['timestamp'].diff().dt.total_seconds()
    df['is_gap'] = df['time_gap'] > 300  # 5-minute gap threshold
    return df
```

When computing rolling features, reset at session boundaries:

```python
def session_safe_rolling(series: pd.Series, window: int, 
                         session_starts: pd.Series, func) -> pd.Series:
    """Apply rolling function, resetting at session boundaries.
    
    NaN is produced for any window that spans a session boundary.
    """
    result = pd.Series(np.nan, index=series.index)
    session_groups = session_starts.cumsum()
    for _, group_idx in series.groupby(session_groups).groups.items():
        group = series.loc[group_idx]
        if len(group) >= window:
            result.loc[group_idx] = func(group, window)
    return result
```

---

## 2. Feature Construction

### Design Principles

1. **Compute, do not tune.** Use reasonable defaults. Move on.
2. **Session-safe.** No feature spans overnight gaps.
3. **Point-in-time.** Percentile normalization uses ONLY past data (trailing window). No future information.
4. **Coarse-correct.** If a feature requires surgical parameters to work, it is not structural.

### 2.1 PathEff — Directional Transmission Efficiency

**What it measures:** How efficiently price displacement accumulates vs. realized path variance.

```python
def compute_path_efficiency(df: pd.DataFrame, window: int) -> pd.Series:
    """
    PathEff = |displacement| / (realized_vol * sqrt(window) + epsilon)
    
    Under random walk: E[PathEff] ≈ 1.0
    PathEff >> 1: structured directional flow (straighter path than noise)
    PathEff << 1: mean-reverting or choppy
    
    Args:
        df: DataFrame with 'close' column, session-boundary-aware
        window: lookback in bars
    Returns:
        Series of PathEff values
    """
    close = df['close']
    returns = close.pct_change()
    
    displacement = (close - close.shift(window)).abs()
    realized_vol = returns.rolling(window).std() * np.sqrt(window)
    
    epsilon = 1e-8
    path_eff = displacement / (realized_vol + epsilon)
    
    # NaN at session boundaries
    path_eff[df['is_session_start'].rolling(window).sum() > 0] = np.nan
    
    return path_eff
```

**Multi-scale computation:**

```python
PATHEFF_WINDOWS = [5, 15, 45]

for w in PATHEFF_WINDOWS:
    df[f'patheff_{w}'] = compute_path_efficiency(df, w)

# Primary PathEff: geometric mean across scales (coherence across scales = no dispersion)
df['patheff_multiscale'] = np.exp(
    np.log(df[[f'patheff_{w}' for w in PATHEFF_WINDOWS]].clip(lower=1e-8)).mean(axis=1)
)
```

**Normalization (point-in-time, trailing 5 trading days = ~1950 RTH bars):**

```python
NORM_WINDOW = 1950  # ~5 trading days of 1-min bars

def percentile_normalize(series: pd.Series, window: int) -> pd.Series:
    """Point-in-time percentile rank within trailing window. Output: [0, 1]."""
    def _pctile(x):
        if len(x) < window * 0.5:  # require ≥50% data
            return np.nan
        return (x.values[:-1] < x.values[-1]).mean()
    return series.rolling(window, min_periods=window // 2).apply(_pctile, raw=False)

df['patheff_norm'] = percentile_normalize(df['patheff_multiscale'], NORM_WINDOW)
```

### 2.2 CounterFail — Opposition Failure + Recovery Quality

**What it measures:** Two-stage institutional footprint: (A) opposing moves fail, (B) direction reasserts quickly.

```python
def compute_counter_fail(df: pd.DataFrame, 
                         trend_window: int = 15,
                         min_counter_bars: int = 2) -> pd.Series:
    """
    Detect counter-moves and measure their failure characteristics.
    
    For each bar, look back over recent counter-move events and score:
    - depth: how deep was the counter-move relative to ATR?
    - duration: how many bars did it last?
    - recovery_speed: how quickly did price return to pre-counter level?
    - recovery_efficiency: did PathEff recover after the counter-move?
    
    Output: [0, 1] where 1 = perfect counter-move failure (shallow, brief, fast recovery)
    """
    close = df['close']
    atr = df['atr'] if 'atr' in df.columns else _compute_atr(df, 14)
    
    # Determine dominant direction over trend_window
    direction = np.sign(close - close.shift(trend_window))
    
    # Identify counter-move bars: return sign opposes dominant direction
    bar_return = close.pct_change()
    is_counter = (np.sign(bar_return) != direction) & (direction != 0)
    
    # Label counter-move episodes (consecutive counter bars)
    counter_episodes = (is_counter != is_counter.shift(1)).cumsum()
    counter_episodes[~is_counter] = 0  # only label counter bars
    
    # For each episode, compute characteristics
    result = pd.Series(np.nan, index=df.index)
    
    # Vectorized approximation for efficiency:
    # Rolling statistics of counter-move characteristics
    for lookback in [20, 40]:  # recent history
        # depth: max adverse excursion during counter-moves / ATR
        depth_score = _rolling_counter_depth(close, direction, atr, lookback)
        # duration: average counter-move length
        duration_score = _rolling_counter_duration(is_counter, lookback)
        # recovery: how quickly does direction resume
        recovery_score = _rolling_recovery_quality(close, direction, is_counter, lookback)
        
        # Two-stage score: opposition failure * recovery quality
        fail_score = (1 / (1 + depth_score)) * (1 / (1 + duration_score))
        episode_score = fail_score * recovery_score
        
        result = result.combine_first(episode_score)
    
    return result.clip(0, 1)
```

**Helper functions (simplified for clarity — production should vectorize):**

```python
def _rolling_counter_depth(close, direction, atr, window):
    """Average depth of counter-moves in ATR units over trailing window."""
    adverse = pd.Series(0.0, index=close.index)
    # For each bar, measure distance against dominant direction
    for i in range(1, min(window, len(close))):
        move = (close - close.shift(i)) * (-direction.shift(i))
        adverse = adverse.combine(move.clip(lower=0), max)
    return (adverse / atr.clip(lower=1e-8)).rolling(window).mean()

def _rolling_counter_duration(is_counter, window):
    """Average duration of counter-move episodes over trailing window."""
    # Length of current counter-move streak
    streak = is_counter.groupby((~is_counter).cumsum()).cumsum()
    return streak.rolling(window).mean()

def _rolling_recovery_quality(close, direction, is_counter, window):
    """How quickly does PathEff-like efficiency recover after counter-moves."""
    # Simplified: ratio of forward-direction bars to total bars after counter ends
    post_counter = is_counter.shift(1) & ~is_counter  # first bar after counter ends
    # Count how many of the next 5 bars are directional
    forward_align = pd.Series(0.0, index=close.index)
    for offset in range(1, 6):
        bar_dir = np.sign(close.pct_change().shift(-offset))
        forward_align += (bar_dir == direction).astype(float)
    recovery = forward_align / 5.0
    # Only measure at post-counter points, then forward-fill
    recovery[~post_counter] = np.nan
    return recovery.rolling(window, min_periods=1).mean().ffill().clip(0, 1)
```

**Normalization:**

```python
df['counterfail_norm'] = percentile_normalize(
    df['counterfail_raw'], NORM_WINDOW
)
```

### 2.3 VolStore — Stored Energy + Release

**What it measures:** Volatility compression followed by active release. NOT a ratio — a state machine.

```python
def compute_vol_store(df: pd.DataFrame,
                      short_span: int = 5,
                      long_span: int = 45,
                      compression_threshold: float = 0.7,
                      release_ratio: float = 1.5,
                      min_compression_bars: int = 10) -> pd.Series:
    """
    VolStore captures the compression → release transition.
    
    States:
    - NEUTRAL: no compression or release
    - COMPRESSING: vol_short / vol_long < threshold (energy accumulating)
    - RELEASING: vol_short rapidly expanding after compression period
    
    Output: [0, 1] where 1 = deep + long compression now actively releasing
    """
    returns = df['close'].pct_change()
    
    vol_short = returns.ewm(span=short_span).std()
    vol_long = returns.ewm(span=long_span).std()
    
    compression_ratio = vol_short / vol_long.clip(lower=1e-8)
    
    # Compression detection: ratio below threshold
    is_compressed = compression_ratio < compression_threshold
    
    # Compression duration: consecutive bars of compression
    compression_streak = is_compressed.groupby((~is_compressed).cumsum()).cumsum()
    
    # Release detection: vol_short expanding rapidly after compression
    vol_short_change = vol_short / vol_short.shift(3).clip(lower=1e-8)
    is_releasing = (vol_short_change > release_ratio) & (compression_streak.shift(1) >= min_compression_bars)
    
    # Energy score: depth * log(1 + duration)
    compression_depth = (1 - compression_ratio).clip(lower=0)
    raw_store = compression_depth * np.log1p(compression_streak)
    
    # Only produce score when actively releasing (or within release window)
    # Release window: 10 bars after release trigger
    release_window = is_releasing.rolling(10).sum() > 0
    
    vol_store = pd.Series(0.0, index=df.index)
    vol_store[release_window] = raw_store[release_window]
    
    # Normalize
    max_store = raw_store.rolling(NORM_WINDOW, min_periods=NORM_WINDOW // 2).quantile(0.99)
    vol_store_norm = (vol_store / max_store.clip(lower=1e-8)).clip(0, 1)
    
    return vol_store_norm
```

### 2.4 PropAccel — Formation Velocity of Structure

**What it measures:** Rate of change of PathEff — is directional structure forming right now?

```python
def compute_prop_accel(df: pd.DataFrame,
                       base_k: int = 5,
                       vol_ref_window: int = 100) -> pd.Series:
    """
    PropAccel = d(PathEff) / dt, with regime-adaptive lookback.
    
    Lookback k scales with volatility:
    - High vol → longer k (need more bars to confirm genuine acceleration)
    - Low vol → shorter k (signal arrives faster in calm markets)
    
    Output: raw acceleration (will be sigmoid-mapped in PS aggregation)
    """
    patheff = df['patheff_multiscale']
    returns = df['close'].pct_change()
    
    vol_current = returns.ewm(span=20).std()
    vol_ref = returns.rolling(vol_ref_window).std().rolling(vol_ref_window).mean()
    
    # Adaptive lookback: scale base_k by vol ratio, bounded [3, 15]
    vol_ratio = (vol_current / vol_ref.clip(lower=1e-8)).clip(0.5, 3.0)
    adaptive_k = (base_k * vol_ratio).round().clip(3, 15).astype(int)
    
    # Compute acceleration with adaptive lookback
    # Vectorized approximation: use median adaptive_k for efficiency
    median_k = int(adaptive_k.median())
    prop_accel = (patheff - patheff.shift(median_k)) / median_k
    
    return prop_accel
```

### 2.5 Propagation Direction

**Critical addition not in the expert's template.** PS measures intensity. Direction determines which way to trade.

```python
def compute_propagation_direction(df: pd.DataFrame, window: int = 15) -> pd.Series:
    """
    Signed direction of propagation. +1 = upward propagation, -1 = downward.
    
    Based on the sign of displacement over the dominant PathEff window.
    Smoothed to avoid bar-to-bar flipping.
    """
    displacement = df['close'] - df['close'].shift(window)
    # Smooth with EMA to prevent jitter
    smooth_displacement = displacement.ewm(span=5).mean()
    return np.sign(smooth_displacement)
```

### 2.6 Propagation Score Aggregation

```python
def compute_propagation_score(df: pd.DataFrame) -> pd.Series:
    """
    PS = (PathEff * CounterFail * max(VolStore, floor) * sigmoid(PropAccel))^(1/4)
    
    Geometric mean: weak components veto the score.
    VolStore floor (0.3): allows continuation trades without prior compression.
    Sigmoid on PropAccel: maps acceleration to (0, 1) smoothly.
    """
    patheff = df['patheff_norm'].clip(lower=1e-8)
    counterfail = df['counterfail_norm'].clip(lower=1e-8)
    volstore = df['volstore_norm'].clip(lower=0.3)  # floor
    
    # Sigmoid: maps PropAccel to (0, 1) with inflection at 0
    prop_accel_sigmoid = 1 / (1 + np.exp(-5 * df['prop_accel_norm']))
    prop_accel_sigmoid = prop_accel_sigmoid.clip(lower=1e-8)
    
    ps = (patheff * counterfail * volstore * prop_accel_sigmoid) ** 0.25
    
    return ps

def compute_prop_accel_norm(df: pd.DataFrame) -> pd.Series:
    """Normalize PropAccel to roughly [-1, 1] via trailing percentile."""
    raw = df['prop_accel_raw']
    abs_ref = raw.abs().rolling(NORM_WINDOW, min_periods=NORM_WINDOW // 2).quantile(0.95)
    return (raw / abs_ref.clip(lower=1e-8)).clip(-1, 1)
```

### 2.7 Diagnostics (Feature Layer)

```python
def compute_diagnostics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute PS diagnostic metadata."""
    
    # PS velocity: rate of PS change (campaign vs spike classifier)
    df['ps_velocity'] = df['ps'].diff(3) / 3
    
    # Component divergence: std of normalized components (high = components disagree)
    components = df[['patheff_norm', 'counterfail_norm', 'volstore_norm']].copy()
    components['propaccel_sig'] = 1 / (1 + np.exp(-5 * df['prop_accel_norm']))
    df['ps_component_divergence'] = components.std(axis=1)
    
    # RPS: idiosyncratic vs beta decomposition (for non-ETF symbols)
    # Computed in cross-sectional step (Section 2.8)
    
    return df
```

### 2.8 Relative Propagation Strength (RPS)

Computed cross-sectionally after PS is available for all symbols.

```python
def compute_rps(all_data: Dict[str, pd.DataFrame], 
                market_proxy: str = 'SPY',
                beta_window: int = 1950) -> Dict[str, pd.DataFrame]:
    """
    RPS = Symbol_PS - beta_PS * Market_PS
    
    Decomposes propagation into systematic (beta) and idiosyncratic components.
    """
    market_ps = all_data[market_proxy]['ps']
    
    for symbol, df in all_data.items():
        if symbol == market_proxy:
            df['rps'] = 0.0  # market is its own beta
            continue
        
        symbol_ps = df['ps']
        
        # Rolling OLS: symbol_PS = alpha + beta * market_PS
        # Use simple rolling correlation * vol ratio as beta estimate
        rolling_cov = symbol_ps.rolling(beta_window).cov(market_ps)
        rolling_var = market_ps.rolling(beta_window).var()
        beta_ps = (rolling_cov / rolling_var.clip(lower=1e-8)).clip(-3, 3)
        
        df['rps'] = symbol_ps - beta_ps * market_ps
    
    return all_data
```

---

## 3. Forward Return Computation

**This section closes Gap 4 from the critique: forward returns must be precisely defined.**

### Direction-Adjusted Forward Returns

```python
def compute_forward_returns(df: pd.DataFrame, 
                            horizons: List[int] = [5, 15, 30]) -> pd.DataFrame:
    """
    Compute direction-adjusted forward returns.
    
    CRITICAL SPECIFICATIONS:
    - Entry: at CLOSE of signal bar (we observe PS at bar close)
    - Exit: at CLOSE of bar t+horizon
    - Direction: signed by propagation direction at entry
    - Session-safe: returns that span overnight are marked (not excluded, but flagged)
    
    Returns are in basis points for interpretability.
    """
    for h in horizons:
        # Raw forward return
        raw_fwd = (df['close'].shift(-h) / df['close'] - 1) * 10000  # bps
        
        # Direction-adjusted: positive = correct direction
        direction = df['prop_direction']
        df[f'fwd_return_{h}bar_bps'] = raw_fwd * direction
        
        # Flag returns that span overnight
        df[f'fwd_spans_overnight_{h}bar'] = (
            df['is_session_start'].shift(-1).rolling(h).sum() > 0
        )
    
    return df
```

### Transaction Cost Deduction

Use the existing calibrated model parameters from `base_config.yaml`:

```python
# From existing system: conservative round-trip cost estimate
# spread: 5 bps (one-way) + slippage: 2 bps (one-way) + commission: ~0.5 bps
# Round-trip: ~15 bps total
ROUND_TRIP_COST_BPS = 15.0

for h in [5, 15, 30]:
    df[f'fwd_return_{h}bar_net_bps'] = df[f'fwd_return_{h}bar_bps'] - ROUND_TRIP_COST_BPS
```

---

## 4. Statistical Tests

### Addressing Temporal Dependence (Gap 2)

PS values on consecutive bars are highly autocorrelated. Naive significance tests overstate p-values by 5-10x.

**Solution: Block-bootstrap permutation tests.**

```python
def block_permutation_test(ps_quintiles: pd.Series, 
                           forward_returns: pd.Series,
                           n_permutations: int = 5000,
                           block_size: int = 30) -> float:
    """
    Test whether Q5 forward returns differ from Q1 using block permutation.
    
    Block bootstrap preserves temporal autocorrelation structure.
    Block size of 30 bars (~30 minutes) captures typical PS persistence.
    
    Returns: p-value
    """
    q5_mask = ps_quintiles == 5
    q1_mask = ps_quintiles == 1
    
    observed_diff = forward_returns[q5_mask].mean() - forward_returns[q1_mask].mean()
    
    # Block permutation: shuffle blocks, not individual bars
    n_blocks = len(ps_quintiles) // block_size
    block_labels = np.repeat(np.arange(n_blocks), block_size)[:len(ps_quintiles)]
    
    null_diffs = []
    for _ in range(n_permutations):
        # Shuffle block assignments
        shuffled_blocks = np.random.permutation(n_blocks)
        shuffled_quintiles = ps_quintiles.copy()
        for new_pos, old_block in enumerate(shuffled_blocks):
            old_mask = block_labels == old_block
            new_mask = block_labels == new_pos
            shuffled_quintiles.iloc[new_mask] = ps_quintiles.iloc[old_mask].values
        
        sq5 = shuffled_quintiles == 5
        sq1 = shuffled_quintiles == 1
        if sq5.sum() > 0 and sq1.sum() > 0:
            null_diffs.append(
                forward_returns[sq5].mean() - forward_returns[sq1].mean()
            )
    
    p_value = (np.array(null_diffs) >= observed_diff).mean()
    return p_value
```

### Minimum Sample Size Per Cell

```python
MIN_OBSERVATIONS_PER_CELL = 50  # minimum independent observations per quintile-regime cell

# With block_size=30, effective independent observations ≈ total_bars / 30
# For 6 months (≈ 48,750 RTH bars per symbol), effective N ≈ 1625 per symbol
# Per quintile: ~325 effective observations → sufficient
# Per quintile-regime (15 cells): ~108 → marginal but acceptable
```

---

## 5. Test Sequence (13 Tests, Ordered)

### Test 1: State Detection — Distribution Analysis

```python
def test_state_detection(df: pd.DataFrame) -> Dict[str, Any]:
    """Does PS identify a distinct market state?"""
    ps = df['ps'].dropna()
    
    results = {}
    
    # A. Distribution shape
    results['skewness'] = ps.skew()
    results['kurtosis'] = ps.kurtosis()
    results['is_right_skewed'] = ps.skew() > 0.5  # expect fat right tail
    
    # B. Hartigan's dip test for multimodality (optional but powerful)
    try:
        from diptest import diptest
        dip_stat, dip_pval = diptest(ps.values)
        results['dip_statistic'] = dip_stat
        results['dip_pvalue'] = dip_pval
        results['is_multimodal'] = dip_pval < 0.05
    except ImportError:
        results['dip_test'] = 'SKIPPED (diptest not installed)'
    
    # C. Is PS Gaussian? (Bad sign if yes)
    from scipy.stats import normaltest
    stat, pval = normaltest(ps.values)
    results['normality_pvalue'] = pval
    results['is_non_gaussian'] = pval < 0.05  # WANT this to be True
    
    # PASS if: non-Gaussian AND (right-skewed OR multimodal)
    results['PASS'] = results['is_non_gaussian'] and results.get('is_right_skewed', True)
    
    return results
```

### Test 2: State Detection — Temporal Clustering

```python
def test_temporal_clustering(df: pd.DataFrame, 
                             threshold_pctile: float = 0.80) -> Dict[str, Any]:
    """Does high PS persist? Or is it random jitter?"""
    ps = df['ps']
    threshold = ps.quantile(threshold_pctile)
    
    is_high = ps > threshold
    
    # Duration of high-PS episodes
    episodes = (is_high != is_high.shift(1)).cumsum()
    episode_durations = is_high.groupby(episodes).sum()
    episode_durations = episode_durations[episode_durations > 0]
    
    results = {
        'n_episodes': len(episode_durations),
        'median_duration_bars': episode_durations.median(),
        'mean_duration_bars': episode_durations.mean(),
        'max_duration_bars': episode_durations.max(),
        'p90_duration_bars': episode_durations.quantile(0.9),
    }
    
    # PASS if median duration ≥ 5 bars (propagation should persist ≥5 minutes)
    results['PASS'] = results['median_duration_bars'] >= 5
    
    return results
```

### Test 3: Conditional Return Analysis (Quintile Stratification)

```python
def test_conditional_returns(df: pd.DataFrame, 
                             horizon: int = 15) -> Dict[str, Any]:
    """When PS is high, are returns different?"""
    ps = df['ps'].dropna()
    fwd = df[f'fwd_return_{horizon}bar_net_bps'].dropna()
    
    # Align
    common_idx = ps.index.intersection(fwd.index)
    ps = ps.loc[common_idx]
    fwd = fwd.loc[common_idx]
    
    # Quintile assignment
    quintiles = pd.qcut(ps, 5, labels=[1, 2, 3, 4, 5])
    
    # Statistics per quintile
    table = {}
    for q in range(1, 6):
        mask = quintiles == q
        q_returns = fwd[mask]
        table[f'Q{q}'] = {
            'n_obs': len(q_returns),
            'mean_bps': q_returns.mean(),
            'median_bps': q_returns.median(),
            'std_bps': q_returns.std(),
            'skew': q_returns.skew(),
            'hit_rate': (q_returns > 0).mean(),
            'p95_loss_bps': q_returns.quantile(0.05),  # 5th percentile = worst outcomes
        }
    
    results = {
        'table': table,
        'q5_minus_q1_mean': table['Q5']['mean_bps'] - table['Q1']['mean_bps'],
        'q5_minus_q1_hitrate': table['Q5']['hit_rate'] - table['Q1']['hit_rate'],
        'q5_skew_improvement': table['Q5']['skew'] - table['Q1']['skew'],
    }
    
    return results
```

### Test 4: Monotonicity Test

```python
def test_monotonicity(quintile_table: Dict) -> Dict[str, Any]:
    """Clean Q1 < Q2 < Q3 < Q4 < Q5 gradient in forward returns."""
    means = [quintile_table[f'Q{q}']['mean_bps'] for q in range(1, 6)]
    
    inversions = sum(1 for i in range(4) if means[i+1] < means[i])
    is_monotonic = inversions <= 1  # allow 1 adjacent inversion
    
    # Spearman rank correlation between quintile number and mean return
    from scipy.stats import spearmanr
    ranks = list(range(1, 6))
    corr, pval = spearmanr(ranks, means)
    
    results = {
        'quintile_means': means,
        'inversions': inversions,
        'spearman_corr': corr,
        'spearman_pval': pval,
        'PASS': is_monotonic and corr > 0.8
    }
    
    return results
```

### Test 5: Left-Tail / MAE Test

```python
def test_left_tail(df: pd.DataFrame, horizon: int = 30) -> Dict[str, Any]:
    """Does high PS reduce maximum adverse excursion?"""
    ps = df['ps'].dropna()
    
    quintiles = pd.qcut(ps, 5, labels=[1, 2, 3, 4, 5])
    
    # Compute MAE: worst drawdown within horizon bars after entry
    mae = pd.Series(np.nan, index=df.index)
    direction = df['prop_direction']
    
    for i in range(len(df) - horizon):
        entry_price = df['close'].iloc[i]
        future_prices = df['close'].iloc[i+1:i+horizon+1]
        
        if direction.iloc[i] == 1:  # long
            worst = (future_prices.min() - entry_price) / entry_price * 10000
        elif direction.iloc[i] == -1:  # short
            worst = (entry_price - future_prices.max()) / entry_price * 10000
        else:
            worst = np.nan
        
        mae.iloc[i] = worst  # negative = adverse
    
    df['mae_bps'] = mae
    
    # Compare MAE by quintile
    mae_by_quintile = {}
    for q in range(1, 6):
        mask = quintiles == q
        q_mae = mae[mask].dropna()
        mae_by_quintile[f'Q{q}'] = {
            'mean_mae_bps': q_mae.mean(),
            'median_mae_bps': q_mae.median(),
            'p95_mae_bps': q_mae.quantile(0.05),  # 5th percentile = deepest drawdowns
        }
    
    # Left-tail improvement: Q5 vs Q1
    q5_p95 = mae_by_quintile['Q5']['p95_mae_bps']
    q1_p95 = mae_by_quintile['Q1']['p95_mae_bps']
    
    # Both values are negative; improvement means Q5 is less negative (closer to 0)
    improvement_pct = (1 - q5_p95 / q1_p95) * 100 if q1_p95 != 0 else 0
    
    results = {
        'mae_by_quintile': mae_by_quintile,
        'tail_improvement_pct': improvement_pct,
        'PASS': improvement_pct >= 15  # ≥15% reduction in 95th-pctile MAE
    }
    
    return results
```

### Test 6: Statistical Significance (Block Permutation)

```python
def test_significance(df: pd.DataFrame, horizon: int = 15) -> Dict[str, Any]:
    """Block-bootstrap permutation test for Q5 vs Q1 return difference."""
    ps = df['ps'].dropna()
    fwd = df[f'fwd_return_{horizon}bar_net_bps'].dropna()
    
    common_idx = ps.index.intersection(fwd.index)
    ps = ps.loc[common_idx]
    fwd = fwd.loc[common_idx]
    
    quintiles = pd.qcut(ps, 5, labels=[1, 2, 3, 4, 5])
    
    p_value = block_permutation_test(quintiles, fwd, n_permutations=5000, block_size=30)
    
    results = {
        'p_value': p_value,
        'PASS': p_value < 0.05
    }
    
    return results
```

### Test 7: Regime Invariance

```python
def test_regime_invariance(df: pd.DataFrame, horizon: int = 15) -> Dict[str, Any]:
    """Does PS work across volatility regimes?"""
    returns = df['close'].pct_change()
    vol_20d = returns.rolling(20 * 390).std()  # 20-day realized vol
    
    vol_terciles = pd.qcut(vol_20d, 3, labels=['low_vol', 'mid_vol', 'high_vol'])
    
    results_by_regime = {}
    regime_passes = 0
    
    for regime in ['low_vol', 'mid_vol', 'high_vol']:
        mask = vol_terciles == regime
        regime_df = df[mask].copy()
        
        if len(regime_df) < MIN_OBSERVATIONS_PER_CELL * 5:
            results_by_regime[regime] = {'SKIP': 'insufficient data'}
            continue
        
        ps = regime_df['ps'].dropna()
        fwd = regime_df[f'fwd_return_{horizon}bar_net_bps'].dropna()
        common = ps.index.intersection(fwd.index)
        
        if len(common) < MIN_OBSERVATIONS_PER_CELL * 5:
            results_by_regime[regime] = {'SKIP': 'insufficient data'}
            continue
        
        quintiles = pd.qcut(ps.loc[common], 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
        
        q5_mean = fwd.loc[common][quintiles == 5].mean()
        q1_mean = fwd.loc[common][quintiles == 1].mean()
        
        mono_means = [fwd.loc[common][quintiles == q].mean() for q in range(1, 6)]
        inversions = sum(1 for i in range(4) if mono_means[i+1] < mono_means[i])
        
        regime_pass = (q5_mean > q1_mean) and (inversions <= 2)
        if regime_pass:
            regime_passes += 1
        
        results_by_regime[regime] = {
            'q5_minus_q1': q5_mean - q1_mean,
            'quintile_means': mono_means,
            'inversions': inversions,
            'PASS': regime_pass,
        }
    
    results = {
        'by_regime': results_by_regime,
        'regimes_passed': regime_passes,
        'PASS': regime_passes >= 2  # must work in ≥2 of 3 regimes
    }
    
    return results
```

### Test 8: Parameter Perturbation Surface

```python
def test_parameter_robustness(df_raw: pd.DataFrame) -> Dict[str, Any]:
    """Does performance degrade gracefully across parameter choices?"""
    
    # Vary PathEff windows
    window_sets = [
        [3, 10, 30],
        [5, 15, 45],   # default
        [8, 20, 60],
        [5, 13, 34],   # Fibonacci-like
        [4, 12, 40],
    ]
    
    results = {}
    q5_q1_diffs = []
    
    for i, windows in enumerate(window_sets):
        # Recompute PS with different windows
        test_df = compute_all_features(df_raw, patheff_windows=windows)
        
        ps = test_df['ps'].dropna()
        fwd = test_df['fwd_return_15bar_net_bps'].dropna()
        common = ps.index.intersection(fwd.index)
        
        quintiles = pd.qcut(ps.loc[common], 5, labels=[1, 2, 3, 4, 5])
        q5_q1 = fwd.loc[common][quintiles == 5].mean() - fwd.loc[common][quintiles == 1].mean()
        
        results[f'window_set_{i}'] = {
            'windows': windows,
            'q5_minus_q1': q5_q1,
        }
        q5_q1_diffs.append(q5_q1)
    
    # Check for graceful degradation: no cliff (max/min ratio < 5)
    diffs_arr = np.array(q5_q1_diffs)
    positive_diffs = diffs_arr[diffs_arr > 0]
    
    if len(positive_diffs) >= 3:
        ratio = positive_diffs.max() / positive_diffs.min()
        graceful = ratio < 5.0
    else:
        graceful = False
    
    results['all_positive'] = (diffs_arr > 0).sum()
    results['total_sets'] = len(window_sets)
    results['PASS'] = graceful and results['all_positive'] >= 4
    
    return results
```

### Test 9: RPS Validation (Beta Decomposition)

```python
def test_rps_validation(all_data: Dict[str, pd.DataFrame], 
                        horizon: int = 15) -> Dict[str, Any]:
    """Does idiosyncratic propagation outperform beta-driven propagation?"""
    
    high_ps_high_rps = []  # idiosyncratic
    high_ps_low_rps = []   # beta passenger
    
    for symbol, df in all_data.items():
        if symbol in ['SPY', 'QQQ']:  # skip market proxies
            continue
        
        ps = df['ps']
        rps = df['rps']
        fwd = df[f'fwd_return_{horizon}bar_net_bps']
        
        high_ps = ps > ps.quantile(0.8)
        high_rps = rps > rps.quantile(0.6)  # above-average idiosyncratic
        low_rps = rps < rps.quantile(0.4)   # below-average (beta-driven)
        
        mask_idio = high_ps & high_rps
        mask_beta = high_ps & low_rps
        
        high_ps_high_rps.extend(fwd[mask_idio].dropna().tolist())
        high_ps_low_rps.extend(fwd[mask_beta].dropna().tolist())
    
    idio_returns = np.array(high_ps_high_rps)
    beta_returns = np.array(high_ps_low_rps)
    
    results = {
        'idio_mean_bps': idio_returns.mean() if len(idio_returns) > 0 else np.nan,
        'beta_mean_bps': beta_returns.mean() if len(beta_returns) > 0 else np.nan,
        'idio_mae_p95': np.percentile(idio_returns, 5) if len(idio_returns) > 30 else np.nan,
        'beta_mae_p95': np.percentile(beta_returns, 5) if len(beta_returns) > 30 else np.nan,
        'idio_n': len(idio_returns),
        'beta_n': len(beta_returns),
    }
    
    results['idio_outperforms'] = results['idio_mean_bps'] > results['beta_mean_bps']
    results['PASS'] = results['idio_outperforms']  # informational, not a kill criterion
    
    return results
```

### Test 10: Trade Geometry Analysis

```python
def test_trade_geometry(df: pd.DataFrame, 
                        entry_threshold_pctile: float = 0.80,
                        horizon: int = 30) -> Dict[str, Any]:
    """Simulate naive entries at high PS. Measure trade behavior, not just returns."""
    
    ps = df['ps']
    threshold = ps.quantile(entry_threshold_pctile)
    direction = df['prop_direction']
    
    entries = ps > threshold
    # Thin entries: require ≥5 bars between entries (avoid clustering)
    entries = _thin_entries(entries, min_gap=5)
    
    trades = []
    for idx in df.index[entries]:
        pos = df.index.get_loc(idx)
        if pos + horizon >= len(df):
            continue
        
        entry_price = df['close'].iloc[pos]
        future_slice = df['close'].iloc[pos+1:pos+horizon+1]
        trade_dir = direction.iloc[pos]
        
        if trade_dir == 0:
            continue
        
        # Direction-adjusted price path
        if trade_dir == 1:
            adj_path = (future_slice.values - entry_price) / entry_price * 10000
        else:
            adj_path = (entry_price - future_slice.values) / entry_price * 10000
        
        # Metrics
        max_heat = adj_path.min()  # worst point
        time_to_profit = next((i for i, r in enumerate(adj_path) if r > 0), horizon)
        final_pnl = adj_path[-1] - ROUND_TRIP_COST_BPS
        max_favorable = adj_path.max()
        
        # Excursion ratio: max favorable / |max adverse|
        excursion_ratio = max_favorable / max(abs(max_heat), 1e-8)
        
        # Path smoothness: correlation of cumulative path with straight line
        if len(adj_path) > 2:
            ideal_line = np.linspace(0, adj_path[-1], len(adj_path))
            from scipy.stats import pearsonr
            smoothness, _ = pearsonr(adj_path, ideal_line)
        else:
            smoothness = np.nan
        
        trades.append({
            'max_heat_bps': max_heat,
            'time_to_profit_bars': time_to_profit,
            'final_pnl_bps': final_pnl,
            'excursion_ratio': excursion_ratio,
            'path_smoothness': smoothness,
        })
    
    if not trades:
        return {'PASS': False, 'reason': 'no trades generated'}
    
    trades_df = pd.DataFrame(trades)
    
    results = {
        'n_trades': len(trades_df),
        'mean_heat_bps': trades_df['max_heat_bps'].mean(),
        'mean_time_to_profit': trades_df['time_to_profit_bars'].mean(),
        'mean_excursion_ratio': trades_df['excursion_ratio'].mean(),
        'mean_path_smoothness': trades_df['path_smoothness'].mean(),
        'mean_pnl_bps': trades_df['final_pnl_bps'].mean(),
        'hit_rate': (trades_df['final_pnl_bps'] > 0).mean(),
        'PASS': (trades_df['excursion_ratio'].mean() > 1.5 and 
                 trades_df['mean_time_to_profit'].mean() < horizon * 0.5)
    }
    
    return results

def _thin_entries(entries: pd.Series, min_gap: int) -> pd.Series:
    """Ensure minimum gap between entries to avoid autocorrelation."""
    thinned = entries.copy()
    last_entry_idx = -min_gap - 1
    for i, val in enumerate(entries):
        if val and (i - last_entry_idx) >= min_gap:
            last_entry_idx = i
        else:
            thinned.iloc[i] = False
    return thinned
```

### Test 11: Shock Regime Inspection

```python
def test_shock_behavior(df: pd.DataFrame,
                        shock_dates: Optional[List[str]] = None) -> Dict[str, Any]:
    """Does PS spike before violent reversals during known events?"""
    
    if shock_dates is None:
        # Auto-detect: days with >3x normal daily range
        daily_range = df.groupby(df['timestamp'].dt.date).apply(
            lambda x: (x['high'].max() - x['low'].min()) / x['close'].iloc[0]
        )
        normal_range = daily_range.median()
        shock_days = daily_range[daily_range > 3 * normal_range].index.tolist()
    else:
        shock_days = [pd.Timestamp(d).date() for d in shock_dates]
    
    results = {
        'n_shock_days': len(shock_days),
        'shock_days': [str(d) for d in shock_days[:20]],  # first 20
    }
    
    # For each shock day, check PS behavior in the 30 bars before the reversal
    false_signals = 0
    total_checks = 0
    
    for day in shock_days:
        day_data = df[df['timestamp'].dt.date == day]
        if len(day_data) < 30:
            continue
        
        # Find the bar with maximum adverse move
        returns = day_data['close'].pct_change()
        worst_bar = returns.abs().idxmax()
        worst_bar_pos = day_data.index.get_loc(worst_bar)
        
        if worst_bar_pos < 10:
            continue
        
        # Was PS high in the 10 bars before the worst move?
        pre_shock_ps = day_data['ps'].iloc[max(0, worst_bar_pos-10):worst_bar_pos]
        if pre_shock_ps.mean() > day_data['ps'].quantile(0.7):
            false_signals += 1
        total_checks += 1
    
    results['false_signal_rate'] = false_signals / max(total_checks, 1)
    results['total_checks'] = total_checks
    # This is informational, not a kill criterion — maps the failure surface
    results['INFO'] = 'High false_signal_rate = PS unreliable during shocks (expected)'
    
    return results
```

### Test 12: Cross-Sectional PS Correlation

```python
def test_cross_sectional_correlation(all_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """When many symbols propagate simultaneously, portfolio risk spikes."""
    
    # Align PS across symbols
    symbols = [s for s in all_data if s not in ['SPY', 'QQQ']]
    ps_matrix = pd.DataFrame({s: all_data[s]['ps'] for s in symbols})
    
    # Rolling pairwise correlation (30-bar window)
    rolling_corr = ps_matrix.rolling(30).corr()
    
    # Average pairwise correlation per timestamp
    avg_corr = []
    for t in ps_matrix.index[30:]:
        corr_mat = rolling_corr.loc[t]
        # Upper triangle, excluding diagonal
        mask = np.triu(np.ones(corr_mat.shape), k=1).astype(bool)
        avg_corr.append(corr_mat.values[mask].mean())
    
    avg_corr = pd.Series(avg_corr, index=ps_matrix.index[30:])
    
    results = {
        'mean_ps_correlation': avg_corr.mean(),
        'p90_ps_correlation': avg_corr.quantile(0.9),
        'pct_time_high_corr': (avg_corr > 0.5).mean(),
        'INFO': 'High correlation = PS-driven trades will cluster. Risk engine must cap.'
    }
    
    return results
```

### Test 13: Temporal Stability (First Half vs Second Half)

```python
def test_temporal_stability(df: pd.DataFrame, horizon: int = 15) -> Dict[str, Any]:
    """Does the signal hold in both halves of the sample?"""
    
    midpoint = len(df) // 2
    first_half = df.iloc[:midpoint]
    second_half = df.iloc[midpoint:]
    
    results = {}
    for label, half in [('first_half', first_half), ('second_half', second_half)]:
        ps = half['ps'].dropna()
        fwd = half[f'fwd_return_{horizon}bar_net_bps'].dropna()
        common = ps.index.intersection(fwd.index)
        
        quintiles = pd.qcut(ps.loc[common], 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
        means = [fwd.loc[common][quintiles == q].mean() for q in range(1, 6)]
        inversions = sum(1 for i in range(4) if means[i+1] < means[i])
        
        results[label] = {
            'quintile_means': means,
            'inversions': inversions,
            'q5_minus_q1': means[4] - means[0],
            'is_monotonic': inversions <= 1,
        }
    
    # Both halves must show Q5 > Q1 and ≤2 inversions
    results['PASS'] = (
        results['first_half']['q5_minus_q1'] > 0 and
        results['second_half']['q5_minus_q1'] > 0 and
        results['first_half']['inversions'] <= 2 and
        results['second_half']['inversions'] <= 2
    )
    
    return results
```

---

## 6. Orchestration: Main Execution Script

```python
"""
Phase 0: Propagation Backscan
==============================
Run from project root:
    python -m backtest.experiments.phase0_propagation_backscan.run

Output: JSON results + decision page to backtest/results/phase0/
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd

# Data infrastructure
from core_engine.data.manager import ClickHouseDataManager
from core_engine.data.rth_filter import filter_bars_to_rth
from core_engine.data.market_calendar import MarketCalendar

# Local modules (to be implemented in this directory)
from .features import (
    compute_path_efficiency, compute_counter_fail, compute_vol_store,
    compute_prop_accel, compute_propagation_direction, compute_propagation_score,
    compute_prop_accel_norm, compute_diagnostics, compute_rps,
    add_session_boundaries, percentile_normalize, compute_forward_returns,
    compute_all_features
)
from .tests import (
    test_state_detection, test_temporal_clustering, test_conditional_returns,
    test_monotonicity, test_left_tail, test_significance,
    test_regime_invariance, test_parameter_robustness, test_rps_validation,
    test_trade_geometry, test_shock_behavior, test_cross_sectional_correlation,
    test_temporal_stability
)
from .validation import validate_data
from .visualization import generate_decision_charts


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════
UNIVERSE = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'SPY', 'QQQ']
START_DATE = datetime(2025, 2, 1)
END_DATE = datetime(2025, 12, 31)
ROUND_TRIP_COST_BPS = 15.0
NORM_WINDOW = 1950
FORWARD_HORIZONS = [5, 15, 30]
PRIMARY_HORIZON = 15  # primary horizon for kill criteria
OUTPUT_DIR = Path('backtest/results/phase0')


async def run_phase0():
    """Main Phase 0 execution."""
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("PHASE 0: PROPAGATION BACKSCAN")
    logger.info("Objective: Detect propagation state — NOT optimize returns")
    logger.info("=" * 80)
    
    # ───────────────────────────────────────
    # Step 0: Load and validate data
    # ───────────────────────────────────────
    logger.info("Step 0: Loading data...")
    data_manager = ClickHouseDataManager()
    await data_manager.initialize()
    
    calendar = MarketCalendar()
    all_data: Dict[str, pd.DataFrame] = {}
    
    for symbol in UNIVERSE:
        raw = await data_manager.load_market_data(
            symbols=[symbol], start_time=START_DATE, end_time=END_DATE, interval="1min"
        )
        filtered = filter_bars_to_rth(raw, symbol=symbol, calendar=calendar)
        report = validate_data(filtered, symbol)
        logger.info(f"  {symbol}: {report['total_bars']} bars, {report['trading_days']} days, "
                     f"missing={report['missing_rate']:.4f}")
        
        filtered = add_session_boundaries(filtered)
        all_data[symbol] = filtered
    
    # ───────────────────────────────────────
    # Step 1: Compute features per symbol
    # ───────────────────────────────────────
    logger.info("Step 1: Computing propagation features...")
    for symbol, df in all_data.items():
        all_data[symbol] = compute_all_features(df)
        all_data[symbol] = compute_forward_returns(all_data[symbol], FORWARD_HORIZONS)
        logger.info(f"  {symbol}: PS computed, range [{df['ps'].min():.3f}, {df['ps'].max():.3f}]")
    
    # ───────────────────────────────────────
    # Step 2: Compute cross-sectional features
    # ───────────────────────────────────────
    logger.info("Step 2: Computing RPS (cross-sectional)...")
    all_data = compute_rps(all_data, market_proxy='SPY')
    
    # ───────────────────────────────────────
    # Step 3: Run test battery
    # ───────────────────────────────────────
    logger.info("Step 3: Running test battery...")
    
    # Aggregate across non-ETF symbols for main tests
    equity_symbols = [s for s in UNIVERSE if s not in ['SPY', 'QQQ']]
    combined = pd.concat([all_data[s] for s in equity_symbols], ignore_index=True)
    
    results = {}
    
    # Test 1: State detection
    results['T01_state_detection'] = test_state_detection(combined)
    logger.info(f"  T01 State Detection: {'PASS' if results['T01_state_detection']['PASS'] else 'FAIL'}")
    
    # Test 2: Temporal clustering
    results['T02_temporal_clustering'] = test_temporal_clustering(combined)
    logger.info(f"  T02 Temporal Clustering: {'PASS' if results['T02_temporal_clustering']['PASS'] else 'FAIL'}")
    
    # Test 3: Conditional returns
    results['T03_conditional_returns'] = test_conditional_returns(combined, PRIMARY_HORIZON)
    logger.info(f"  T03 Conditional Returns: Q5-Q1 = {results['T03_conditional_returns']['q5_minus_q1_mean']:.2f} bps")
    
    # Test 4: Monotonicity
    results['T04_monotonicity'] = test_monotonicity(results['T03_conditional_returns']['table'])
    logger.info(f"  T04 Monotonicity: {'PASS' if results['T04_monotonicity']['PASS'] else 'FAIL'}")
    
    # Test 5: Left tail
    results['T05_left_tail'] = test_left_tail(combined, horizon=30)
    logger.info(f"  T05 Left Tail: {results['T05_left_tail']['tail_improvement_pct']:.1f}% improvement")
    
    # Test 6: Statistical significance
    results['T06_significance'] = test_significance(combined, PRIMARY_HORIZON)
    logger.info(f"  T06 Significance: p={results['T06_significance']['p_value']:.4f}")
    
    # Test 7: Regime invariance
    results['T07_regime_invariance'] = test_regime_invariance(combined, PRIMARY_HORIZON)
    logger.info(f"  T07 Regime Invariance: {results['T07_regime_invariance']['regimes_passed']}/3 regimes pass")
    
    # Test 8: Parameter robustness (expensive — runs feature recomputation)
    logger.info("  T08 Parameter Robustness (this may take a few minutes)...")
    # Run on single representative symbol for efficiency
    results['T08_parameter_robustness'] = test_parameter_robustness(all_data['AAPL'].copy())
    logger.info(f"  T08 Parameter Robustness: {'PASS' if results['T08_parameter_robustness']['PASS'] else 'FAIL'}")
    
    # Test 9: RPS validation
    results['T09_rps_validation'] = test_rps_validation(all_data, PRIMARY_HORIZON)
    logger.info(f"  T09 RPS: idio={results['T09_rps_validation']['idio_mean_bps']:.2f} vs beta={results['T09_rps_validation']['beta_mean_bps']:.2f}")
    
    # Test 10: Trade geometry
    results['T10_trade_geometry'] = test_trade_geometry(combined)
    logger.info(f"  T10 Trade Geometry: excursion_ratio={results['T10_trade_geometry'].get('mean_excursion_ratio', 'N/A')}")
    
    # Test 11: Shock behavior
    results['T11_shock_behavior'] = test_shock_behavior(combined)
    logger.info(f"  T11 Shock Behavior: false_signal_rate={results['T11_shock_behavior']['false_signal_rate']:.2f}")
    
    # Test 12: Cross-sectional correlation
    results['T12_cross_correlation'] = test_cross_sectional_correlation(all_data)
    logger.info(f"  T12 Cross-Sectional Corr: mean={results['T12_cross_correlation']['mean_ps_correlation']:.3f}")
    
    # Test 13: Temporal stability
    results['T13_temporal_stability'] = test_temporal_stability(combined, PRIMARY_HORIZON)
    logger.info(f"  T13 Temporal Stability: {'PASS' if results['T13_temporal_stability']['PASS'] else 'FAIL'}")
    
    # ───────────────────────────────────────
    # Step 4: Decision page
    # ───────────────────────────────────────
    decision = generate_decision_page(results)
    
    logger.info("\n" + "=" * 80)
    logger.info("DECISION PAGE")
    logger.info("=" * 80)
    for key, value in decision.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 80)
    logger.info(f"VERDICT: {decision['VERDICT']}")
    logger.info("=" * 80)
    
    # ───────────────────────────────────────
    # Step 5: Save results + generate charts
    # ───────────────────────────────────────
    output = {
        'metadata': {
            'run_timestamp': datetime.now().isoformat(),
            'universe': UNIVERSE,
            'date_range': f"{START_DATE} to {END_DATE}",
            'cost_model_bps': ROUND_TRIP_COST_BPS,
            'primary_horizon': PRIMARY_HORIZON,
        },
        'tests': results,
        'decision': decision,
    }
    
    output_path = OUTPUT_DIR / f"phase0_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    logger.info(f"Results saved to: {output_path}")
    
    # Generate 6-chart decision dashboard
    generate_decision_charts(all_data, results, OUTPUT_DIR)
    
    return output


def generate_decision_page(results: Dict[str, Any]) -> Dict[str, str]:
    """Binary decision page. No commentary. No storytelling."""
    
    decision = {
        'STATE_DETECTED': 'YES' if (
            results['T01_state_detection']['PASS'] and
            results['T02_temporal_clustering']['PASS']
        ) else 'NO',
        
        'STATISTICAL_EDGE': 'PASS' if results['T06_significance']['PASS'] else 'FAIL',
        
        'ECONOMIC_EDGE': 'PASS' if (
            results['T03_conditional_returns']['q5_minus_q1_mean'] > 0 and
            results['T10_trade_geometry'].get('mean_pnl_bps', 0) > 0
        ) else 'FAIL',
        
        'LEFT_TAIL_IMPROVED': 'YES' if results['T05_left_tail']['PASS'] else 'NO',
        
        'REGIME_STABLE': 'YES' if results['T07_regime_invariance']['PASS'] else 'NO',
        
        'MONOTONIC': 'YES' if results['T04_monotonicity']['PASS'] else 'NO',
        
        'PARAM_ROBUST': 'YES' if results['T08_parameter_robustness']['PASS'] else 'NO',
        
        'TEMPORALLY_STABLE': 'YES' if results['T13_temporal_stability']['PASS'] else 'NO',
    }
    
    # Kill criteria evaluation
    kill_criteria_passed = sum([
        decision['STATISTICAL_EDGE'] == 'PASS',
        decision['ECONOMIC_EDGE'] == 'PASS',
        decision['TEMPORALLY_STABLE'] == 'YES',
        decision['MONOTONIC'] == 'YES',
        decision['LEFT_TAIL_IMPROVED'] == 'YES',
    ])
    
    decision['KILL_CRITERIA_PASSED'] = f"{kill_criteria_passed}/5"
    
    if kill_criteria_passed >= 5:
        decision['VERDICT'] = 'PROCEED TO PHASE 1'
    elif kill_criteria_passed >= 3 and decision['LEFT_TAIL_IMPROVED'] == 'YES':
        decision['VERDICT'] = 'CONSIDER EXIT-ONLY DEPLOYMENT'
    else:
        decision['VERDICT'] = 'TERMINATE — PROPAGATION NOT VALIDATED'
    
    return decision


if __name__ == '__main__':
    asyncio.run(run_phase0())
```

---

## 7. Visualization: Decision Dashboard (6 Charts)

```python
"""
6 charts that let a PM understand the edge in under 3 minutes.
"""

def generate_decision_charts(all_data, results, output_dir):
    """Generate the 6-chart decision dashboard."""
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    
    fig = plt.figure(figsize=(20, 14))
    gs = gridspec.GridSpec(2, 3, hspace=0.35, wspace=0.3)
    
    combined = pd.concat([all_data[s] for s in all_data if s not in ['SPY', 'QQQ']])
    
    # ── Chart 1: PS Distribution with State Thresholds ──
    ax1 = fig.add_subplot(gs[0, 0])
    ps = combined['ps'].dropna()
    ax1.hist(ps, bins=80, density=True, alpha=0.7, color='steelblue', edgecolor='none')
    ax1.axvline(ps.quantile(0.8), color='red', linestyle='--', label='80th pctile')
    ax1.set_title('PS Distribution (State Detection)', fontweight='bold')
    ax1.set_xlabel('Propagation Score')
    ax1.legend()
    
    # ── Chart 2: Quintile Return Staircase ──
    ax2 = fig.add_subplot(gs[0, 1])
    table = results['T03_conditional_returns']['table']
    means = [table[f'Q{q}']['mean_bps'] for q in range(1, 6)]
    colors = ['#d32f2f' if m < 0 else '#388e3c' for m in means]
    ax2.bar(range(1, 6), means, color=colors, edgecolor='black', linewidth=0.5)
    ax2.axhline(0, color='black', linewidth=0.5)
    ax2.set_xlabel('PS Quintile')
    ax2.set_ylabel('Forward Return (bps, net of costs)')
    ax2.set_title('Quintile Monotonicity', fontweight='bold')
    ax2.set_xticks(range(1, 6))
    ax2.set_xticklabels(['Q1\n(weakest)', 'Q2', 'Q3', 'Q4', 'Q5\n(strongest)'])
    
    # ── Chart 3: MAE vs PS Percentile (THE chart that exposes fake alpha) ──
    ax3 = fig.add_subplot(gs[0, 2])
    mae_table = results['T05_left_tail']['mae_by_quintile']
    mae_p95 = [mae_table[f'Q{q}']['p95_mae_bps'] for q in range(1, 6)]
    ax3.plot(range(1, 6), mae_p95, 'o-', color='#d32f2f', linewidth=2, markersize=8)
    ax3.set_xlabel('PS Quintile')
    ax3.set_ylabel('95th Percentile MAE (bps)')
    ax3.set_title('Left-Tail Improvement', fontweight='bold')
    ax3.set_xticks(range(1, 6))
    
    # ── Chart 4: Regime Invariance ──
    ax4 = fig.add_subplot(gs[1, 0])
    regime_data = results['T07_regime_invariance']['by_regime']
    regimes = ['low_vol', 'mid_vol', 'high_vol']
    for i, regime in enumerate(regimes):
        if regime in regime_data and 'quintile_means' in regime_data[regime]:
            ax4.plot(range(1, 6), regime_data[regime]['quintile_means'], 
                    'o-', label=regime, linewidth=1.5)
    ax4.axhline(0, color='black', linewidth=0.5)
    ax4.set_xlabel('PS Quintile')
    ax4.set_ylabel('Forward Return (bps)')
    ax4.set_title('Regime Invariance', fontweight='bold')
    ax4.legend()
    
    # ── Chart 5: Parameter Robustness ──
    ax5 = fig.add_subplot(gs[1, 1])
    param_data = results['T08_parameter_robustness']
    q5_q1s = [param_data[k]['q5_minus_q1'] for k in sorted(param_data.keys()) 
              if k.startswith('window_set_')]
    labels = [str(param_data[k]['windows']) for k in sorted(param_data.keys())
              if k.startswith('window_set_')]
    colors = ['#388e3c' if v > 0 else '#d32f2f' for v in q5_q1s]
    ax5.barh(range(len(q5_q1s)), q5_q1s, color=colors, edgecolor='black', linewidth=0.5)
    ax5.set_yticks(range(len(labels)))
    ax5.set_yticklabels(labels, fontsize=8)
    ax5.set_xlabel('Q5-Q1 Spread (bps)')
    ax5.set_title('Parameter Robustness', fontweight='bold')
    ax5.axvline(0, color='black', linewidth=0.5)
    
    # ── Chart 6: Decision Summary ──
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')
    decision = generate_decision_page(results)
    text = "DECISION PAGE\n" + "─" * 30 + "\n"
    for k, v in decision.items():
        icon = "●" if v in ['YES', 'PASS'] else ("○" if v in ['NO', 'FAIL'] else "")
        text += f"\n{icon} {k}: {v}"
    ax6.text(0.1, 0.95, text, transform=ax6.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='#f5f5f5', alpha=0.8))
    
    plt.savefig(output_dir / 'phase0_decision_dashboard.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Dashboard saved to: {output_dir / 'phase0_decision_dashboard.png'}")
```

---

## 8. File Structure

```
backtest/experiments/phase0_propagation_backscan/
├── __init__.py
├── ENGINEERING_PLAN.md       # This document
├── run.py                    # Main orchestrator (Section 6)
├── features.py               # Feature computation (Section 2)
├── tests.py                  # Statistical tests (Section 5)
├── validation.py             # Data validation (Section 1)
├── visualization.py          # Charts and dashboard (Section 7)
└── config.py                 # Constants and configuration
```

---

## 9. Dependencies

```
# Already in project
numpy
pandas
scipy

# May need to add
diptest          # Hartigan's dip test (optional — gracefully skipped if missing)
matplotlib       # Visualization
```

---

## 10. Execution Checklist

```
□ 1. Verify ClickHouse is running and has ≥6 months of 1-min data
□ 2. Run data validation — all symbols pass integrity checks
□ 3. Run feature computation — verify PS distribution is non-degenerate
□ 4. Run test battery — all 13 tests execute without error
□ 5. Review decision page — binary verdicts, no interpretation
□ 6. Review decision dashboard — 6 charts tell the story
□ 7. Run TWICE with different date boundaries (shift by 1 month)
□ 8. If conclusions flip between runs → instability detected → do not proceed
□ 9. Final verdict: PROCEED / EXIT-ONLY / TERMINATE
```

---

## 11. What This Plan Does NOT Cover (Explicitly Deferred)

- Feature tuning or optimization (forbidden in Phase 0)
- Integration with existing feature pipeline (Phase 1)
- Exit cascade modification (Phase 3)
- Entry strategy implementation (Phase 4)
- Live execution (Phase 4+)

Phase 0 answers exactly one question: **does propagation exist as a tradable state?**

Everything else waits for that answer.
