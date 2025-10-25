# Complete Trading Signal Generation Flow
## From Raw OHLCV Data → Processing Brick → Momentum Strategy → Risk Manager → Execution

**Date:** October 24, 2025  
**System:** StatArb_Gemini Core Engine  
**Flow:** Data-to-Execution Pipeline

---

## Executive Summary

This document traces the complete flow from **raw OHLCV market data** through the **Processing Brick**, into the **Momentum Strategy**, through **Risk Manager authorization**, and finally to **execution**. This is the **core trading pipeline** of the StatArb_Gemini system.

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 0: DATA INGESTION                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  ClickHouse Database (1-minute OHLCV bars)             │
         │  - Raw market data storage                             │
         │  - High-frequency tick data aggregated to 1-min bars  │
         │  - Columns: timestamp, open, high, low, close, volume │
         └───────────────────────────────────────────────────────┘
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: DATA LAYER (SUPPORT LAYER)                       │
│                    Rule 3: Unified Data Flow Pipeline                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  ClickHouseDataManager (core_engine/data/manager.py)   │
         │  - ISystemComponent (initialize, start, stop)         │
         │  - Single data authority (Rule 3)                      │
         │  - Methods:                                            │
         │    • load_market_data(symbols, start, end, interval)  │
         │    • get_historical_data(symbol, timeframe)           │
         │  - Caching & validation                                │
         │  - Output: pd.DataFrame with OHLCV columns             │
         └───────────────────────────────────────────────────────┘
                                     ↓
                    **Raw OHLCV DataFrame**
                    Columns: timestamp, open, high, low, close, volume
                    Frequency: 1-minute bars
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 2: PROCESSING BRICK - INDICATORS LAYER                    │
│                    Rule 3: Data Processing Pipeline                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  EnhancedTechnicalIndicators                          │
         │  (core_engine/processing/indicators/engine.py)        │
         │  - ISystemComponent + IRegimeAware                    │
         │  - Methods:                                            │
         │    • calculate_indicators(market_data: DataFrame)     │
         │  - Calculates 29+ technical indicators:               │
         │                                                        │
         │  ** Trend Indicators **                                │
         │    • SMA (10, 20, 50, 200 period)                     │
         │    • EMA (9, 12, 26, 50 period)                       │
         │    • MACD (12, 26, 9)                                 │
         │    • ADX (14) - Trend strength                        │
         │    • Parabolic SAR                                     │
         │                                                        │
         │  ** Momentum Indicators **                             │
         │    • RSI (14) - Relative Strength Index               │
         │    • Stochastic (14, 3, 3)                            │
         │    • CCI (20) - Commodity Channel Index               │
         │    • Williams %R (14)                                  │
         │    • ROC (12) - Rate of Change                        │
         │    • MOM (10) - Momentum                               │
         │                                                        │
         │  ** Volatility Indicators **                           │
         │    • ATR (14) - Average True Range                    │
         │    • Bollinger Bands (20, 2)                          │
         │    • Keltner Channels                                  │
         │    • Donchian Channels (20)                           │
         │    • Historical Volatility (20)                        │
         │                                                        │
         │  ** Volume Indicators **                               │
         │    • OBV - On-Balance Volume                          │
         │    • Volume MA (20)                                    │
         │    • VWAP - Volume Weighted Average Price             │
         │    • MFI (14) - Money Flow Index                      │
         │    • A/D Line - Accumulation/Distribution             │
         │                                                        │
         │  Output: market_data with 29+ indicator columns       │
         └───────────────────────────────────────────────────────┘
                                     ↓
              **Enriched DataFrame with Indicators**
              Original OHLCV + 29+ indicator columns
              (SMA_10, SMA_20, RSI_14, MACD, ATR_14, etc.)
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 3: PROCESSING BRICK - FEATURE ENGINEERING                 │
│                    Rule 3: Data Processing Pipeline                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  EnhancedFeatureEngineer                              │
         │  (core_engine/processing/features/engineer.py)        │
         │  - ISystemComponent + IRegimeAware                    │
         │  - Methods:                                            │
         │    • create_features(indicators_df: DataFrame)        │
         │  - Creates ML-ready features from indicators:         │
         │                                                        │
         │  ** Price Features **                                  │
         │    • returns_1, returns_5, returns_10                 │
         │    • log_returns                                       │
         │    • price_momentum (various periods)                  │
         │    • price_acceleration                                │
         │                                                        │
         │  ** Trend Features **                                  │
         │    • trend_strength (from ADX)                        │
         │    • trend_direction (bullish/bearish/neutral)        │
         │    • ma_crossovers (short vs long MA)                 │
         │    • macd_signal_cross                                 │
         │                                                        │
         │  ** Momentum Features **                               │
         │    • rsi_normalized (0-1 scale)                       │
         │    • rsi_divergence                                    │
         │    • momentum_acceleration                             │
         │    • relative_momentum (vs market)                     │
         │                                                        │
         │  ** Volatility Features **                             │
         │    • volatility_ratio (current vs historical)         │
         │    • atr_normalized                                    │
         │    • bollinger_position (price vs bands)              │
         │    • volatility_trend                                  │
         │                                                        │
         │  ** Volume Features **                                 │
         │    • volume_ratio (vs MA)                             │
         │    • obv_trend                                         │
         │    • mfi_divergence                                    │
         │    • volume_price_correlation                          │
         │                                                        │
         │  ** Cross-Asset Features **                            │
         │    • relative_strength (vs benchmark)                 │
         │    • correlation_rolling                               │
         │    • beta_estimate                                     │
         │                                                        │
         │  Output: DataFrame with ~50+ engineered features      │
         └───────────────────────────────────────────────────────┘
                                     ↓
              **Feature-Rich DataFrame**
              OHLCV + Indicators + 50+ Engineered Features
              Ready for strategy consumption
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 4: PROCESSING BRICK - SIGNAL GENERATION                   │
│                    Rule 3: Data Processing Pipeline                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  EnhancedSignalGenerator                              │
         │  (core_engine/processing/signals/generator.py)        │
         │  - ISystemComponent + IRegimeAware                    │
         │  - Methods:                                            │
         │    • generate_signals(features_df: DataFrame)         │
         │  - Generates preliminary trading signals:             │
         │                                                        │
         │  ** Signal Types **                                    │
         │    • BUY signals (bullish conditions)                 │
         │    • SELL signals (bearish conditions)                │
         │    • HOLD signals (neutral conditions)                │
         │    • CLOSE signals (exit conditions)                  │
         │                                                        │
         │  ** Signal Strength **                                 │
         │    • WEAK (1) - Low confidence                        │
         │    • MODERATE (2) - Medium confidence                 │
         │    • STRONG (3) - High confidence                     │
         │    • VERY_STRONG (4) - Very high confidence           │
         │                                                        │
         │  ** Signal Logic **                                    │
         │    • Multi-indicator confirmation                      │
         │    • Trend alignment check                             │
         │    • Volume confirmation                               │
         │    • Volatility filtering                              │
         │    • Regime-aware thresholds                           │
         │                                                        │
         │  Output: DataFrame with signal columns                │
         │    - signal_type (BUY/SELL/HOLD)                      │
         │    - signal_strength (1-4)                            │
         │    - confidence (0.0-1.0)                             │
         └───────────────────────────────────────────────────────┘
                                     ↓
              **Signal-Enriched DataFrame**
              Features + Preliminary Signals
              (Not yet strategy-specific)
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                PHASE 5: STRATEGY LAYER - MOMENTUM STRATEGY                   │
│                    Rule 5: Multi-Strategy Coordination                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  EnhancedMomentumStrategy                             │
         │  (strategies/implementations/momentum/)               │
         │  - Extends EnhancedBaseStrategy                       │
         │  - ISystemComponent + IRegimeAware                    │
         │  - Methods:                                            │
         │    • generate_signals(market_data: DataFrame)         │
         │    • evaluate_opportunity(symbol, data)               │
         │                                                        │
         │  ** Momentum Strategy Logic **                         │
         │                                                        │
         │  1. Multi-Timeframe Momentum Analysis:                │
         │     • Primary timeframe: 5min                         │
         │     • Confirmation timeframes: 15min, 1h              │
         │     • Require alignment across timeframes             │
         │                                                        │
         │  2. Momentum Calculation:                             │
         │     • Short-term momentum: (price - SMA_10) / SMA_10 │
         │     • Medium-term momentum: (price - SMA_20) / SMA_20│
         │     • Long-term momentum: (price - SMA_50) / SMA_50  │
         │     • Composite momentum score                        │
         │                                                        │
         │  3. Trend Quality Assessment (ADX):                   │
         │     • ADX > 25: Strong trend (tradeable)              │
         │     • ADX < 25: Weak trend (avoid)                    │
         │     • +DI/-DI for direction confirmation              │
         │                                                        │
         │  4. Volume Confirmation:                              │
         │     • Volume > 1.2 * Volume_MA_20                     │
         │     • OBV trend alignment                              │
         │     • Accumulation/Distribution confirmation          │
         │                                                        │
         │  5. Breakout Detection (Optional):                    │
         │     • Price > 20-period high                          │
         │     • Volume surge confirmation                        │
         │     • Momentum continuation signal                     │
         │                                                        │
         │  6. Risk Management:                                   │
         │     • Momentum-based position sizing                  │
         │     • Strong momentum → larger position (up to 8%)    │
         │     • Weak momentum → smaller position (3%)           │
         │     • Stop loss: entry - (3% * entry)                 │
         │     • Trailing stop: current_price - (2% * current)   │
         │     • Profit target: 3x risk (9% above entry)         │
         │                                                        │
         │  ** Signal Generation Logic **                         │
         │                                                        │
         │  BUY Signal Conditions (ALL must be true):            │
         │    ✓ Composite momentum > momentum_threshold (2%)     │
         │    ✓ ADX > adx_threshold (25)                         │
         │    ✓ Volume > volume_threshold * Volume_MA (1.2x)    │
         │    ✓ Multi-timeframe confirmation (if enabled)        │
         │    ✓ RSI < 70 (not overbought)                        │
         │    ✓ Price above SMA_50 (uptrend)                     │
         │    ✓ No existing position in symbol                   │
         │                                                        │
         │  SELL Signal Conditions (ALL must be true):           │
         │    ✓ Composite momentum < -momentum_threshold (-2%)   │
         │    ✓ ADX > adx_threshold (25)                         │
         │    ✓ Volume > volume_threshold * Volume_MA (1.2x)    │
         │    ✓ Multi-timeframe confirmation (if enabled)        │
         │    ✓ RSI > 30 (not oversold)                          │
         │    ✓ Price below SMA_50 (downtrend)                   │
         │    ✓ No existing short position in symbol             │
         │                                                        │
         │  HOLD Signal:                                          │
         │    • Conditions not met for BUY or SELL               │
         │    • Maintain existing positions                       │
         │                                                        │
         │  EXIT Signal Conditions (ANY triggers exit):          │
         │    ✓ Stop loss hit (price < entry - 3%)               │
         │    ✓ Trailing stop hit (price < current - 2%)         │
         │    ✓ Profit target reached (price > entry + 9%)       │
         │    ✓ Momentum decay detected (momentum < threshold/2) │
         │    ✓ Max holding period exceeded (20 bars)            │
         │    ✓ ADX < 20 (trend weakness)                        │
         │    ✓ Volume dries up (< 0.8 * Volume_MA)              │
         │                                                        │
         │  Output: List[StrategySignal]                         │
         └───────────────────────────────────────────────────────┘
                                     ↓
              **Strategy Signals (StrategySignal objects)**
              Each signal contains:
                - symbol: str (e.g., "AAPL")
                - signal_type: SignalType (BUY/SELL/HOLD/CLOSE)
                - confidence: float (0.6-1.0)
                - quantity: float (calculated by strategy)
                - entry_price: float (current market price)
                - stop_loss: float (entry - 3%)
                - take_profit: float (entry + 9%)
                - strategy_id: str ("momentum_strategy_001")
                - metadata: Dict (momentum_score, adx, volume_ratio, etc.)
                - timestamp: datetime
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│            PHASE 6: GOVERNANCE LAYER - RISK MANAGER (REQUIRED)               │
│                    Rule 4: Central Risk Manager Governance                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  Create TradingDecisionRequest                        │
         │  (Momentum Strategy creates this)                     │
         │                                                        │
         │  request = TradingDecisionRequest(                    │
         │      decision_type = POSITION_ENTRY,                  │
         │      strategy_id = "momentum_strategy_001",           │
         │      symbol = "AAPL",                                  │
         │      side = "buy",  # from signal_type                │
         │      quantity = 100.0,  # from signal                 │
         │      confidence = 0.85,  # from signal                │
         │      expected_return = 0.09,  # 9% target             │
         │      current_price = 150.00,                          │
         │      market_regime = "normal_volatility",             │
         │      requesting_component = "MomentumStrategy"        │
         │  )                                                     │
         └───────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  CentralRiskManager.authorize_trading_decision()      │
         │  (core_engine/system/central_risk_manager.py)         │
         │  - SINGLE POINT OF AUTHORITY (Rule 4)                 │
         │  - ISystemComponent + IRegimeAware                    │
         │  - ALL trades MUST get authorization                  │
         │                                                        │
         │  ** Risk Authorization Process **                      │
         │                                                        │
         │  Step 1: Request Validation                           │
         │    ✓ Valid strategy_id?                               │
         │    ✓ Valid symbol?                                     │
         │    ✓ Valid quantity > 0?                               │
         │    ✓ Confidence > min_threshold (60%)?                │
         │                                                        │
         │  Step 2: Position Limit Checks                        │
         │    ✓ Max position size check:                         │
         │       position_value = quantity * price               │
         │       position_pct = position_value / portfolio_value │
         │       Must be ≤ max_position_size (10%)               │
         │                                                        │
         │    ✓ Concentration limit check:                       │
         │       total_exposure = sum(all positions)             │
         │       Must be ≤ concentration_limit (15%)             │
         │                                                        │
         │    ✓ Strategy allocation check:                       │
         │       strategy_total = sum(strategy positions)        │
         │       Must be ≤ strategy_limit (33%)                  │
         │                                                        │
         │  Step 3: Cash Availability (BUY orders)               │
         │    ✓ For BUY orders:                                  │
         │       required_cash = quantity * price                │
         │       available_cash = portfolio_value * 0.95         │
         │       Must have: required_cash ≤ available_cash       │
         │       If insufficient: reduce quantity or REJECT      │
         │                                                        │
         │  Step 4: Position Validation (SELL orders)            │
         │    ✓ For SELL orders:                                 │
         │       current_position = positions[symbol]            │
         │       Must have: current_position > 0                 │
         │       quantity = min(quantity, current_position)      │
         │       If no position: REJECT                           │
         │                                                        │
         │  Step 5: Risk Budget Check                            │
         │    ✓ Daily VaR check:                                 │
         │       current_var = calculate_portfolio_var()         │
         │       Must be ≤ max_daily_var (5%)                    │
         │                                                        │
         │    ✓ Drawdown check:                                  │
         │       current_drawdown = (peak - current) / peak      │
         │       Must be ≤ max_drawdown (20%)                    │
         │                                                        │
         │  Step 6: Regime-Based Adjustment                      │
         │    ✓ Get current regime from RegimeEngine             │
         │    ✓ Apply regime-specific risk multipliers:          │
         │       • low_volatility: 1.2x risk allowed             │
         │       • normal_volatility: 1.0x risk allowed          │
         │       • high_volatility: 0.7x risk allowed            │
         │       • extreme_volatility: 0.4x risk allowed         │
         │                                                        │
         │    ✓ Adjust authorized quantity by regime             │
         │                                                        │
         │  Step 7: Authorization Decision                       │
         │    IF all checks pass:                                │
         │      → AuthorizationLevel.AUTOMATIC                   │
         │      → Create ExecutionAuthorization                  │
         │      → Return authorization to strategy               │
         │                                                        │
         │    IF minor violations:                               │
         │      → AuthorizationLevel.STANDARD                    │
         │      → Reduce quantity to fit limits                  │
         │      → Return modified authorization                  │
         │                                                        │
         │    IF major violations:                               │
         │      → AuthorizationLevel.REJECTED                    │
         │      → Log rejection reason                           │
         │      → Return rejection to strategy                   │
         │                                                        │
         │  Output: TradingAuthorization                         │
         └───────────────────────────────────────────────────────┘
                                     ↓
              **TradingAuthorization (if approved)**
              Contains:
                - authorization_id: str (unique ID)
                - authorization_level: AuthorizationLevel
                - authorized: bool (True/False)
                - request: TradingDecisionRequest (original)
                - authorized_quantity: float (may be reduced)
                - risk_score: float (0.0-1.0)
                - risk_budget_impact: float
                - authorization_conditions: List[str]
                - rejection_reason: Optional[str]
                - expires_at: datetime (1 hour validity)
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 7: EXECUTION LAYER - TRADING ENGINE (HOW)                 │
│                    Rule 7: Execution Management                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  EnhancedTradingEngine.create_execution_plan()        │
         │  (core_engine/trading/engine.py)                      │
         │  - Determines HOW to execute the authorized trade     │
         │  - ISystemComponent + IRegimeAware                    │
         │                                                        │
         │  ** Execution Planning **                              │
         │                                                        │
         │  Step 1: Select Execution Algorithm                   │
         │    • Quantity < 1000: MARKET order                    │
         │    • Quantity 1000-5000: ADAPTIVE                     │
         │    • Quantity > 5000 + time: TWAP/VWAP                │
         │    • Urgent trades: MARKET                             │
         │                                                        │
         │  Step 2: Determine Urgency                            │
         │    • Market regime volatility level                   │
         │    • Signal strength/confidence                       │
         │    • Time of day (market hours)                       │
         │                                                        │
         │  Step 3: Create Execution Request                     │
         │    execution_request = ExecutionRequest(              │
         │        authorization = authorization,                 │
         │        symbol = "AAPL",                                │
         │        side = "buy",                                   │
         │        quantity = 100.0,  # authorized qty            │
         │        algorithm = ExecutionAlgorithm.ADAPTIVE,       │
         │        urgency = ExecutionUrgency.NORMAL,             │
         │        time_horizon = 300,  # 5 minutes               │
         │        limit_price = None,  # market execution        │
         │    )                                                   │
         │                                                        │
         │  Output: ExecutionRequest                             │
         └───────────────────────────────────────────────────────┘
                                     ↓
              **ExecutionRequest**
              Ready for actual execution
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│           PHASE 8: EXECUTION LAYER - UNIFIED EXECUTION (ACTION)              │
│                    Rule 7: Execution Management                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  UnifiedExecutionEngine.execute_authorized_trade()    │
         │  (core_engine/system/unified_execution_engine.py)     │
         │  - Performs the ACTUAL trade execution                │
         │  - ISystemComponent integration                       │
         │  - Rule 4 compliance: Only executes authorized trades │
         │                                                        │
         │  ** Execution Process **                               │
         │                                                        │
         │  Step 1: Validate Authorization                       │
         │    ✓ Authorization not expired?                       │
         │    ✓ Authorization not already used?                  │
         │    ✓ Authorization level not REJECTED?                │
         │                                                        │
         │  Step 2: Broker Selection                             │
         │    • Select optimal broker (via BrokerManager)        │
         │    • Regime-aware broker selection                    │
         │    • High volatility → most reliable broker           │
         │                                                        │
         │  Step 3: Execute Trade                                │
         │    • Send order to broker                             │
         │    • Monitor execution progress                       │
         │    • Handle partial fills                             │
         │    • Track execution quality                          │
         │                                                        │
         │  Step 4: Record Execution                             │
         │    execution_result = ExecutionResult(                │
         │        execution_id = uuid,                           │
         │        request = execution_request,                   │
         │        status = ExecutionStatus.FILLED,               │
         │        filled_quantity = 100.0,                       │
         │        avg_fill_price = 150.25,                       │
         │        total_cost = 15025.00,                         │
         │        execution_timestamp = datetime.now(),          │
         │        broker_order_id = "BROKER_12345",              │
         │        slippage_bps = 2.5,  # 2.5 basis points        │
         │        execution_time_ms = 150,                       │
         │    )                                                   │
         │                                                        │
         │  Step 5: Position Update (via Risk Manager)           │
         │    CRITICAL: Cannot update positions directly!        │
         │    Must call risk_manager.update_position():          │
         │                                                        │
         │    await risk_manager.update_position(                │
         │        symbol = "AAPL",                                │
         │        side = "buy",                                   │
         │        quantity = 100.0,                               │
         │        price = 150.25,                                 │
         │        timestamp = datetime.now()                     │
         │    )                                                   │
         │                                                        │
         │  Output: ExecutionResult                              │
         └───────────────────────────────────────────────────────┘
                                     ↓
              **ExecutionResult**
              Trade complete, positions updated
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              PHASE 9: POSITION TRACKING & PERFORMANCE MONITORING             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  CentralRiskManager - Position Management             │
         │  (SINGLE SOURCE OF TRUTH for positions - Rule 4)      │
         │                                                        │
         │  Updated Position State:                              │
         │    current_positions = {                              │
         │        "AAPL": 100.0  # shares owned                  │
         │    }                                                   │
         │                                                        │
         │    position_history = [                               │
         │        {                                               │
         │            "timestamp": "2025-10-24 14:30:00",        │
         │            "symbol": "AAPL",                          │
         │            "side": "buy",                              │
         │            "quantity": 100.0,                          │
         │            "price": 150.25,                           │
         │            "position_value": 15025.00,                │
         │            "portfolio_value": 1000000.00,             │
         │            "position_pct": 0.015025  # 1.5%           │
         │        }                                               │
         │    ]                                                   │
         └───────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  EnhancedPortfolioManager - Portfolio Tracking        │
         │  (core_engine/trading/portfolio/manager_enhanced.py)  │
         │                                                        │
         │  Receives position update notification                │
         │  Updates portfolio metrics:                           │
         │    • P&L tracking                                      │
         │    • Risk attribution                                  │
         │    • Performance analytics                             │
         └───────────────────────────────────────────────────────┘
                                     ↓
         ┌───────────────────────────────────────────────────────┐
         │  EnhancedAnalyticsManager - Performance Analysis      │
         │  (core_engine/analytics/manager_enhanced.py)          │
         │                                                        │
         │  Analyzes trade performance:                          │
         │    • Return metrics                                    │
         │    • Risk-adjusted metrics (Sharpe, Sortino)          │
         │    • Drawdown analysis                                 │
         │    • Strategy attribution                              │
         │    • Regime-specific performance                       │
         └───────────────────────────────────────────────────────┘
                                     ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MONITORING & CONTINUOUS LOOP                          │
