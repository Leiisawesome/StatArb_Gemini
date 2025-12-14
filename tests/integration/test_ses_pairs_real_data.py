"""
SES Pairs Trading Strategy - Real Data Integration Test
========================================================

Tests the Spread Exhaustion Scoring (SES) pairs trading strategy
with real market data from ClickHouse (polygon_data.ticks).

Usage:
    python -m tests.integration.test_ses_pairs_real_data
    python -m tests.integration.test_ses_pairs_real_data --days 30
    python -m tests.integration.test_ses_pairs_real_data --start 2024-01-01 --end 2024-06-30
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging
import sys
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import SES Strategy components
from core_engine.trading.strategies.implementations.pairs_trading import (
    SpreadExhaustionScorer,
    MeanReversionCore,
    SpreadDirection
)
from core_engine.config import PairsConfig
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.config import IndicatorConfig

class ClickHouseDirectReader:
    """
    Direct ClickHouse reader for polygon_data.ticks table.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        database: str = "polygon_data",
        table: str = "ticks"
    ):
        self.url = f"http://{host}:{port}"
        self.database = database
        self.table = table
        self.full_table = f"{database}.{table}"

    def test_connection(self) -> bool:
        """Test ClickHouse connection."""
        try:
            resp = requests.post(self.url, data="SELECT 1")
            return resp.status_code == 200
        except:
            return False

    def get_available_date_range(self, ticker: str) -> Dict[str, Any]:
        """Get available date range for a ticker."""
        query = f'''
        SELECT
            min(toDate(toDateTime64(window_start / 1000000000, 3))) as first_date,
            max(toDate(toDateTime64(window_start / 1000000000, 3))) as last_date,
            count(*) as total_bars
        FROM {self.full_table}
        WHERE ticker = '{ticker}'
        '''
        resp = requests.post(self.url, data=query, params={'default_format': 'JSON'})
        if resp.status_code == 200:
            data = resp.json().get('data', [{}])[0]
            return {
                'first_date': data.get('first_date'),
                'last_date': data.get('last_date'),
                'total_bars': data.get('total_bars', 0)
            }
        return {}

    def load_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        resample: str = "1h"
    ) -> pd.DataFrame:
        """
        Load OHLCV data for a ticker.

        Args:
            ticker: Stock ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            resample: Resample interval (1min, 5min, 15min, 1h, 1d)

        Returns:
            DataFrame with OHLCV data
        """
        # Convert resample to ClickHouse interval
        interval_map = {
            '1min': 'toStartOfMinute',
            '5min': 'toStartOfFiveMinute',
            '15min': 'toStartOfFifteenMinutes',
            '1h': 'toStartOfHour',
            '1d': 'toDate'
        }
        interval_func = interval_map.get(resample, 'toStartOfHour')

        query = f'''
        SELECT
            {interval_func}(toDateTime64(window_start / 1000000000, 3)) as timestamp,
            argMin(open, window_start) as open,
            max(high) as high,
            min(low) as low,
            argMax(close, window_start) as close,
            sum(volume) as volume
        FROM {self.full_table}
        WHERE ticker = '{ticker}'
          AND toDate(toDateTime64(window_start / 1000000000, 3)) >= '{start_date}'
          AND toDate(toDateTime64(window_start / 1000000000, 3)) <= '{end_date}'
        GROUP BY timestamp
        ORDER BY timestamp
        '''

        resp = requests.post(self.url, data=query, params={'default_format': 'JSON'})

        if resp.status_code == 200:
            data = resp.json().get('data', [])
            if data:
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                df = df.astype({
                    'open': float, 'high': float, 'low': float,
                    'close': float, 'volume': float
                })
                return df

        return pd.DataFrame()

