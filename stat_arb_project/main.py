"""
Entry point for the Intraday Statistical Arbitrage trading strategy pipeline.
"""
import pandas as pd
from config import CONFIG_DICT
from structs import Config
from data import data_loader
from evaluation import metrics, diagnostics, ablation, robustness
from strategy import pair_selection, trading
from utils import helpers
from typing import List, Tuple

def run_backtest(config: Config, data: pd.DataFrame, pairs: List[Tuple[str, str]]) -> pd.DataFrame | None:
    """
    Core backtesting logic for intraday, using bar-based walk-forward analysis.
    """
    logger = helpers.setup_logging()
    all_trades: List[pd.DataFrame] = []

    for t in range(config.training_window_bars, len(data), config.sample_window_bars):
        training_data = data.iloc[t - config.training_window_bars : t]
        sample_data_end_index = min(t + config.sample_window_bars, len(data))
        sample_data = data.iloc[t : sample_data_end_index]

        if sample_data.empty or len(training_data) < config.training_window_bars // 2:
            continue

        logger.info(f"\n--- Walk-forward window: "
                    f"Training: {training_data.index[0]} to {training_data.index[-1]}, "
                    f"Sampling: {sample_data.index[0]} to {sample_data.index[-1]} ---")

        for pair in pairs:
            try:
                if config.use_dynamic_pairs and not pair_selection.is_cointegrated(training_data[pair[0]], training_data[pair[1]]):
                    logger.warning(f"Pair {pair} no longer cointegrated. Skipping.")
                    continue
                
                trade_log = trading.simulate_trading(pair, training_data, sample_data, config)
                if trade_log is not None and not trade_log.empty:
                    all_trades.append(trade_log)
            except Exception as e:
                logger.error(f"Error processing pair {pair} in walk-forward window: {e}", exc_info=True)
                continue
    
    if not all_trades:
        return None
        
    return pd.concat(all_trades).sort_values(by='entry_date').reset_index(drop=True)

def stat_arb_main(config_dict: dict):
    """ Main pipeline for the intraday statistical arbitrage strategy. """
    logger = helpers.setup_logging()
    logger.info("Starting Intraday Statistical Arbitrage Pipeline...")
    
    config = Config(**config_dict)

    try:
        data = data_loader.load_intraday_data(
            tickers=config.tickers,
            duration_days=config.history_duration_days,
            interval=config.data_interval
        )
        if data.empty: return
        
        if len(data) < config.training_window_bars:
            logger.error(f"Insufficient data for a single training window. "
                         f"Loaded {len(data)} bars, but require {config.training_window_bars}. "
                         "Try increasing 'history_duration_days' in the config.")
            return

        logger.info("Intraday data loaded successfully.")

        if config.use_dynamic_pairs:
            initial_training_data = data.iloc[0:config.training_window_bars]
            pairs = pair_selection.dynamic_pair_selection(initial_training_data)
        else:
            if all(ticker in data.columns for ticker in config.tickers):
                pairs = [tuple(config.tickers)]
            else:
                logger.error(f"Predefined tickers {config.tickers} not found in loaded data columns: {data.columns.tolist()}")
                pairs = []
        
        if not pairs:
            logger.warning("No valid pairs found. Exiting.")
            return
            
        logger.info(f"Selected {len(pairs)} pairs for trading: {pairs}")
        
        full_trade_log = run_backtest(config, data, pairs)

        if full_trade_log is not None:
            logger.info("\n--- Evaluating Main Strategy Performance ---")
            metrics.calculate_and_plot_metrics(full_trade_log, config, "main_strategy_performance.png")
            diagnostics.run_diagnostics(full_trade_log, config)
        else:
            logger.warning("Main strategy executed no trades. Performance evaluation skipped.")

        if config.perform_ablation:
            ablation.run_ablation_tests(config, data, pairs)
        
        robustness.run_cross_validation(config, data, pairs)
        robustness.run_monte_carlo_backtests(config, data, pairs)
        
        logger.info("\nStatistical Arbitrage Pipeline Finished Successfully.")
    except Exception as e:
        logger.critical(f"A critical error occurred in the main pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    stat_arb_main(CONFIG_DICT) 