└─────────────────────────────────────────────────────────────────────────────┘

The process repeats continuously:
• New OHLCV data arrives (1-minute bars)
• Processing brick processes data → indicators → features → signals
• Momentum strategy evaluates conditions
• Risk Manager authorizes trades
• Execution Engine executes approved trades
• Positions and performance tracked
• Process loops for next bar

```

---

## Detailed Component Methods

### 1. DataManager.load_market_data()
```python
# File: core_engine/data/manager.py
# Method signature:
def load_market_data(
    self,
    symbols: List[str],
    start_time: datetime,
    end_time: datetime,
    interval: str = "1min"
) -> pd.DataFrame:
    """
    Load market data from ClickHouse
    
    Returns DataFrame with columns:
    - timestamp
    - symbol
    - open, high, low, close, volume
    """
```

### 2. EnhancedTechnicalIndicators.calculate_indicators()
```python
# File: core_engine/processing/indicators/engine.py
# Method signature:
def calculate_indicators(
    self,
    market_data: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate 29+ technical indicators
    
    Input: DataFrame with OHLCV
    Output: DataFrame with OHLCV + indicators
    
    Adds columns:
    - SMA_10, SMA_20, SMA_50, SMA_200
    - EMA_9, EMA_12, EMA_26
    - RSI_14, MACD, ADX_14, ATR_14
    - (and 20+ more indicators)
    """
```

### 3. EnhancedFeatureEngineer.create_features()
```python
# File: core_engine/processing/features/engineer.py
# Method signature:
def create_features(
    self,
    indicators_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Engineer features from indicators
    
    Input: DataFrame with indicators
    Output: DataFrame with indicators + features
    
    Adds columns:
    - returns_1, returns_5, returns_10
    - momentum_score, trend_strength
    - volatility_ratio, volume_ratio
    - (and 40+ more features)
    """
```

### 4. EnhancedMomentumStrategy.generate_signals()
```python
# File: core_engine/trading/strategies/implementations/momentum/
# Method signature:
async def generate_signals(
    self,
    market_data: pd.DataFrame
) -> List[StrategySignal]:
    """
    Generate momentum trading signals
    
    Input: DataFrame with features
    Output: List of StrategySignal objects
    
    Each signal contains:
    - symbol, signal_type, confidence
    - quantity, entry_price, stop_loss
    - take_profit, strategy_id, metadata
    """
```

### 5. CentralRiskManager.authorize_trading_decision()
```python
# File: core_engine/system/central_risk_manager.py
# Method signature:
async def authorize_trading_decision(
    self,
    request: TradingDecisionRequest
) -> TradingAuthorization:
    """
    Authorize or reject trading decision
    
    Input: TradingDecisionRequest
    Output: TradingAuthorization
    
    Checks:
    - Position limits, cash availability
    - Risk budget, concentration limits
    - Regime-based adjustments
    
    Returns authorization with:
    - authorized: bool
    - authorized_quantity: float (may be reduced)
    - authorization_level: AuthorizationLevel
    - rejection_reason: Optional[str]
    """
```

### 6. UnifiedExecutionEngine.execute_authorized_trade()
```python
# File: core_engine/system/unified_execution_engine.py
# Method signature:
async def execute_authorized_trade(
    self,
    request: ExecutionRequest
) -> ExecutionResult:
    """
    Execute authorized trade
    
    Input: ExecutionRequest (with authorization)
    Output: ExecutionResult
    
    Process:
    1. Validate authorization
    2. Select broker
    3. Execute trade
    4. Update positions (via RiskManager)
    5. Return execution result
    """
```

---

## Key Architectural Principles

### 1. Rule 3: Unified Data Flow Pipeline
**ALL data flows through standardized pipeline:**
```
Raw Data → DataManager → Indicators → Features → Signals → Strategy
```
- **NO direct database access** allowed
- **NO pipeline bypassing** allowed
- **Standardized DataFrame format** throughout

### 2. Rule 4: Central Risk Manager Governance
**ALL trades require RiskManager authorization:**
```
Strategy Signal → RiskManager Authorization → Execution
```
- **NO component can trade independently**
- **Position updates ONLY through RiskManager**
- **Single source of truth for positions**

### 3. Rule 2: Regime-First Principle
**ALL components are regime-aware:**
```
RegimeEngine → Regime Context → All Components Adapt
```
- **Indicators adapt** to regime (thresholds, periods)
- **Features adapt** to regime (normalization, scaling)
- **Strategies adapt** to regime (signal sensitivity)
- **Risk limits adapt** to regime (multipliers)

### 4. Rule 7: Execution Management
**Clear separation of concerns:**
```
Strategy (WHAT) → RiskManager (AUTHORIZE) → TradingEngine (HOW) → ExecutionEngine (ACTION)
```
- **Strategy decides WHAT** to trade
- **RiskManager AUTHORIZES** the decision
- **TradingEngine plans HOW** to execute
- **ExecutionEngine performs ACTION**

---

## Example: Complete Flow for AAPL Buy Signal

```
Time: 2025-10-24 14:30:00
Symbol: AAPL
Strategy: Momentum

1. Data Ingestion:
   ClickHouse → 1-minute OHLCV bar
   AAPL: open=150.00, high=150.50, low=149.80, close=150.25, volume=1,000,000

2. DataManager:
   load_market_data(["AAPL"], start, end, "1min")
   → DataFrame with AAPL OHLCV

3. Indicators Engine:
   calculate_indicators(ohlcv_df)
   → Adds: SMA_10=149.50, SMA_20=148.00, RSI_14=65, ADX_14=28, ATR_14=2.50

4. Feature Engineer:
   create_features(indicators_df)
   → Adds: momentum_score=0.025 (2.5%), trend_strength=0.75, volume_ratio=1.3

5. Signal Generator:
   generate_signals(features_df)
   → Preliminary signals (not strategy-specific yet)

6. Momentum Strategy:
   generate_signals(features_df)
   
   Evaluates conditions:
   ✓ momentum_score (0.025) > threshold (0.02) ✓
   ✓ ADX (28) > threshold (25) ✓
   ✓ volume_ratio (1.3) > threshold (1.2) ✓
   ✓ RSI (65) < 70 (not overbought) ✓
   ✓ Price (150.25) > SMA_50 (145.00) ✓
   ✓ No existing position ✓
   
   → Generates BUY signal
   → confidence=0.85, quantity=100, entry=150.25, stop=145.74, target=163.73

7. Risk Manager Authorization:
   authorize_trading_decision(request)
   
   Checks:
   ✓ Position size: 15,025 / 1,000,000 = 1.5% < 10% ✓
   ✓ Cash available: 950,000 > 15,025 ✓
   ✓ Confidence: 0.85 > 0.60 ✓
   ✓ Daily VaR: within limits ✓
   ✓ Regime: normal_volatility (1.0x multiplier) ✓
   
   → AUTHORIZED: quantity=100, level=AUTOMATIC

8. Trading Engine:
   create_execution_plan(authorization)
   → algorithm=ADAPTIVE, urgency=NORMAL, time_horizon=300s

9. Execution Engine:
   execute_authorized_trade(execution_request)
   → Sends order to broker
   → Filled: 100 shares @ 150.25
   → Calls risk_manager.update_position("AAPL", "buy", 100, 150.25)

10. Position Tracking:
    RiskManager updates:
    current_positions["AAPL"] = 100
    position_value = 15,025
    
    Portfolio Manager notified
    Analytics Manager tracks performance

Result: AAPL position opened, 100 shares @ $150.25
```

---

## Summary

**Complete Flow:**
1. **Raw OHLCV Data** (ClickHouse 1-min bars)
2. **DataManager** loads data
3. **Indicators Engine** calculates 29+ indicators
4. **Feature Engineer** creates 50+ features
5. **Signal Generator** creates preliminary signals
6. **Momentum Strategy** generates strategy-specific signals
7. **Risk Manager** authorizes trades (REQUIRED)
8. **Trading Engine** plans execution (HOW)
9. **Execution Engine** executes trades (ACTION)
10. **Position Tracking** updates state
11. **Loop** repeats for next bar

**Key Compliance:**
- ✅ Rule 3: Unified data flow (no bypassing)
- ✅ Rule 4: Central risk governance (all trades authorized)
- ✅ Rule 2: Regime-first (all components regime-aware)
- ✅ Rule 7: Execution management (WHAT → HOW → ACTION)

**This is the institutional-grade trading pipeline of StatArb_Gemini!**


