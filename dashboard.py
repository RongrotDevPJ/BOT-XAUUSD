import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sys
import os

# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.data_tool import export_trade_history, export_market_data

# Page Config
st.set_page_config(page_title="XAUUSD Bot Dashboard", layout="wide", page_icon="📈")

# Sidebar
st.sidebar.title("🛠️ Control Panel")
if st.sidebar.button("🔄 Refresh Data (Fetch New)"):
    with st.spinner("🚀 Fetching latest data from MT5..."):
        try:
            export_trade_history()
            export_market_data(days=30)
            st.cache_data.clear() # Clear cache to reload new CSVs
            st.rerun() 
        except Exception as e:
            st.error(f"Error updating data: {e}")

st.title("📊 XAUUSD Trading Bot")

# Load Data
@st.cache_data
def load_data():
    try:
        # Load Trade History
        trades = pd.read_csv('data/export_trade_history.csv')
        if not trades.empty:
            trades['time'] = pd.to_datetime(trades['time'])
            trades['cumulative_profit'] = trades['profit'].cumsum()
            trades['date'] = trades['time'].dt.date
        
        # Load Market Data
        market = pd.read_csv('data/export_market_data.csv')
        if not market.empty:
            market['time'] = pd.to_datetime(market['time'])
            
        return trades, market
    except FileNotFoundError:
        return None, None

trades, market = load_data()

if trades is None or market is None:
    st.warning("⚠️ Data not found! Please run `python utils/data_tool.py` to export data first.")
    st.stop()

# --- KPI METRICS ROW ---
if not trades.empty:
    # ----------------------------------------------------
    # 0. SYMBOL FILTER
    # ----------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Filtering")
    symbols = ['All'] + sorted(trades['symbol'].unique().tolist())
    selected_symbol = st.sidebar.selectbox("Select Symbol", symbols)
    
    display_trades = trades.copy()
    if selected_symbol != 'All':
        display_trades = display_trades[display_trades['symbol'] == selected_symbol]

    # ----------------------------------------------------
    # 1. TRADE STATUS CLASSIFICATION (TP vs SL vs BR)
    # ----------------------------------------------------
    def classify_trade(row):
        profit = row['profit']
        comment = str(row['comment']).lower()
        
        if profit > 0:
            if 'tp' in comment:
                return 'TP 🎯'  # Take Profit Hit
            elif 'sl' in comment:
                return 'BR 🛡️'  # Trailing Stop (Break Even)
            else:
                return 'WIN ✅' # Manual Close (Profit)
        elif profit < 0:
            return 'SL ❌'      # Stop Loss Hit
        else:
            return 'BE ➖'      # Break Even (Exactly 0)

    display_trades['status'] = display_trades.apply(classify_trade, axis=1)

    # Calculate Counts
    status_counts = display_trades['status'].value_counts()
    
    total_trades = len(display_trades)
    win_trades = len(display_trades[display_trades['profit'] > 0])
    loss_trades = total_trades - win_trades
    total_profit = display_trades['profit'].sum()
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
    
    # Calculate Profit Factor
    gross_profit = display_trades[display_trades['profit'] > 0]['profit'].sum()
    gross_loss = abs(display_trades[display_trades['profit'] < 0]['profit'].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Net Profit", f"${total_profit:,.2f}", delta=f"{total_profit:,.2f}")
    col2.metric("🎯 Win Rate", f"{win_rate:.1f}%", f"{win_trades} W / {loss_trades} L")
    col3.metric("📊 Profit Factor", f"{pf:.2f}", help="> 1.5 is Good, > 2.0 is Excellent")
    col4.metric("🔢 Total Trades", f"{total_trades}")
else:
    st.info("No trades to display.")
    display_trades = pd.DataFrame()


st.markdown("---")

# Layout: Tabs
tab1, tab2, tab3 = st.tabs(["📈 Performance Analysis", "🕯️ Market Chart", "📝 Trade History"])

with tab1:
    if not display_trades.empty:
        # Row 1: Equity Curve (Full Width)
        st.subheader(f"📈 Profit Growth ({selected_symbol})")
        fig_equity = px.line(display_trades, x='time', y='cumulative_profit', markers=True)
        fig_equity.update_traces(line_color='#00CC96', line_width=3)
        fig_equity.update_layout(xaxis_title="Time", yaxis_title="Balance Growth ($)", hovermode="x unified")
        st.plotly_chart(fig_equity, width="stretch")

        # Row 2: Two Columns
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("📅 Daily Profit/Loss")
            daily_profit = display_trades.groupby('date')['profit'].sum().reset_index()
            daily_profit['color'] = daily_profit['profit'].apply(lambda x: 'green' if x >= 0 else 'red')
            
            fig_daily = px.bar(
                daily_profit, 
                x='date', 
                y='profit', 
                text_auto='.2s', 
                color='profit',
                color_continuous_scale=['red', 'green'],
                title="Total Profit per Day"
            )
            # Customizing to make it look like separate bars with specific colors
            fig_daily.update_traces(marker_color=daily_profit['color'], textposition='auto')
            fig_daily.update_layout(
                xaxis_title="Date", 
                yaxis_title="Profit ($)", 
                xaxis=dict(type='category'), # Force distinct days
                bargap=0.5, # Prevent bars from being too wide
                showlegend=False
            )
            # Add a zero line for reference
            fig_daily.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_daily, width="stretch")

        with c2:
            st.subheader("🍰 Trade Result Breakdown")
            # Use Status Counts for Pie Chart
            fig_pie = px.pie(display_trades, names='status', title='TP vs SL vs BR', hole=0.4, 
                             color='status',
                             color_discrete_map={
                                 'TP 🎯': '#00CC96',  # Green
                                 'BR 🛡️': '#FFA15A',  # Orange
                                 'WIN ✅': '#AB63FA', # Purple
                                 'SL ❌': '#EF553B',  # Red
                                 'BE ➖': '#B6E880'   # Light Green
                             })
            fig_pie.update_layout(showlegend=True, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, width="stretch")

with tab2:
    st.subheader(f"🕯️ {selected_symbol if selected_symbol != 'All' else 'Market'} Price Chart")
    if not market.empty:
        # Show last 200 candles by default for performance
        recent_market = market.tail(200)
        
        fig_candle = go.Figure(data=[go.Candlestick(
            x=recent_market['time'],
            open=recent_market['open'],
            high=recent_market['high'],
            low=recent_market['low'],
            close=recent_market['close'],
            name=selected_symbol
        )])
        
        fig_candle.update_layout(height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_candle, width="stretch")
    else:
        st.info("No market data found.")

with tab3:
    st.subheader("📝 Trade Log Details")
    if not display_trades.empty:
        # Filter Options
        status_filter = st.multiselect("Filter by Status", options=display_trades['status'].unique(), default=display_trades['status'].unique())
        filtered_df = display_trades[display_trades['status'].isin(status_filter)]

        # Style the dataframe
        def color_profit(val):
            return f'color: {"green" if val > 0 else "red"}'

        styled_df = filtered_df[['time', 'ticket', 'symbol', 'type', 'status', 'volume', 'price', 'profit', 'comment']].sort_values(by='time', ascending=False)
        st.dataframe(styled_df.style.map(color_profit, subset=['profit']), width="stretch", height=600)
    else:
        st.info("No trade logs available.")

