"""
Streamlit dashboard for real-time monitoring and plotting.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Adjust relative paths for Streamlit execution from root
from config import CONFIG_DICT
from structs import Config, Position
from data import data_loader
from strategy import pair_selection, trading
from strategy.spread import compute_spread

def initialize_session_state():
    """Initializes all necessary variables in Streamlit's session state."""
    st.session_state.session_started = False
    st.session_state.data = None
    st.session_state.pairs = []
    st.session_state.selected_pair = None
    st.session_state.kf = None
    st.session_state.hmm = None
    st.session_state.clf = None
    st.session_state.train_spread = None
    st.session_state.sample_data = None
    st.session_state.current_bar_index = 0
    st.session_state.position = Position()
    st.session_state.trades = []
    st.session_state.live_spread_history = []
    st.session_state.live_zscore_history = []
    st.session_state.pnl_history = [0.0]


def start_session():
    """Loads data, finds pairs, and trains initial models."""
    config = Config(**CONFIG_DICT)
    st.session_state.data = data_loader.load_intraday_data(config.tickers, config.history_duration_days, config.data_interval)
    if st.session_state.data.empty:
        st.error("Failed to load data.")
        return

    initial_training_data = st.session_state.data.iloc[0:config.training_window_bars]
    if config.use_dynamic_pairs:
        st.session_state.pairs = pair_selection.dynamic_pair_selection(initial_training_data)
    else:
        st.session_state.pairs = [tuple(config.tickers)]

    if not st.session_state.pairs:
        st.error("No valid pairs found in the initial training period.")
        return
        
    st.session_state.session_started = True
    st.session_state.selected_pair = st.session_state.pairs[0]
    st.experimental_rerun()


def setup_pair_for_simulation():
    """Trains models for the selected pair."""
    config = Config(**CONFIG_DICT)
    pair = st.session_state.selected_pair
    data = st.session_state.data
    
    training_data = data.iloc[0:config.training_window_bars]
    st.session_state.sample_data = data.iloc[config.training_window_bars:]
    
    kf, hmm, clf, train_spread = trading.train_models_and_get_spread(pair, training_data, config)
    
    st.session_state.kf = kf
    st.session_state.hmm = hmm
    st.session_state.clf = clf
    st.session_state.train_spread = train_spread
    
    initialize_session_state() # Reset simulation state for the new pair
    st.session_state.session_started = True # Keep session active
    st.session_state.data = data # Restore data
    st.session_state.pairs = [pair] # Restore pairs
    st.session_state.selected_pair = pair # Restore selected pair

def process_next_bar():
    """Processes one bar of data to simulate a live tick."""
    if st.session_state.current_bar_index >= len(st.session_state.sample_data):
        st.warning("End of historical data reached.")
        return

    idx = st.session_state.current_bar_index
    y_ticker, x_ticker = st.session_state.selected_pair
    config = Config(**CONFIG_DICT)

    current_bar = st.session_state.sample_data.iloc[[idx]]
    y_price = current_bar[y_ticker].iloc[0]
    x_price = current_bar[x_ticker].iloc[0]
    
    state = st.session_state.kf.get_current_state()
    spread = compute_spread(y_price, x_price, state, config.spread_type)
    
    if config.use_hmm and st.session_state.hmm:
        params = st.session_state.hmm.get_regime_params()
        regime = st.session_state.hmm.predict_regime(spread)
        mean, std = params[regime]['mean'], params[regime]['std']
    else:
        mean, std = st.session_state.train_spread.mean(), st.session_state.train_spread.std()
    
    z_score = (spread - mean) / std if std > 1e-6 else 0
    
    st.session_state.live_spread_history.append(spread)
    st.session_state.live_zscore_history.append(z_score)

    pos = st.session_state.position
    if pos.type != 'FLAT':
        pos.holding_period += 1
        exit_cond = (pos.type == 'LONG' and z_score > -config.exit_z) or (pos.type == 'SHORT' and z_score < config.exit_z)
        stop_cond = (pos.type == 'LONG' and z_score < -config.stop_loss_mult) or (pos.type == 'SHORT' and z_score > config.stop_loss_mult)
        hold_limit = pos.holding_period > config.max_hold_bars

        if exit_cond or stop_cond or hold_limit:
            pnl = trading.calculate_pnl(pos, y_price, x_price)
            st.session_state.trades.append({'pair': (y_ticker, x_ticker), 'entry_date': pos.entry_date, 'exit_date': current_bar.index[0], 'pnl': pnl, 'type': pos.type})
            st.session_state.pnl_history.append(st.session_state.pnl_history[-1] + pnl)
            st.session_state.position = Position()

    else:
        if z_score > config.entry_z or z_score < -config.entry_z:
            trade_signal = 'SHORT' if z_score > config.entry_z else 'LONG'
            beta = state[0]
            if y_price > 0 and x_price > 0:
                y_shares = config.trade_size_dollars / y_price
                x_shares = (config.trade_size_dollars * beta) / x_price
                st.session_state.position = Position(
                    type=trade_signal, entry_date=current_bar.index[0], holding_period=0, 
                    entry_y_price=y_price, entry_x_price=x_price, 
                    y_shares=y_shares, x_shares=x_shares
                )

    st.session_state.current_bar_index += 1

