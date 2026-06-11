import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

STOCKS = {
    "?°è‚¡": {
        "2330": "?°ç???, "2317": "é´»æµ·", "2454": "?¯ç™¼ç§?, "2412": "ä¸­è¯?»ä¿¡",
        "2308": "?°é???, "2881": "å¯Œé‚¦?‘æ§", "2882": "?‹æ³°?‘æ§", "3008": "å¤§ç???,
        "1301": "?°å?", "1303": "?—ä?", "2002": "ä¸­é‹¼", "1101": "?°æ³¥",
        "1216": "çµ±ä?", "2912": "çµ±ä?è¶…å?", "2303": "?¯é›»", "3231": "ç·¯å‰µ",
        "2382": "å»??", "2357": "?¯ç¢©", "2376": "?€??, "3034": "?¯è?",
        "4904": "? å‚³?»ä¿¡", "3045": "?°ç£å¤§å“¥å¤?, "8454": "å¯Œé‚¦åª’é?", "1590": "äºå¾·å®?KY",
        "2327": "?‹å·¨", "2345": "?ºé‚¦", "3017": "å¥‡é?ç§‘æ?", "4915": "?´ä¼¸",
        "2337": "?ºå?", "2344": "?¯é‚¦??, "2408": "?—ä?ç§?, "2449": "äº¬å??»å?",
        "2603": "?·æ¦®", "2609": "?½æ?", "2610": "ä¸­è¯?ªç©º", "2618": "?·æ¦®?ªç©º",
        "2891": "ä¸­ä¿¡?‘æ§", "2886": "?†è??‘æ§", "2884": "?‰å±±?‘æ§", "5880": "?ˆåº«?‘æ§",
        "3037": "æ¬???»å?", "8046": "?—é›»", "3189": "?¯ç¢©", "3711": "?¥æ??‰æ???,
        "6488": "?°ç??¶å?", "3532": "?°å??ç?", "3010": "?¯ç?", "2356": "?±æ¥­??,
        "2353": "å®ç?", "2377": "å¾®æ?ç§‘æ?", "2395": "?”è¯", "6415": "?½å?*-KY",
        "5269": "ç¥¥ç¢©", "3443": "?µæ??»å?", "3661": "ä¸–èŠ¯-KY", "5274": "ä¿¡é?ç§‘æ?",
        "6649": "?°å??»å?", "6278": "?°è¡¨ç§?, "4958": "?»é?-KY", "8150": "?—è?",
    },
    "ç¾è‚¡": {
        "AAPL": "?‹æ?", "MSFT": "å¾®è?", "GOOGL": "è°·æ?", "AMZN": "äºé¦¬??,
        "META": "Meta", "NVDA": "è¼é?", "TSLA": "?¹æ–¯??, "AVGO": "?šé€?,
        "JPM": "?©æ ¹å¤§é€?, "V": "VISA", "MA": "?¬ä??”å¡", "JNJ": "å¬Œç?",
        "WMT": "æ²ƒçˆ¾??, "PG": "å¯¶é¹¼", "XOM": "?ƒå?æ£®ç?å­?,
        "UNH": "?¯å??¥åº·", "HD": "å®¶å?å¯?, "BAC": "ç¾å??€è¡?,
        "DIS": "è¿ªå£«å°?, "ADBE": "å¥§å?æ¯?, "NFLX": "ç¶²é?", "CRM": "è³½å???,
        "INTC": "?±ç‰¹??, "AMD": "è¶…å¾®?Šå?é«?, "COST": "å¥½å?å¤?, "KO": "?¯å£?¯æ?",
        "PEP": "?¾ä??¯æ?", "MRK": "é»˜å?", "ABBV": "?¾ä¼¯ç¶?, "TMO": "è³½é?é£›ä???,
        "NKE": "?å?", "ORCL": "?²éª¨??, "IBM": "IBM", "CSCO": "?ç?",
        "QCOM": "é«˜é€?, "TXN": "å¾·å??€??, "BA": "æ³¢éŸ³",
        "GE": "å¥‡ç•°", "CAT": "?¡ç‰¹å½¼å?", "MCD": "éº¥ç•¶??,
        "SBUX": "?Ÿå·´??, "UBER": "?ªæ­¥", "ABNB": "Airbnb", "PYPL": "PayPal",
        "SNAP": "Snap", "SNOW": "Snowflake", "PLTR": "Palantir", "DASH": "DoorDash",
    },
    "?°è‚¡ETF": {
        "0050": "?ƒå¤§?°ç£50", "0056": "?ƒå¤§é«˜è‚¡??, "00878": "?‹æ³°æ°¸ç?é«˜è‚¡??,
        "006208": "å¯Œé‚¦??0", "00692": "å¯Œé‚¦?¬å¸æ²»ç?", "00850": "?ƒå¤§ESGæ°¸ç?",
        "00929": "å¾©è¯?°ç£ç§‘æ??ªæ¯", "00919": "ç¾¤ç??°ç£ç²¾é¸é«˜æ¯",
        "00923": "ç¾¤ç??°ç£ESGä½ç¢³", "00713": "?ƒå¤§?°ç£é«˜æ¯ä½æ³¢",
        "00631L": "?ƒå¤§?°ç£50æ­?", "00632R": "?ƒå¤§?°ç£50??",
        "00881": "?‹æ³°?°ç£5G+", "0051": "?ƒå¤§ä¸­å?100", "00733": "å¯Œé‚¦?ºç£ä¸­å?",
        "00690": "?†è??ç?30", "00900": "å¯Œé‚¦?¹é¸é«˜è‚¡??0", "00922": "?‹æ³°?°ç£?˜è?50",
    },
    "ç¾è‚¡ETF": {
        "SPY": "SPDR æ¨™æ™®500", "QQQ": "Invesco ç´æ–¯?”å?100", "VTI": "?ˆé??´é?å¸‚å ´",
        "VOO": "?ˆé?æ¨™æ™®500", "IVV": "iShares ?¸å?æ¨™æ™®500",
        "IWM": "iShares ç¾…ç?2000", "DIA": "SPDR ?“ç?",
        "TLT": "iShares 20å¹´æ?ä»¥ä??¬å‚µ", "AGG": "iShares ?¸å?ç¾å??µåˆ¸",
        "BND": "?ˆé?ç¸½å‚µ??, "GLD": "SPDR é»ƒé?", "SLV": "iShares ?½é?",
        "VNQ": "?ˆé?ä¸å???, "XLF": "?‘è?é¡è‚¡",
        "XLK": "ç§‘æ?é¡è‚¡", "XLE": "?½æ?é¡è‚¡",
        "XLV": "?«ç?ä¿å¥é¡è‚¡", "XLI": "å·¥æ¥­é¡è‚¡",
        "SMH": "è²»å??Šå?é«?, "SOXX": "iShares ?Šå?é«?,
        "ARKK": "ARK ?µæ–°", "TQQQ": "ProShares 3?ç?å¤šç???,
        "SQQQ": "ProShares 3?æ”¾ç©ºç???, "UPRO": "ProShares 3?ç?å¤šæ???,
    },
}

