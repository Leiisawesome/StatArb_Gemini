# Diagnostic: Missing Threshold Logs

**Date:** November 13, 2025  
**Issue:** Added diagnostic logs to `_check_composite_entry()` but they're not appearing

## Findings

1. **Method is being called** - confirmed by log: "About to call _check_composite_entry with composite_z=2.087"
2. **Cache cleared** - Python `__pycache__` directories removed
3. **No logs after line 1540** - The method must be returning/exiting before reaching that line

## The Mystery

We have this code structure:
```python
def _check_composite_entry(symbol, current_bar):
    # Line 1522: Get composite signals
    composite_z = current_bar.get('composite_z', None)
    composite_pct = current_bar.get('composite_pct', None)
    
    # Line 1528: LOG (✅ WE SEE THIS)
    logger.info(f"🔍 {symbol} composite check: composite_z={composite_z:.4f}...")
    
    # Line 1530: Check composite_z
    if composite_z is None or pd.isna(composite_z):
        return False, None
    
    # Line 1534-1537: composite_pct check is COMMENTED OUT
    
    # Line 1540: LOG (❌ WE DON'T SEE THIS)
    logger.info(f"🔍 [{symbol}] About to get regime-adjusted thresholds...")
```

**Question:** How can line 1528 log appear but line 1540 log doesn't?

## Hypothesis

There might be an exception being raised between lines 1528 and 1540 that's being caught elsewhere, preventing execution from reaching line 1540.

## Next Step

Add try/except logging around the entire method to catch any hidden exceptions.

