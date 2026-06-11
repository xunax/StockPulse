import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import requests
from datetime import datetime

STOCKS = {
    "?°è‚¡ä¸Šå?": {
        "2330": "?°ç???, "2317": "é´»æµ·", "2454": "?¯ç™¼ç§?, "2412": "ä¸­è¯?»ä¿¡",
        "2308": "?°é???, "2881": "å¯Œé‚¦?‘æŽ§", "2882": "?‹æ³°?‘æŽ§", "3008": "å¤§ç???,
        "1301": "?°å?", "1303": "?—ä?", "2002": "ä¸­é‹¼", "1101": "?°æ³¥",
        "1216": "çµ±ä?", "2912": "çµ±ä?è¶…å?", "2303": "?¯é›»", "3231": "ç·¯å‰µ",
        "2382": "å»??", "2357": "?¯ç¢©", "2376": "?€??, "3034": "?¯è?",
        "4904": "? å‚³?»ä¿¡", "3045": "?°ç£å¤§å“¥å¤?, "8454": "å¯Œé‚¦åª’é?", "1590": "äºžå¾·å®?KY",
        "2327": "?‹å·¨", "2345": "?ºé‚¦", "3017": "å¥‡é?ç§‘æ?", "4915": "?´ä¼¸",
        "2337": "?ºå?", "2344": "?¯é‚¦??, "2408": "?—ä?ç§?, "2449": "äº¬å??»å?",
        "2603": "?·æ¦®", "2609": "?½æ?", "2610": "ä¸­è¯?ªç©º", "2618": "?·æ¦®?ªç©º",
        "2891": "ä¸­ä¿¡?‘æŽ§", "2886": "?†è??‘æŽ§", "2884": "?‰å±±?‘æŽ§", "5880": "?ˆåº«?‘æŽ§",
        "3037": "æ¬???»å?", "8046": "?—é›»", "3189": "?¯ç¢©", "3711": "?¥æ??‰æ???,
        "6488": "?°ç??¶å?", "3532": "?°å??ç?", "3010": "?¯ç?", "2356": "?±æ¥­??,
        "2353": "å®ç?", "2377": "å¾®æ?ç§‘æ?", "2395": "?”è¯", "6415": "?½å?*-KY",
        "5269": "ç¥¥ç¢©", "3443": "?µæ??»å?", "3661": "ä¸–èŠ¯-KY", "5274": "ä¿¡é?ç§‘æ?",
        "6649": "?°å??»å?", "6278": "?°è¡¨ç§?, "4958": "?»é?-KY", "8150": "?—è?",
        "8043": "?œæ?å¯?,
    },
    "?°è‚¡ä¸Šæ?": {
        "3105": "ç©©æ?", "5483": "ä¸­ç???, "4966": "è­œç?-KY",
        "8299": "ç¾¤è¯", "6121": "?°æ™®", "8069": "?ƒå¤ªç§‘æ?", "8086": "å®æ·ç§?,
        "5347": "ä¸–ç??ˆé€?, "6732": "?‡ä½³?»å?", "3218": "å¤§å­¸??, "6274": "?°ç‡¿",
        "3227": "?Ÿç›¸", "3374": "ç²¾æ?", "6182": "?ˆæ™¶", "6510": "ç²¾æ¸¬",
        "6679": "?ºå¤ª", "6683": "?æ™ºç§‘æ?", "6719": "?›æ™º", "1785": "?‰æ?ç§?,
        "1815": "å¯Œå–¬", "3260": "å¨å?", "5009": "æ¦®å?", "5905": "?—ä?æ¹?,
        "8436": "å¤§æ?", "4123": "?Ÿå¾·", "4743": "?ˆä?", "4766": "?—å¯¶",
        "4736": "æ³°å?", "4162": "?ºæ?", "6541": "æ³°ç?-KY", "6561": "?¯æ–¹",
        "6757": "?°ç£?Žèˆª", "6763": "ç¶ ç?ç§‘æ?", "6805": "å¯Œä???, "6811": "å®ç?è³‡è?",
        "6854": "?µå?", "6861": "?¿ç??‰é›»", "6870": "é¨°é›²", "6901": "?½çŸ³?•è?",
        "6928": "?¸æ³°ç§‘æ?",
    },
    "ç¾Žè‚¡": {
        "AAPL": "AAPL", "MSFT": "MSFT", "GOOGL": "GOOGL", "AMZN": "AMZN",
        "META": "META", "NVDA": "NVDA", "TSLA": "TSLA", "AVGO": "AVGO",
        "JPM": "JPM", "V": "V", "MA": "MA", "JNJ": "JNJ",
        "WMT": "WMT", "PG": "PG", "XOM": "XOM",
        "UNH": "UNH", "HD": "HD", "BAC": "BAC",
        "DIS": "DIS", "ADBE": "ADBE", "NFLX": "NFLX", "CRM": "CRM",
        "INTC": "INTC", "AMD": "AMD", "COST": "COST", "KO": "KO",
        "PEP": "PEP", "MRK": "MRK", "ABBV": "ABBV", "TMO": "TMO",
        "NKE": "NKE", "ORCL": "ORCL", "IBM": "IBM", "CSCO": "CSCO",
        "QCOM": "QCOM", "TXN": "TXN", "BA": "BA",
        "GE": "GE", "CAT": "CAT", "MCD": "MCD",
        "SBUX": "SBUX", "UBER": "UBER", "ABNB": "ABNB", "PYPL": "PYPL",
        "SNAP": "SNAP", "SNOW": "SNOW", "PLTR": "PLTR", "DASH": "DASH",
    },
    "?°è‚¡ETF": {
        "0050": "?ƒå¤§?°ç£50", "0056": "?ƒå¤§é«˜è‚¡??, "00878": "?‹æ³°æ°¸ç?é«˜è‚¡??,
        "006208": "å¯Œé‚¦??0", "00692": "å¯Œé‚¦?¬å¸æ²»ç?", "00850": "?ƒå¤§ESGæ°¸ç?",
        "00929": "å¾©è¯?°ç£ç§‘æ??ªæ¯", "00919": "ç¾¤ç??°ç£ç²¾é¸é«˜æ¯",
        "00923": "ç¾¤ç??°ç£ESGä½Žç¢³", "00713": "?ƒå¤§?°ç£é«˜æ¯ä½Žæ³¢",
        "00631L": "?ƒå¤§?°ç£50æ­?", "00632R": "?ƒå¤§?°ç£50??",
        "00881": "?‹æ³°?°ç£5G+", "0051": "?ƒå¤§ä¸­å?100", "00733": "å¯Œé‚¦?ºç£ä¸­å?",
        "00690": "?†è??ç?30", "00900": "å¯Œé‚¦?¹é¸é«˜è‚¡??0", "00922": "?‹æ³°?°ç£?˜è?50",
    },
    "ç¾Žè‚¡ETF": {
        "SPY": "SPY", "QQQ": "QQQ", "VTI": "VTI",
        "VOO": "VOO", "IVV": "IVV",
        "IWM": "IWM", "DIA": "DIA",
        "TLT": "TLT", "AGG": "AGG",
        "BND": "BND", "GLD": "GLD", "SLV": "SLV",
        "VNQ": "VNQ", "XLF": "XLF",
        "XLK": "XLK", "XLE": "XLE",
        "XLV": "XLV", "XLI": "XLI",
        "SMH": "SMH", "SOXX": "SOXX",
        "ARKK": "ARKK", "TQQQ": "TQQQ",
        "SQQQ": "SQQQ", "UPRO": "UPRO",
    },
}

