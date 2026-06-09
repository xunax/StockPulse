import pandas as pd
import numpy as np
from backtest import Action

def sma_crossover(df, fast=5, slow=20):
    df = df.copy()
    df["ma_fast"] = df["close"].rolling(fast).mean()
    df["ma_slow"] = df["close"].rolling(slow).mean()
    signals = [Action.HOLD] * len(df)
    for i in range(1, len(df)):
        if pd.isna(df["ma_fast"].iloc[i]) or pd.isna(df["ma_slow"].iloc[i]):
            continue
        prev_fast = df["ma_fast"].iloc[i - 1]
        prev_slow = df["ma_slow"].iloc[i - 1]
        cur_fast = df["ma_fast"].iloc[i]
        cur_slow = df["ma_slow"].iloc[i]
        if prev_fast <= prev_slow and cur_fast > cur_slow:
            signals[i] = Action.BUY
        elif prev_fast >= prev_slow and cur_fast < cur_slow:
            signals[i] = Action.SELL
    return signals

def rsi_strategy(df, period=14, oversold=30, overbought=70):
    from utils import calc_rsi
    rsi = calc_rsi(df["close"], period)
    signals = [Action.HOLD] * len(df)
    for i in range(1, len(df)):
        if pd.isna(rsi.iloc[i]):
            continue
        if rsi.iloc[i - 1] <= oversold and rsi.iloc[i] > oversold:
            signals[i] = Action.BUY
        elif rsi.iloc[i - 1] >= overbought and rsi.iloc[i] < overbought:
            signals[i] = Action.SELL
    return signals

def macd_strategy(df, fast=12, slow=26, signal=9):
    from utils import calc_macd
    macd_line, signal_line, _ = calc_macd(df["close"], fast, slow, signal)
    signals = [Action.HOLD] * len(df)
    for i in range(1, len(df)):
        if pd.isna(macd_line.iloc[i]) or pd.isna(signal_line.iloc[i]):
            continue
        if macd_line.iloc[i - 1] <= signal_line.iloc[i - 1] and macd_line.iloc[i] > signal_line.iloc[i]:
            signals[i] = Action.BUY
        elif macd_line.iloc[i - 1] >= signal_line.iloc[i - 1] and macd_line.iloc[i] < signal_line.iloc[i]:
            signals[i] = Action.SELL
    return signals

def bollinger_strategy(df, period=20, std_dev=2):
    from utils import calc_bollinger
    ma, upper, lower = calc_bollinger(df["close"], period, std_dev)
    signals = [Action.HOLD] * len(df)
    for i in range(1, len(df)):
        if pd.isna(df["close"].iloc[i]) or pd.isna(lower.iloc[i]) or pd.isna(upper.iloc[i]):
            continue
        if df["close"].iloc[i - 1] >= lower.iloc[i - 1] and df["close"].iloc[i] < lower.iloc[i]:
            signals[i] = Action.BUY
        elif df["close"].iloc[i - 1] <= upper.iloc[i - 1] and df["close"].iloc[i] > upper.iloc[i]:
            signals[i] = Action.SELL
    return signals

STRATEGIES = {
    "均線黃金交叉": {
        "fn": sma_crossover,
        "params": [
            {"name": "fast", "label": "快線天數", "min": 3, "max": 60, "default": 5, "step": 1},
            {"name": "slow", "label": "慢線天數", "min": 10, "max": 120, "default": 20, "step": 1},
        ],
    },
    "RSI 策略": {
        "fn": rsi_strategy,
        "params": [
            {"name": "period", "label": "RSI 天數", "min": 6, "max": 30, "default": 14, "step": 1},
            {"name": "oversold", "label": "超賣線", "min": 10, "max": 40, "default": 30, "step": 5},
            {"name": "overbought", "label": "超買線", "min": 60, "max": 90, "default": 70, "step": 5},
        ],
    },
    "MACD 策略": {
        "fn": macd_strategy,
        "params": [
            {"name": "fast", "label": "快線 EMA", "min": 5, "max": 20, "default": 12, "step": 1},
            {"name": "slow", "label": "慢線 EMA", "min": 15, "max": 40, "default": 26, "step": 1},
            {"name": "signal", "label": "信號線 EMA", "min": 5, "max": 15, "default": 9, "step": 1},
        ],
    },
    "布林通道策略": {
        "fn": bollinger_strategy,
        "params": [
            {"name": "period", "label": "通道天數", "min": 10, "max": 40, "default": 20, "step": 1},
            {"name": "std_dev", "label": "標準差倍數", "min": 1.0, "max": 3.0, "default": 2.0, "step": 0.1},
        ],
    },
}
