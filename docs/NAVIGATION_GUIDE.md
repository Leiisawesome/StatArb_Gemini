# Documentation Navigation Guide

**Last Updated:** November 14, 2025  
**Organization:** Institutional-grade structure

---

## Quick Start

### New Users Start Here 🚀
1. **Main README:** `README.md` - Overview of documentation
2. **Quick Start Guide:** `01_quick_start/` - Get started quickly
3. **Momentum Strategy:** `MOMENTUM_STRATEGY_IMPLEMENTATION.md` - Primary implementation guide

### Looking for Something Specific?

**Production Documentation:**
- Implementation guides → See below
- Testing documentation → `07_testing/`
- Compliance audits → `03_compliance_audits/`

**Development History:**
- Development decisions → `development_history/momentum_strategy/`
- Bug fixes → `development_history/momentum_strategy/bug_fixes/`
- Investigations → `development_history/momentum_strategy/investigations/`

---

## Documentation Structure

### 📁 01_quick_start/
**Purpose:** Getting started guides and quick examples

**Files:**
- `EXAMPLE_TSLA_1WEEK_GUIDE.md` - 1-week backtest example

**Use When:** You need to run the system quickly

---

### 📁 02_architecture/
**Purpose:** System architecture and design documentation

**Files:**
- `INSTITUTIONAL_BACKTEST_ENGINE_EVALUATION.md` - Backtest engine analysis
- `QUANTITATIVE_INFRASTRUCTURE_ANALYSIS.md` - Infrastructure design

**Use When:** Understanding system design

---

### 📁 03_compliance_audits/
**Purpose:** Rule compliance and architectural audits

**Files:**
- `INSTITUTIONAL_BACKTEST_COMPLIANCE.md` - Backtest compliance
- `RULE_2_HIERARCHICAL_ARCHITECTURE_UPDATED.md` - Architecture compliance
- `RULE_3_DATA_PIPELINE_UPDATED.md` - Data pipeline compliance

**Use When:** Reviewing compliance with architectural rules

---

### 📁 04_implementation/
**Purpose:** Implementation details and guides

**Use When:** Implementing new features or understanding existing ones

---

### 📁 05_project_summaries/
**Purpose:** Project completion summaries and milestone documents

**Files:**
- `COMPLIANCE_AUDIT_COMPLETE.md` - Compliance audit summary
- `EXAMPLES_ORGANIZATION_COMPLETE.md` - Examples organization
- `ISSUES_2_3_FIX_SUMMARY.md` - Bug fix summaries

**Use When:** Reviewing completed projects and milestones

---

### 📁 06_archived_phase_summaries/
**Purpose:** Archived project phase summaries

**Use When:** Historical reference for completed phases

---

### 📁 07_testing/
**Purpose:** Testing documentation, coverage, and test results

**Subdirectories:**
- `coverage/` - Test coverage analysis
- `integration/` - Integration test documentation
  - `LIVE_DATA_VALIDATION_16_TRADES_DETAILS.md` - Live test results
  - `QUICKSTART_RUN_RESULTS.md` - Quick start test results
  - `RECOMMENDED_MOMENTUM_TEST_DATES.md` - Test date recommendations
  - `integration_test_suite_plan.md` - Test suite planning
  - `integration_test_suite_verification.md` - Test verification

**Use When:** 
- Running tests
- Understanding test coverage
- Reviewing test results

---

### 📁 08_analysis/
**Purpose:** System analysis, investigations, and deep dives

**Subdirectories:**
- `compliance/` - Compliance analysis
- `dataframes/` - DataFrame analysis and audits
- `expert_review/` - Expert system reviews
- `signals/` - Signal generation analysis
  - `DIAGNOSTIC_NO_THRESHOLD_LOGS.md` - Signal diagnostics
  - `TRADE_REJECTION_DETAILED_ANALYSIS.md` - Trade rejection analysis
  - `230_SHARES_CALCULATION_EXPLAINED.md` - Quantity calculation
  - `84_signals_logic_analysis.md` - Signal logic analysis
  - `signal_generation_rate_analysis.md` - Generation rate analysis
- `simulation/` - Simulation analysis
- `strategies/` - Strategy analysis

**Use When:**
- Debugging signal generation
- Understanding trade rejections
- Analyzing system behavior

---

### 📁 09_reports/
**Purpose:** System reports and analytics outputs

**Use When:** Reviewing system performance reports

---

### 📁 development_history/momentum_strategy/
**Purpose:** Complete development history of momentum strategy v2.0

**Subdirectories:**
- `cleanup_phases/` - Cleanup project (Phases 1-5)
  - `CLEANUP_PROJECT_COMPLETE.md` - ⭐ Final cleanup summary
  - `CODE_CLEANUP_PLAN.md` - Cleanup planning
  - `PHASE1_CLEANUP_COMPLETE.md` - Quick wins
  - `PHASE2_COMPLETE.md` - Investigation (composite_pct)
  - `PHASE3_DOCUMENTATION_CLEANUP_COMPLETE.md` - Documentation organization
  - `PHASE4_FINAL_VALIDATION_COMPLETE.md` - Final validation (+815% return)

