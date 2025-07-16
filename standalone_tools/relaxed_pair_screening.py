#!/usr/bin/env python3
"""
Relaxed ClickHouse Pair Screening - Demo Version
==============================================

This is a modified version of the pair screening script with relaxed criteria
to demonstrate functionality and find viable pairs in the current market.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from clickhouse_pair_screening import *

def create_relaxed_config():
    """Create configuration with relaxed criteria for demonstration"""
    return ScreeningConfig(
        # Database settings
        clickhouse_host='localhost',
        clickhouse_port=8123,
        clickhouse_user='default',
        clickhouse_password='',
        database_name='polygon_data',
        
        # Data settings - shorter range for faster processing
        start_date='2024-06-01',
        end_date='2024-12-31',
        
        # Relaxed analysis settings
        min_correlation=0.25,  # Lowered from 0.3
        min_cointegration_pvalue=0.10,  # Relaxed from 0.05
        min_lookback_days=100,  # Reduced from 252
        max_pairs_to_test=50,   # Reduced for faster processing
        
        # Relaxed regime-aware settings
        regime_window=30,  # Reduced from 60
        min_regime_stability=0.3,  # Relaxed from 0.5
        max_regime_transitions=100,  # Increased from 50
        min_correlation_consistency=0.2,  # Relaxed from 0.3
        
        # Performance settings
        max_workers=4,
        batch_size=3000,  # Smaller batches
        
        # Output settings
        results_dir='results',
        save_plots=True,
        save_data=True
    )

class RelaxedPairScreener(ClickHousePairScreener):
    """Relaxed version of the pair screener for demonstration"""
    
    def __init__(self, config: ScreeningConfig):
        super().__init__(config)
        print("🎯 Using RELAXED criteria for demonstration:")
        print(f"   • Min correlation: {config.min_correlation}")
        print(f"   • Cointegration p-value: {config.min_cointegration_pvalue}")
        print(f"   • Transaction cost threshold: 200 bps")
        print(f"   • Liquidity score threshold: 0.2")
        print(f"   • Regime stability threshold: 0.3")
    
    def screen_pairs(self):
        """Screen pairs with relaxed criteria"""
        # Ensure results directory exists
        os.makedirs(self.config.results_dir, exist_ok=True)
        
        # Step 1: Create optimized 5-minute prices table
        logger.info("Using existing 5-minute prices table...")
        
        # Step 2: Get popular symbols
        logger.info("Getting popular symbols...")
        symbols = self.db_manager.get_popular_symbols(30)  # Reduced to 30 symbols
        
        if not symbols:
            logger.warning("No symbols found in database")
            return
        
        # Step 3: Find correlated pairs
        correlated_pairs = self.db_manager.get_correlated_pairs_batch(
            symbols, self.config.min_correlation, batch_size=10
        )
        
        if not correlated_pairs:
            logger.warning("No correlated pairs found with current threshold")
            return
        
        logger.info(f"Testing {len(correlated_pairs)} pairs for cointegration...")
        
        # Step 4: Test pairs with RELAXED criteria
        for i, (symbol1, symbol2, correlation) in enumerate(correlated_pairs):
            try:
                logger.info(f"Testing pair {i+1}/{len(correlated_pairs)}: {symbol1}-{symbol2}")
                
                # Get price data
                data1, data2 = self.db_manager.get_pair_data(symbol1, symbol2)
                
                if data1.empty or data2.empty:
                    continue
                
                # Test cointegration
                coint_result = self.analyzer.test_cointegration(
                    data1['close'], data2['close']
                )
                
                # RELAXED cointegration criteria
                if coint_result['pvalue'] < self.config.min_cointegration_pvalue:
                    
                    # Calculate regime-adjusted analysis
                    regime_analysis = self.analyzer.calculate_regime_adjusted_score(
                        data1['close'], data2['close']
                    )
                    
                    # Analyze liquidity profile
                    liquidity_profile = self.analyzer.analyze_liquidity_profile(
                        symbol1, symbol2, data1, data2
                    )
                    
                    # Estimate transaction costs
                    transaction_costs = self.analyzer.estimate_transaction_costs(
                        symbol1, symbol2, liquidity_profile
                    )
                    
                    # RELAXED screening criteria
                    regime_stable = (regime_analysis['regime_stability']['stable'] or 
                                   regime_analysis['regime_adjusted_score'] > 0.05)  # Relaxed
                    
                    liquidity_adequate = liquidity_profile['liquidity_score'] > 0.2  # Relaxed
                    transaction_costs_acceptable = transaction_costs['total_cost_bps'] < 200  # Relaxed to 20bp
                    
                    # Accept if at least 2 out of 3 criteria are met (VERY relaxed)
                    criteria_met = sum([regime_stable, liquidity_adequate, transaction_costs_acceptable])
                    
                    if criteria_met >= 2:  # At least 2 out of 3 criteria
                        
                        # Calculate spread statistics
                        spread_stats = self.analyzer.calculate_spread_stats(
                            data1['close'], data2['close'], coint_result['hedge_ratio']
                        )
                        
                        result = {
                            'symbol1': symbol1,
                            'symbol2': symbol2,
                            'correlation': correlation,
                            'cointegration_pvalue': coint_result['pvalue'],
                            'cointegration_score': coint_result['score'],
                            'regime_adjusted_score': regime_analysis['regime_adjusted_score'],
                            'regime_stable': regime_analysis['regime_stability']['stable'],
                            'regime_changes': regime_analysis['regime_stability']['regime_changes'],
                            'stability_penalty': regime_analysis['stability_penalty'],
                            'transition_penalty': regime_analysis['transition_penalty'],
                            'correlation_consistency': regime_analysis['correlation_consistency'],
                            
                            # Liquidity metrics
                            'liquidity_score': liquidity_profile['liquidity_score'],
                            'execution_risk': liquidity_profile['execution_risk'],
                            'volume_ratio': liquidity_profile['volume_ratio'],
                            'tick_size_ratio': liquidity_profile['tick_size_ratio'],
                            'volatility_asymmetry': liquidity_profile['volatility_asymmetry'],
                            'liquidity_correlation': liquidity_profile['liquidity_correlation'],
                            
                            # Transaction cost metrics
                            'total_cost_bps': transaction_costs['total_cost_bps'],
                            'spread_cost_bps': transaction_costs['spread_cost_bps'],
                            'market_impact_bps': transaction_costs['market_impact_bps'],
                            'execution_lag_bps': transaction_costs['execution_lag_bps'],
                            'commission_bps': transaction_costs['commission_bps'],
                            'annual_borrow_cost_bps': transaction_costs['annual_borrow_cost_bps'],
                            'borrow_rate1': transaction_costs['borrow_rate1'],
                            'borrow_rate2': transaction_costs['borrow_rate2'],
                            
                            'hedge_ratio': coint_result['hedge_ratio'],
                            'spread_mean': spread_stats['mean'],
                            'spread_std': spread_stats['std'],
                            'spread_skew': spread_stats['skew'],
                            'spread_kurtosis': spread_stats['kurtosis'],
                            'current_zscore': spread_stats['z_score'],
                            'data_points': coint_result['data_points'],
                            'criteria_met': criteria_met
                        }
                        
                        self.results.append(result)
                        
                        criteria_status = []
                        if regime_stable:
                            criteria_status.append("✓regime-stable")
                        else:
                            criteria_status.append("✗regime-unstable")
                        
                        if liquidity_adequate:
                            criteria_status.append("✓liquidity-ok")
                        else:
                            criteria_status.append(f"✗poor-liquidity({liquidity_profile['liquidity_score']:.2f})")
                        
                        if transaction_costs_acceptable:
                            criteria_status.append("✓cost-ok")
                        else:
                            criteria_status.append(f"✗high-costs({transaction_costs['total_cost_bps']:.1f}bps)")
                        
                        logger.info(f"✅ ACCEPTED pair: {symbol1}-{symbol2} "
                                  f"(p={coint_result['pvalue']:.4f}, "
                                  f"score={regime_analysis['regime_adjusted_score']:.4f}) "
                                  f"[{', '.join(criteria_status)}]")
                    else:
                        rejection_reasons = []
                        if not regime_stable:
                            rejection_reasons.append("regime-unstable")
                        if not liquidity_adequate:
                            rejection_reasons.append(f"poor-liquidity({liquidity_profile['liquidity_score']:.2f})")
                        if not transaction_costs_acceptable:
                            rejection_reasons.append(f"high-costs({transaction_costs['total_cost_bps']:.1f}bps)")
                        
                        logger.info(f"❌ Rejected pair: {symbol1}-{symbol2} - {', '.join(rejection_reasons)}")
                
            except Exception as e:
                logger.error(f"Error testing pair {symbol1}-{symbol2}: {e}")
                continue
        
        logger.info(f"🎯 Found {len(self.results)} viable pairs with relaxed criteria")

def main():
    """Main execution function with relaxed criteria"""
    print("🚀 RELAXED ClickHouse Pair Screening for Statistical Arbitrage")
    print("=" * 70)
    
    config = create_relaxed_config()
    
    print(f"📊 Relaxed Configuration:")
    print(f"  📅 Date range: {config.start_date} to {config.end_date}")
    print(f"  📈 Min correlation: {config.min_correlation}")
    print(f"  🔬 Cointegration p-value: {config.min_cointegration_pvalue}")
    print(f"  💰 Max transaction costs: 200 bps")
    print(f"  💧 Min liquidity score: 0.2")
    print(f"  🎲 Min criteria to meet: 2/3")
    
    # Create screener
    screener = RelaxedPairScreener(config)
    
    try:
        # Screen pairs
        print("\n🔍 1. Screening pairs for cointegration...")
        screener.screen_pairs()
        
        # Save results
        print("\n💾 2. Saving and ranking results...")
        df_results = screener.rank_and_save_results()
        
        # Create visualizations
        if df_results is not None and not df_results.empty and config.save_plots:
            print("\n📊 3. Creating visualizations...")
            screener.create_visualizations(df_results)
        
        print("\n" + "="*70)
        print("🎉 RELAXED SCREENING COMPLETE!")
        print(f"🎯 Found {len(screener.results)} viable pairs")
        
        if screener.results:
            print("\n📈 Top pairs by composite score:")
            for i, result in enumerate(screener.results[:5]):
                print(f"  {i+1}. {result['symbol1']}-{result['symbol2']}: "
                      f"corr={result['correlation']:.3f}, "
                      f"p={result['cointegration_pvalue']:.4f}, "
                      f"cost={result['total_cost_bps']:.1f}bps")
        
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n🛑 Screening interrupted by user")
    except Exception as e:
        logger.error(f"❌ Screening failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