class SESPairsRealDataTest:
    """
    Integration test for SES Pairs Trading with real ClickHouse data.
    """

    # Test pairs - Crypto ETFs (BTC/ETH proxies)
    TEST_PAIRS = [
        ('IBIT', 'ETHA'),    # iShares Bitcoin / iShares Ethereum
        ('FBTC', 'FETH'),    # Fidelity Bitcoin / Fidelity Ethereum
        ('GBTC', 'ETHE'),    # Grayscale Bitcoin / Grayscale Ethereum
        ('IBIT', 'FBTC'),    # Two Bitcoin ETFs (should be highly correlated)
        ('ETHA', 'FETH'),    # Two Ethereum ETFs (should be highly correlated)
    ]

    def __init__(
        self,
        start_date: str = None,
        end_date: str = None,
        lookback_days: int = 60,
        resample: str = "1h"
    ):
        """
        Initialize test with date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            lookback_days: Number of days to look back if dates not specified
            resample: Data resampling interval (1min, 5min, 15min, 1h, 1d)
        """
        # Set date range (default to recent data with crypto ETF overlap)
        if end_date is None:
            end_date = "2025-06-27"  # Last full trading day in data
        if start_date is None:
            # Start from 2024-07-23 when ETHA/FETH/ETHE launched
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_dt = max(
                end_dt - timedelta(days=lookback_days),
                datetime(2024, 7, 23)  # Earliest date for all crypto ETFs
            )
            start_date = start_dt.strftime('%Y-%m-%d')

        self.start_date = start_date
        self.end_date = end_date
        self.resample = resample

        # Get all unique symbols from pairs
        self.symbols = list(set(
            symbol for pair in self.TEST_PAIRS for symbol in pair
        ))

        logger.info(f"📅 Test period: {start_date} to {end_date}")
        logger.info(f"📊 Testing {len(self.TEST_PAIRS)} pairs with {len(self.symbols)} symbols")
        logger.info(f"⏱️ Resample interval: {resample}")

        # Components
        self.ch_reader = ClickHouseDirectReader()
        self.indicator_engine: Optional[EnhancedTechnicalIndicators] = None
        self.ses_scorer: Optional[SpreadExhaustionScorer] = None

        # Results
        self.raw_data: Dict[str, pd.DataFrame] = {}
        self.enriched_data: Dict[str, pd.DataFrame] = {}
        self.pair_results: Dict[str, Dict[str, Any]] = {}

    def setup(self) -> bool:
        """Initialize all components."""
        logger.info("🔧 Setting up components...")

        try:
            # Test ClickHouse connection
            if not self.ch_reader.test_connection():
                logger.error("❌ ClickHouse connection failed!")
                return False
            logger.info("✅ ClickHouse connected")

            # Initialize Indicator Engine
            indicator_config = IndicatorConfig()
            self.indicator_engine = EnhancedTechnicalIndicators(indicator_config)
            logger.info("✅ Indicator Engine initialized")

            # Initialize SES Scorer
            pairs_config = PairsConfig(
                asset_universe=self.symbols,
                entry_zscore=2.0,
                exit_zscore=0.5,
                stop_loss_zscore=3.5,
                max_pairs=5,
                lookback_period=200,
                min_correlation=0.6,
                cointegration_threshold=0.10,
                position_size_pct=0.05
            )
            self.ses_scorer = SpreadExhaustionScorer(pairs_config)
            logger.info("✅ SES Scorer initialized")

            return True

        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_data(self) -> bool:
        """Load market data from ClickHouse."""
        logger.info("📥 Loading market data from ClickHouse...")

        try:
            for symbol in self.symbols:
                df = self.ch_reader.load_ohlcv(
                    ticker=symbol,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    resample=self.resample
                )

                if df is not None and not df.empty:
                    self.raw_data[symbol] = df
                    logger.info(f"   ✅ {symbol}: {len(df)} bars, ${df['close'].iloc[-1]:.2f}")
                else:
                    logger.warning(f"   ⚠️ {symbol}: No data available")

            if len(self.raw_data) < 2:
                logger.error("❌ Need at least 2 symbols with data")
                return False

            logger.info(f"📊 Loaded data for {len(self.raw_data)} symbols")
            return True

        except Exception as e:
            logger.error(f"❌ Data loading failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def calculate_indicators(self) -> bool:
        """Calculate technical indicators for all symbols."""
        logger.info("📈 Calculating indicators...")

        try:
            for symbol, df in self.raw_data.items():
                # Calculate indicators
                try:
                    enriched = self.indicator_engine.calculate_indicators(df.copy())

                    if enriched is not None and not enriched.empty:
                        self.enriched_data[symbol] = enriched
                        indicator_cols = [c for c in enriched.columns
                                         if c not in ['open', 'high', 'low', 'close', 'volume']]
                        logger.info(f"   ✅ {symbol}: {len(indicator_cols)} indicators")
                    else:
                        self.enriched_data[symbol] = df
                        logger.warning(f"   ⚠️ {symbol}: Using raw data")
                except Exception as e:
                    self.enriched_data[symbol] = df
                    logger.warning(f"   ⚠️ {symbol}: Indicator calc failed - {e}")

            return True

        except Exception as e:
            logger.error(f"❌ Indicator calculation failed: {e}")
            return False

    def analyze_pairs(self) -> None:
        """Analyze all pairs using SES framework."""
        logger.info("\n" + "=" * 70)
        logger.info("🔬 ANALYZING PAIRS WITH SES FRAMEWORK")
        logger.info("=" * 70)

        for stock1, stock2 in self.TEST_PAIRS:
            self._analyze_single_pair(stock1, stock2)

    def _analyze_single_pair(self, stock1: str, stock2: str) -> None:
        """Analyze a single pair."""
        pair_id = f"{stock1}_{stock2}"
        logger.info(f"\n{'─' * 60}")
        logger.info(f"📊 Analyzing Pair: {stock1} / {stock2}")
        logger.info(f"{'─' * 60}")

        # Check data availability
        if stock1 not in self.enriched_data or stock2 not in self.enriched_data:
            logger.warning(f"   ⚠️ Missing data for {pair_id}")
            return

        df1 = self.enriched_data[stock1]
        df2 = self.enriched_data[stock2]

        # Align data
        df1 = df1[~df1.index.duplicated(keep='first')]
        df2 = df2[~df2.index.duplicated(keep='first')]
        aligned = pd.concat([df1['close'], df2['close']], axis=1, join='inner')
        aligned.columns = [stock1, stock2]

        if len(aligned) < 50:
            logger.warning(f"   ⚠️ Insufficient aligned data: {len(aligned)} bars")
            return

        logger.info(f"   📈 Data points: {len(aligned)} bars")
        logger.info(f"   📅 Period: {aligned.index[0].date()} to {aligned.index[-1].date()}")
        logger.info(f"   💰 {stock1}: ${aligned[stock1].iloc[-1]:.2f} | {stock2}: ${aligned[stock2].iloc[-1]:.2f}")

        # Calculate correlation
        correlation = aligned[stock1].corr(aligned[stock2])
        logger.info(f"   🔗 Correlation: {correlation:.3f}")

        # Calculate cointegration
        try:
            from statsmodels.tsa.stattools import coint
            _, p_value, _ = coint(aligned[stock1], aligned[stock2])
            coint_status = "✅ Cointegrated" if p_value < 0.05 else "⚠️ Not cointegrated"
            logger.info(f"   🧪 Cointegration p-value: {p_value:.4f} {coint_status}")
        except Exception as e:
            p_value = 1.0
            logger.warning(f"   ⚠️ Cointegration test failed: {e}")

        # Calculate hedge ratio (OLS)
        try:
            from sklearn.linear_model import LinearRegression
            X = aligned[stock1].values.reshape(-1, 1)
            y = aligned[stock2].values
            reg = LinearRegression().fit(X, y)
            hedge_ratio = reg.coef_[0]
            logger.info(f"   ⚖️ Hedge Ratio: {hedge_ratio:.4f}")
        except Exception as e:
            hedge_ratio = 1.0
            logger.warning(f"   ⚠️ Hedge ratio calculation failed: {e}")

        # Calculate spread
        spread = aligned[stock2] - hedge_ratio * aligned[stock1]
        spread_series = spread

        # Spread statistics
        spread_mean = spread.mean()
        spread_std = spread.std()
        current_spread = spread.iloc[-1]
        current_zscore = (current_spread - spread_mean) / spread_std

        logger.info(f"\n   📊 Spread Statistics:")
        logger.info(f"      Mean: ${spread_mean:.2f}")
        logger.info(f"      Std Dev: ${spread_std:.2f}")
        logger.info(f"      Current: ${current_spread:.2f}")
        logger.info(f"      Z-Score: {current_zscore:+.2f}")

        # Mean Reversion Analysis (Dimension 5)
        half_life = MeanReversionCore.calculate_half_life(spread_series)
        hurst = MeanReversionCore.calculate_hurst_exponent(spread_series)
        ewma_z = MeanReversionCore.calculate_ewma_zscore(spread_series)

        logger.info(f"\n   📈 Mean Reversion Metrics (Dimension 5):")
        hl_status = "✅ Fast" if half_life < 20 else ("⚠️ Moderate" if half_life < 50 else "❌ Slow")
        h_status = "✅ Mean-Reverting" if hurst < 0.45 else ("⚠️ Neutral" if hurst < 0.55 else "❌ Trending")
        logger.info(f"      Half-Life: {half_life:.1f} bars {hl_status}")
        logger.info(f"      Hurst Exponent: {hurst:.3f} {h_status}")
        logger.info(f"      EWMA Z-Score: {ewma_z:+.2f}")

        # Determine spread direction
        if current_zscore < -2.0:
            spread_direction = SpreadDirection.LONG
        elif current_zscore > 2.0:
            spread_direction = SpreadDirection.SHORT
        else:
            spread_direction = SpreadDirection.NEUTRAL

        # Get enriched data for SES
        stock1_enriched = self.enriched_data.get(stock1, pd.DataFrame())
        stock2_enriched = self.enriched_data.get(stock2, pd.DataFrame())

        # Calculate SES Score
        ses_score, breakdown = self.ses_scorer.calculate_ses(
            spread_series=spread_series,
            stock1_data=stock1_enriched,
            stock2_data=stock2_enriched,
            spread_direction=spread_direction,
            regime_context=None,
            pair_correlation=correlation
        )

        logger.info(f"\n   🎯 SES Analysis:")
        logger.info(f"      Total SES Score: {ses_score:.1f}/100")
        logger.info(f"      Entry Threshold: {self.ses_scorer.SES_ENTRY_THRESHOLD}")
        entry_status = "✅ QUALIFIED" if ses_score >= self.ses_scorer.SES_ENTRY_THRESHOLD else "❌ Not qualified"
        logger.info(f"      Entry Status: {entry_status}")
        logger.info(f"      Confidence: {breakdown.confidence:.1%}")

        logger.info(f"\n   📊 6-Dimension Breakdown:")
        logger.info(f"      D1 - Dislocation Quality:  {breakdown.dislocation_quality:5.1f}/100 (25%)")
        logger.info(f"      D2 - Individual Stocks:    {breakdown.individual_stocks:5.1f}/100 (20%)")
        logger.info(f"      D3 - Regime Compatibility: {breakdown.regime_compatibility:5.1f}/100 (15%)")
        logger.info(f"      D4 - Volume Confirmation:  {breakdown.volume_confirmation:5.1f}/100 (15%)")
        logger.info(f"      D5 - Mean Reversion Speed: {breakdown.mean_reversion_speed:5.1f}/100 (15%)")
        logger.info(f"      D6 - Lead-Lag:             {breakdown.lead_lag:5.1f}/100 (10%)")

        # Trading recommendation
        logger.info(f"\n   📋 Trading Recommendation:")
        if ses_score >= self.ses_scorer.SES_ENTRY_THRESHOLD and abs(current_zscore) >= 2.0:
            if spread_direction == SpreadDirection.LONG:
                logger.info(f"      🚀 ENTER LONG SPREAD:")
                logger.info(f"         → BUY {stock1} (long leg)")
                logger.info(f"         → SELL {stock2} (short leg, hedge ratio {hedge_ratio:.2f})")
            elif spread_direction == SpreadDirection.SHORT:
                logger.info(f"      🚀 ENTER SHORT SPREAD:")
                logger.info(f"         → SELL {stock1} (short leg)")
                logger.info(f"         → BUY {stock2} (long leg, hedge ratio {hedge_ratio:.2f})")
        elif abs(current_zscore) < 0.5:
            logger.info(f"      ⏹️ EXIT/STAY FLAT: Spread near mean (Z={current_zscore:.2f})")
        else:
            reason = f"SES={ses_score:.1f} < {self.ses_scorer.SES_ENTRY_THRESHOLD}" if ses_score < self.ses_scorer.SES_ENTRY_THRESHOLD else f"|Z|={abs(current_zscore):.2f} < 2.0"
            logger.info(f"      ⏸️ NO ACTION: {reason}")

        # Store results
        self.pair_results[pair_id] = {
            'stock1': stock1,
            'stock2': stock2,
            'stock1_price': aligned[stock1].iloc[-1],
            'stock2_price': aligned[stock2].iloc[-1],
            'correlation': correlation,
            'cointegration_pvalue': p_value,
            'hedge_ratio': hedge_ratio,
            'current_zscore': current_zscore,
            'half_life': half_life,
            'hurst_exponent': hurst,
            'ewma_zscore': ewma_z,
            'ses_score': ses_score,
            'ses_breakdown': breakdown.to_dict(),
            'spread_direction': spread_direction.value,
            'entry_qualified': ses_score >= self.ses_scorer.SES_ENTRY_THRESHOLD and abs(current_zscore) >= 2.0
        }

    def print_summary(self) -> None:
        """Print summary of all pairs analysis."""
        logger.info("\n" + "=" * 80)
        logger.info("📋 SUMMARY: ALL PAIRS ANALYSIS")
        logger.info("=" * 80)

        if not self.pair_results:
            logger.warning("No pairs analyzed!")
            return

        # Sort by SES score
        sorted_pairs = sorted(
            self.pair_results.items(),
            key=lambda x: x[1]['ses_score'],
            reverse=True
        )

        print("\n{:^15} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>12}".format(
            "Pair", "Corr", "Coint", "Z-Score", "HL", "Hurst", "SES", "Status"
        ))
        print("-" * 90)

        for pair_id, result in sorted_pairs:
            coint_str = f"{result['cointegration_pvalue']:.3f}"
            hl_str = f"{result['half_life']:.0f}" if result['half_life'] != float('inf') else "∞"
            status = "🚀 TRADE" if result['entry_qualified'] else "⏸️ Wait"

            print("{:^15} {:>8.3f} {:>8} {:>+8.2f} {:>8} {:>8.3f} {:>8.1f} {:>12}".format(
                pair_id,
                result['correlation'],
                coint_str,
                result['current_zscore'],
                hl_str,
                result['hurst_exponent'],
                result['ses_score'],
                status
            ))

        # Best opportunities
        trade_opportunities = [p for p in sorted_pairs if p[1]['entry_qualified']]

        if trade_opportunities:
            logger.info(f"\n🏆 TRADE OPPORTUNITIES ({len(trade_opportunities)}):")
            for pair_id, result in trade_opportunities:
                direction = "LONG" if result['spread_direction'] == 'long_spread' else "SHORT"
                logger.info(f"   {pair_id}: {direction} spread | SES={result['ses_score']:.1f} | Z={result['current_zscore']:+.2f}")
        else:
            logger.info("\n⏸️ No trade opportunities at current levels")

        # Summary stats
        logger.info(f"\n📊 Summary Statistics:")
        avg_ses = np.mean([r['ses_score'] for r in self.pair_results.values()])
        avg_corr = np.mean([r['correlation'] for r in self.pair_results.values()])
        coint_pairs = sum(1 for r in self.pair_results.values() if r['cointegration_pvalue'] < 0.05)
        mr_pairs = sum(1 for r in self.pair_results.values() if r['hurst_exponent'] < 0.5)

        logger.info(f"   Average SES Score: {avg_ses:.1f}")
        logger.info(f"   Average Correlation: {avg_corr:.3f}")
        logger.info(f"   Cointegrated Pairs: {coint_pairs}/{len(self.pair_results)}")
        logger.info(f"   Mean-Reverting Pairs (H<0.5): {mr_pairs}/{len(self.pair_results)}")

    def run(self) -> bool:
        """Run the complete test."""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 SES PAIRS TRADING - REAL DATA TEST")
        logger.info("=" * 70)

        # Setup
        if not self.setup():
            return False

        # Load data
        if not self.load_data():
            return False

        # Calculate indicators
        if not self.calculate_indicators():
            return False

        # Analyze pairs
        self.analyze_pairs()

        # Print summary
        self.print_summary()

        logger.info("\n✅ Test completed successfully!")
        return True

def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='SES Pairs Trading Real Data Test')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=60, help='Lookback days (default: 60)')
    parser.add_argument('--resample', type=str, default='1h',
                       choices=['1min', '5min', '15min', '1h', '1d'],
                       help='Resample interval (default: 1h)')
    args = parser.parse_args()

    # Run test
    test = SESPairsRealDataTest(
        start_date=args.start,
        end_date=args.end,
        lookback_days=args.days,
        resample=args.resample
    )

    success = test.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
