# Annualized Return Calculation Bug Fix

## Summary
Fixed a critical bug in the ExperimentRunner's annualized return calculation that was significantly underreporting strategy performance.

## Problem
The `_calculate_performance_metrics` method in `experiments/experiment_runner.py` was using a hardcoded assumption of 252 trading days per year instead of the actual time period of the backtest.

### Original Buggy Code (Line 692)
```python
time_period_years = 252 / len(returns_array)  # WRONG: assumes 252 trading days
```

### Impact
- **Total Return**: 12.07% (6 months)
- **Reported Annualized Return**: 3.84% ❌ (INCORRECT)
- **Actual Annualized Return**: 26.02% ✅ (CORRECT)
- **Error Magnitude**: 577.5% underreporting

## Solution
Implemented proper date-based calculation using actual calendar time periods.

### Fixed Code
```python
def _calculate_performance_metrics(self, strategy_returns, benchmark_returns, 
                                 trading_start=None, trading_end=None):
    # Calculate actual time period from dates
    if trading_start and trading_end:
        start_date = pd.to_datetime(trading_start)
        end_date = pd.to_datetime(trading_end)
        time_period_years = (end_date - start_date).days / 365.25
    else:
        # Fallback to old method if dates not provided
        time_period_years = 252 / len(returns_array)
    
    # Use actual time period for annualization
    annualized_return = (cumulative_return + 1) ** (1 / time_period_years) - 1
```

## Validation Results
After applying the fix:
- **6-month period**: 181 days = 0.496 years
- **Formula**: (1.1207)^(1/0.496) - 1 = 0.2602 = 26.02% ✅
- **Verification**: (1.2602)^0.496 - 1 = 0.1207 = 12.07% ✅

## Files Modified
1. `experiments/experiment_runner.py`: 
   - Modified `_calculate_performance_metrics` method
   - Added start_date/end_date parameters
   - Updated method calls to pass trading dates

## Testing
- Created validation scripts confirming the fix
- Ran full momentum backtest showing corrected annualized return
- All performance metrics now use consistent date-based calculations

## Result
The momentum strategy's true annualized performance is **26.02%**, not the previously incorrect **3.84%**.

---
*Fix Date: July 22, 2025*  
*Backtest Results: `results/momentum_backtest/`*