_OTC_CODES = {
    3105, 5483, 4966, 8299, 6121, 8069, 8086, 5347, 6732, 3218,
    6274, 3227, 3374, 6182, 6510, 6679, 6683, 6719, 1785, 1815,
    3260, 5009, 5905, 8436, 4123, 4743, 4766, 4736, 4162, 6541,
    6561, 6757, 6763, 6805, 6811, 6854, 6861, 6870, 6901, 6928,
}

_PERIOD_MONTHS = {"6mo": 6, "1y": 12, "2y": 24, "3y": 36, "5y": 60, "ytd": 6, "max": 60}


def _roc_to_ad(roc_str):
    parts = roc_str.split("/")
    return f"{int(parts[0]) + 1911}-{parts[1]}-{parts[2]}"


def _is_tw_stock(symbol):
    return symbol.isdigit()


def _tw_prefix(symbol):
    return "otc" if int(symbol) >= 5000 or int(symbol) in _OTC_CODES else "tse"


def _fetch_twse_realtime(symbol):
    prefix = _tw_prefix(symbol)
    try:
        resp = requests.get(
            f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={prefix}_{symbol}.tw&json=1",
            timeout=5,
        )
        if resp.status_code == 200:
            rt = resp.json()
            if rt.get("msgArray"):
                return rt["msgArray"][0]
    except:
        pass
    return None


