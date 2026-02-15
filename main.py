import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import numpy as np
import time

st.set_page_config(page_title="TSX Institutional Engine", layout="wide")

st.title("🇨🇦 TSX Institutional Signal Engine")

tabs = st.tabs(["Live Scanner", "Backtest Engine"])

# =========================
# SETTINGS
# =========================

ACCOUNT_SIZE = 100000
RISK_PERCENT = 1

stocks = [
    "SHOP.TO","SU.TO","RY.TO","TD.TO","BNS.TO",
    "ENB.TO","CNQ.TO","CP.TO","CNR.TO","BAM.TO"
]

# =========================
# LIVE TAB
# =========================

with tabs[0]:

    st.subheader("🔥 Live 1H Momentum Scanner")

    results = []

    for ticker in stocks:

        df = yf.download(ticker, period="30d", interval="1h")

        if df.empty:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df["Close"]

        df["EMA20"] = ta.trend.ema_indicator(close, 20)
        df["EMA50"] = ta.trend.ema_indicator(close, 50)
        df["RSI"] = ta.momentum.rsi(close, 14)
        df["ATR"] = ta.volatility.average_true_range(
            df["High"], df["Low"], df["Close"], 14
        )

        last = df.iloc[-1]

        score = 0

        if last["EMA20"] > last["EMA50"]:
            score += 1

        if last["Close"] > last["EMA20"]:
            score += 1

        if 55 < last["RSI"] < 75:
            score += 1

        entry = float(last["Close"])
        atr = float(last["ATR"])
        stop = entry - atr
        target = entry + (2 * atr)

        risk_amount = ACCOUNT_SIZE * (RISK_PERCENT / 100)
        shares = int(risk_amount / (entry - stop)) if (entry - stop) > 0 else 0

        results.append({
            "Stock": ticker,
            "Price": round(entry,2),
            "Entry": round(entry,2),
            "Stop": round(stop,2),
            "Target": round(target,2),
            "RSI": round(float(last["RSI"]),2),
            "Score": score,
            "Shares": shares
        })

    if len(results) > 0:
        df_results = pd.DataFrame(results)
        best = df_results.sort_values(by="Score", ascending=False).iloc[0]

        st.write("### Best Trade Right Now")
        st.write(best)

        st.write("### Ranked Signals")
        st.dataframe(df_results.sort_values(by="Score", ascending=False))
    else:
        st.warning("No signals found.")

# =========================
# BACKTEST TAB
# =========================

with tabs[1]:

    st.subheader("📊 Strategy Backtest")

    ticker = st.selectbox("Select Stock", stocks)

    df = yf.download(ticker, period="6mo", interval="1d")

    if not df.empty:

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df["EMA20"] = ta.trend.ema_indicator(df["Close"], 20)
        df["EMA50"] = ta.trend.ema_indicator(df["Close"], 50)
        df["RSI"] = ta.momentum.rsi(df["Close"], 14)

        df["Signal"] = 0
        df.loc[
            (df["EMA20"] > df["EMA50"]) &
            (df["RSI"] > 55),
            "Signal"
        ] = 1

        df["Position"] = df["Signal"].shift(1)
        df["Returns"] = df["Close"].pct_change()
        df["Strategy"] = df["Returns"] * df["Position"]

        equity_curve = (1 + df["Strategy"]).cumprod()

        total_trades = df["Signal"].sum()
        wins = (df["Strategy"] > 0).sum()
        losses = (df["Strategy"] < 0).sum()

        win_rate = round((wins / total_trades)*100,2) if total_trades>0 else 0
        total_return = round((equity_curve.iloc[-1]-1)*100,2)

        drawdown = (equity_curve / equity_curve.cummax() - 1).min()
        sharpe = np.sqrt(252) * df["Strategy"].mean() / df["Strategy"].std() if df["Strategy"].std()!=0 else 0

        st.write("### Performance Metrics")
        st.write(f"Total Trades: {int(total_trades)}")
        st.write(f"Win Rate: {win_rate}%")
        st.write(f"Total Return: {total_return}%")
        st.write(f"Max Drawdown: {round(drawdown*100,2)}%")
        st.write(f"Sharpe Ratio: {round(sharpe,2)}")

        st.line_chart(equity_curve)

    else:
        st.warning("No historical data.")
