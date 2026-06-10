import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

STOCKS = {
    "台股上市": {
        "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2412": "中華電信",
        "2308": "台達電", "2881": "富邦金控", "2882": "國泰金控", "3008": "大立光",
        "1301": "台塑", "1303": "南亞", "2002": "中鋼", "1101": "台泥",
        "1216": "統一", "2912": "統一超商", "2303": "聯電", "3231": "緯創",
        "2382": "廣達", "2357": "華碩", "2376": "技嘉", "3034": "聯詠",
        "4904": "遠傳電信", "3045": "台灣大哥大", "8454": "富邦媒體", "1590": "亞德客-KY",
        "2327": "國巨", "2345": "智邦", "3017": "奇鋐科技", "4915": "致伸",
        "2337": "旺宏", "2344": "華邦電", "2408": "南亞科", "2449": "京元電子",
        "2603": "長榮", "2609": "陽明", "2610": "中華航空", "2618": "長榮航空",
        "2891": "中信金控", "2886": "兆豐金控", "2884": "玉山金控", "5880": "合庫金控",
        "3037": "欣興電子", "8046": "南電", "3189": "景碩", "3711": "日月光投控",
        "6488": "環球晶圓", "3532": "台塑勝科", "3010": "華立", "2356": "英業達",
        "2353": "宏碁", "2377": "微星科技", "2395": "研華", "6415": "矽力*-KY",
        "5269": "祥碩", "3443": "創意電子", "3661": "世芯-KY", "5274": "信驊科技",
        "6649": "台光電子", "6278": "台表科", "4958": "臻鼎-KY", "8150": "南茂",
    },
    "台股上櫃": {
        "3105": "穩懋", "5483": "中美晶", "4966": "譜瑞-KY",
        "8299": "群聯", "6121": "新普", "8069": "元太科技", "8086": "宏捷科",
        "5347": "世界先進", "6732": "昇佳電子", "3218": "大學光", "6274": "台燿",
        "3227": "原相", "3374": "精材", "6182": "合晶", "6510": "精測",
        "6679": "鈺太", "6683": "雍智科技", "6719": "力智", "1785": "光洋科",
        "1815": "富喬", "3260": "威剛", "5009": "榮剛", "5905": "南仁湖",
        "8436": "大江", "4123": "晟德", "4743": "合一", "4766": "南寶",
        "4736": "泰博", "4162": "智擎", "6541": "泰福-KY", "6561": "是方",
        "6757": "台灣虎航", "6763": "綠界科技", "6805": "富世達", "6811": "宏碁資訊",
        "6854": "創威", "6861": "睿生光電", "6870": "騰雲", "6901": "鑽石投資",
        "6928": "攸泰科技",
    },
    "美股": {
        "AAPL": "蘋果", "MSFT": "微軟", "GOOGL": "谷歌", "AMZN": "亞馬遜",
        "META": "Meta", "NVDA": "輝達", "TSLA": "特斯拉", "AVGO": "博通",
        "JPM": "摩根大通", "V": "VISA", "MA": "萬事達卡", "JNJ": "嬌生",
        "WMT": "沃爾瑪", "PG": "寶鹼", "XOM": "埃克森美孚",
        "UNH": "聯合健康", "HD": "家得寶", "BAC": "美國銀行",
        "DIS": "迪士尼", "ADBE": "奧多比", "NFLX": "網飛", "CRM": "賽富時",
        "INTC": "英特爾", "AMD": "超微半導體", "COST": "好市多", "KO": "可口可樂",
        "PEP": "百事可樂", "MRK": "默克", "ABBV": "艾伯維", "TMO": "賽默飛世爾",
        "NKE": "耐吉", "ORCL": "甲骨文", "IBM": "IBM", "CSCO": "思科",
        "QCOM": "高通", "TXN": "德州儀器", "BA": "波音",
        "GE": "奇異", "CAT": "卡特彼勒", "MCD": "麥當勞",
        "SBUX": "星巴克", "UBER": "優步", "ABNB": "Airbnb", "PYPL": "PayPal",
        "SNAP": "Snap", "SNOW": "Snowflake", "PLTR": "Palantir", "DASH": "DoorDash",
    },
    "台股ETF": {
        "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息",
        "006208": "富邦台50", "00692": "富邦公司治理", "00850": "元大ESG永續",
        "00929": "復華台灣科技優息", "00919": "群益台灣精選高息",
        "00923": "群益台灣ESG低碳", "00713": "元大台灣高息低波",
        "00631L": "元大台灣50正2", "00632R": "元大台灣50反1",
        "00881": "國泰台灣5G+", "0051": "元大中型100", "00733": "富邦臺灣中小",
        "00690": "兆豐藍籌30", "00900": "富邦特選高股息30", "00922": "國泰台灣領袖50",
    },
    "美股ETF": {
        "SPY": "SPDR 標普500", "QQQ": "Invesco 納斯達克100", "VTI": "先鋒整體市場",
        "VOO": "先鋒標普500", "IVV": "iShares 核心標普500",
        "IWM": "iShares 羅素2000", "DIA": "SPDR 道瓊",
        "TLT": "iShares 20年期以上公債", "AGG": "iShares 核心美國債券",
        "BND": "先鋒總債券", "GLD": "SPDR 黃金", "SLV": "iShares 白銀",
        "VNQ": "先鋒不動產", "XLF": "金融類股",
        "XLK": "科技類股", "XLE": "能源類股",
        "XLV": "醫療保健類股", "XLI": "工業類股",
        "SMH": "費城半導體", "SOXX": "iShares 半導體",
        "ARKK": "ARK 創新", "TQQQ": "ProShares 3倍看多納指",
        "SQQQ": "ProShares 3倍放空納指", "UPRO": "ProShares 3倍看多標普",
    },
}