- `investigations/` - Technical investigations
  - `EXECUTION_INVESTIGATION_SUCCESS.md` - Execution issue resolution
  - `EXECUTION_ISSUE_ROOT_CAUSE_COMPLETE.md` - Root cause analysis

- `bug_fixes/` - Bug fixes and resolutions
  - Various bug fix documents

- `planning/` - Design and planning documents
  - Exit logic planning
  - Position tracking decisions

- [26 Phase Documents] - Original development phases

**Use When:**
- Understanding development decisions
- Tracing design rationale
- Learning from past issues

---

## Common Use Cases

### 🎯 "I want to implement the momentum strategy"
1. Read `MOMENTUM_STRATEGY_IMPLEMENTATION.md` (root)
2. Check `01_quick_start/EXAMPLE_TSLA_1WEEK_GUIDE.md`
3. Review `03_compliance_audits/` for architectural requirements

### 🐛 "I found a bug"
1. Check `08_analysis/signals/` for similar issues
2. Review `development_history/momentum_strategy/bug_fixes/` for past fixes
3. Check `07_testing/integration/` for test coverage

### 📊 "I want to understand test results"
1. Start with `07_testing/integration/LIVE_DATA_VALIDATION_16_TRADES_DETAILS.md`
2. Check `07_testing/integration/QUICKSTART_RUN_RESULTS.md`
3. Review test date recommendations

### 🔍 "Why was my trade rejected?"
1. Read `08_analysis/signals/TRADE_REJECTION_DETAILED_ANALYSIS.md`
2. Check `08_analysis/signals/230_SHARES_CALCULATION_EXPLAINED.md`
3. Review risk management configuration

### 📈 "I want to see performance results"
1. Check `development_history/momentum_strategy/cleanup_phases/PHASE4_FINAL_VALIDATION_COMPLETE.md`
2. Review `07_testing/integration/LIVE_DATA_VALIDATION_16_TRADES_DETAILS.md`
3. See execution investigation results

### 🏗️ "I need to understand the architecture"
1. Read architectural rules in `03_compliance_audits/`
2. Check `02_architecture/` for design documents
3. Review `MOMENTUM_STRATEGY_IMPLEMENTATION.md` for implementation

---

## Key Documents

### Essential Reading ⭐
1. **`README.md`** - Main documentation index
2. **`MOMENTUM_STRATEGY_IMPLEMENTATION.md`** - Complete implementation guide
3. **`development_history/momentum_strategy/cleanup_phases/CLEANUP_PROJECT_COMPLETE.md`** - Project completion summary

### Performance & Results 📊
1. **`development_history/momentum_strategy/cleanup_phases/PHASE4_FINAL_VALIDATION_COMPLETE.md`** - +815% return validation
2. **`07_testing/integration/LIVE_DATA_VALIDATION_16_TRADES_DETAILS.md`** - Detailed test results

### Development History 📚
1. **`development_history/momentum_strategy/README.md`** - Complete timeline
2. **`development_history/momentum_strategy/cleanup_phases/`** - Cleanup project (8 docs)
3. **`development_history/momentum_strategy/investigations/`** - Technical investigations (2 docs)

---

## Finding What You Need

### By Topic

**Configuration:**
- See `MOMENTUM_STRATEGY_IMPLEMENTATION.md` → Configuration section

**Testing:**
- Start in `07_testing/integration/`

**Bug Fixes:**
- Check `development_history/momentum_strategy/bug_fixes/`

**Compliance:**
- Review `03_compliance_audits/`

**Performance:**
- See Phase 4 validation results

**Signals:**
- Check `08_analysis/signals/`

### By File Type

**`.md` files:** All documentation
**`README.md`:** Index files (start here in any folder)

---

## Tips for Navigation

### 1. Start with README files
Every major folder has a README that explains its contents.

### 2. Use the folder structure
The numbered folders (01-09) are in priority order:
- 01 = Start here
- 09 = Advanced/reports

### 3. Check development_history for "why"
If you wonder "why was this done?", check development_history.

### 4. Look for summary documents
Files ending in "COMPLETE" are summaries of major milestones.

### 5. Follow the breadcrumbs
Documents reference related documents - follow the trail.

---

## Organization Principles

### Production vs. Development
- **Root folders (01-09):** Production documentation
- **development_history/:** Development decisions and history

### Naming Conventions
- **UPPERCASE:** Important summary documents
- **lowercase:** Ongoing documentation
- **_COMPLETE:** Finished milestone documents

### Folder Numbers
- **01-03:** Getting started and fundamentals
- **04-06:** Implementation and projects
- **07-09:** Testing, analysis, and reports

---

## Need Help?

### Can't Find Something?
1. Check this navigation guide
2. Look in the most relevant numbered folder
3. Search development_history for historical context

### Understanding Organization?
- This guide explains the structure
- Each folder's README explains its purpose
- Follow the quick start path for new users

---

## Recent Changes

**November 14, 2025:**
- Organized 42 loose files into proper categories
- Created development_history subdirectories
- Moved 22 files to archive
- Moved 10 files to proper categories
- Only 2 essential files remain in root

**Result:** Clean, professional documentation structure

---

**This guide helps you navigate the complete StatArb_Gemini documentation efficiently.**


