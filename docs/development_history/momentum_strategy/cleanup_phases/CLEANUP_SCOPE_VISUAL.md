# Cleanup Scope - Files and Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLEANUP SCOPE OVERVIEW                        │
└─────────────────────────────────────────────────────────────────┘

PRIORITY 1: PRODUCTION-CRITICAL 🔴
═══════════════════════════════════
📁 core_engine/trading/strategies/implementations/momentum/
   └── enhanced_momentum.py (1,966 lines)
       ├── Line 1574: TODO - composite_pct investigation
       ├── Line 1580: Remove "TESTING MODE" label
       ├── Line 1589: Remove "TESTING MODE" label
       ├── Line 907-908: Remove commented position tracking
       └── Line 30: Update version to 2.0.0
       Status: 5 items to fix

📁 core_engine/config/
   └── strategies.py (Lines 101-260)
       ├── Line 212: Update scan_all_bars default (True→False)
       ├── Add: composite_z_entry parameter
       └── Add: composite_pct_entry parameter
       Status: 3 items to fix


PRIORITY 2: INVESTIGATION REQUIRED 🟠
════════════════════════════════════════
📁 core_engine/processing/features/
   └── engineer.py
       └── _create_composite_momentum_features()
           └── Investigate composite_pct output format
               ├── Option A: 0-1 decimal
               ├── Option B: 0-100 percentage
               └── Option C: -1 to 1 normalized
       Status: Investigation + fix based on findings


PRIORITY 3: DOCUMENTATION CLEANUP 🟡
═══════════════════════════════════════
📁 docs/
   ├── Development History (TO ARCHIVE):
   │   ├── PHASE25_OLD_TRACKING_CLEANUP_COMPLETE.md
   │   ├── PHASE3_HYBRID_EXIT_LOGIC_COMPLETE.md
   │   ├── PHASE4_ENTRY_LOGIC_PLANNING.md
   │   ├── PHASE4B_TYPE2_REGIME_AWARENESS_IMPLEMENTATION.md
   │   ├── PHASE4C_ROOT_CAUSE_RESOLVED.md
   │   ├── COMPOSITE_Z_REGIME_AWARENESS_ANALYSIS.md
   │   ├── SIGNAL_GENERATION_ROOT_CAUSE_COMPLETE.md
   │   ├── INVESTIGATION_COMPLETE_ALL_SYSTEMS_OPERATIONAL.md
   │   └── VICTORY_SIGNAL_GENERATION_COMPLETE.md
   │
   └── TO CREATE:
       └── MOMENTUM_STRATEGY_IMPLEMENTATION.md (consolidated guide)
   Status: 9 files to archive, 1 to create


PRIORITY 4: TEST INFRASTRUCTURE 🟢
═══════════════════════════════════
📁 tests/integration/
   └── live_data_validation.py (2,769 lines)
       ├── Line 608: Add comment for scan_all_bars override
       └── Review: Reduce diagnostic logging verbosity
       Status: 2 items to review


┌─────────────────────────────────────────────────────────────────┐
│                    DEPENDENCY CHAIN                              │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  FeatureEngineer│
                    │  (Investigation)│
                    └────────┬────────┘
                             │
                    Creates composite_pct
                             │
                             ▼
                    ┌─────────────────┐
                    │ MomentumConfig  │
                    │ Add Parameters  │
                    └────────┬────────┘
                             │
                    Defines thresholds
                             │
                             ▼
                    ┌─────────────────┐
                    │EnhancedMomentum │
                    │ Strategy Cleanup│
                    └────────┬────────┘
                             │
                    Uses config values
                             │
                             ▼
                    ┌─────────────────┐
                    │ Live Data Test  │
                    │ Validation      │
                    └─────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION SEQUENCE                       │
└─────────────────────────────────────────────────────────────────┘

Step 1: Quick Cosmetic Fixes (Safe, No Dependencies)
├── enhanced_momentum.py: Remove "TESTING MODE" labels
├── enhanced_momentum.py: Remove commented code
└── enhanced_momentum.py: Update version number

Step 2: Investigation (Must Complete Before Step 3)
└── engineer.py: Investigate composite_pct format
    └── Document findings

Step 3: Configuration Updates (Depends on Step 2)
├── strategies.py: Add composite_z_entry parameter
├── strategies.py: Add composite_pct_entry parameter
└── strategies.py: Update scan_all_bars default

Step 4: Production Fix (Depends on Step 3)
└── enhanced_momentum.py: Re-enable composite_pct check
    └── With correct thresholds from investigation

Step 5: Validation (Final Gate)
└── Run live_data_validation.py
    └── Verify 162+ signals still generated


┌─────────────────────────────────────────────────────────────────┐
│                    CHECKLIST SUMMARY                             │
└─────────────────────────────────────────────────────────────────┘

Production Critical (Must Fix):
☐ Remove "TESTING MODE" labels (2 locations)
☐ Remove commented code (1 location)
☐ Update strategy version (1 location)
☐ Add config parameters (2 parameters)
☐ Investigate composite_pct format (1 investigation)
☐ Re-enable composite_pct check (1 fix)

Documentation (Should Fix):
☐ Archive development docs (9 files)
☐ Create consolidated guide (1 file)
☐ Update scan_all_bars default (1 config)

Testing (Nice to Have):
☐ Add test config comment (1 comment)
☐ Review logging verbosity (multiple locations)

Total Items: 18 (6 must-fix, 11 should-fix, 1 nice-to-have)
Estimated Time: 5 hours total


┌─────────────────────────────────────────────────────────────────┐
│                    FILES NOT REQUIRING CLEANUP                   │
└─────────────────────────────────────────────────────────────────┘

✅ Core Architecture (All Clean):
   ├── ProcessingPipelineOrchestrator
   ├── CentralRiskManager
   ├── UnifiedExecutionEngine
   ├── EnhancedRegimeEngine
   └── StrategyManager

✅ Other Strategy Implementations (Not Modified):
   ├── mean_reversion/
   ├── statistical_arbitrage/
   ├── breakout/
   └── [7 more strategies]

✅ Data Pipeline (Working Correctly):
   ├── ClickHouseDataManager
   ├── EnhancedTechnicalIndicators
   └── EnhancedFeatureEngineer (except composite_pct investigation)

✅ Test Infrastructure (Functional):
   └── live_data_validation.py (only minor comments needed)

