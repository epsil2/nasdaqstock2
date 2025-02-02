# app.py
import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# Configuration
API_KEY = "XSNKMIGE7B4OSCNA"  # Replace with your key
NASDAQ_SYMBOLS = ["AAPL", "MSFT", "AMZN", "GOOGL", "TSLA", "META", "NVDA"]
INDICATORS = ["MACD", "RSI (14-day)", "VWAP", "Bollinger Bands"]

# Helper Functions
def get_stock_data(symbol, interval="daily"):
    """Fetch stock price data from Alpha Vantage"""
    function_map = {
        "daily": "TIME_SERIES_DAILY",
        "weekly": "TIME_SERIES_WEEKLY",
        "monthly": "TIME_SERIES_MONTHLY"
    }
    
    url = f"https://www.alphavantage.co/query?function={function_map[interval]}&symbol={symbol}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    # Handle API errors
    if "Error Message" in data:
        raise ValueError(f"API Error: {data['Error Message']}")
    if "Note" in data:  # API rate limit message
        raise ValueError(f"API Limit: {data['Note']}")
    
    # Find the correct time series key
    time_series_keys = {
        "daily": "Time Series (Daily)",
        "weekly": "Weekly Time Series",
        "monthly": "Monthly Time Series"
    }
    
    time_series_key = time_series_keys.get(interval)
    
    if not time_series_key or time_series_key not in data:
        raise ValueError(f"Unexpected API response format for {symbol}")
    
    time_series = data[time_series_key]
    
    df = pd.DataFrame.from_dict(time_series, orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.rename(columns={
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close",
        "5. volume": "volume"
    }).astype(float)
    
    return df.sort_index()

def get_financial_ratios(symbol):
    """Fetch key financial ratios from Alpha Vantage"""
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    return {
        "P/E Ratio": data.get("PERatio", "N/A"),
        "EPS": data.get("EPS", "N/A"),
        "ROE": data.get("ReturnOnEquityTTM", "N/A"),
        "Market Cap": f"${data.get('MarketCapitalization', 'N/A')}",
        "Dividend Yield": f"{data.get('DividendYield', 'N/A')}%",
        "Profit Margin": data.get("ProfitMargin", "N/A"),
        "52 Week High": data.get("52WeekHigh", "N/A"),
        "52 Week Low": data.get("52WeekLow", "N/A")
    }

# Technical Indicator Calculations
def calculate_rsi(data, window=14):
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_vwap(data):
    tp = (data['high'] + data['low'] + data['close']) / 3
    return (tp * data['volume']).cumsum() / data['volume'].cumsum()

# Streamlit App
st.set_page_config(page_title="Advanced Stock Analyzer", layout="wide")

# Sidebar Controls
st.sidebar.title("Controls")
symbol = st.sidebar.selectbox("Select NASDAQ Stock", NASDAQ_SYMBOLS)
interval = st.sidebar.radio("Chart Interval", ["daily", "weekly", "monthly"])
selected_indicator = st.sidebar.selectbox("Select Technical Indicator", INDICATORS)

# Main Content
st.title(f"Advanced Stock Analyzer - {symbol}")

# Fetch Data
try:
    with st.spinner("Loading data..."):
        data = get_stock_data(symbol, interval)
        ratios = get_financial_ratios(symbol)
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Common fixes: Check API key, try a different stock, or wait 1 minute if you hit rate limits")
    st.stop()

# Price Chart
st.subheader(f"Price Chart ({interval.capitalize()})")
price_fig = go.Figure()
price_fig.add_trace(go.Candlestick(
    x=data.index,
    open=data['open'],
    high=data['high'],
    low=data['low'],
    close=data['close'],
    name='Price'
))
price_fig.update_layout(
    height=400,
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    title=f"{symbol} Price Chart"
)
st.plotly_chart(price_fig, use_container_width=True)

# Indicator Chart
st.subheader(f"{selected_indicator} Analysis")
indicator_fig = go.Figure()

if selected_indicator == "RSI (14-day)":
    data['RSI'] = calculate_rsi(data)
    indicator_fig.add_trace(go.Scatter(
        x=data.index, y=data['RSI'], 
        name='RSI', line=dict(color='orange')
    ))
    indicator_fig.add_hline(y=30, line_dash="dot", line_color="green")
    indicator_fig.add_hline(y=70, line_dash="dot", line_color="red")
    
elif selected_indicator == "MACD":
    macd, signal = calculate_macd(data)
    indicator_fig.add_trace(go.Scatter(
        x=data.index, y=macd, 
        name='MACD', line=dict(color='blue')
    ))
    indicator_fig.add_trace(go.Scatter(
        x=data.index, y=signal, 
        name='Signal Line', line=dict(color='orange')
    ))
    
elif selected_indicator == "VWAP":
    vwap = calculate_vwap(data)
    indicator_fig.add_trace(go.Scatter(
        x=data.index, y=vwap, 
        name='VWAP', line=dict(color='purple')
    ))
    indicator_fig.add_trace(go.Scatter(
        x=data.index, y=data['close'], 
        name='Price', line=dict(color='lightblue')
    ))
    
elif selected_indicator == "Bollinger Bands":
    data['MA20'] = data['close'].rolling(20).mean()
    data['Upper'] = data['MA20'] + 2*data['close'].rolling(20).std()
    data['Lower'] = data['MA20'] - 2*data['close'].rolling(20).std()
    
    indicator_fig.add_trace(go.Scatter(
        x=data.index, y=data['Upper'], 
        name='Upper Band', line=dict(color='gray')
    ))
    indicator_fig.add_trace(go.Scatter(
        x=data.index, y=data['Lower'], 
        name='Lower Band', line=dict(color='gray'),
        fill='tonexty'
    ))
    indicator_fig.add_trace(go.Scatter(
        x=data.index, y=data['MA20'], 
        name='Moving Average', line=dict(color='blue')
    ))

indicator_fig.update_layout(
    height=400,
    template="plotly_dark",
    title=f"{selected_indicator} Chart"
)
st.plotly_chart(indicator_fig, use_container_width=True)

# Financial Ratios
st.subheader("Fundamental Analysis")
cols = st.columns(4)
ratio_data = [
    ("P/E Ratio", ratios["P/E Ratio"]),
    ("EPS", ratios["EPS"]),
    ("ROE", ratios["ROE"]),
    ("Market Cap", ratios["Market Cap"]),
    ("Dividend Yield", ratios["Dividend Yield"]),
    ("Profit Margin", ratios["Profit Margin"]),
    ("52 Week High", ratios["52 Week High"]),
    ("52 Week Low", ratios["52 Week Low"])
]

for i, (name, value) in enumerate(ratio_data):
    cols[i % 4].metric(label=name, value=value)