# Rules Compliance Checklist
**Quick Reference Guide for Developers**

## Rule 1: Component Integration ✅ 98%

- [x] Implement ISystemComponent interface
- [x] Use centralized configuration (core_engine.config)
- [x] Register with HierarchicalSystemOrchestrator
- [x] Implement health_check() method
- [ ] Add enhanced lifecycle methods (v2.0)
- [x] No scattered config definitions

## Rule 2: Hierarchical Architecture ✅ 97%

- [x] EnhancedRegimeEngine initializes FIRST
- [x] Implement IRegimeAware for operational components
- [x] Use RegimeContext dataclass
- [x] set_regime_engine() method
- [x] on_regime_change() handler
- [ ] Integrate fast regime detection
- [x] Follow initialization order

## Rule 3: Data Flow Pipeline ✅ 95%

- [x] Use ProcessingPipelineOrchestrator
- [x] Follow Phase 1-4 pipeline
- [x] Consume EnrichedMarketData
- [x] NO indicator calculation in strategies
- [x] Read pre-calculated indicators only
- [ ] Add pipeline entry validation
- [x] Use ClickHouseDataManager for data

## Rule 4: Risk Governance ✅ 98%

- [x] ALL trades through CentralRiskManager
- [x] Call authorize_trading_decision()
- [x] Use TradingDecisionRequest
- [x] Respect TradingAuthorization
- [x] ONLY RiskManager updates positions
- [ ] Implement pre-trade compliance (7 checks)
- [ ] Add real-time P&L tracking
- [ ] Add position reconciliation
- [x] Circuit breakers implemented

## Rule 5: Multi-Strategy Coordination ✅ 96%

- [x] Register with StrategyManager
- [x] Use MultiStrategySignalAggregator
- [x] Handle SignalConflictResolver
- [x] Provide strategy metadata
- [x] Participate in coordination
- [ ] Add strategy correlation analysis
- [x] Strategy factory pattern

## Rule 6: Advanced Analytics ⚠️ 88%

- [x] Implement ISystemComponent
- [x] Implement IRegimeAware
- [ ] Implement IAnalyticsComponent (MISSING!)
- [x] Use EnhancedAnalyticsManager
- [ ] Support real-time processing
- [ ] Support batch processing
- [ ] Multi-timeframe analysis
- [x] Performance attribution

## Rule 7: Execution Management ✅ 97%

- [x] Execute ONLY with authorization
- [x] Use UnifiedExecutionEngine
- [x] EnhancedTradingEngine for planning (HOW)
- [x] Position updates via RiskManager callback
- [x] NO direct position updates
- [ ] Implement order rejection handler
- [ ] Add position aging monitor
- [ ] Market impact modeling
- [x] Smart order routing exists

---

## Quick Compliance Check

### Before Writing New Component:

1. Does it implement ISystemComponent? ✓
2. Does it need regime awareness? If yes, implement IRegimeAware ✓
3. Does it use centralized config? ✓
4. Does it register with orchestrator? ✓
5. Does it follow authorization patterns? ✓

### Before Writing New Strategy:

1. Does it extend EnhancedBaseStrategy? ✓
2. Does it consume EnrichedMarketData? ✓
3. Does it calculate its own indicators? ✗ (PROHIBITED!)
4. Does it read pre-calculated indicators? ✓
5. Does it register with StrategyManager? ✓

### Before Executing Trades:

1. Did you get RiskManager authorization? ✓ (MANDATORY!)
2. Do you update positions directly? ✗ (PROHIBITED!)
3. Do you use RiskManager callbacks? ✓
4. Do you respect authorization limits? ✓
5. Do you handle rejections? ✓

---

## Prohibited Patterns ❌

### NEVER DO THIS:

```python
# ❌ Calculate indicators in strategy
def _calculate_rsi(self, data):
    rsi = ...  # WRONG!

# ❌ Update positions directly
self.positions[symbol] += quantity  # WRONG!

# ❌ Execute without authorization
await self.broker.place_order(order)  # WRONG!

# ❌ Bypass pipeline
raw_data = self.database.query(...)  # WRONG!

# ❌ Scattered config
@dataclass
class MyConfig:  # WRONG! Use core_engine.config
    param: int = 10
```

### ALWAYS DO THIS:

```python
# ✅ Read pre-calculated indicators
rsi = data['RSI_14'].iloc[-1]  # CORRECT!

# ✅ Update via RiskManager
await risk_manager.update_position(...)  # CORRECT!

# ✅ Get authorization first
auth = await risk_manager.authorize_trading_decision(request)
if auth.authorized:
    await execution_engine.execute(auth)  # CORRECT!

# ✅ Use pipeline
enriched = await pipeline.process_market_data(symbols)  # CORRECT!

# ✅ Centralized config
from core_engine.config import MyConfig
config = MyConfig(param=10)  # CORRECT!
```

---

## Common Violations

1. **Calculating indicators in strategies** (Rule 3)
   - Solution: Read from enriched_data DataFrame
   
2. **Direct position updates** (Rule 4)
   - Solution: Use RiskManager callbacks
   
3. **Bypassing authorization** (Rule 4)
   - Solution: Always call authorize_trading_decision()
   
4. **Not implementing IRegimeAware** (Rule 2)
   - Solution: Add interface to operational components
   
5. **Scattered configs** (Rule 1)
   - Solution: Use core_engine.config

---

## Need Help?

- **Full Audit:** `docs/03_compliance_audits/COMPREHENSIVE_RULES_COMPLIANCE_AUDIT.md`
- **Summary:** `docs/03_compliance_audits/AUDIT_EXECUTIVE_SUMMARY.md`
- **Rules:** See workspace rules in `.cursor/rules/`
- **Examples:** Check existing components for patterns

**Last Updated:** November 23, 2025

