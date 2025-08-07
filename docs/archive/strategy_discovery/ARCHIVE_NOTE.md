# Strategy Discovery Module - Archived

## Overview
This directory contains the archived Strategy Discovery module that was moved from the root `strategy_discovery/` directory during the codebase cleanup.

## Why Archived?
The Strategy Discovery module was archived because:

1. **Standalone Module**: It's a complete but isolated system that wasn't integrated with the main trading system
2. **Not Integrated**: No imports or references from other parts of the codebase
3. **Implementation Plan Only**: Only exists as part of a planned feature, not actively used
4. **No Active Development**: No recent development activity or integration work

## Contents
- `academic_miner.py` - Academic paper mining engine (12KB, 343 lines)
- `public_miner.py` - Public repository mining engine (20KB, 614 lines)
- `enhancer.py` - Strategy enhancement module (12KB, 348 lines)
- `validator.py` - Strategy validation framework (18KB, 502 lines)
- `integration.py` - Integration utilities (10KB, 276 lines)
- `main.py` - Main discovery system (11KB, 263 lines)
- `README.md` - Module documentation (7.6KB, 291 lines)
- `requirements.txt` - Module dependencies (595B, 40 lines)

## Module Features
- Academic strategy mining from SSRN, ArXiv, JSTOR, Google Scholar
- Public repository mining from Zipline, Backtrader, FinRL, Qlib
- NLP-based strategy extraction from papers
- AI enhancement with modern risk management
- JSON schema standardization
- Multi-level validation framework
- Integration with Trading Strategy Layer

## Note
This module is kept for historical reference and potential future implementation. The code is functional but not integrated with the current system architecture. If you need to implement strategy discovery functionality, this archived code can serve as a reference for the planned architecture.

## Current Development
For current development patterns and active modules, refer to:
- The actual implementation files in `core_structure/`
- Test files in `tests/` directory
- Documentation in `docs/` directory
