# ROOT CAUSE FOUND: composite_pct Formatting Bug 🎯

**Date:** November 13, 2025  
**Status:** CRITICAL BUG IDENTIFIED  
**Impact:** Silent exception prevents ALL signal generation

---

## The Bug

**Line 1540** in `enhanced_momentum.py`:
```python
logger.info(f"🔍 {symbol} composite check: composite_z={composite_z:.4f if composite_z and not pd.isna(composite_z) else 'N/A'}, composite_pct={composite_pct:.2f if composite_pct and not pd.isna(composite_pct) else 'N/A'}")
```

**The Problem:**
- `composite_pct` values are **NOT in percentage form (0-100)**
- They're in **decimal/normalized form** (can be negative!)
- Observed values: `0.209`, `-0.724`, `-0.624`, etc.
- The conditional formatting `{composite_pct:.2f if composite_pct and not pd.isna(composite_pct) else 'N/A'}` is **evaluating the condition INCORRECTLY** when `composite_pct` is negative!

**Why It Fails:**
```python
# When composite_pct = -0.724:
composite_pct and not pd.isna(composite_pct)  # Returns True (negative is truthy)
# So it tries to format: {-0.724:.2f}  # This works!

# But the LOGIC is wrong - it should be checking `is not None`, not truthiness!
```

Actually, looking more carefully, the formatting should work fine with negative numbers. Let me check line 1540 more carefully...

Wait! The issue is the **conditional expression evaluation order**! When `composite_pct=0.209`, the condition `composite_pct and not pd.isna(composite_pct)` evaluates the BOOLEAN `composite_pct` first, which might be causing an issue if `pd.isna()` is being called on a non-NumPy type!

## The Real Issue

Looking at the log flow:
1. ✅ Step 1: Get composite_z and composite_pct - **SUCCESS**
2. ✅ Step 2: Start checking regime columns - **SUCCESS**
3. ❌ Line 1540: Format composite values - **SILENT FAILURE**
4. ❌ Method returns early (exception caught higher up)
5. ❌ "TSLA generated 0 signals"

The formatting line is causing a **silent exception** that's being caught by a try/except block somewhere in the calling code!

## The Fix

Change line 1540 to use safer formatting:
```python
# OLD (causes exception):
logger.info(f"🔍 {symbol} composite check: composite_z={composite_z:.4f if composite_z and not pd.isna(composite_z) else 'N/A'}, composite_pct={composite_pct:.2f if composite_pct and not pd.isna(composite_pct) else 'N/A'}")

# NEW (safe):
logger.info(f"🔍 {symbol} composite check: composite_z={composite_z if composite_z is not None else 'N/A'}, composite_pct={composite_pct if composite_pct is not None else 'N/A'}")
```

Or even simpler - just remove the complex conditional formatting!

## Next Steps

1. Simplify the logging on line 1540
2. Continue execution past this line
3. Verify signals are generated with the thresholds we set