@st.cache_data(ttl=60)
def get_stock_data(symbol, period="6mo"):
    if symbol.isdigit() or symbol.endswith(".TW"):
        sym = f"{symbol}.TW" if not symbol.endswith(".TW") else symbol
    else:
        sym = symbol
    df = yf.download(sym, period=period, auto_adjust=True, progress=False)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    return df

@st.cache_data(ttl=60)
def get_stock_info(symbol):
    sym = f"{symbol}.TW" if symbol.isdigit() else symbol
    try:
        tk = yf.Ticker(sym)
        info = tk.info
        return {
            "name": info.get("longName", info.get("shortName", symbol)),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "eps": info.get("trailingEps", 0),
            "dividend_yield": info.get("dividendYield", 0),
            "high_52w": info.get("fiftyTwoWeekHigh", 0),
            "low_52w": info.get("fiftyTwoWeekLow", 0),
            "volume_avg": info.get("averageVolume", 0),
        }
    except:
        return {"name": symbol}

SECTORS_TW = {
    "?Šå?é«?: ["2330", "2454", "2303", "2317", "2382", "3231", "2376", "3034",
              "3037", "8046", "3189", "3711", "6488", "6649", "5269", "3443",
              "3661", "5274", "6278", "8150"],
    "?‘è?ä¿éšª": ["2881", "2882", "2891", "2886", "2884", "5880"],
    "?»å??¶ç?ä»?: ["2308", "3008", "2327", "2345", "3017", "4915",
                 "2337", "2344", "2408", "2449", "4958", "3010"],
    "?»ä¿¡?šè?": ["2412", "4904", "3045"],
    "?³ç”¢": ["1301", "1303", "2002", "1101"],
    "?ªé?": ["2603", "2609", "2610", "2618"],
    "?»è…¦?±é?": ["2357", "2356", "2353", "2377", "2395"],
    "æ¶ˆè²»": ["1216", "2912", "8454", "1590"],
}