def run_dashboard():
    st.set_page_config(layout="wide")
    st.title("Stat-Arb Live Trading Dashboard")

    if 'session_started' not in st.session_state:
        initialize_session_state()

    if not st.session_state.session_started:
        st.button("Start New Session", on_click=start_session)
    else:
        with st.sidebar:
            st.header("Controls")
            
            if st.session_state.pairs:
                selected_pair_str = st.selectbox(
                    "Select Pair for Simulation",
                    options=[f"{p[0]}-{p[1]}" for p in st.session_state.pairs],
                    key='selected_pair_str'
                )
                st.session_state.selected_pair = tuple(selected_pair_str.split('-'))

                if st.button("Load Pair and Train Models"):
                    with st.spinner("Training models for selected pair..."):
                        setup_pair_for_simulation()
            
            if st.session_state.kf:
                st.button("Process Next Bar", on_click=process_next_bar)

        if st.session_state.kf and st.session_state.sample_data is not None and st.session_state.current_bar_index > 0:
            y_ticker, x_ticker = st.session_state.selected_pair
            idx = st.session_state.current_bar_index
            
            current_date = st.session_state.sample_data.index[idx-1].strftime('%Y-%m-%d %H:%M:%S')
            st.subheader(f"Live Simulation for {y_ticker}-{x_ticker}")
            st.caption(f"Current Bar: {current_date}")

            col1, col2, col3, col4 = st.columns(4)
            state = st.session_state.kf.get_current_state()
            col1.metric("Hedge Ratio (Beta)", f"{state[0]:.4f}")
            col2.metric("Current Spread", f"{st.session_state.live_spread_history[-1]:.4f}")
            col3.metric("Current Z-Score", f"{st.session_state.live_zscore_history[-1]:.4f}")
            
            position_type = st.session_state.position.type
            color = "off"
            if position_type == 'LONG': color = "green"
            elif position_type == 'SHORT': color = "red"
            col4.metric("Position", position_type, delta_color=color)

            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=(f"Prices: {y_ticker} vs {x_ticker}", "Spread and Z-Score", "Live P&L"))
            sim_data = st.session_state.sample_data.iloc[:idx]
            fig.add_trace(go.Scatter(x=sim_data.index, y=sim_data[y_ticker], name=y_ticker), row=1, col=1)
            fig.add_trace(go.Scatter(x=sim_data.index, y=sim_data[x_ticker], name=x_ticker), row=1, col=1)

            z_series = pd.Series(st.session_state.live_zscore_history, index=sim_data.index)
            fig.add_trace(go.Scatter(x=z_series.index, y=z_series, name='Z-Score', line=dict(color='purple')), row=2, col=1)
            entry_z, exit_z = CONFIG_DICT['entry_z'], CONFIG_DICT['exit_z']
            fig.add_hline(y=entry_z, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=-entry_z, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=exit_z, line_dash="dash", line_color="green", row=2, col=1)
            fig.add_hline(y=-exit_z, line_dash="dash", line_color="green", row=2, col=1)
            
            pnl_df = pd.DataFrame({'pnl': st.session_state.pnl_history})
            fig.add_trace(go.Scatter(x=np.arange(len(pnl_df)), y=pnl_df['pnl'], name='Cumulative PnL', line=dict(color='orange')), row=3, col=1)

            fig.update_layout(height=800, title_text="Live Pair Analysis")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Trade Log")
            if st.session_state.trades:
                trades_df = pd.DataFrame(st.session_state.trades).sort_values(by='exit_date', ascending=False)
                st.dataframe(trades_df.style.format({'pnl': "{:.2f}"}))
            else:
                st.write("No trades closed yet.")

if __name__ == "__main__":
    run_dashboard() 