def _fetch_twse_history(symbol, n_months=6):
    all_rows = []
    today = datetime.today()
    for i in range(n_months):
        m = today.month - i
        y = today.year
        while m < 1:
            m += 12
            y -= 1
        try:
            resp = requests.get(
                f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={y}{m:02d}01&stockNo={symbol}",
                timeout=10,
            )
            if resp.status_code == 200:
                d = resp.json()
                if d.get("stat") == "OK" and d.get("data"):
                    all_rows.extend(d["data"])
                    fields = d.get("fields", [])
        except:
            continue

    if not all_rows:
        return pd.DataFrame(), []

    fields = d.get("fields", [])
    df = pd.DataFrame(all_rows, columns=fields)
    col_map = {
        "?¥æ?": "date", "?äº¤?¡æ•¸": "volume", "?‹ç›¤??: "open",
        "?€é«˜åƒ¹": "high", "?€ä½Žåƒ¹": "low", "?¶ç›¤??: "close",
    }
    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)
    df["date"] = df["date"].apply(_roc_to_ad)
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"].astype(str).str.replace(",", ""), errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df.sort_values("date").drop_duplicates(subset="date")
    df.set_index("date", inplace=True)
    df.index = pd.to_datetime(df.index)
    cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[cols]
    return df, cols


@st.cache_data(ttl=60)
def get_stock_data(symbol, period="6mo"):
    if not _is_tw_stock(symbol):
        sym = symbol
        df = yf.download(sym, period=period, auto_adjust=True, progress=False)
        if df.empty:
            return df
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]
        return df

    n_months = _PERIOD_MONTHS.get(period, 6)
    df, cols = _fetch_twse_history(symbol, n_months)
    if df.empty:
        return df

    item = _fetch_twse_realtime(symbol)
    if item:
        z = item.get("z")
        if z and z != "-":
            today_str = datetime.today().strftime("%Y-%m-%d")
            close = float(z)
            open_p = float(item["o"]) if item.get("o", "-") != "-" else close
            high_v = float(item["h"]) if item.get("h", "-") != "-" else close
            low_v = float(item["l"]) if item.get("l", "-") != "-" else close
            vol = int(item["v"].replace(",", "")) if item.get("v", "-") != "-" else 0
            if today_str not in df.index:
                nr = pd.DataFrame(
                    [[open_p, high_v, low_v, close, vol]],
                    columns=cols,
                    index=[pd.Timestamp(today_str)],
                )
                df = pd.concat([df, nr])
            else:
                df.loc[today_str, "close"] = close
                df.loc[today_str, "high"] = max(df.loc[today_str, "high"], high_v)
                df.loc[today_str, "low"] = min(df.loc[today_str, "low"], low_v)

    return df


@st.cache_data(ttl=60)
def get_stock_info(symbol):
    if not _is_tw_stock(symbol):
        try:
            tk = yf.Ticker(symbol)
            info = tk.info
            if info and info.get("regularMarketPrice"):
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
            pass
        return {"name": symbol}

    for cat in STOCKS.values():
        if symbol in cat:
            name = cat[symbol]
            break
    else:
        name = symbol

    item = _fetch_twse_realtime(symbol)
    if item:
        z = item.get("z")
        price = float(z) if z and z != "-" else 0
        return {
            "name": name,
            "market_cap": 0,
            "pe_ratio": 0,
            "eps": 0,
            "dividend_yield": 0,
            "high_52w": 0,
            "low_52w": 0,
            "volume_avg": 0,
        }
    return {"name": name}


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
    "ç¾Žè‚¡ETF": ["SPY", "QQQ", "VTI", "VOO", "IVV", "IWM", "DIA",
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
    if df.empty or len(df) < 15:
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

