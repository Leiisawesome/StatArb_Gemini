#!/usr/bin/env python3
"""
Pair Discovery Integration - Missing Indicators Handler
=====================================================

This script integrates with your pair discovery system to automatically
download missing technical indicators for newly discovered pairs.

Features:
✅ Integrates with pair screening results
✅ Checks ClickHouse for missing indicators
✅ Downloads only what's needed
✅ Updates pair screening with indicator availability
✅ Maintains indicator completeness for backtesting

Usage in your pair discovery workflow:
    from pair_indicator_integration import PairIndicatorManager
    
    # After discovering new pairs
    manager = PairIndicatorManager()
    manager.ensure_indicators_for_pairs(new_pairs)
"""

import os
import sys
import json
import logging
from typing import List, Dict, Set, Tuple
from datetime import datetime, timedelta
import clickhouse_connect

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from on_demand_indicator_downloader import OnDemandIndicatorDownloader

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PairIndicatorManager:
    """Manage technical indicators for discovered pairs"""
    
    def __init__(self, api_key: str = None):
        self.downloader = OnDemandIndicatorDownloader(api_key)
        self.setup_clickhouse()
        
    def setup_clickhouse(self):
        """Setup ClickHouse connection for pair data queries"""
        try:
            self.ch_client = clickhouse_connect.get_client(
                host="localhost",
                port=8123,
                database='polygon_data'
            )
            logger.info("✅ ClickHouse connection for pairs established")
        except Exception as e:
            logger.error(f"ClickHouse connection failed: {e}")
            raise
    
    def extract_symbols_from_pairs(self, pairs: List[Tuple[str, str]]) -> Set[str]:
        """Extract unique symbols from pair tuples"""
        symbols = set()
        for pair in pairs:
            symbols.add(pair[0])
            symbols.add(pair[1])
        return symbols
    
    def get_pair_screening_results(self) -> List[Tuple[str, str]]:
        """Get recent pair screening results from ClickHouse"""
        try:
            # Query your pair screening results table
            query = """
            SELECT DISTINCT symbol1, symbol2 
            FROM pair_screening_results 
            WHERE passed_screening = 1
            AND screening_date >= today() - 30  -- Last 30 days
            ORDER BY symbol1, symbol2
            """
            
            result = self.ch_client.query(query)
            pairs = [(row[0], row[1]) for row in result.result_set]
            
            logger.info(f"Found {len(pairs)} pairs from recent screening")
            return pairs
            
        except Exception as e:
            logger.warning(f"Could not query pair screening results: {e}")
            # Fallback to known pairs
            return [
                ("QQQ", "TQQQ"), ("BITX", "IBIT"), ("TLT", "TMF"),
                ("NVDA", "NVDL"), ("SOFI", "SPY"), ("NVDA", "SOXL")
            ]
    
    def check_indicator_completeness(self, symbols: List[str], 
                                   start_date: str = "2023-01-01",
                                   end_date: str = "2025-06-30") -> Dict[str, Dict]:
        """Check indicator completeness for symbols"""
        
        completeness_report = {}
        
        for symbol in symbols:
            missing_indicators = self.downloader.get_missing_indicators(
                symbol, start_date, end_date
            )
            
            completeness_report[symbol] = {
                "complete": len(missing_indicators) == 0,
                "missing_count": len(missing_indicators),
                "missing_indicators": missing_indicators,
                "ready_for_backtesting": len(missing_indicators) == 0
            }
        
        return completeness_report
    
    def ensure_indicators_for_pairs(self, pairs: List[Tuple[str, str]], 
                                  start_date: str = "2023-01-01",
                                  end_date: str = "2025-06-30") -> Dict:
        """Ensure all pairs have complete indicator data"""
        
        logger.info(f"\n🔍 PAIR INDICATOR COMPLETENESS CHECK")
        logger.info(f"{'='*50}")
        logger.info(f"Checking {len(pairs)} pairs for indicator completeness")
        
        # Extract unique symbols
        symbols = list(self.extract_symbols_from_pairs(pairs))
        logger.info(f"Unique symbols to check: {len(symbols)}")
        
        # Check completeness
        completeness = self.check_indicator_completeness(symbols, start_date, end_date)
        
        # Identify symbols needing downloads
        symbols_to_download = [
            symbol for symbol, report in completeness.items() 
            if not report["complete"]
        ]
        
        if not symbols_to_download:
            logger.info("✅ All pairs have complete indicator data!")
            return {
                "status": "complete",
                "pairs_checked": len(pairs),
                "symbols_complete": len(symbols),
                "downloads_needed": 0
            }
        
        logger.info(f"📥 {len(symbols_to_download)} symbols need indicator downloads")
        
        # Download missing indicators
        download_results = self.downloader.download_missing_for_symbols(
            symbols_to_download, start_date, end_date
        )
        
        # Generate pair readiness report
        return self.generate_pair_readiness_report(pairs, completeness, download_results)
    
    def generate_pair_readiness_report(self, pairs: List[Tuple[str, str]], 
                                     completeness: Dict, 
                                     download_results: Dict) -> Dict:
        """Generate comprehensive pair readiness report"""
        
        # Re-check completeness after downloads
        symbols = list(self.extract_symbols_from_pairs(pairs))
        updated_completeness = self.check_indicator_completeness(symbols)
        
        pair_readiness = []
        ready_pairs = 0
        
        for pair in pairs:
            symbol1, symbol2 = pair
            
            symbol1_ready = updated_completeness.get(symbol1, {}).get("complete", False)
            symbol2_ready = updated_completeness.get(symbol2, {}).get("complete", False)
            pair_ready = symbol1_ready and symbol2_ready
            
            if pair_ready:
                ready_pairs += 1
            
            pair_readiness.append({
                "pair": f"{symbol1}-{symbol2}",
                "symbol1": symbol1,
                "symbol2": symbol2,
                "symbol1_ready": symbol1_ready,
                "symbol2_ready": symbol2_ready,
                "pair_ready": pair_ready,
                "missing_indicators": {
                    symbol1: updated_completeness.get(symbol1, {}).get("missing_count", 0),
                    symbol2: updated_completeness.get(symbol2, {}).get("missing_count", 0)
                }
            })
        
        report = {
            "status": "processed",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_pairs": len(pairs),
                "ready_pairs": ready_pairs,
                "completion_rate": f"{(ready_pairs/len(pairs)*100):.1f}%",
                "symbols_processed": download_results.get("symbols_processed", 0),
                "indicators_downloaded": download_results.get("total_downloaded", 0),
                "download_errors": download_results.get("total_errors", 0)
            },
            "pair_readiness": pair_readiness,
            "download_details": download_results
        }
        
        # Log summary
        logger.info(f"\n📊 PAIR READINESS SUMMARY")
        logger.info(f"{'='*35}")
        logger.info(f"Ready pairs: {ready_pairs}/{len(pairs)} ({report['summary']['completion_rate']})")
        logger.info(f"Indicators downloaded: {report['summary']['indicators_downloaded']}")
        logger.info(f"Download errors: {report['summary']['download_errors']}")
        
        # Save detailed report
        report_file = f"pair_indicator_readiness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📁 Detailed report saved: {report_file}")
        
        return report
    
    def auto_maintain_pair_indicators(self) -> Dict:
        """Automatically maintain indicators for all discovered pairs"""
        
        logger.info("\n🔄 AUTO-MAINTAINING PAIR INDICATORS")
        logger.info("="*45)
        
        # Get recent pair discoveries
        pairs = self.get_pair_screening_results()
        
        if not pairs:
            logger.warning("No pairs found in screening results")
            return {"status": "no_pairs", "message": "No pairs found"}
        
        # Ensure indicators for all pairs
        return self.ensure_indicators_for_pairs(pairs)
    
    def get_backtest_ready_pairs(self) -> List[Tuple[str, str]]:
        """Get pairs that are ready for backtesting (complete indicators)"""
        
        pairs = self.get_pair_screening_results()
        symbols = list(self.extract_symbols_from_pairs(pairs))
        completeness = self.check_indicator_completeness(symbols)
        
        ready_pairs = []
        for pair in pairs:
            symbol1, symbol2 = pair
            if (completeness.get(symbol1, {}).get("complete", False) and 
                completeness.get(symbol2, {}).get("complete", False)):
                ready_pairs.append(pair)
        
        logger.info(f"Found {len(ready_pairs)}/{len(pairs)} pairs ready for backtesting")
        return ready_pairs


