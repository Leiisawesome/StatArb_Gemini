import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yaml
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from io import StringIO

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from picker.runner import SymbolPickerRunner
from core_engine.utils.structured_logging import init_logging, LogConfig

# --- UI Configuration ---
st.set_page_config(
    page_title="StatArb Symbol Picker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Logging Handler for UI ---
class StreamlitLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()

    def emit(self, record):
        msg = self.format(record)
        if 'logs' not in st.session_state:
            st.session_state.logs = ""
        st.session_state.logs += msg + "\n"

# Setup logging
ui_handler = StreamlitLogHandler()
ui_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(ui_handler)
logging.getLogger().setLevel(logging.INFO)

# --- Session State Initialization ---
if 'results' not in st.session_state:
    st.session_state.results = None
if 'logs' not in st.session_state:
    st.session_state.logs = ""
if 'running' not in st.session_state:
    st.session_state.running = False

# --- Helper Functions ---
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

async def run_picker(config, target_date):
    runner = SymbolPickerRunner(config)
    try:
        # runner.run() now returns a dict
        result = await runner.run(target_date)
        return result
    except Exception as e:
        st.error(f"Error running picker: {e}")
        return None

# --- Sidebar ---
st.sidebar.title("⚙️ Picker Settings")
config = load_config()

target_date = st.sidebar.date_input("Target Date", value=datetime(2024, 12, 20))
target_count = st.sidebar.slider("Target Universe Size", 5, 100, config['selection']['target_count'])
min_price = st.sidebar.number_input("Min Price ($)", 1.0, 1000.0, float(config['filters']['min_price']))
min_adv = st.sidebar.number_input("Min ADV 30d ($M)", 1.0, 1000.0, float(config['filters']['min_adv_30d'] / 1e6)) * 1e6

if st.sidebar.button("🚀 Run Picker", disabled=st.session_state.running):
    st.session_state.running = True
    st.session_state.logs = "Starting picker run...\n"
    
    # Update config with UI values
    config['selection']['target_count'] = target_count
    config['filters']['min_price'] = min_price
    config['filters']['min_adv_30d'] = min_adv
    
    # Run the picker
    with st.spinner("Fetching data and computing features..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_picker(config, target_date))
        
    if result:
        st.sidebar.success("Picker run complete!")
        st.session_state.results = result
    
    st.session_state.running = False
    st.rerun()

# --- Main Area ---
st.title("📈 StatArb Symbol Picker Dashboard")

if st.session_state.results:
    res = st.session_state.results
    symbols_data = res['universe']
    regime = res['regime']['label']
    
    # Summary Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Regime", regime.upper())
    col2.metric("Symbols Selected", len(symbols_data))
    col3.metric("Avg Hurst", f"{np.mean([s['metrics']['hurst'] for s in symbols_data.values()]):.2f}")
    col4.metric("Avg Vol (Ann)", f"{np.mean([s['metrics']['volatility_ann'] for s in symbols_data.values()]):.1%}")

    tab1, tab2, tab3 = st.tabs(["📋 Universe", "📊 Analytics", "📜 Logs"])

    with tab1:
        st.subheader("Selected Universe")
        df = pd.DataFrame.from_dict(symbols_data, orient='index')
        # Flatten metrics
        metrics_df = pd.json_normalize(df['metrics'])
        metrics_df.index = df.index
        
        display_df = pd.concat([df[['bucket', 'rank']], metrics_df], axis=1)
        display_df = display_df.sort_values('rank')
        
        st.dataframe(
            display_df.style.background_gradient(subset=['hurst'], cmap='RdYlGn_r')
            .background_gradient(subset=['volatility_ann'], cmap='Blues')
            .format({'volatility_ann': '{:.1%}', 'avg_spread_bps': '{:.1f}', 'hurst': '{:.2f}'}),
            use_container_width=True
        )

    with tab2:
        st.subheader("Quant Analytics")
        
        c1, c2 = st.columns(2)
        
        with c1:
            # Hurst vs Volatility Scatter
            fig = px.scatter(
                display_df, 
                x="volatility_ann", 
                y="hurst", 
                color="bucket",
                hover_name=display_df.index,
                title="Hurst Exponent vs Annualized Volatility",
                labels={"hurst": "Hurst (Lower = More Mean Reverting)", "volatility_ann": "Ann. Volatility"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            # Bucket Distribution
            fig = px.pie(display_df, names='bucket', title="Universe Composition by Bucket")
            st.plotly_chart(fig, use_container_width=True)

        # Correlation Heatmap
        if 'correlation_matrix' in res and res['correlation_matrix'] is not None:
            st.subheader("Shrinkage Correlation Matrix")
            corr = res['correlation_matrix']
            # Filter to selected symbols
            selected_syms = list(symbols_data.keys())[:20] # Top 20 for visibility
            if all(s in corr.index for s in selected_syms):
                subset_corr = corr.loc[selected_syms, selected_syms]
                fig = px.imshow(
                    subset_corr, 
                    text_auto=".2f", 
                    aspect="auto",
                    color_continuous_scale='RdBu_r',
                    zmin=-1, zmax=1,
                    title="Top 20 Symbols Correlation (Shrinkage Estimator)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Correlation matrix symbols do not match selected universe.")

    with tab3:
        col_log1, col_log2 = st.columns([0.9, 0.1])
        col_log1.subheader("Execution Logs")
        if col_log2.button("🗑️ Clear"):
            st.session_state.logs = ""
            st.rerun()
        st.text_area("Logs", value=st.session_state.logs, height=600, label_visibility="collapsed")

    # Download Button
    if 'artifact_path' in res:
        with open(res['artifact_path'], 'r') as f:
            st.sidebar.download_button(
                label="💾 Download Universe JSON",
                data=f.read(),
                file_name=os.path.basename(res['artifact_path']),
                mime="application/json"
            )


else:
    st.info("👈 Adjust settings and click 'Run Picker' to generate a universe.")
    
    # Show existing artifacts if any
    artifact_dir = "symbolpicks"
    if os.path.exists(artifact_dir):
        files = [f for f in os.listdir(artifact_dir) if f.endswith('.json')]
        if files:
            st.subheader("Recent Artifacts")
            for f in sorted(files, reverse=True)[:5]:
                if st.button(f"Load {f}"):
                    with open(os.path.join(artifact_dir, f), 'r') as file:
                        st.session_state.results = yaml.safe_load(file)
                    st.rerun()
