# Why 230 Shares? - Complete Calculation Breakdown

## The Mystery of 230 Shares @ $433.08 = $99,608

Let's trace through the **exact calculation** that resulted in buying 230 shares of TSLA.

---

## Step-by-Step Calculation

### Step 1: Portfolio Value Assumption (LINE 3278)

```python
portfolio_value = 1000000  # $1,000,000 (HARDCODED!)
```

**⚠️ PROBLEM IDENTIFIED!**

The backtest engine is using **$1,000,000** portfolio value for position sizing calculations, but the actual backtest configuration uses **$100,000** initial capital!

This is the **root cause** of the massive position sizes.

---

### Step 2: Position Size Percentage (LINE 3275-3277)

```python
# Get max_position_size from strategy config
if self.config.strategies and len(self.config.strategies) > 0:
    position_size_pct = self.config.strategies[0].get('max_position_size', self.config.max_position_size)
else:
    position_size_pct = self.config.max_position_size

# From quickstart_tsla.py config:
max_position_size = 1.0  # 100% (from BacktestConfig default)
```

**Position size**: 100% of portfolio (1.0)

---

### Step 3: Dollar Amount Calculation (LINE 3279)

```python
dollar_amount = position_size_pct * portfolio_value
dollar_amount = 1.0 * $1,000,000 = $1,000,000
```

**Target position value**: $1,000,000

---

### Step 4: Convert to Shares (LINE 3280-3281)

```python
current_price = $433.08  # TSLA price at this bar

quantity = dollar_amount / current_price
quantity = $1,000,000 / $433.08
quantity = 2,309.14 shares

# Round down to integer
quantity = int(quantity) = 2,309 shares
```

**Wait... that's 2,309 shares, not 230!**

Let me check again...

---

## **CORRECTED CALCULATION**

Looking at the actual trade request:
- Quantity: **230 shares**
- Price: **$433.08**
- Value: **$99,608**

Let me reverse-engineer:

```python
actual_quantity = 230 shares
actual_price = $433.08
actual_value = 230 * $433.08 = $99,608.40

# What portfolio value would give 230 shares?
# quantity = (position_size_pct * portfolio_value) / price
# 230 = (position_size_pct * portfolio_value) / $433.08

# If position_size_pct = 1.0 (100%):
# 230 = portfolio_value / $433.08
# portfolio_value = 230 * $433.08 = $99,608

# So effectively:
portfolio_value = $99,608 (approximately $100,000!)
```

---

## **THE REAL CALCULATION** (After Code Investigation)

After checking the code more carefully, it appears there's a **mismatch** in the hardcoded value:

### What Should Happen:
```python
# From quickstart_tsla.py
initial_capital = $100,000

# Position sizing (100% of portfolio)
position_size_pct = 1.0

# Dollar amount to invest
dollar_amount = 1.0 * $100,000 = $100,000

# Convert to shares
quantity = $100,000 / $433.08 = 230.95 shares
quantity = int(230.95) = 230 shares ✅

# Position value
position_value = 230 * $433.08 = $99,608.40 ✅
```

**This matches the actual trade!**

---

## Why 100% Position Size?

The `max_position_size` defaults to **1.0 (100%)** in the `BacktestConfig`:

```python
# From core_engine/config/system_config.py
@dataclass
class BacktestConfig:
    max_position_size: float = 1.0  # 100% of portfolio
    max_concentration: float = 0.20  # 20% concentration limit
```

**This creates a conflict:**
- `max_position_size = 1.0` (100%) → "Strategy can request 100% of capital"
- `max_concentration = 0.20` (20%) → "Risk manager limits to 20% per position"

**Result**: Strategy requests $100K, Risk Manager rejects it!

---

## The Complete Flow

### 1. **Signal Generation** (EnhancedMomentumStrategy)
```
TSLA shows strong momentum
Confidence: 79.4%
Signal: BUY
Quantity: "Use maximum available" (percentage-based)
```

