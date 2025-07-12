#!/usr/bin/env python3
"""
ClickHouse-based Pair Screening for Statistical Arbitrage
========================================================

This script implements high-performance pair screening using ClickHouse database
for superior analytics performance on large-scale financial data.

Features:
- ClickHouse database for ultra-fast analytics
- Parallel data loading and processing
- Advanced correlation and cointegration analysis
- Comprehensive pair ranking and visualization
- Production-ready error handling and logging

Author: Pro Quant Desk Trader
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional, Any
import clickhouse_connect
from clickhouse_connect.driver.client import Client
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clickhouse_connect.driver.client import Client as ClickHouseClient
import warnings
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
from dataclasses import dataclass
from scipy import stats
from statsmodels.tsa.stattools import coint
import traceback

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('clickhouse_screening.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ScreeningConfig:
    """Configuration for pair screening"""
    # Database settings
    clickhouse_host: str = 'localhost'
    clickhouse_port: int = 8123
    clickhouse_user: str = 'default'
    clickhouse_password: str = ''
    database_name: str = 'polygon_data'
    
    # Data settings
    data_dir: str = 'data/polygon'
    sample_files: int = 100
    start_date: str = '2023-01-01'
    end_date: str = '2024-12-31'
    
    # Analysis settings
    min_correlation: float = 0.15
    min_cointegration_pvalue: float = 0.05
    min_lookback_days: int = 252
    max_pairs_to_test: int = 1000
    
    # Performance settings
    max_workers: int = 4
    batch_size: int = 10000
    
    # Output settings
    results_dir: str = 'results'
    save_plots: bool = True
    save_data: bool = True

class ClickHouseManager:
    """Manages ClickHouse database operations"""
    
    def __init__(self, config: ScreeningConfig):
        self.config = config
        self.client: Optional[Any] = None
        self._connect()
    
    def _connect(self):
        """Establish connection to ClickHouse"""
        try:
            self.client = clickhouse_connect.get_client(
                host=self.config.clickhouse_host,
                port=self.config.clickhouse_port,
                user=self.config.clickhouse_user,
                password=self.config.clickhouse_password
            )
            logger.info(f"Connected to ClickHouse at {self.config.clickhouse_host}:{self.config.clickhouse_port}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise
    
    def create_database(self):
        """Create database if it doesn't exist"""
        try:
            self.client.command(f"CREATE DATABASE IF NOT EXISTS {self.config.database_name}")
            logger.info(f"Database {self.config.database_name} ready")
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise
    
    def create_table(self):
        """Create optimized table for polygon data"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.config.database_name}.polygon_data (
            symbol String,
            timestamp DateTime64(3),
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume UInt64,
            vwap Float64,
            date Date
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (symbol, date, timestamp)
        SETTINGS index_granularity = 8192
        """
        
        try:
            self.client.command(create_table_sql)
            logger.info("Polygon data table created successfully")
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise
    
    def insert_data(self, data: pd.DataFrame):
        """Insert data into ClickHouse table"""
        if data.empty:
            return
        
        try:
            # Prepare data for ClickHouse
            data_clickhouse = data.copy()
            data_clickhouse['date'] = pd.to_datetime(data_clickhouse['timestamp']).dt.date
            
            # Insert in batches for better performance
            batch_size = self.config.batch_size
            for i in range(0, len(data_clickhouse), batch_size):
                batch = data_clickhouse.iloc[i:i+batch_size]
                self.client.insert_df(
                    f"{self.config.database_name}.polygon_data",
                    batch,
                    column_names=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'date']
                )
            
            logger.info(f"Inserted {len(data_clickhouse)} records")
        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            raise
    
    def create_daily_prices_table(self):
        """Create pre-aggregated 5-minute prices table for faster analysis"""
        try:
            # Drop existing table if it exists
            self.client.command(f"DROP TABLE IF EXISTS {self.config.database_name}.prices_5min")
            
            # Create optimized 5-minute prices table
            create_table_sql = f"""
            CREATE TABLE {self.config.database_name}.prices_5min (
                ticker String,
                timestamp_5min DateTime,
                close_price Float64,
                volume_sum UInt64,
                trade_count UInt32
            ) ENGINE = MergeTree()
            ORDER BY (ticker, timestamp_5min)
            """
            
            self.client.command(create_table_sql)
            
            # Populate with 5-minute aggregated data
            insert_sql = f"""
            INSERT INTO {self.config.database_name}.prices_5min
            SELECT 
                ticker,
                toStartOfFiveMinutes(toDateTime(window_start / 1000000000)) as timestamp_5min,
                argMax(close, window_start) as close_price,
                sum(volume) as volume_sum,
                count(*) as trade_count
            FROM {self.config.database_name}.ticks
            WHERE toDateTime(window_start / 1000000000) BETWEEN '{self.config.start_date}' AND '{self.config.end_date}'
            GROUP BY ticker, timestamp_5min
            ORDER BY ticker, timestamp_5min
            """
            
            logger.info("Creating 5-minute aggregated prices table...")
            self.client.command(insert_sql)
            
            # Get row count
            count_result = self.client.query_df(f"SELECT COUNT(*) as count FROM {self.config.database_name}.prices_5min")
            row_count = count_result['count'].iloc[0]
            logger.info(f"5-minute prices table created with {row_count:,} rows")
            
        except Exception as e:
            logger.error(f"Failed to create 5-minute prices table: {e}")
            raise

    def get_popular_symbols(self, limit: int = 100) -> List[str]:
        """Get most frequently traded symbols using 5-minute prices table"""
        query = f"""
        SELECT ticker as symbol, SUM(trade_count) as total_trades
        FROM {self.config.database_name}.prices_5min
        WHERE timestamp_5min BETWEEN '{self.config.start_date}' AND '{self.config.end_date}'
        GROUP BY ticker
        ORDER BY total_trades DESC
        LIMIT {limit}
        """
        
        try:
            result = self.client.query_df(query)
            symbols = result['symbol'].tolist()
            logger.info(f"Found {len(symbols)} popular symbols")
            return symbols
        except Exception as e:
            logger.error(f"Failed to get popular symbols: {e}")
            return []
    
    def get_correlated_pairs_batch(self, symbols: List[str], min_correlation: float, batch_size: int = 20) -> List[Tuple[str, str, float]]:
        """Find correlated pairs using batched processing on 5-minute data"""
        if len(symbols) < 2:
            return []
        
        all_pairs = []
        
        # Process symbols in batches to avoid memory issues
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_symbols)} symbols")
            
            # Calculate returns for this batch using 5-minute prices table
            returns_query = f"""
            WITH returns_5min AS (
                SELECT 
                    ticker as symbol,
                    timestamp_5min,
                    close_price,
                    lag(close_price) OVER (PARTITION BY ticker ORDER BY timestamp_5min) as prev_close
                FROM {self.config.database_name}.prices_5min
                WHERE ticker IN ({','.join([f"'{s}'" for s in batch_symbols])})
                AND timestamp_5min BETWEEN '{self.config.start_date}' AND '{self.config.end_date}'
            ),
            returns AS (
                SELECT 
                    symbol,
                    timestamp_5min,
                    (close_price - prev_close) / prev_close as return
                FROM returns_5min
                WHERE prev_close > 0
            )
            SELECT 
                r1.symbol as symbol1,
                r2.symbol as symbol2,
                corr(r1.return, r2.return) as correlation
            FROM returns r1
            JOIN returns r2 ON r1.timestamp_5min = r2.timestamp_5min AND r1.symbol < r2.symbol
            GROUP BY r1.symbol, r2.symbol
            HAVING correlation >= {min_correlation}
            ORDER BY correlation DESC
            """
            
            try:
                result = self.client.query_df(returns_query)
                batch_pairs = [(row.symbol1, row.symbol2, row.correlation) 
                              for row in result.itertuples()]
                all_pairs.extend(batch_pairs)
                logger.info(f"Batch {i//batch_size + 1}: Found {len(batch_pairs)} correlated pairs")
                
            except Exception as e:
                logger.error(f"Failed to process batch {i//batch_size + 1}: {e}")
                continue
        
        # Sort all pairs by correlation and limit results
        all_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        limited_pairs = all_pairs[:self.config.max_pairs_to_test]
        
        logger.info(f"Total correlated pairs found: {len(limited_pairs)}")
        return limited_pairs
    
    def get_pair_data(self, symbol1: str, symbol2: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get price data for a pair of symbols using 5-minute prices table"""
        query1 = f"""
        SELECT timestamp_5min as timestamp, close_price as close
        FROM {self.config.database_name}.prices_5min
        WHERE ticker = '{symbol1}'
        AND timestamp_5min BETWEEN '{self.config.start_date}' AND '{self.config.end_date}'
        ORDER BY timestamp_5min
        """
        
        query2 = f"""
        SELECT timestamp_5min as timestamp, close_price as close
        FROM {self.config.database_name}.prices_5min
        WHERE ticker = '{symbol2}'
        AND timestamp_5min BETWEEN '{self.config.start_date}' AND '{self.config.end_date}'
        ORDER BY timestamp_5min
        """
        
        try:
            data1 = self.client.query_df(query1)
            data2 = self.client.query_df(query2)
            return data1, data2
        except Exception as e:
            logger.error(f"Failed to get pair data for {symbol1}-{symbol2}: {e}")
            return pd.DataFrame(), pd.DataFrame()

class PairAnalyzer:
    """Analyzes pairs for cointegration and trading signals"""
    
    @staticmethod
    def calculate_hedge_ratio(price1: pd.Series, price2: pd.Series) -> float:
        """Calculate hedge ratio using OLS regression"""
        try:
            # Ensure same length and no NaN values
            common_idx = price1.index.intersection(price2.index)
            price1_clean = price1.loc[common_idx].dropna()
            price2_clean = price2.loc[common_idx].dropna()
            
            if len(price1_clean) != len(price2_clean) or len(price1_clean) < 10:
                return 1.0  # Default hedge ratio
            
            # Calculate hedge ratio using OLS: price1 = alpha + beta * price2
            X = price2_clean.values.reshape(-1, 1)
            y = price1_clean.values
            
            # Manual OLS calculation to avoid sklearn dependency
            X_mean = np.mean(X)
            y_mean = np.mean(y)
            
            numerator = np.sum((X.flatten() - X_mean) * (y - y_mean))
            denominator = np.sum((X.flatten() - X_mean) ** 2)
            
            if denominator == 0:
                return 1.0
            
            hedge_ratio = numerator / denominator
            return hedge_ratio
            
        except Exception as e:
            logger.error(f"Hedge ratio calculation failed: {e}")
            return 1.0

    @staticmethod
    def test_cointegration(price1: pd.Series, price2: pd.Series) -> Dict[str, Any]:
        """Test for cointegration between two price series"""
        try:
            # Ensure same length and no NaN values
            common_idx = price1.index.intersection(price2.index)
            if len(common_idx) < 50:  # Minimum data requirement
                return {'cointegrated': False, 'pvalue': 1.0, 'score': 0.0, 'hedge_ratio': 1.0}
            
            price1_clean = price1.loc[common_idx].dropna()
            price2_clean = price2.loc[common_idx].dropna()
            
            if len(price1_clean) != len(price2_clean) or len(price1_clean) < 50:
                return {'cointegrated': False, 'pvalue': 1.0, 'score': 0.0, 'hedge_ratio': 1.0}
            
            # Calculate hedge ratio first
            hedge_ratio = PairAnalyzer.calculate_hedge_ratio(price1_clean, price2_clean)
            
            # Test cointegration
            score, pvalue, _ = coint(price1_clean, price2_clean)
            
            # Calculate additional metrics using proper spread
            correlation = price1_clean.corr(price2_clean)
            spread = price1_clean - (hedge_ratio * price2_clean)
            spread_std = spread.std()
            
            # Composite score
            score_value = (1 - pvalue) * abs(correlation) * (1 / (1 + spread_std))
            
            return {
                'cointegrated': pvalue < 0.05,
                'pvalue': pvalue,
                'score': score_value,
                'correlation': correlation,
                'spread_std': spread_std,
                'data_points': len(price1_clean),
                'hedge_ratio': hedge_ratio
            }
        except Exception as e:
            logger.error(f"Cointegration test failed: {e}")
            return {'cointegrated': False, 'pvalue': 1.0, 'score': 0.0, 'hedge_ratio': 1.0}
    
    @staticmethod
    def calculate_spread_stats(price1: pd.Series, price2: pd.Series, hedge_ratio: float = 1.0) -> Dict[str, float]:
        """Calculate spread statistics using proper hedge ratio"""
        try:
            # Calculate spread using hedge ratio: spread = price1 - (hedge_ratio * price2)
            spread = price1 - (hedge_ratio * price2)
            
            # Handle case where spread calculation fails
            if spread.empty or spread.isna().all():
                return {'mean': 0, 'std': 1, 'skew': 0, 'kurtosis': 0, 'z_score': None}
            
            spread_mean = spread.mean()
            spread_std = spread.std()
            
            # Calculate current z-score (last observation)
            current_zscore = None
            if len(spread) > 0 and not pd.isna(spread.iloc[-1]) and spread_std > 0:
                current_zscore = (spread.iloc[-1] - spread_mean) / spread_std
            
            return {
                'mean': spread_mean,
                'std': spread_std,
                'skew': spread.skew(),
                'kurtosis': spread.kurtosis(),
                'z_score': current_zscore
            }
        except Exception as e:
            logger.error(f"Spread calculation failed: {e}")
            return {'mean': 0, 'std': 1, 'skew': 0, 'kurtosis': 0, 'z_score': None}

class ClickHousePairScreener:
    """Main class for ClickHouse-based pair screening"""
    
    def __init__(self, config: ScreeningConfig):
        self.config = config
        self.db_manager = ClickHouseManager(config)
        self.analyzer = PairAnalyzer()
        self.results = []
        
        # Create results directory
        Path(config.results_dir).mkdir(exist_ok=True)
    
    def screen_pairs(self):
        """Screen pairs for cointegration"""
        # Ensure results directory exists
        os.makedirs(self.config.results_dir, exist_ok=True)
        
        # Step 1: Create optimized 5-minute prices table
        logger.info("Creating 5-minute prices table for faster analysis...")
        self.db_manager.create_daily_prices_table()
        
        # Step 2: Get popular symbols from 5-minute data
        logger.info("Getting popular symbols...")
        symbols = self.db_manager.get_popular_symbols(50)  # Reduced from 200 to 50
        
        if not symbols:
            logger.warning("No symbols found in database")
            return
        
        # Step 3: Find correlated pairs using batch processing
        correlated_pairs = self.db_manager.get_correlated_pairs_batch(
            symbols, self.config.min_correlation, batch_size=15  # Process 15 symbols at a time
        )
        
        if not correlated_pairs:
            logger.warning("No correlated pairs found with current threshold")
            return
        
        logger.info(f"Testing {len(correlated_pairs)} pairs for cointegration...")
        
        # Step 4: Test pairs for cointegration in batches
        batch_size = 20  # Process 20 pairs at a time
        for batch_start in range(0, len(correlated_pairs), batch_size):
            batch_end = min(batch_start + batch_size, len(correlated_pairs))
            batch_pairs = correlated_pairs[batch_start:batch_end]
            
            logger.info(f"Processing cointegration batch {batch_start//batch_size + 1}/{(len(correlated_pairs) + batch_size - 1)//batch_size}")
            
            for i, (symbol1, symbol2, correlation) in enumerate(batch_pairs):
                try:
                    pair_idx = batch_start + i + 1
                    logger.info(f"Testing pair {pair_idx}/{len(correlated_pairs)}: {symbol1}-{symbol2}")
                    
                    # Get price data
                    data1, data2 = self.db_manager.get_pair_data(symbol1, symbol2)
                    
                    if data1.empty or data2.empty:
                        continue
                    
                    # Test cointegration
                    coint_result = self.analyzer.test_cointegration(
                        data1['close'], data2['close']
                    )
                    
                    if coint_result['cointegrated']:
                        # Calculate additional statistics using the hedge ratio
                        spread_stats = self.analyzer.calculate_spread_stats(
                            data1['close'], data2['close'], coint_result['hedge_ratio']
                        )
                        
                        result = {
                            'symbol1': symbol1,
                            'symbol2': symbol2,
                            'correlation': correlation,
                            'cointegration_pvalue': coint_result['pvalue'],
                            'cointegration_score': coint_result['score'],
                            'hedge_ratio': coint_result['hedge_ratio'],
                            'spread_mean': spread_stats['mean'],
                            'spread_std': spread_stats['std'],
                            'spread_skew': spread_stats['skew'],
                            'spread_kurtosis': spread_stats['kurtosis'],
                            'current_zscore': spread_stats['z_score'],
                            'data_points': coint_result['data_points']
                        }
                        
                        self.results.append(result)
                        logger.info(f"Found cointegrated pair: {symbol1}-{symbol2} (p={coint_result['pvalue']:.4f})")
                    
                except Exception as e:
                    logger.error(f"Error testing pair {symbol1}-{symbol2}: {e}")
                    continue
        
        logger.info(f"Found {len(self.results)} cointegrated pairs")
    
    def rank_and_save_results(self):
        """Rank results and save to files"""
        if not self.results:
            logger.warning("No results to save")
            return
        
        # Convert to DataFrame
        df_results = pd.DataFrame(self.results)
        
        # Calculate composite score
        df_results['composite_score'] = (
            (1 - df_results['cointegration_pvalue']) * 
            df_results['correlation'] * 
            (1 / (1 + df_results['spread_std'])) *
            np.log(df_results['data_points'])
        )
        
        # Sort by composite score
        df_results = df_results.sort_values('composite_score', ascending=False)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save to CSV
        csv_path = f"{self.config.results_dir}/clickhouse_pairs_{timestamp}.csv"
        df_results.to_csv(csv_path, index=False)
        logger.info(f"Results saved to {csv_path}")
        
        # Save to JSON
        json_path = f"{self.config.results_dir}/clickhouse_pairs_{timestamp}.json"
        df_results.to_json(json_path, orient='records', indent=2)
        logger.info(f"Results saved to {json_path}")
        
        # Print top results
        print("\n" + "="*80)
        print("TOP COINTEGRATED PAIRS")
        print("="*80)
        print(df_results.head(10).to_string(index=False))
        
        return df_results
    
    def create_visualizations(self, df_results: pd.DataFrame):
        """Create visualizations of results"""
        if df_results.empty:
            return
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('ClickHouse Pair Screening Results', fontsize=16, fontweight='bold')
        
        # 1. Correlation vs Cointegration Score
        axes[0, 0].scatter(df_results['correlation'], df_results['cointegration_score'], 
                          alpha=0.6, s=50)
        axes[0, 0].set_xlabel('Correlation')
        axes[0, 0].set_ylabel('Cointegration Score')
        axes[0, 0].set_title('Correlation vs Cointegration Score')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Composite Score Distribution
        axes[0, 1].hist(df_results['composite_score'], bins=20, alpha=0.7, edgecolor='black')
        axes[0, 1].set_xlabel('Composite Score')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('Composite Score Distribution')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Spread Statistics
        axes[1, 0].scatter(df_results['spread_std'], df_results['spread_skew'], 
                          alpha=0.6, s=50)
        axes[1, 0].set_xlabel('Spread Standard Deviation')
        axes[1, 0].set_ylabel('Spread Skewness')
        axes[1, 0].set_title('Spread Statistics')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Current Z-Scores
        axes[1, 1].set_title('Current Z-Score Distribution')
        valid_zscores = df_results['current_zscore'].dropna()
        if len(valid_zscores) > 0:
            axes[1, 1].hist(valid_zscores, bins=20, alpha=0.7, edgecolor='black')
            axes[1, 1].axvline(x=0, color='red', linestyle='--', alpha=0.7, label='Mean')
            axes[1, 1].axvline(x=2, color='orange', linestyle='--', alpha=0.7, label='+2σ')
            axes[1, 1].axvline(x=-2, color='orange', linestyle='--', alpha=0.7, label='-2σ')
            axes[1, 1].legend()
        else:
            axes[1, 1].text(0.5, 0.5, 'No valid Z-scores', ha='center', va='center', transform=axes[1, 1].transAxes)
        axes[1, 1].set_xlabel('Z-Score')
        axes[1, 1].set_ylabel('Frequency')
        
        plt.tight_layout()
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plot_path = f"{self.config.results_dir}/clickhouse_results_{timestamp}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"Visualization saved to {plot_path}")
        
        if self.config.save_plots:
            plt.show()
        else:
            plt.close()

def main():
    """Main execution function"""
    print("ClickHouse Pair Screening for Statistical Arbitrage")
    print("=" * 60)
    
    # Optimized configuration for faster processing
    config = ScreeningConfig(
        # Shorter date range for faster processing
        start_date='2024-01-01',
        end_date='2024-12-31',
        
        # Reduced thresholds for faster screening
        min_correlation=0.3,  # Increased threshold for fewer pairs
        max_pairs_to_test=200,  # Reduced from 1000
        
        # Performance settings
        sample_files=50,  # Reduced sample size
        max_workers=6,  # Increased for better parallelism
        batch_size=5000  # Smaller batches
    )
    
    print(f"Configuration:")
    print(f"  Date range: {config.start_date} to {config.end_date}")
    print(f"  Min correlation: {config.min_correlation}")
    print(f"  Max pairs to test: {config.max_pairs_to_test}")
    print(f"  Batch size: {config.batch_size}")
    
    # Create screener
    screener = ClickHousePairScreener(config)
    
    try:
        # Screen pairs (now includes daily table creation)
        print("\n1. Screening pairs for cointegration...")
        screener.screen_pairs()
        
        # Save results
        print("\n2. Saving and ranking results...")
        df_results = screener.rank_and_save_results()
        
        # Create visualizations
        if df_results is not None and not df_results.empty and config.save_plots:
            print("\n3. Creating visualizations...")
            screener.create_visualizations(df_results)
        
        print("\n" + "="*60)
        print("SCREENING COMPLETE!")
        print(f"Found {len(screener.results)} cointegrated pairs")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\nScreening interrupted by user")
    except Exception as e:
        logger.error(f"Screening failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 