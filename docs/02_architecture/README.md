# Architecture Documentation

Documentation for the StatArb_Gemini core_engine architecture, design patterns, and system organization.

---

## Architectural Rules

The core_engine follows **7 architectural rules** that ensure institutional-grade quality and maintainability.

**📍 Primary Reference:** [../../.cursor/rules/TIER-1-ARCHITECTURAL-RULES/](../../.cursor/rules/TIER-1-ARCHITECTURAL-RULES/)

### The 7 Rules

1. **Component Integration Standards** - ISystemComponent interface and orchestrator integration
2. **Hierarchical Architecture with Regime-First** - 6-layer hierarchy with regime engine priority
3. **Data Flow Pipeline** - Unified data management through ClickHouseDataManager
4. **Risk Governance** - Centralized risk control through CentralRiskManager
5. **Multi-Strategy Coordination** - Coordinated multi-strategy signal aggregation
6. **Advanced Analytics** - Real-time and batch analytics capabilities
7. **Execution Management** - Unified execution with liquidity assessment

---

## System Architecture

### 6-Layer Hierarchical Structure

```
Layer 0: System Orchestration (HierarchicalSystemOrchestrator)
    ↓
Layer 1: Governance (CentralRiskManager)
    ↓
Layer 2: Data Management (ClickHouseDataManager)
    ↓
Layer 3: Core Processing (Indicators → Features → Signals)
    ↓
Layer 4: Analytics & Strategy (StrategyManager, Analytics)
    ↓
Layer 5: Trading & Execution (TradingEngine, ExecutionEngine)
```

### Initialization Order

Components initialize in strict dependency order:

1. **EnhancedRegimeEngine** (order=5) - FIRST (Regime-First Principle)
2. ClickHouseDataManager (order=10)
3. EnhancedTechnicalIndicators (order=15)
4. StrategyManager (order=20)
5. CentralRiskManager (order=25)
6. EnhancedTradingEngine (order=30)
7. Analytics components (order=32-35)
8. UnifiedExecutionEngine (order=40)

---

## Key Interfaces

### ISystemComponent

All components implement this interface for lifecycle management:

```python
class ISystemComponent(ABC):
    async def initialize(self) -> bool
    async def start(self) -> bool
    async def stop(self) -> bool
    async def health_check(self) -> Dict[str, Any]
    def get_status(self) -> Dict[str, Any]
```

### IRegimeAware

Components that adapt to market regimes implement this interface:

```python
class IRegimeAware(ABC):
    def set_regime_engine(self, regime_engine) -> None
    async def on_regime_change(self, regime_context) -> None
    def get_current_regime_context(self) -> Optional[RegimeContext]
    async def adapt_to_regime(self, regime_context) -> Dict[str, Any]
    def validate_regime_dependency(self) -> bool
```

---

## Design Patterns

### 1. Regime-First Principle

Market regime detection initializes FIRST and provides context for all downstream operations.

**Implementation:**
- EnhancedRegimeEngine initializes at order=5 (first)
- All operational components implement IRegimeAware
- Dynamic adaptation to regime changes

### 2. Single Data Authority

All market data access goes through ClickHouseDataManager (NO direct database access).

**Implementation:**
- ClickHouseDataManager is the only component accessing database
- All other components use DataManager API
- Proper caching and validation

### 3. Centralized Risk Governance

ALL trading decisions require authorization from CentralRiskManager.

**Implementation:**
- CentralRiskManager is single authority for trades
- Position management centralized
- Cash management enforced

### 4. Multi-Strategy Coordination

Multiple strategies coordinate through StrategyManager with signal aggregation.

**Implementation:**
- StrategyManager coordinates 10 strategies
- Signal conflict resolution
- Dynamic strategy weighting

---

## Component Catalog

### Core System Components

- **HierarchicalSystemOrchestrator** - Component lifecycle and coordination
- **CentralRiskManager** - Risk governance and trade authorization
- **ClickHouseDataManager** - Unified data access

### Processing Components

- **EnhancedRegimeEngine** - Market regime detection (Regime-First)
- **EnhancedTechnicalIndicators** - Technical indicator calculation
- **EnhancedFeatureEngineer** - Feature engineering pipeline
- **EnhancedSignalGenerator** - Trading signal generation

### Strategy Components

- **StrategyManager** - Multi-strategy coordination
- **10 Enhanced Strategies** - Complete strategy implementations
- **MultiStrategySignalAggregator** - Signal aggregation
- **SignalConflictResolver** - Conflict resolution

### Analytics Components

- **EnhancedAnalyticsManager** - Analytics orchestration
- **EnhancedMetricsCalculator** - Performance metrics
- **PerformanceAnalyzer** - Performance analysis

### Execution Components

- **EnhancedTradingEngine** - Execution planning
- **UnifiedExecutionEngine** - Trade execution
- **EnhancedPortfolioManager** - Portfolio management

---

## Architecture Compliance

**Current Status:** ✅ 100% COMPLIANCE

All components follow architectural rules and patterns.

**Last Audit:** October 21, 2025  
**Compliance Report:** [../03_compliance_audits/2025-10-21_final_compliance_report.md](../03_compliance_audits/2025-10-21_final_compliance_report.md)

---

## Further Reading

**Detailed Rules:** [../../.cursor/rules/](../../.cursor/rules/)  
**Compliance Audits:** [../03_compliance_audits/](../03_compliance_audits/)  
**Implementation Guides:** [../04_implementation/](../04_implementation/)

---

**Last Updated:** October 21, 2025  
**Architecture Version:** v2.1

