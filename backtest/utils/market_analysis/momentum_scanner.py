"""
Momentum Period Scanner
=======================

Professional utility to identify momentum-favorable periods in historical data.

This scanner analyzes market data across multiple symbols and time periods to:
1. Calculate momentum characteristics (strength, persistence, ADX)
2. Score each period's momentum favorability
3. Generate a ranked catalog of optimal testing periods

Usage:
    from backtest.utils.market_analysis import MomentumPeriodScanner

    scanner = MomentumPeriodScanner(
        symbols=['NVDA', 'TSLA', 'AAPL'],
        start_year=2023,
        end_year=2024
    )

    results = scanner.scan_all_periods()
    report = scanner.generate_report(results)
    scanner.save_report(report, 'momentum_scan_results.json')
"""

import pandas as pd
from typing import Dict, List, Optional
import logging

from .period_scanner_base import PeriodScannerBase, PeriodAnalysisResult

logger = logging.getLogger(__name__)

class MomentumPeriodScanner(PeriodScannerBase):
    """
    Scanner to identify momentum-favorable periods in historical data.

    Analyzes momentum characteristics including:
    - Short/medium/long-term momentum strength
    - Average Directional Index (ADX) for trend strength
    - Trend persistence
    - Volatility
    - High-momentum day frequency
    """

    def __init__(self,
                 symbols: List[str] = None,
                 start_year: int = 2023,
                 end_year: int = 2024,
                 clickhouse_host: str = 'localhost',
                 clickhouse_port: int = 8123,
                 clickhouse_database: str = 'polygon_data'):
        """
        Initialize Momentum Period Scanner.

        Args:
            symbols: List of symbols to analyze (default: ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN'])
            start_year: Starting year for analysis
            end_year: Ending year for analysis
            clickhouse_host: ClickHouse server host
            clickhouse_port: ClickHouse server port
            clickhouse_database: ClickHouse database name
        """
        if symbols is None:
            symbols = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN']

        super().__init__(symbols, start_year, end_year)

        # Initialize ClickHouse client
        from clickhouse_connect import get_client
        self.ch_client = get_client(
            host=clickhouse_host,
            port=clickhouse_port,
            database=clickhouse_database
        )

        # Momentum scoring weights
        self.scoring_weights = {
            'avg_momentum': 0.30,
            'trend_persistence': 0.30,
            'avg_adx': 0.20,
            'abs_return': 0.20
        }

    def load_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Load data directly from ClickHouse.

        Args:
            symbol: Symbol to load
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data or None if no data
        """
        import datetime

        # Convert dates to nanosecond timestamps
        start_dt = datetime.datetime.strptime(f"{start_date} 09:30:00", "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.datetime.strptime(f"{end_date} 16:00:00", "%Y-%m-%d %H:%M:%S")
        start_ns = int(start_dt.timestamp() * 1e9)
        end_ns = int(end_dt.timestamp() * 1e9)

        query = f"""
        SELECT
            window_start,
            open,
            high,
            low,
            close,
            volume
        FROM ticks
        WHERE ticker = '{symbol}'
          AND window_start >= {start_ns}
          AND window_start <= {end_ns}
        ORDER BY window_start
        """

        try:
            result = self.ch_client.query(query)

            if not result.result_rows:
                return None

            df = pd.DataFrame(
                result.result_rows,
                columns=['time_ns', 'open', 'high', 'low', 'close', 'volume']
            )

            # Convert nanosecond timestamps to datetime
            df['time'] = pd.to_datetime(df['time_ns'], unit='ns')
            df = df.drop('time_ns', axis=1)
            df.set_index('time', inplace=True)

            return df

        except Exception as e:
            self.logger.error(f"Error loading data for {symbol}: {e}")
            return None

    def calculate_trend_persistence(self, data: pd.DataFrame, lookback: int = None) -> float:
        """
        Calculate how many days maintain the same trend direction.

        Args:
            data: DataFrame with price data
            lookback: Number of days to analyze (default: all data)

        Returns:
            Trend persistence ratio (0-1)
        """
        returns = data['close'].pct_change()

        if lookback is None:
            lookback = len(returns)

        # Count consecutive days with same sign
        trend_days = 0
        max_trend_days = 0
        prev_sign = 0

        for ret in returns.iloc[-lookback:]:
            if pd.isna(ret):
                continue

            curr_sign = 1 if ret > 0 else -1

            if curr_sign == prev_sign:
                trend_days += 1
                max_trend_days = max(max_trend_days, trend_days)
            else:
                trend_days = 1

            prev_sign = curr_sign

        return max_trend_days / lookback if lookback > 0 else 0.0

    def analyze_period(self, symbol: str, start_date: str, end_date: str) -> Optional[PeriodAnalysisResult]:
        """
        Analyze a specific period for momentum characteristics.

        Args:
            symbol: Symbol to analyze
            start_date: Period start date (YYYY-MM-DD)
            end_date: Period end date (YYYY-MM-DD)

        Returns:
            PeriodAnalysisResult or None if analysis fails
        """
        try:
            # Load data
            data = self.load_data(symbol, start_date, end_date)

            if data is None or len(data) < 100:
                self.logger.warning(f"Insufficient data for {symbol} {start_date} to {end_date}")
                return None

            # Resample to daily for analysis
            daily_data = data.resample('1D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()

            if len(daily_data) < 20:
                self.logger.warning(f"Insufficient daily data for {symbol}")
                return None

            # Calculate momentum metrics
            short_momentum = self.calculate_momentum(daily_data, period=10)
            medium_momentum = self.calculate_momentum(daily_data, period=20)
            adx = self.calculate_adx(daily_data, period=14)

            # Calculate summary statistics
            avg_short_momentum = abs(short_momentum.mean())
            avg_medium_momentum = abs(medium_momentum.mean())
            avg_adx = adx.mean()
            trend_persistence = self.calculate_trend_persistence(daily_data)

            # Calculate period return
            period_return = (daily_data['close'].iloc[-1] - daily_data['close'].iloc[0]) / daily_data['close'].iloc[0]

            # Calculate volatility
            volatility = self.calculate_volatility(daily_data)

            # Count trading days with momentum > 1%
            high_momentum_days = (abs(short_momentum) > 1.0).sum()

            metrics = {
                'avg_short_momentum': avg_short_momentum,
                'avg_medium_momentum': avg_medium_momentum,
                'avg_adx': avg_adx,
                'trend_persistence': trend_persistence,
                'period_return': period_return * 100,  # Convert to percentage
                'abs_return': abs(period_return) * 100,
                'volatility': volatility * 100,
                'high_momentum_days': high_momentum_days,
                'total_days': len(daily_data),
                'high_momentum_pct': high_momentum_days / len(daily_data) * 100 if len(daily_data) > 0 else 0
            }

            # Calculate momentum favorability score
            score = self.calculate_period_score(metrics)

            # Extract period label (e.g., "2023 Q1")
            year = start_date[:4]
            month = int(start_date[5:7])
            quarter = (month - 1) // 3 + 1
            period_label = f"{year} Q{quarter}"

            return PeriodAnalysisResult(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                period_label=period_label,
                score=score,
                metrics=metrics
            )

        except Exception as e:
            self.logger.error(f"Error analyzing {symbol} {start_date} to {end_date}: {e}")
            return None

    def calculate_period_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate momentum favorability score based on metrics.

        Args:
            metrics: Dictionary of calculated metrics

        Returns:
            Momentum favorability score (0-100)
        """
        score = (
            metrics['avg_short_momentum'] * self.scoring_weights['avg_momentum'] +
            metrics['trend_persistence'] * 100 * self.scoring_weights['trend_persistence'] +
            min(metrics['avg_adx'] / 40, 1.0) * 100 * self.scoring_weights['avg_adx'] +
            min(metrics['abs_return'] / 50, 1.0) * 100 * self.scoring_weights['abs_return']
        )

        return score

    def print_top_periods(self, results: List[PeriodAnalysisResult], top_n: int = 15):
        """
        Print formatted summary of top periods.

        Args:
            results: List of analysis results
            top_n: Number of top periods to display
        """
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)

        self.logger.info("=" * 80)
        self.logger.info(f"📊 MOMENTUM PERIOD RANKING - TOP {top_n} PERIODS")
        self.logger.info("=" * 80)
        self.logger.info("")

        for i, result in enumerate(sorted_results[:top_n], 1):
            m = result.metrics
            self.logger.info(f"Rank {i:2d}: {result.symbol:5s} {result.period_label} - Score: {result.score:5.1f}")
            self.logger.info(f"         Return: {m['period_return']:+6.2f}% | Momentum: {m['avg_short_momentum']:5.2f}% | ADX: {m['avg_adx']:4.1f}")
            self.logger.info(f"         Trend Persistence: {m['trend_persistence']*100:4.1f}% | High-Mom Days: {m['high_momentum_pct']:.1f}%")
            self.logger.info("")

# Standalone execution script
async def main():
    """Main execution for standalone usage"""

    scanner = MomentumPeriodScanner()

    # Scan all periods
    results = scanner.scan_all_periods()

    if not results:
        logger.error("❌ No results from scan!")
        return

    # Print top periods
    scanner.print_top_periods(results, top_n=15)

    # Generate and save report
    report = scanner.generate_report(results)
    scanner.save_report(report, 'momentum_period_scan_results.json')

    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ MOMENTUM PERIOD SCAN COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Review top-ranked periods")
    logger.info("2. Run baseline backtest on primary test period")
    logger.info("3. Proceed with parameter optimization")
    logger.info("")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