SECTORS_US = {
    "ç§‘æ?": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AVGO",
            "INTC", "AMD", "ADBE", "CRM", "NFLX", "ORCL", "IBM", "CSCO",
            "QCOM", "TXN", "SNAP", "SNOW", "PLTR"],
    "?‘è?": ["JPM", "V", "MA", "BAC"],
    "?«ç?": ["JNJ", "UNH", "MRK", "ABBV", "TMO"],
    "æ¶ˆè²»": ["WMT", "PG", "COST", "KO", "PEP", "NKE", "MCD", "SBUX", "HD"],
    "å·¥æ¥­/?½æ?": ["XOM", "BA", "GE", "CAT"],
    "?°å‰µç§‘æ?": ["UBER", "ABNB", "PYPL", "DASH", "DIS"],
}

SECTORS_ETF = {
    "?°è‚¡ETF": ["0050", "0056", "00878", "006208", "00692", "00850",
               "00929", "00919", "00923", "00713", "00881", "0051",
               "00733", "00690", "00900", "00922", "00631L", "00632R"],
    "ç¾è‚¡ETF": ["SPY", "QQQ", "VTI", "VOO", "IVV", "IWM", "DIA",
               "ARKK", "TQQQ", "SQQQ", "UPRO"],
    "?µåˆ¸/?†å?ETF": ["TLT", "AGG", "BND", "GLD", "SLV", "VNQ"],
    "?¢æ¥­ETF": ["XLF", "XLK", "XLE", "XLV", "XLI", "SMH", "SOXX"],
}

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_bollinger(series, period=20, std_dev=2):
    ma = series.rolling(window=period).mean()
    sd = series.rolling(window=period).std()
    upper = ma + std_dev * sd
    lower = ma - std_dev * sd
    return ma, upper, lower

def calc_all_indicators(df, rsi_period=14, bb_period=20, bb_std=2, kd_period=14):
    if df.empty or len(df) < 50:
        return df

    df["ma5"] = df["close"].rolling(5).mean()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()
    df["ma120"] = df["close"].rolling(120).mean()

    df["rsi"] = calc_rsi(df["close"], period=rsi_period)
    df["macd"], df["macd_signal"], df["macd_hist"] = calc_macd(df["close"])
    df["bb_mid"], df["bb_upper"], df["bb_lower"] = calc_bollinger(df["close"], period=bb_period, std_dev=bb_std)

    df["volume_ma5"] = df["volume"].rolling(5).mean()

    df["stoch_k"] = ((df["close"] - df["low"].rolling(kd_period).min()) /
                     (df["high"].rolling(kd_period).max() - df["low"].rolling(kd_period).min())) * 100
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    return df