@st.cache_data(ttl=3600)
def get_stock_data(symbol, period="6mo"):
    if symbol.isdigit():
        sym_variants = [f"{symbol}.TW", f"{symbol}.TWO"]
    elif symbol.endswith(".TW") or symbol.endswith(".TWO"):
        sym_variants = [symbol]
    else:
        sym_variants = [symbol]
    for sym in sym_variants:
        for attempt in range(3):
            try:
                df = yf.download(sym, period=period, auto_adjust=True, progress=False)
                if not df.empty:
                    break
            except Exception:
                import time
                time.sleep(1)
                df = pd.DataFrame()
        if not df.empty:
            break
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    return df

@st.cache_data(ttl=3600)
def get_stock_info(symbol):
    if symbol.isdigit():
        sym_variants = [f"{symbol}.TW", f"{symbol}.TWO"]
    elif symbol.endswith(".TW") or symbol.endswith(".TWO"):
        sym_variants = [symbol]
    else:
        sym_variants = [symbol]
    for sym in sym_variants:
        try:
            tk = yf.Ticker(sym)
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
            continue
    return {"name": symbol}

SECTORS_TW = {
    "半導體": ["2330", "2454", "2303", "2317", "2382", "3231", "2376", "3034",
              "3037", "8046", "3189", "3711", "6488", "6649", "5269", "3443",
              "3661", "5274", "6278", "8150"],
    "金融保險": ["2881", "2882", "2891", "2886", "2884", "5880"],
    "電子零組件": ["2308", "3008", "2327", "2345", "3017", "4915",
                 "2337", "2344", "2408", "2449", "4958", "3010"],
    "電信通訊": ["2412", "4904", "3045"],
    "傳產": ["1301", "1303", "2002", "1101"],
    "航運": ["2603", "2609", "2610", "2618"],
    "電腦週邊": ["2357", "2356", "2353", "2377", "2395"],
    "消費": ["1216", "2912", "8454", "1590"],
}

SECTORS_US = {
    "科技": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AVGO",
            "INTC", "AMD", "ADBE", "CRM", "NFLX", "ORCL", "IBM", "CSCO",
            "QCOM", "TXN", "SNAP", "SNOW", "PLTR"],
    "金融": ["JPM", "V", "MA", "BAC"],
    "醫療": ["JNJ", "UNH", "MRK", "ABBV", "TMO"],
    "消費": ["WMT", "PG", "COST", "KO", "PEP", "NKE", "MCD", "SBUX", "HD"],
    "工業/能源": ["XOM", "BA", "GE", "CAT"],
    "新創科技": ["UBER", "ABNB", "PYPL", "DASH", "DIS"],
}

SECTORS_ETF = {
    "台股ETF": ["0050", "0056", "00878", "006208", "00692", "00850",
               "00929", "00919", "00923", "00713", "00881", "0051",
               "00733", "00690", "00900", "00922", "00631L", "00632R"],
    "美股ETF": ["SPY", "QQQ", "VTI", "VOO", "IVV", "IWM", "DIA",
               "ARKK", "TQQQ", "SQQQ", "UPRO"],
    "債券/商品ETF": ["TLT", "AGG", "BND", "GLD", "SLV", "VNQ"],
    "產業ETF": ["XLF", "XLK", "XLE", "XLV", "XLI", "SMH", "SOXX"],
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
