"""
Signal generation and position handling for backtesting.
"""
import numpy as np
import pandas as pd
from typing import Tuple, List
from structs import Config, Position, Trade
from model.kalman import KalmanFilter
from model.hmm import GaussianHMM
from model.ensemble import train_classifier
from strategy.spread import compute_spread
from strategy.pair_selection import is_stationary
from strategy.execution import simulate_execution

def train_models_and_get_spread(pair: Tuple[str, str], training_data: pd.DataFrame, config: Config) -> Tuple:
    """Trains models and returns them along with the historical spread series."""
    y_train = training_data[pair[0]]
    x_train = training_data[pair[1]]
    kf = KalmanFilter().fit(y_train, x_train)
    
    spread_series = pd.Series(
        [compute_spread(y_train.iloc[i], x_train.iloc[i], kf.state_means[i], config.spread_type) for i in range(len(training_data))],
        index=training_data.index
    )
    
    hmm = GaussianHMM(num_regimes=config.num_regimes).fit(spread_series) if config.use_hmm else None
    clf = train_classifier(spread_series) if config.use_ensemble_classifier else None
        
    return kf, hmm, clf, spread_series

def calculate_pnl(position: Position, exit_y_price: float, exit_x_price: float) -> float:
    """Calculates the PnL of a closed trade based on asset prices."""
    if position.type == 'LONG': # Long Y, Short X
        y_pnl = (exit_y_price - position.entry_y_price) * position.y_shares
        x_pnl = (position.entry_x_price - exit_x_price) * position.x_shares
    elif position.type == 'SHORT': # Short Y, Long X
        y_pnl = (position.entry_y_price - exit_y_price) * position.y_shares
        x_pnl = (exit_x_price - position.entry_x_price) * position.x_shares
    else:
        return 0.0
    return y_pnl + x_pnl

def simulate_trading(pair: Tuple[str, str], training_data: pd.DataFrame, sample_data: pd.DataFrame, config: Config) -> pd.DataFrame | None:
    """Main procedure for simulating the trading strategy on a given pair."""
    kf, hmm, clf, train_spread = train_models_and_get_spread(pair, training_data, config)
    
    position = Position()
    trades: List[Trade] = []
    y_ticker, x_ticker = pair

    for i in range(len(sample_data)):
        current_date = sample_data.index[i]
        y_price, x_price = sample_data[y_ticker].iloc[i], sample_data[x_ticker].iloc[i]
        
        current_state = kf.get_current_state()
        beta = current_state[0]
        current_spread = compute_spread(y_price, x_price, current_state, config.spread_type)

        if not is_stationary(train_spread.append(pd.Series(current_spread))):
            if position.type != 'FLAT':
                pnl = calculate_pnl(position, y_price, x_price)
                trades.append(Trade(pair=pair, entry_date=position.entry_date, exit_date=current_date, pnl=pnl, type=position.type))
                position = Position()
            continue
        
        if config.use_hmm and hmm:
            regime_params = hmm.get_regime_params()
            current_regime = hmm.predict_regime(current_spread)
            mean, std = regime_params[current_regime]['mean'], regime_params[current_regime]['std']
        else:
            mean, std = train_spread.mean(), train_spread.std()

        if std < 1e-6: continue
        z_score = (current_spread - mean) / std

        if position.type != 'FLAT':
            position.holding_period += 1
            exit_condition = (position.type == 'LONG' and z_score > -config.exit_z) or (position.type == 'SHORT' and z_score < config.exit_z)
            stop_condition = (position.type == 'LONG' and z_score < -config.stop_loss_mult) or (position.type == 'SHORT' and z_score > config.stop_loss_mult)
            hold_limit_reached = position.holding_period > config.max_hold_bars

            if exit_condition or stop_condition or hold_limit_reached:
                pnl = calculate_pnl(position, y_price, x_price)
                trades.append(Trade(pair=pair, entry_date=position.entry_date, exit_date=current_date, pnl=pnl, type=position.type))
                position = Position()
        else:
            trade_signal = 'NONE'
            if z_score > config.entry_z: trade_signal = 'SHORT'
            elif z_score < -config.entry_z: trade_signal = 'LONG'

            if trade_signal != 'NONE':
                classifier_approval = True
                if config.use_ensemble_classifier and clf:
                    features = pd.DataFrame({'spread': [current_spread], 'spread_lag_1': [train_spread.iloc[-1]], 'volatility_10d': [train_spread.rolling(window=10).std().iloc[-1]]})
                    prediction = clf.predict(features)[0]
                    classifier_approval = (prediction == 1)

                if classifier_approval:
                    if y_price <= 0 or x_price <= 0: continue
                    y_shares = config.trade_size_dollars / y_price
                    x_shares = (config.trade_size_dollars * beta) / x_price
                    position = Position(
                        type=trade_signal, entry_date=current_date, holding_period=0,
                        entry_y_price=simulate_execution(y_price, trade_signal, config),
                        entry_x_price=simulate_execution(x_price, 'SHORT' if trade_signal == 'LONG' else 'LONG', config),
                        y_shares=y_shares, x_shares=x_shares
                    )

    if not trades:
        return None
    return pd.DataFrame([t.__dict__ for t in trades]) 