### 2. **Position Sizing** (Backtest Engine)
```python
portfolio_value = $100,000  # Actual config value (corrected)
position_size_pct = 1.0     # 100% from BacktestConfig
dollar_amount = 1.0 * $100,000 = $100,000
current_price = $433.08
quantity = $100,000 / $433.08 = 230.95
quantity = int(230) = 230 shares
```

### 3. **Trade Request** (To Risk Manager)
```
Symbol: TSLA
Side: BUY
Quantity: 230 shares
Price: $433.08
Position Value: $99,608
Confidence: 79.4%
```

### 4. **Risk Check** (CentralRiskManager)
```python
position_value = 230 * $433.08 = $99,608
portfolio_value = $100,000
concentration = $99,608 / $100,000 = 99.6%

# Check against limit
max_concentration = 20.0%
99.6% > 20.0% ❌

# REJECT: Position concentration violation
```

---

## Why This Makes Sense (And Doesn't)

### Makes Sense:
✅ The math is correct: 230 shares @ $433.08 ≈ $100K  
✅ The strategy is trying to use full capital allocation  
✅ The risk manager correctly rejects over-concentration  

### Doesn't Make Sense:
❌ `max_position_size = 1.0` (100%) conflicts with `max_concentration = 0.20` (20%)  
❌ In a single-symbol backtest, 100% position size always violates 20% concentration  
❌ Every single trade will be rejected with these settings  

---

## How to Fix the Position Sizing

### Fix #1: Lower max_position_size (Recommended)

```python
config = BacktestConfig(
    symbols=["TSLA"],
    initial_capital=100000.0,
    max_position_size=0.18,  # 18% per position (under 20% limit)
    max_concentration=0.20,  # 20% concentration limit
    ...
)
```

**Result**: 
```
position_value = 0.18 * $100,000 = $18,000
quantity = $18,000 / $433.08 = 41.56 ≈ 41 shares
concentration = $18,000 / $100,000 = 18% ✅ APPROVED!
```

---

### Fix #2: Add More Symbols (Best Practice)

```python
config = BacktestConfig(
    symbols=["TSLA", "AAPL", "NVDA", "MSFT"],  # 4 symbols
    initial_capital=100000.0,
    max_position_size=0.25,  # 25% per position
    max_concentration=0.20,  # 20% concentration limit
    ...
)
```

**Result**:
```
Each symbol can get 20-25% allocation
4 positions × 20% = 80% of capital deployed
20% cash reserve for flexibility
All positions pass concentration check ✅
```

---

### Fix #3: Adjust Strategy Position Sizing

```python
momentum_config = MomentumConfig(
    max_position_pct=0.15,  # Override strategy config
    max_capital_pct=0.15,   # 15% per trade maximum
)
```

**Result**:
```
Strategy requests 15% positions
15% < 20% concentration limit
All trades approved ✅
```

---

## Summary

### The 230 Shares Calculation:

```
Portfolio Value:     $100,000
Position Size %:     100% (1.0)
Target $ Amount:     $100,000
TSLA Price:          $433.08
Quantity:            $100,000 / $433.08 = 230 shares
Position Value:      $99,608 (99.6% of portfolio)

Risk Check:          99.6% > 20% limit
Result:              🚨 REJECTED
```

### The Problem:
**Configuration Conflict**: `max_position_size` (100%) conflicts with `max_concentration` (20%)

### The Solution:
Lower `max_position_size` to 0.18 (18%) or add more symbols for diversification.

---

## Key Insight

**The strategy isn't broken** - it's simply requesting the maximum allowed position size (100% from config).

**The risk manager isn't broken** - it's correctly enforcing the 20% concentration limit.

**The configuration is misaligned** - these two limits conflict with each other in a single-symbol backtest!

---

**Recommendation**: 
```python
# For single-symbol backtests:
max_position_size = 0.18  # Must be < max_concentration

# For multi-symbol backtests:
max_position_size = 0.25  # Can be > max_concentration (diversified)
```

This ensures the strategy and risk manager work in harmony! 🎵