def main():
    """CLI interface for pair indicator management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage indicators for discovered pairs")
    parser.add_argument("--check-pairs", action="store_true", help="Check pair indicator completeness")
    parser.add_argument("--auto-maintain", action="store_true", help="Auto-maintain all pair indicators")
    parser.add_argument("--list-ready", action="store_true", help="List backtest-ready pairs")
    parser.add_argument("--ensure-pairs", type=str, help="Ensure indicators for specific pairs (format: SYM1-SYM2,SYM3-SYM4)")
    
    args = parser.parse_args()
    
    try:
        manager = PairIndicatorManager()
        
        if args.check_pairs:
            pairs = manager.get_pair_screening_results()
            symbols = list(manager.extract_symbols_from_pairs(pairs))
            completeness = manager.check_indicator_completeness(symbols)
            
            print(f"\n📊 Indicator Completeness Report")
            print("="*40)
            for symbol, report in completeness.items():
                status = "✅ Complete" if report["complete"] else f"❌ Missing {report['missing_count']}"
                print(f"{symbol:8} {status}")
        
        if args.list_ready:
            ready_pairs = manager.get_backtest_ready_pairs()
            print(f"\n✅ Backtest-Ready Pairs ({len(ready_pairs)})")
            print("="*30)
            for pair in ready_pairs:
                print(f"{pair[0]}-{pair[1]}")
        
        if args.ensure_pairs:
            pair_strings = args.ensure_pairs.split(",")
            pairs = []
            for pair_str in pair_strings:
                sym1, sym2 = pair_str.strip().split("-")
                pairs.append((sym1, sym2))
            
            manager.ensure_indicators_for_pairs(pairs)
        
        if args.auto_maintain:
            manager.auto_maintain_pair_indicators()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
