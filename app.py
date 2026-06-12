import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils import get_stock_data, get_stock_info, calc_all_indicators, STOCKS, SECTORS_TW, SECTORS_US, SECTORS_ETF
from charts import plot_candlestick, plot_volume_profile
from backtest import backtest, format_metrics, Action
from strategies import STRATEGIES
import auth
import database as db

st.set_page_config(
    page_title="股票分析系統",
    page_icon="📈",
    layout="wide",
)

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "PingFang TC", "Heiti TC", "Noto Sans TC", "Source Han Sans TC", "Microsoft YaHei", "SimHei", sans-serif;
    }
    .main > div { padding: 0 1rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 20px; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
    [data-baseweb="select"] { font-family: "Microsoft JhengHei", "PingFang TC", "Heiti TC", "Noto Sans TC", sans-serif !important; }

    /* ─── 手機版響應式 ─── */
    @media (max-width: 768px) {
        /* 縮小整體 padding */
        .block-container { padding: 1rem 0.5rem !important; }

        /* 標題縮小 */
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }

        /* Metric 卡片改為橫排 */
        [data-testid="stMetric"] {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 8px 12px !important;
            margin-bottom: 4px;
        }
        div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
        div[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }

        /* Tabs 改為可捲動 */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        .stTabs [data-baseweb="tab"] {
            padding: 6px 12px !important;
            font-size: 0.8rem !important;
            white-space: nowrap;
            min-width: auto !important;
        }

        /* Sidebar 在手機上收合 */
        section[data-testid="stSidebar"] {
            width: 85vw !important;
            min-width: 85vw !important;
        }

        /* 按鈕全寬 */
        .stButton > button { width: 100%; }

        /* DataFrame 表格字型縮小 */
        .stDataFrame { font-size: 0.75rem !important; }

        /* Plotly 圖表高度調整 */
        .stPlotlyChart { height: auto !important; }

        /* Radio / Checkbox 橫向排列 */
        .stRadio > div { flex-wrap: wrap; }
        .stMultiSelect > div { font-size: 0.85rem; }

        /* Expander 內文字型 */
        .streamlit-expanderContent { font-size: 0.85rem !important; }
    }

    @media (max-width: 480px) {
        h1 { font-size: 1.2rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1rem !important; }
        .stTabs [data-baseweb="tab"] { font-size: 0.7rem !important; padding: 4px 8px !important; }
    }
</style>
""", unsafe_allow_html=True)

# ─── 登入系統 ───
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""

if st.session_state.get("supabase_session") and not st.session_state["logged_in"]:
    auth.restore_session_from_state()
    if st.session_state.get("username"):
        st.session_state["logged_in"] = True

if not st.session_state["logged_in"]:
    st.title("📈 股票技術分析與回測系統")

    login_tab, register_tab = st.tabs(["🔑 登入", "📝 註冊"])

    with login_tab:
        login_user = st.text_input("帳號", key="login_user")
        login_pass = st.text_input("密碼", type="password", key="login_pass")
        if st.button("登入", type="primary", use_container_width=True, key="btn_login"):
            if login_user and login_pass:
                ok, msg = auth.login(login_user, login_pass)
                if ok:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = login_user
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("請輸入帳號和密碼")

    with register_tab:
        reg_user = st.text_input("帳號（至少 2 個字元）", key="reg_user")
        reg_pass = st.text_input("密碼（至少 4 個字元）", type="password", key="reg_pass")
        reg_pass2 = st.text_input("確認密碼", type="password", key="reg_pass2")
        if st.button("註冊", type="primary", use_container_width=True, key="btn_register"):
            if reg_user and reg_pass:
                if reg_pass != reg_pass2:
                    st.error("兩次密碼不一致")
                else:
                    ok, msg = auth.register(reg_user, reg_pass)
                    if ok:
                        st.success(msg + "，請登入")
                    else:
                        st.error(msg)
            else:
                st.warning("請輸入帳號和密碼")

    st.stop()

# ─── 已登入 ───
with st.sidebar:
    st.markdown(f"👤 **{st.session_state['username']}**")
    if st.button("🚪 登出", key="btn_logout"):
        auth.logout()
        st.rerun()

st.title("📈 股票技術分析與回測系統")

# ─── Sidebar ───
with st.sidebar:
    st.header("📊 參數設定")

    color_theme = st.radio("漲跌配色", ["紅漲綠跌 (台股)", "綠漲紅跌 (美股)"], horizontal=True, key="color_theme")
    if color_theme == "紅漲綠跌 (台股)":
        up_color = "#ef5350"
        down_color = "#26a69a"
    else:
        up_color = "#26a69a"
        down_color = "#ef5350"

    input_mode = st.radio("輸入方式", ["下拉選擇", "手動輸入"], horizontal=True, key="input_mode")

    if input_mode == "下拉選擇":
        cat = st.selectbox("分類", list(STOCKS.keys()), key="cat")
        stock_options = STOCKS[cat]
        code_list = list(stock_options.keys())
        if "stock_select" not in st.session_state or st.session_state.stock_select not in code_list:
            st.session_state.stock_select = code_list[0]
        symbol = st.selectbox(
            "選擇標的",
            code_list,
            key="stock_select",
            format_func=lambda c: stock_options[c],
        )
        stock_name = stock_options[symbol]
    else:
        symbol = st.text_input("股票代碼", "2330", key="manual_symbol").strip()
        stock_name = symbol

    period_map = {
        "1 個月": "1mo", "3 個月": "3mo", "6 個月": "6mo",
        "1 年": "1y", "2 年": "2y", "5 年": "5y",
    }
    period_label = st.selectbox("資料區間", list(period_map.keys()), index=3, key="period")
    period = period_map[period_label]

    with st.expander("🔧 技術指標", expanded=True):
        show_ma5 = st.checkbox("5日均線", True, key="ma5")
        show_ma10 = st.checkbox("10日均線", True, key="ma10")
        show_ma20 = st.checkbox("20日均線", True, key="ma20")
        show_ma60 = st.checkbox("60日均線", False, key="ma60")
        show_ma120 = st.checkbox("120日均線", False, key="ma120")
        show_bb = st.checkbox("布林通道", True, key="bb")
        show_kd = st.checkbox("KD 指標", True, key="kd")
        show_volume_profile = st.checkbox("成交量分布圖", False, key="vp")

    with st.expander("⚙️ 指標參數", expanded=False):
        rsi_period = st.slider("RSI 天數", 6, 30, 14, key="rsi_period")
        bb_period = st.slider("布林天數", 10, 40, 20, key="bb_period")
        bb_std = st.slider("布林標準差", 1.0, 3.0, 2.0, 0.1, key="bb_std")
        kd_period = st.slider("KD 天數", 5, 30, 14, key="kd_period")

    with st.expander("🔄 回測設定", expanded=False):
        strategy_name = st.selectbox("交易策略", list(STRATEGIES.keys()), key="strategy")
        bt_initial = st.number_input("初始資金", 100000, 10000000, 1000000, step=100000, key="bt_init")
        strategy_info = STRATEGIES[strategy_name]
        for p in strategy_info["params"]:
            st.slider(p["label"], p["min"], p["max"], p["default"], step=p["step"], key=f"sp_{p['name']}")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 技術分析", "💰 回測系統", "📋 原始資料", "📈 多股對比", "🏛️ 主力動向", "🔔 持股監控"])

# ─── Load data ───
with st.spinner("載入資料中..."):
    df = get_stock_data(symbol, period)
    info = get_stock_info(symbol)

if df.empty:
    st.error("無法取得股票資料，請確認代碼是否正確")
    st.stop()

df = calc_all_indicators(df, rsi_period=rsi_period, bb_period=bb_period, bb_std=bb_std, kd_period=kd_period)

# ═══════════════════════════════════════
# TAB 1: 技術分析
# ═══════════════════════════════════════
with tab1:
    if "redirect_stock" in st.session_state and st.session_state["redirect_stock"]:
        r_name = st.session_state.get("redirect_name", "")
        r_code = st.session_state["redirect_stock"]
        st.success(f"已從主力動向分析導向至 **{r_name}({r_code})** 的技術分析頁面")
        st.session_state["redirect_stock"] = None

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    chg = latest["close"] - prev["close"]
    chg_pct = chg / prev["close"] * 100

    all_stocks = {k: v for cat in STOCKS.values() for k, v in cat.items()}
    stock_display_name = all_stocks.get(symbol, symbol)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(f"### 📌 {stock_display_name} ({symbol})")
    st.caption(f"最後更新 {now_str} · 資料來源 Yahoo Finance，價格可能延遲15-20分鐘")

    col1, col2, col3, col4, col5 = st.columns(5)
    price_color = up_color if chg >= 0 else down_color
    col1.markdown(f"**現價**<br><span style='font-size:1.5em;color:{price_color}'>{latest['close']:.2f}</span><br><small style='color:{price_color}'>{chg:+.2f} ({chg_pct:+.2f}%)</small>", unsafe_allow_html=True)
    col2.markdown(f"**開盤**<br><span style='font-size:1.3em'>{latest['open']:.2f}</span>", unsafe_allow_html=True) 
    col3.markdown(f"**最高**<br><span style='font-size:1.3em;color:{up_color}'>{latest['high']:.2f}</span>", unsafe_allow_html=True)
    col4.markdown(f"**最低**<br><span style='font-size:1.3em;color:{down_color}'>{latest['low']:.2f}</span>", unsafe_allow_html=True)
    col5.markdown(f"**成交量**<br><span style='font-size:1.3em'>{latest['volume']:,.0f}</span>", unsafe_allow_html=True)

    if info and info.get("pe_ratio"):
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**本益比**<br>{info['pe_ratio']:.2f}" if info['pe_ratio'] else "**本益比**<br>N/A", unsafe_allow_html=True)
        c2.markdown(f"**EPS**<br>{info['eps']:.2f}" if info['eps'] else "**EPS**<br>N/A", unsafe_allow_html=True)
        dy_val = info['dividend_yield'] * 100 if info['dividend_yield'] < 1 else info['dividend_yield']
        c3.markdown(f"**殖利率**<br>{dy_val:.2f}%" if info['dividend_yield'] else "**殖利率**<br>N/A", unsafe_allow_html=True)
        c4.markdown(f"**市值**<br>{info['market_cap']/1e8:.1f}億" if info['market_cap'] else "**市值**<br>N/A", unsafe_allow_html=True)

    # ─── 預先定義評分所需變數 ───
    close = float(latest["close"])
    vol = float(latest["volume"])
    rsi_val = float(latest["rsi"]) if "rsi" in latest and not pd.isna(latest["rsi"]) else None
    ma5_val = float(latest["ma5"]) if "ma5" in latest and not pd.isna(latest["ma5"]) else None
    ma10_val = float(latest["ma10"]) if "ma10" in latest and not pd.isna(latest["ma10"]) else None
    ma20_val = float(latest["ma20"]) if "ma20" in latest and not pd.isna(latest["ma20"]) else None
    ma60_val = float(latest["ma60"]) if "ma60" in latest and not pd.isna(latest["ma60"]) else None
    ma120_val = float(latest["ma120"]) if "ma120" in latest and not pd.isna(latest["ma120"]) else None

    # 一句話結論
    if ma5_val is not None and ma20_val is not None and rsi_val is not None:
        if ma5_val > ma20_val and rsi_val > 50:
            verdict = f"🟢 整體偏多 — 短均線在長均線之上，RSI {rsi_val:.1f} 偏多區"
        elif ma5_val < ma20_val and rsi_val < 50:
            verdict = f"🔴 整體偏空 — 短均線在長均線之下，RSI {rsi_val:.1f} 偏空區"
        elif ma5_val > ma20_val and rsi_val < 50:
            verdict = f"🟡 短多但動能不足 — 均線偏多，但 RSI {rsi_val:.1f} 中性偏弱"
        elif ma5_val < ma20_val and rsi_val > 50:
            verdict = f"🟡 短空但醞釀反彈 — 均線偏空，但 RSI {rsi_val:.1f} 脫離弱勢區"
        else:
            verdict = "⚪ 方向不明 — 多空指標分歧"
        st.info(verdict)

    if info and info.get("high_52w") and info.get("low_52w"):
        high_52w = info["high_52w"]
        low_52w = info["low_52w"]
        cur_price = float(latest["close"])
        if high_52w > low_52w:
            pct_52w = (cur_price - low_52w) / (high_52w - low_52w) * 100
            pct_52w = max(0, min(100, pct_52w))
            bar_color = up_color if pct_52w >= 50 else down_color
            # 背景色隨主題切換
            theme = st.session_state.get("color_theme", "紅漲綠跌 (台股)")
            bg_color = "#333333" if theme == "紅漲綠跌 (台股)" else "#444444"
            st.markdown(f"""
**📊 52 週股價區間**
<div style="background:{bg_color};border-radius:8px;padding:4px 0;width:100%;position:relative;height:24px;border:1px solid #555;">
  <div style="background:{bar_color};width:{pct_52w:.1f}%;height:100%;border-radius:8px;opacity:0.9;"></div>
  <span style="position:absolute;top:50%;left:0;transform:translateY(-50%);padding-left:8px;font-size:0.8em;color:#ccc;">低 {low_52w:.2f}</span>
  <span style="position:absolute;top:50%;right:0;transform:translateY(-50%);padding-right:8px;font-size:0.8em;color:#ccc;">高 {high_52w:.2f}</span>
  <span style="position:absolute;top:50%;left:{pct_52w:.1f}%;transform:translate(-50%,-50%);font-size:0.75em;color:#fff;background:rgba(0,0,0,0.7);padding:2px 6px;border-radius:4px;">{cur_price:.2f} ({pct_52w:.0f}%)</span>
</div>
""", unsafe_allow_html=True)

    bb_u = float(latest["bb_upper"]) if "bb_upper" in latest and not pd.isna(latest["bb_upper"]) else None
    bb_l = float(latest["bb_lower"]) if "bb_lower" in latest and not pd.isna(latest["bb_lower"]) else None
    vol_ma5 = float(latest["volume_ma5"]) if "volume_ma5" in latest and not pd.isna(latest["volume_ma5"]) else None
    stoch_k = float(latest["stoch_k"]) if "stoch_k" in latest and not pd.isna(latest["stoch_k"]) else None
    stoch_d = float(latest["stoch_d"]) if "stoch_d" in latest and not pd.isna(latest["stoch_d"]) else None

    # ─── 短期評分（當沖 / 波段 1~10 天）───
    s_score = 0
    s_reasons = []

    # 1. RSI 短線超買超賣
    if rsi_val is not None:
        if rsi_val > 80:
            s_score -= 15
            s_reasons.append(f"⚠️ RSI = {rsi_val:.1f}，嚴重超買，短期回檔機率極高")
        elif rsi_val > 70:
            s_score -= 10
            s_reasons.append(f"⚠️ RSI = {rsi_val:.1f}，超買，短线不宜追高")
        elif rsi_val > 55:
            s_score += 10
            s_reasons.append(f"✅ RSI = {rsi_val:.1f}，多頭動能充足")
        elif rsi_val > 40:
            s_score += 5
            s_reasons.append(f"✅ RSI = {rsi_val:.1f}，中性偏多")
        elif rsi_val < 25:
            s_score -= 5
            s_reasons.append(f"⚠️ RSI = {rsi_val:.1f}，超賣，可能有反彈但需確認")
        elif rsi_val < 35:
            s_score += 5
            s_reasons.append(f"✅ RSI = {rsi_val:.1f}，低檔區，可觀察反彈訊號")

    # 2. 成交量異動
    if vol_ma5 is not None and vol_ma5 > 0:
        vol_ratio = vol / vol_ma5
        if vol_ratio > 2.5 and chg > 0:
            s_score += 15
            s_reasons.append(f"✅ 量能爆發（{vol_ratio:.1f} 倍）且上漲，短線強勢表態")
        elif vol_ratio > 2.0 and chg < 0:
            s_score -= 15
            s_reasons.append(f"⚠️ 量增價跌（{vol_ratio:.1f} 倍），主力大量出貨")
        elif vol_ratio > 1.5 and chg > 0:
            s_score += 10
            s_reasons.append(f"✅ 量增價漲（{vol_ratio:.1f} 倍），短線動能強")
        elif vol_ratio > 1.5 and chg < 0:
            s_score -= 5
            s_reasons.append(f"⚠️ 量增價跌（{vol_ratio:.1f} 倍），賣壓湧現")
        elif vol_ratio < 0.5:
            s_reasons.append(f"ℹ️ 成交量萎縮（{vol_ratio:.1f} 倍），短線方向不明")

    # 3. 近 5 日漲跌幅（短線過熱）
    if len(df) >= 6:
        five_day_chg = (close - float(df.iloc[-6]["close"])) / float(df.iloc[-6]["close"]) * 100
        if five_day_chg > 15:
            s_score -= 15
            s_reasons.append(f"⚠️ 近 5 日暴漲 {five_day_chg:.1f}%，嚴重過熱")
        elif five_day_chg > 8:
            s_score -= 5
            s_reasons.append(f"⚠️ 近 5 日上漲 {five_day_chg:.1f}%，漲幅偏大")
        elif five_day_chg > 2:
            s_score += 10
            s_reasons.append(f"✅ 近 5 日溫和上漲 {five_day_chg:.1f}%，趨勢健康")
        elif five_day_chg < -10:
            s_score -= 5
            s_reasons.append(f"⚠️ 近 5 日大跌 {five_day_chg:.1f}%，短線偏弱")
        elif five_day_chg < -3:
            s_score += 5
            s_reasons.append(f"✅ 近 5 日回檔 {five_day_chg:.1f}%，可觀察反彈")

    # 4. KD 短線
    if stoch_k is not None and stoch_d is not None:
        if stoch_k > 85 and stoch_d > 80:
            s_score -= 10
            s_reasons.append(f"⚠️ KD（K={stoch_k:.1f}）超買區，短線回檔風險高")
        elif stoch_k < 20 and stoch_d < 25:
            s_score += 10
            s_reasons.append(f"✅ KD（K={stoch_k:.1f}）超賣區，短線反彈機會")
        if stoch_k > stoch_d and stoch_k < 50:
            s_score += 5
            s_reasons.append("✅ KD 黃金交叉且低位，短線轉多")
        elif stoch_k < stoch_d and stoch_k > 50:
            s_score -= 5
            s_reasons.append("⚠️ KD 死亡交叉且高位，短線轉空")

    # 5. BB 短線位置
    if bb_u is not None and bb_l is not None:
        bb_width = bb_u - bb_l
        if bb_width > 0:
            bb_pos = (close - bb_l) / bb_width
            if bb_pos > 0.95:
                s_score -= 10
                s_reasons.append("⚠️ 觸及布林上軌，短線超漲")
            elif bb_pos > 0.8:
                s_score += 5
                s_reasons.append("✅ 強勢區，接近上軌")
            elif bb_pos < 0.05:
                s_score -= 5
                s_reasons.append("⚠️ 觸及布林下軌，短線超賣")
            elif bb_pos < 0.2:
                s_score += 5
                s_reasons.append("✅ 弱勢區接近下軌，可能反彈")

    # 6. 均線短線排列
    if ma5_val is not None and ma10_val is not None:
        if ma5_val > ma10_val:
            s_score += 5
            s_reasons.append("✅ MA5 > MA10，短線多頭排列")
        else:
            s_score -= 5
            s_reasons.append("⚠️ MA5 < MA10，短線空頭排列")

    # ─── 長期評分（存股 / 波段 1~6 個月）───
    l_score = 0
    l_reasons = []

    # 1. 52 週高低點位置
    if info and info.get("high_52w") and info.get("low_52w"):
        h52 = float(info["high_52w"])
        l52 = float(info["low_52w"])
        if h52 > l52:
            pos = (close - l52) / (h52 - l52)
            if pos >= 0.85:
                l_score -= 20
                l_reasons.append(f"⚠️ 股價在 52 週高點 {pos*100:.0f}% 位置，長期追高風險大")
            elif pos >= 0.6:
                l_score += 5
                l_reasons.append(f"✅ 股價在 52 週中高段（{pos*100:.0f}%），趨勢明確")
            elif pos >= 0.3:
                l_score += 15
                l_reasons.append(f"✅ 股價在 52 週中低段（{pos*100:.0f}%），長期佈局空間大")
            else:
                l_score += 10
                l_reasons.append(f"✅ 股價在 52 週低位（{pos*100:.0f}%），有估值修復空間")

    # 2. 均線長期排列（多頭/空頭）
    if ma20_val is not None and ma60_val is not None:
        if ma20_val > ma60_val:
            l_score += 10
            l_reasons.append("✅ MA20 > MA60，中期趨勢向上")
        else:
            l_score -= 10
            l_reasons.append("⚠️ MA20 < MA60，中期趨勢向下")

    if ma60_val is not None and ma120_val is not None:
        if ma60_val > ma120_val:
            l_score += 10
            l_reasons.append("✅ MA60 > MA120，長期趨勢向上")
        else:
            l_score -= 10
            l_reasons.append("⚠️ MA60 < MA120，長期趨勢偏空")

    # 3. 價格 vs 均線乖離率
    if ma20_val is not None:
        diff20 = (close - ma20_val) / ma20_val * 100
        if diff20 > 15:
            l_score -= 10
            l_reasons.append(f"⚠️ 股價高於 MA20 達 {diff20:.1f}%，乖離過大，回檔風險高")
        elif diff20 > 5:
            l_score += 5
            l_reasons.append(f"✅ 股價在 MA20 之上 {diff20:.1f}%，均線多頭")
        elif diff20 < -15:
            l_score -= 5
            l_reasons.append(f"⚠️ 股價低於 MA20 達 {diff20:.1f}%，偏弱")
        elif diff20 < -5:
            l_reasons.append(f"ℹ️ 股價低於 MA20 {diff20:.1f}%，均線空頭，等待止跌")

    if ma60_val is not None:
        diff60 = (close - ma60_val) / ma60_val * 100
        if diff60 > 25:
            l_score -= 15
            l_reasons.append(f"⚠️ 股價高於 MA60 達 {diff60:.1f}%，嚴重超漲")
        elif diff60 > 10:
            l_score += 5
            l_reasons.append(f"✅ 中期趨勢向上（高於 MA60 {diff60:.1f}%）")
        elif diff60 < -15:
            l_score -= 10
            l_reasons.append(f"⚠️ 股價低於 MA60 達 {diff60:.1f}%，中期偏弱")

    # 4. 本益比
    if info and info.get("pe_ratio") and info["pe_ratio"] > 0:
        pe = info["pe_ratio"]
        if pe < 12:
            l_score += 10
            l_reasons.append(f"✅ 本益比 {pe:.1f} 倍，估值偏低，長期投資價值高")
        elif pe < 20:
            l_score += 5
            l_reasons.append(f"✅ 本益比 {pe:.1f} 倍，估值合理")
        elif pe > 40:
            l_score -= 10
            l_reasons.append(f"⚠️ 本益比 {pe:.1f} 倍，估值偏高")
        elif pe > 25:
            l_score -= 5
            l_reasons.append(f"⚠️ 本益比 {pe:.1f} 倍，估值偏高")

    # 5. 殖利率
    if info and info.get("dividend_yield") and info["dividend_yield"] > 0:
        dy = info["dividend_yield"] * 100
        if dy > 5:
            l_score += 10
            l_reasons.append(f"✅ 殖利率 {dy:.2f}%，存股收益佳")
        elif dy > 3:
            l_score += 5
            l_reasons.append(f"✅ 殖利率 {dy:.2f}%，穩定配息")
        elif dy < 1:
            l_reasons.append(f"ℹ️ 殖利率 {dy:.2f}%，配息偏低")

    # 6. 長期波動（年化波動率）
    if len(df) >= 60:
        returns = df["close"].pct_change().dropna()
        annual_vol = float(returns.std() * np.sqrt(252) * 100)
        if annual_vol < 15:
            l_score += 5
            l_reasons.append(f"✅ 年化波動率 {annual_vol:.1f}%，波動低適合存股")
        elif annual_vol > 50:
            l_score -= 5
            l_reasons.append(f"⚠️ 年化波動率 {annual_vol:.1f}%，波動大需注意風險")
        else:
            l_reasons.append(f"ℹ️ 年化波動率 {annual_vol:.1f}%，波動適中")

    # ─── 顯示結果（雙欄）───
    def get_verdict(score):
        if score >= 20:
            return "🟢 技術面強勢", "#26a69a"
        elif score >= 10:
            return "🟢 技術面偏多", "#26a69a"
        elif score >= 0:
            return "🟡 技術面中性", "#FF9800"
        elif score >= -15:
            return "🔴 技術面偏空", "#ef5350"
        else:
            return "🔴 技術面弱勢", "#ef5350"

    s_verdict, s_color = get_verdict(s_score)
    l_verdict, l_color = get_verdict(l_score)

    col_s, col_l = st.columns(2)
    with col_s:
        st.markdown(f"""
<div style="background:#1a1a2e;border:2px solid {s_color};border-radius:12px;padding:16px 20px;margin:12px 0;">
  <div style="font-size:1.1em;font-weight:bold;color:{s_color};margin-bottom:4px;">⚡ 短期（當沖/波段）</div>
  <div style="font-size:1.0em;color:{s_color};margin-bottom:4px;">{s_verdict}</div>
  <div style="font-size:0.85em;color:#aaa;">綜合評分：<b style="color:#fff">{s_score}</b> 分</div>
</div>
""", unsafe_allow_html=True)
        with st.expander("📋 短期評估項目", expanded=False):
            for r in s_reasons:
                st.markdown(f"- {r}")

    with col_l:
        st.markdown(f"""
<div style="background:#1a1a2e;border:2px solid {l_color};border-radius:12px;padding:16px 20px;margin:12px 0;">
  <div style="font-size:1.1em;font-weight:bold;color:{l_color};margin-bottom:4px;">📅 長期（存股/波段）</div>
  <div style="font-size:1.0em;color:{l_color};margin-bottom:4px;">{l_verdict}</div>
  <div style="font-size:0.85em;color:#aaa;">綜合評分：<b style="color:#fff">{l_score}</b> 分</div>
</div>
""", unsafe_allow_html=True)
        with st.expander("📋 長期評估項目", expanded=False):
            for r in l_reasons:
                st.markdown(f"- {r}")

    # K線圖
    indicators = []
    if show_ma5: indicators.append("ma5")
    if show_ma10: indicators.append("ma10")
    if show_ma20: indicators.append("ma20")
    if show_ma60: indicators.append("ma60")
    if show_ma120: indicators.append("ma120")

    fig = plot_candlestick(df, stock_display_name, indicators + ["volume", "rsi", "macd", "kd"], up_color=up_color, down_color=down_color)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key=f"kline_{symbol}_{period}", config={"scrollZoom": True})

    # 指標註解區
    macd_val = float(latest["macd"]) if "macd" in latest and not pd.isna(latest["macd"]) else None
    macd_sig = float(latest["macd_signal"]) if "macd_signal" in latest and not pd.isna(latest["macd_signal"]) else None
    macd_hist = float(latest["macd_hist"]) if "macd_hist" in latest and not pd.isna(latest["macd_hist"]) else None
    ma5_val = float(latest["ma5"]) if "ma5" in latest and not pd.isna(latest["ma5"]) else None
    ma10_val = float(latest["ma10"]) if "ma10" in latest and not pd.isna(latest["ma10"]) else None
    stoch_k = float(latest["stoch_k"]) if "stoch_k" in latest and not pd.isna(latest["stoch_k"]) else None
    stoch_d = float(latest["stoch_d"]) if "stoch_d" in latest and not pd.isna(latest["stoch_d"]) else None
    recent_20 = df.tail(20)
    resistance = float(recent_20["high"].max())
    support = float(recent_20["low"].min())

    st.markdown("### 📖 指標完整解讀")

    with st.expander("🔵 K線（蠟燭圖）— 最基本的看盤工具", expanded=True):
        st.markdown(f"""
- 每根 K 線代表一天的四個價位：**開盤 / 最高 / 最低 / 收盤**
- 🔴 紅色 K 線：**收盤 > 開盤**（當天上漲）
- 🟢 綠色 K 線：**收盤 < 開盤**（當天下跌）
- 上下「影線」代表當天曾經到過的最高和最低價
- **長紅 K 線 + 大量**：買方力道強，未來可能繼續上漲
- **長綠 K 線 + 大量**：賣方力道強，未來可能繼續下跌
- **十字星（上下影線都很長）**：多空交戰，方向不明，觀望為主
- 當前收盤：**{close:.2f}**，距離近 20 日高點 {resistance:.2f} {(resistance-close):.2f}，距離低點 {support:.2f} {(close-support):.2f}
""")

    with st.expander("📈 均線（MA）— 判斷趨勢方向", expanded=True):
        ma_texts = []
        if ma5_val is not None and ma20_val is not None:
            if ma5_val > ma20_val:
                ma_texts.append(f"✅ **5日({ma5_val:.1f}) > 20日({ma20_val:.1f})** — 短線偏多")
            else:
                ma_texts.append(f"⚠️ **5日({ma5_val:.1f}) < 20日({ma20_val:.1f})** — 短線偏空")
        if ma20_val is not None and ma60_val is not None:
            if ma20_val > ma60_val:
                ma_texts.append(f"✅ **20日({ma20_val:.1f}) > 60日({ma60_val:.1f})** — 中期趨勢向上")
            else:
                ma_texts.append(f"⚠️ **20日({ma20_val:.1f}) < 60日({ma60_val:.1f})** — 中期趨勢向下")
        if ma5_val is not None and ma10_val is not None and ma20_val is not None:
            prices = sorted([(ma5_val, "5日"), (ma10_val, "10日"), (ma20_val, "20日")], reverse=True)
            order_text = " > ".join([f"{n}({v:.1f})" for v, n in prices])
            ma_texts.append(f"📊 均線排列：**{order_text}**（由上而下 = 多頭排列 / 由下而上 = 空頭排列）")

        st.markdown(f"""
**均線是什麼**：把過去 N 天的收盤價平均後畫成的線，N 越小越敏感、越大越平穩。

**重要訊號**：
- **黃金交叉**：短期均線由下往上穿越長期均線 → 未來偏多
- **死亡交叉**：短期均線由上往下穿越長期均線 → 未來偏空
- 股價在所有均線**之上** → 強勢多頭
- 股價在所有均線**之下** → 弱勢空頭

**當前狀態**：
{chr(10).join(ma_texts) if ma_texts else "資料不足"}
""")

    with st.expander(f"📊 RSI 相對強弱指標（{rsi_period}日，0~100）— 判斷超買超賣", expanded=True):
        if rsi_val is not None:
            if rsi_val >= 70:
                zone = "⚠️ **超買區**（70 以上）"
                meaning = "短期內漲太多，技術上有回檔壓力，未來 1-2 週回跌機率高"
                strategy = "超買區通常伴隨回檔壓力，短線波動加大"
            elif rsi_val <= 30:
                zone = "💡 **超賣區**（30 以下）"
                meaning = "短期內跌太多，技術上有反彈機會，未來 1-2 週止跌回升機率高"
                strategy = "超賣區通常醞釀反彈機會，短線波動加大"
            elif rsi_val >= 50:
                zone = "✅ **偏多區**（50-70）"
                meaning = "多方力道略佔上風，趨勢偏多但尚未過熱"
                strategy = "偏多區表示多方力道略佔上風"
            else:
                zone = "⚠️ **偏空區**（30-50）"
                meaning = "空方力道略佔上風，趨勢偏弱但尚未超跌"
                strategy = "偏空區表示空方力道略佔上風"

            st.markdown(f"""
**RSI 是什麼**：衡量過去 {rsi_period} 天內「漲的力道」相對於「跌的力道」，數值 0-100。

**判讀原則**：
- **> 70 超買**：股價可能被過度炒作，隨時拉回
- **< 30 超賣**：股價可能被過度拋售，隨時反彈
- **50 為多空分界**

**當前值：{rsi_val:.1f} — {zone}**
- 💡 意義：{meaning}
- 📌 對策：{strategy}
""")
        else:
            st.markdown("資料不足")

    with st.expander("📉 MACD 指標 — 判斷趨勢動能", expanded=True):
        if macd_val is not None and macd_sig is not None:
            if macd_val > macd_sig and macd_hist is not None and macd_hist > 0:
                macd_state = "✅ **多頭訊號**：MACD 在信號線之上，且柱狀圖為正"
                macd_meaning = "短期均線漲幅 > 長期均線，動能向上，未來偏多"
            elif macd_val < macd_sig and macd_hist is not None and macd_hist < 0:
                macd_state = "⚠️ **空頭訊號**：MACD 在信號線之下，且柱狀圖為負"
                macd_meaning = "短期均線跌幅 > 長期均線，動能向下，未來偏空"
            elif macd_val > macd_sig:
                macd_state = "🔄 **轉強中**：MACD 在信號線之上，但柱狀圖縮減"
                macd_meaning = "多頭力道減弱中，留意是否轉弱"
            else:
                macd_state = "🔄 **轉弱中**：MACD 在信號線之下，但柱狀圖縮小"
                macd_meaning = "空頭力道減弱中，留意是否轉強"

            st.markdown(f"""
**MACD 是什麼**：由兩條指數移動平均線（EMA）相減而成，用來看趨勢方向與動能。
- MACD 線 = 12日EMA − 26日EMA
- 信號線 = MACD 的 9日EMA
- 柱狀圖 = MACD − 信號線

**重要訊號**：
- **MACD 向上穿越信號線**：買進訊號，未來偏多
- **MACD 向下穿越信號線**：賣出訊號，未來偏空
- **柱狀圖由負轉正**：動能轉強
- **柱狀圖由正轉負**：動能轉弱

**當前狀態：{macd_state}**
- 💡 意義：{macd_meaning}
""")
        else:
            st.markdown("資料不足")

    with st.expander("🔀 KD 隨機指標（0~100）— 判斷短期超買超賣", expanded=True):
        if stoch_k is not None and stoch_d is not None:
            if stoch_k >= 80:
                kd_zone = "⚠️ **超買區**（80 以上）"
                kd_meaning = "短期內漲幅過大，K 值在高檔鈍化，隨時可能回檔修正"
                kd_strategy = "超買區通常醞釀回檔修正"
            elif stoch_k <= 20:
                kd_zone = "💡 **超賣區**（20 以下）"
                kd_meaning = "短期內跌幅過大，K 值在低檔鈍化，隨時可能反彈"
                kd_strategy = "超賣區通常醞釀反彈機會"
            elif stoch_k > stoch_d:
                kd_zone = "✅ **偏多**：K 值在 D 值之上"
                kd_meaning = "短期多方力道較強，股價有上漲動能"
                kd_strategy = "短線多方力道較強"
            else:
                kd_zone = "⚠️ **偏空**：K 值在 D 值之下"
                kd_meaning = "短期空方力道較強，股價有下跌壓力"
                kd_strategy = "短線空方力道較強"

            if stoch_k > stoch_d and stoch_k < 50:
                kd_signal = "✅ **黃金交叉**：K 值由下往上穿越 D 值，偏多訊號"
            elif stoch_k < stoch_d and stoch_k > 50:
                kd_signal = "⚠️ **死亡交叉**：K 值由上往下穿越 D 值，偏空訊號"
            else:
                kd_signal = "無特殊交叉訊號"

            st.markdown(f"""
**KD 是什麼**：根據最近一段時間的價格範圍，判斷目前收盤價「相對高低位置」的指標。
- K 值 = 快速隨機指標，對價格變化敏感
- D 值 = K 值的移動平均，較平穩

**判讀原則**：
- **> 80 超買**：股價接近近期高檔，回檔風險高
- **< 20 超賣**：股價接近近期低檔，反彈機會高
- **K 向上穿越 D**：黃金交叉，偏多
- **K 向下穿越 D**：死亡交叉，偏空

**當前值：K = {stoch_k:.1f}，D = {stoch_d:.1f} — {kd_zone}**
- 💡 意義：{kd_meaning}
- 📌 對策：{kd_strategy}
- 🔀 {kd_signal}
""")
        else:
            st.markdown("資料不足")

    with st.expander("📦 布林通道（BB）— 判斷波動與相對位置", expanded=True):
        if bb_u is not None and bb_l is not None:
            bb_width = (bb_u - bb_l) / close * 100
            bb_pct = (close - bb_l) / (bb_u - bb_l) * 100 if (bb_u - bb_l) > 0 else 50

            if close >= bb_u * 0.99:
                bb_zone = "🔴 **接近上軌**：股價過熱，短期回跌機率高"
            elif close <= bb_l * 1.01:
                bb_zone = "🟢 **接近下軌**：股價超跌，短期反彈機率高"
            elif bb_pct > 50:
                bb_zone = "✅ **上半部**：偏多位置"
            else:
                bb_zone = "⚠️ **下半部**：偏空位置"

            st.markdown(f"""
**布林通道是什麼**：以 {bb_period}日均線為中線，上下 ± {bb_std} 個標準差畫成的通道，衡量波動範圍。

**判讀原則**：
- 股價碰到**上軌**：過熱訊號
- 股價碰到**下軌**：超跌訊號
- 通道**變窄**：盤整中，隨時可能大波動（噴出或急殺）
- 通道**變寬**：趨勢明確中

**當前狀態**：
- 上軌：{bb_u:.2f}，下軌：{bb_l:.2f}，通道寬度：{bb_width:.1f}%
- 目前股價在通道的 {bb_pct:.0f}% 位置
- {bb_zone}
""")
        else:
            st.markdown("資料不足")

    with st.expander("📊 成交量 — 確認趨勢真假", expanded=True):
        if vol_ma5 is not None:
            vol_ratio = vol / vol_ma5 if vol_ma5 > 0 else 1
            if vol_ratio >= 1.5:
                vol_text = "🔥 **爆量**（量能 > 5日均量 1.5 倍以上）"
                if close > df.iloc[-2]["close"]:
                    vol_meaning = "價漲量增 → 多方強力進攻，趨勢強勁，可偏多操作"
                else:
                    vol_meaning = "價跌量增 → 恐慌性賣壓，趨勢偏弱，宜保守"
            elif vol_ratio >= 0.8:
                vol_text = "✅ **正常量**（與 5日均量相近）"
                vol_meaning = "量能正常，無特殊多空訊號"
            else:
                vol_text = "⚠️ **縮量**（量能 < 5日均量）"
                if close > df.iloc[-2]["close"]:
                    vol_meaning = "價漲量縮 → 追價意願不高，上漲動能不足，留意拉回"
                else:
                    vol_meaning = "價跌量縮 → 賣壓減輕，可能接近底部，等待止跌訊號"

            st.markdown(f"""
**成交量是什麼**：當天買賣的總股數，量是「趨勢的燃料」。

**重要原則**：
- **價漲量增**：健康的上涨，趨勢可信
- **價漲量縮**：虛涨，上漲動能不足
- **價跌量增**：恐慌賣壓，趨勢弱
- **價跌量縮**：賣壓減輕，可能接近底部

**當前狀態**：
- 今日成交量：{vol:,.0f}
- 5日均量：{vol_ma5:,.0f}
- 量比：{vol_ratio:.2f} 倍
- {vol_text}
- 💡 {vol_meaning}
""")
        else:
            st.markdown("資料不足")

    with st.expander("📌 支撐與壓力線 — 關鍵價位", expanded=True):
        dist_to_res = (resistance - close) / close * 100
        dist_to_sup = (support - close) / close * 100
        st.markdown(f"""
**支撐線**：近期股價跌到這價位附近會止跌的位置（買方進場意願強）
**壓力線**：近期股價漲到這價位附近會遇到賣壓的位置（賣方出貨意願強）

**近 20 日關鍵價位**：
- 🔴 **壓力線：{resistance:.2f}**（距離現價 {dist_to_res:+.2f}%）— 突破後上看，可能開啟新一波上漲
- 🟢 **支撐線：{support:.2f}**（距離現價 {dist_to_sup:+.2f}%）— 跌破後下殺，可能加速趨勢走弱

**技術應對參考**：
- 股價接近**壓力線**時：留意是否帶量突破，突破失敗可能回測支撐
- 股價接近**支撐線**時：留意是否止跌回穩，守住支撐可能延續反彈
""")

    # 綜合走勢分析
    st.markdown("### 🔮 未來走勢綜合分析")

    signals = []
    bullish = 0
    bearish = 0

    if ma5_val is not None and ma20_val is not None:
        if ma5_val > ma20_val:
            signals.append(("均線", "偏多", f"5日({ma5_val:.1f})在20日({ma20_val:.1f})之上"))
            bullish += 1
        else:
            signals.append(("均線", "偏空", f"5日({ma5_val:.1f})在20日({ma20_val:.1f})之下"))
            bearish += 1

    if ma20_val is not None and ma60_val is not None:
        if ma20_val > ma60_val:
            signals.append(("中期趨勢", "偏多", "20日均線在60日均線之上"))
            bullish += 1
        else:
            signals.append(("中期趨勢", "偏空", "20日均線在60日均線之下"))
            bearish += 1

    if rsi_val is not None:
        if rsi_val >= 70:
            signals.append(("RSI", "過熱", f"{rsi_val:.1f} 進入超買區，短期回跌風險高"))
            bearish += 1
        elif rsi_val <= 30:
            signals.append(("RSI", "超跌", f"{rsi_val:.1f} 進入超賣區，短期反彈機會高"))
            bullish += 1
        elif rsi_val >= 50:
            signals.append(("RSI", "偏多", f"{rsi_val:.1f} 處於偏多區"))
            bullish += 1
        else:
            signals.append(("RSI", "偏空", f"{rsi_val:.1f} 處於偏空區"))
            bearish += 1

    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig:
            signals.append(("MACD", "偏多", "MACD 在信號線之上，多頭動能"))
            bullish += 1
        else:
            signals.append(("MACD", "偏空", "MACD 在信號線之下，空頭動能"))
            bearish += 1

    if stoch_k is not None and stoch_d is not None:
        if stoch_k >= 80:
            signals.append(("KD", "過熱", f"K={stoch_k:.1f} 進入超買區，短期回檔風險高"))
            bearish += 1
        elif stoch_k <= 20:
            signals.append(("KD", "超跌", f"K={stoch_k:.1f} 進入超賣區，短期反彈機會高"))
            bullish += 1
        elif stoch_k > stoch_d:
            signals.append(("KD", "偏多", f"K={stoch_k:.1f} > D={stoch_d:.1f}，多方力道"))
            bullish += 1
        else:
            signals.append(("KD", "偏空", f"K={stoch_k:.1f} < D={stoch_d:.1f}，空方力道"))
            bearish += 1

    if vol_ma5 is not None:
        vol_ratio = vol / vol_ma5 if vol_ma5 > 0 else 1
        prev_close = float(df.iloc[-2]["close"])
        if vol_ratio >= 1.5 and close > prev_close:
            signals.append(("量能", "偏多", "價漲量增，多方進攻"))
            bullish += 1
        elif vol_ratio >= 1.5 and close < prev_close:
            signals.append(("量能", "偏空", "價跌量增，賣壓沉重"))
            bearish += 1
        elif vol_ratio < 0.8 and close > prev_close:
            signals.append(("量能", "偏空", "價漲量縮，追價意願低"))
            bearish += 1
        elif vol_ratio < 0.8 and close < prev_close:
            signals.append(("量能", "偏多", "價跌量縮，賣壓減輕"))
            bullish += 1

    if close >= resistance * 0.98:
        signals.append(("位置", "接近壓力", f"距離壓力線 {resistance:.2f} 不到 2%"))
    elif close <= support * 1.02:
        signals.append(("位置", "接近支撐", f"距離支撐線 {support:.2f} 不到 2%"))

    total = bullish + bearish
    if total == 0:
        overall = "⚪ **訊號不明** — 各指標無明確方向"
    elif bullish >= bearish + 2:
        overall = "🟢 **強烈偏多** — 多項指標看多，未來上漲機率高"
    elif bullish > bearish:
        overall = "🟢 **偏多** — 多數指標看多"
    elif bearish > bullish + 1:
        overall = "🔴 **強烈偏空** — 多項指標看空，未來下跌機率高"
    else:
        overall = "🔴 **偏空** — 多數指標看空"

    st.markdown(f"#### 整體判斷：{overall}")
    st.markdown(f"**多空票數：偏多 {bullish} 票 / 偏空 {bearish} 票**")

    st.markdown("#### 📋 各指標訊號明細")
    signal_df_rows = []
    for name, verdict, detail in signals:
        if "偏多" in verdict or "超跌" in verdict:
            color = "🟢"
        elif "偏空" in verdict or "過熱" in verdict:
            color = "🔴"
        else:
            color = "🟡"
        signal_df_rows.append([color, name, verdict, detail])
    st.table(signal_df_rows)

    st.markdown("#### 🎯 未來可能的三種情境")
    scenario_bullish_pct = max(20, min(75, 50 + (bullish - bearish) * 15))
    scenario_bearish_pct = max(20, min(75, 50 + (bearish - bullish) * 15))
    scenario_neutral_pct = max(10, 100 - scenario_bullish_pct - scenario_bearish_pct)
    st.markdown(f"""
**🟢 多頭情境**（機率約 {scenario_bullish_pct}%）
- 條件：股價站穩所有均線、成交量放大、MACD 翻正
- 目標價：突破壓力線 {resistance:.2f}，上看近期新高
- 時間：1~2 週內可能實現

**🟡 盤整情境**（機率約 {scenario_neutral_pct}%）
- 條件：股價在支撐 {support:.2f} ~ 壓力 {resistance:.2f} 區間震盪
- 目標價：在區間內高賣低買
- 時間：可能持續 2~4 週

**🔴 空頭情境**（機率約 {scenario_bearish_pct}%）
- 條件：跌破支撐線 {support:.2f}、均線空頭排列、量縮
- 目標價：下看更低支撐（可觀察 60日均線 {ma60_val:.1f} 若有）
- 時間：1~2 週內可能發生
""")

    st.caption("⚠️ 免責聲明：以上分析僅基於技術指標的統計參考，非投資建議。投資有風險，請審慎評估。")

    if show_volume_profile:
        fig_vp = plot_volume_profile(df)
        if fig_vp:
            col_l, col_r = st.columns([3, 1])
            with col_l:
                st.plotly_chart(fig_vp, use_container_width=True, key=f"vp_{symbol}_{period}")
            with col_r:
                row1 = ["高點", f"{latest['high']:.2f}"]
                row2 = ["低點", f"{latest['low']:.2f}"]
                row3 = ["均價", f"{df['close'].mean():.2f}"]
                row4 = ["區間", f"{df['low'].min():.2f} - {df['high'].max():.2f}"]
                st.dataframe(pd.DataFrame([row1, row2, row3, row4], columns=["項目", "數值"]),
                           hide_index=True, use_container_width=True)

    # 技術指標數值表
    with st.expander("📊 最新技術指標數值", expanded=False):
        latest_indicators = {
            f"RSI({rsi_period}日)": f"{latest['rsi']:.2f}" if "rsi" in latest and not pd.isna(latest['rsi']) else "N/A",
            "MACD": f"{latest['macd']:.2f}" if "macd" in latest and not pd.isna(latest['macd']) else "N/A",
            "MACD 信號線": f"{latest['macd_signal']:.2f}" if "macd_signal" in latest and not pd.isna(latest['macd_signal']) else "N/A",
            "KD K值": f"{latest['stoch_k']:.2f}" if "stoch_k" in latest and not pd.isna(latest['stoch_k']) else "N/A",
            "KD D值": f"{latest['stoch_d']:.2f}" if "stoch_d" in latest and not pd.isna(latest['stoch_d']) else "N/A",
            "布林上軌": f"{latest['bb_upper']:.2f}" if "bb_upper" in latest and not pd.isna(latest['bb_upper']) else "N/A",
            "布林下軌": f"{latest['bb_lower']:.2f}" if "bb_lower" in latest and not pd.isna(latest['bb_lower']) else "N/A",
            "5日均線": f"{latest['ma5']:.2f}" if "ma5" in latest and not pd.isna(latest['ma5']) else "N/A",
            "20日均線": f"{latest['ma20']:.2f}" if "ma20" in latest and not pd.isna(latest['ma20']) else "N/A",
        }
        st.dataframe(
            pd.DataFrame(list(latest_indicators.items()), columns=["指標", "數值"]).T,
            use_container_width=True,
        )

# ═══════════════════════════════════════
# TAB 2: 回測系統
# ═══════════════════════════════════════
with tab2:
    st.subheader(f"📈 策略回測 - {strategy_name}")

    col_params = st.columns(3)
    with col_params[0]:
        bt_start = st.date_input("回測開始日", df.index[0].date() if len(df) > 0 else datetime.now() - timedelta(days=365))
    with col_params[1]:
        bt_end = st.date_input("回測結束日", df.index[-1].date() if len(df) > 0 else datetime.now())
    with col_params[2]:
        bt_commission = st.number_input("手續費率", 0.0, 0.01, 0.001425, format="%.6f")

    if st.button("🚀 開始回測", type="primary", use_container_width=True):
        bt_df = df[(df.index >= pd.Timestamp(bt_start)) & (df.index <= pd.Timestamp(bt_end))]
        if len(bt_df) < 50:
            st.warning("資料筆數不足，請選擇更長的區間")
        else:
            strategy_fn = strategy_info["fn"]
            sp = {}
            for p in strategy_info["params"]:
                sp[p["name"]] = st.session_state.get(f"sp_{p['name']}", p["default"])
            result = backtest(bt_df, strategy_fn, initial_cash=bt_initial,
                              commission=bt_commission, strategy_params=sp)

            col_a, col_b = st.columns([1, 2])

            with col_a:
                st.subheader("📊 績效指標")
                mt = result.metrics
                metric_names = {
                    "total_return": "總報酬率", "annual_return": "年化報酬率",
                    "sharpe_ratio": "夏普比率", "max_drawdown": "最大回撤",
                    "win_rate": "勝率", "total_trades": "交易次數",
                    "final_value": "最終資產", "initial_cash": "初始資金",
                    "avg_profit": "平均獲利", "avg_return": "平均報酬率",
                    "avg_holding_days": "平均持有天數",
                    "max_single_profit": "最大單筆獲利", "max_single_loss": "最大單筆虧損",
                    "max_single_return": "最大單筆報酬%", "max_single_loss_pct": "最大單筆虧損%",
                    "profit_factor": "賺賠比", "max_consecutive_loss": "最大連續虧損次數",
                    "total_fees": "總交易費用",
                }
                fmt_map = {
                    "total_return": f"{mt['total_return']:+.2f}%",
                    "annual_return": f"{mt['annual_return']:+.2f}%",
                    "sharpe_ratio": f"{mt['sharpe_ratio']}",
                    "max_drawdown": f"{mt['max_drawdown']:.2f}%",
                    "win_rate": f"{mt['win_rate']}%",
                    "total_trades": f"{mt['total_trades']}",
                    "final_value": f"${mt['final_value']:,.0f}",
                    "initial_cash": f"${mt['initial_cash']:,.0f}",
                    "avg_profit": f"${mt['avg_profit']:,.0f}",
                    "avg_return": f"{mt['avg_return']:+.2f}%",
                    "avg_holding_days": f"{mt['avg_holding_days']:.1f} 天",
                    "max_single_profit": f"${mt['max_single_profit']:,.0f}",
                    "max_single_loss": f"${mt['max_single_loss']:,.0f}",
                    "max_single_return": f"{mt['max_single_return']:+.2f}%",
                    "max_single_loss_pct": f"{mt['max_single_loss_pct']:+.2f}%",
                    "profit_factor": f"{mt['profit_factor']}",
                    "max_consecutive_loss": f"{mt['max_consecutive_loss']} 次",
                    "total_fees": f"${mt['total_fees']:,.0f}",
                }
                rows = [[metric_names.get(k, k), fmt_map.get(k, str(v))]
                        for k, v in mt.items()]
                metrics_df = pd.DataFrame(rows, columns=["指標", "數值"])
                st.dataframe(metrics_df, hide_index=True, use_container_width=True)

            if result.trades:
                trades = result.trades
                last_trade = trades[-1]
                best_trade = max(trades, key=lambda t: t.return_pct)
                worst_trade = min(trades, key=lambda t: t.return_pct)
                st.markdown(f"**📋 交易摘要**  ·  {mt['total_trades']} 筆 · "
                            f"最近：{last_trade.buy_date.strftime('%m/%d')}買 {last_trade.sell_date.strftime('%m/%d')}賣 "
                            f"{last_trade.return_pct:+.2f}% · "
                            f"最賺：{best_trade.return_pct:+.2f}% · "
                            f"最賠：{worst_trade.return_pct:+.2f}%")

            with col_b:
                st.subheader("📈 權益曲線")
                ec = result.equity_curve
                fig_ec = go.Figure()
                fig_ec.add_trace(go.Scatter(
                    x=ec.index, y=ec.values,
                    mode="lines",
                    name="權益曲線",
                    line=dict(color="#2196F3", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(33, 150, 243, 0.1)",
                ))

                rolling_max = ec.expanding().max()
                drawdown = (ec - rolling_max) / rolling_max * 100
                fig_ec.add_trace(go.Scatter(
                    x=ec.index, y=rolling_max,
                    mode="lines",
                    name="歷史高點",
                    line=dict(color="rgba(255,0,0,0.3)", width=1, dash="dash"),
                ))

                fig_ec.add_hline(y=bt_initial, line_dash="dash", line_color="gray",
                               annotation_text="初始資金")
                fig_ec.update_layout(
                    height=350,
                    template="plotly_white",
                    hovermode="x unified",
                    yaxis_title="資產總額",
                )
                st.plotly_chart(fig_ec, use_container_width=True)

            # 回撤圖
            st.subheader("📉 回撤曲線")
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=ec.index, y=drawdown,
                mode="lines",
                name="回撤",
                line=dict(color="#ef5350", width=1.5),
                fill="tozeroy",
                fillcolor="rgba(239, 83, 80, 0.1)",
            ))
            fig_dd.update_layout(
                height=200,
                template="plotly_white",
                hovermode="x unified",
                yaxis_title="回撤 (%)",
                yaxis_tickformat=".1f",
            )
            st.plotly_chart(fig_dd, use_container_width=True)

            # 交易配對分析
            if result.trades:
                st.subheader("🔄 逐筆交易分析")
                trade_records = []
                for t in result.trades:
                    trade_records.append({
                        "買進日期": t.buy_date.strftime("%Y-%m-%d"),
                        "賣出日期": t.sell_date.strftime("%Y-%m-%d"),
                        "買價": f"{t.buy_price:.2f}",
                        "賣價": f"{t.sell_price:.2f}",
                        "股數": f"{t.shares:,}",
                        "獲利": f"${t.profit:,.0f}",
                        "報酬率": f"{t.return_pct:+.2f}%",
                        "持有天數": f"{t.holding_days} 天",
                    })
                df_trades = pd.DataFrame(trade_records)
                st.dataframe(df_trades, hide_index=True, use_container_width=True)

            # 完整交易紀錄
            if result.orders:
                with st.expander("📋 完整交易流水帳", expanded=False):
                    records = []
                    for o in result.orders:
                        records.append({
                            "日期": o.date.strftime("%Y-%m-%d"),
                            "動作": "買進" if o.action == Action.BUY else "賣出",
                            "價格": f"{o.price:.2f}",
                            "股數": f"{o.shares:.0f}",
                            "金額": f"{o.value:,.0f}",
                            "手續費/稅": f"{o.fee:,.0f}",
                        })
                    df_orders = pd.DataFrame(records)
                    st.dataframe(df_orders, hide_index=True, use_container_width=True)

    else:
        st.info("請設定參數後點擊「開始回測」")

# ═══════════════════════════════════════
# TAB 3: 原始資料
# ═══════════════════════════════════════
with tab3:
    st.subheader("📋 原始股價資料")
    col_map = {"open": "開盤", "high": "最高", "low": "最低", "close": "收盤", "volume": "成交量",
               "rsi": f"RSI({rsi_period}日)", "macd": "MACD", "macd_signal": "MACD 信號線"}
    display_cols = ["open", "high", "low", "close", "volume"]
    if "rsi" in df.columns:
        display_cols += ["rsi"]
    if "macd" in df.columns:
        display_cols += ["macd", "macd_signal"]
    display_cols = [c for c in display_cols if c in df.columns]
    df_display = df[display_cols].copy()
    df_display.columns = [col_map.get(c, c) for c in df_display.columns]
    df_display.index = pd.to_datetime(df_display.index).strftime("%Y-%m-%d")

    st.dataframe(
        df_display.sort_index(ascending=False),
        use_container_width=True,
        height=500,
    )

    csv = df_display.to_csv().encode("utf-8-sig")
    st.download_button(
        label="📥 下載 CSV",
        data=csv,
        file_name=f"{symbol}_data.csv",
        mime="text/csv",
    )

# ═══════════════════════════════════════
# TAB 4: 多股走勢對比
# ═══════════════════════════════════════
with tab4:
    st.subheader("📈 多股累計報酬率走勢對比")

    st.info("輸入多檔股票代碼，以逗號分隔。例如：`2330, 2317, 2454` 或 `AAPL, MSFT, NVDA`")

    compare_input = st.text_input(
        "股票代碼（逗號分隔）",
        value=f"{symbol}, 2317, 2454",
        key="compare_symbols",
    )

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        compare_period_map = {
            "1 個月": "1mo", "3 個月": "3mo", "6 個月": "6mo",
            "1 年": "1y", "2 年": "2y", "5 年": "5y",
        }
        compare_period_label = st.selectbox("比較區間", list(compare_period_map.keys()), index=3, key="compare_period")
        compare_period = compare_period_map[compare_period_label]
    with col_c2:
        normalize_start = st.checkbox("從起始日歸一化（0%）", value=True, key="normalize_start")

    if st.button("🔍 開始比較", type="primary", key="btn_compare"):
        symbols_list = [s.strip() for s in compare_input.split(",") if s.strip()]

        if len(symbols_list) < 2:
            st.warning("請輸入至少 2 檔股票代碼")
        elif len(symbols_list) > 10:
            st.warning("最多比較 10 檔股票")
        else:
            compare_colors = ["#ef5350", "#2196F3", "#4CAF50", "#FF9800", "#9C27B0",
                              "#00BCD4", "#E91E63", "#8BC34A", "#FF5722", "#607D8B"]

            with st.spinner("載入資料中..."):
                all_data = {}
                all_names = {}
                failed = []
                all_stocks_flat = {k: v for cat in STOCKS.values() for k, v in cat.items()}
                for sym in symbols_list:
                    d = get_stock_data(sym, compare_period)
                    if not d.empty and len(d) > 5:
                        all_data[sym] = d
                        if sym in all_stocks_flat:
                            all_names[sym] = all_stocks_flat[sym]
                        else:
                            info_tmp = get_stock_info(sym)
                            all_names[sym] = info_tmp.get("name", sym)
                    else:
                        failed.append(sym)

            if failed:
                st.warning(f"以下代碼無法取得資料：{', '.join(failed)}")

            if len(all_data) >= 2:
                fig_compare = go.Figure()

                for idx, (sym, d) in enumerate(all_data.items()):
                    color = compare_colors[idx % len(compare_colors)]
                    name_label = f"{all_names[sym]} ({sym})"
                    prices = d["close"].values
                    if normalize_start and len(prices) > 0:
                        base = prices[0]
                        cum_returns = (prices / base - 1) * 100
                    else:
                        cum_returns = prices
                    fig_compare.add_trace(go.Scatter(
                        x=d.index, y=cum_returns,
                        mode="lines",
                        name=name_label,
                        line=dict(color=color, width=2),
                    ))

                y_title = "累計報酬率 (%)" if normalize_start else "股價"
                fig_compare.update_layout(
                    title=f"多股走勢對比 — {compare_period_label}",
                    xaxis_title="日期",
                    yaxis_title=y_title,
                    template="plotly_white",
                    hovermode="x unified",
                    height=500,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )

                if normalize_start:
                    fig_compare.add_hline(y=0, line_dash="dash", line_color="gray")

                st.plotly_chart(fig_compare, use_container_width=True)

                st.markdown("#### 📊 報酬率明細")
                summary_records = []
                for idx, (sym, d) in enumerate(all_data.items()):
                    name_label = f"{all_names[sym]} ({sym})"
                    prices = d["close"].values
                    start_price = prices[0]
                    end_price = prices[-1]
                    total_return = (end_price / start_price - 1) * 100
                    max_price = prices.max()
                    min_price = prices.min()
                    max_return = (max_price / start_price - 1) * 100
                    min_return = (min_price / start_price - 1) * 100
                    summary_records.append({
                        "股票": name_label,
                        "起始價": f"{start_price:.2f}",
                        "最新價": f"{end_price:.2f}",
                        "累計報酬": f"{total_return:+.2f}%",
                        "最高報酬": f"{max_return:+.2f}%",
                        "最低報酬": f"{min_return:+.2f}%",
                        "波動幅度": f"{(max_price - min_price) / start_price * 100:.2f}%",
                    })
                df_summary = pd.DataFrame(summary_records)
                st.dataframe(df_summary, hide_index=True, use_container_width=True)
            elif len(all_data) == 1:
                st.info("僅成功載入 1 檔股票，無法進行對比")

# ═══════════════════════════════════════
# TAB 5: 主力動向分析
# ═══════════════════════════════════════
with tab5:
    st.subheader("🏛️ 主力買賣超動向分析")
    st.caption("透過價量結構分析主力動向，並非實際法人進出場資料。全部市場一次顯示。")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        market_type = st.selectbox("市場", ["全部市場", "台股", "美股", "ETF"], key="inst_market")
    with col_f2:
        inst_period_map = {"1 個月": "1mo", "3 個月": "3mo", "6 個月": "6mo", "1 年": "1y"}
        inst_period_label = st.selectbox("分析區間", list(inst_period_map.keys()), index=1, key="inst_period")
        inst_period = inst_period_map[inst_period_label]

    if st.button("🔍 分析全部主力動向", type="primary", key="btn_inst"):
        if market_type == "全部市場":
            all_sectors = {"台股": SECTORS_TW, "美股": SECTORS_US, "ETF": SECTORS_ETF}
        elif market_type == "台股":
            all_sectors = {"台股": SECTORS_TW}
        elif market_type == "美股":
            all_sectors = {"美股": SECTORS_US}
        else:
            all_sectors = {"ETF": SECTORS_ETF}

        all_stocks_flat = {k: v for cat in STOCKS.values() for k, v in cat.items()}
        all_analysis = {}

        with st.spinner("載入並分析全部產業資料中..."):
            for market_name, sectors in all_sectors.items():
                for sector_name, codes in sectors.items():
                    full_key = f"{market_name}｜{sector_name}"
                    sector_results = []
                    for code in codes:
                        d = get_stock_data(code, inst_period)
                        if d.empty or len(d) < 20:
                            continue

                        name = all_stocks_flat.get(code, code)
                        close = d["close"].values
                        volume = d["volume"].values
                        open_p = d["open"].values

                        price_start = close[0]
                        price_end = close[-1]
                        price_chg = (price_end / price_start - 1) * 100
                        daily_chg = (close[-1] / close[-2] - 1) * 100 if len(close) >= 2 else 0

                        vol_ma20 = pd.Series(volume).rolling(20).mean().values
                        vol_avg = np.nanmean(vol_ma20)
                        vol_now = volume[-1]
                        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1

                        vol_ma5 = pd.Series(volume).rolling(5).mean().values
                        vol_5avg = np.nanmean(vol_ma5)
                        vol_5ratio = vol_now / vol_5avg if vol_5avg > 0 else 1

                        recent_5 = close[-5:]
                        recent_5_chg = (recent_5[-1] / recent_5[0] - 1) * 100

                        ma5 = np.mean(close[-5:])
                        ma20 = np.mean(close[-20:])

                        gap_up = (open_p[-1] / close[-2] - 1) * 100 if len(close) >= 2 else 0
                        limit_up = daily_chg >= 9.5
                        limit_down = daily_chg <= -9.5
                        up_days = sum(1 for i in range(-5, 0) if close[i] > close[i-1]) if len(close) >= 6 else 0

                        high_10 = max(close[-10:]) if len(close) >= 10 else max(close)
                        drop_from_high = (high_10 - price_end) / high_10 * 100

                        big_down_days = 0
                        big_vol_down = 0
                        for i in range(-10, 0):
                            if len(close) >= abs(i) + 1:
                                day_chg_i = (close[i] / close[i-1] - 1) * 100
                                if day_chg_i < -3:
                                    big_down_days += 1
                                if day_chg_i < -3 and volume[i] > vol_avg * 1.2:
                                    big_vol_down += 1

                        score = 0
                        reasons = []

                        if big_vol_down >= 2:
                            score -= 3
                            reasons.append(f"近期有{big_vol_down}日放量大跌(主力出貨跡象)")
                        elif big_vol_down >= 1:
                            score -= 1
                            reasons.append(f"近期有{big_vol_down}日放量下跌")

                        if big_down_days >= 3:
                            score -= 2
                            reasons.append(f"近10日有{big_down_days}日大跌(跌幅>3%)")

                        if drop_from_high >= 15:
                            score -= 2
                            reasons.append(f"從近期高點回撤{drop_from_high:.1f}%")
                        elif drop_from_high >= 8:
                            score -= 1
                            reasons.append(f"從近期高點回撤{drop_from_high:.1f}%")

                        if vol_ratio >= 2.0:
                            if drop_from_high >= 8:
                                score -= 2
                                reasons.append("爆量但已從高點回落(疑似出貨反弹)")
                            else:
                                score += 2
                                reasons.append(f"爆量({vol_ratio:.1f}倍)")
                        elif vol_ratio >= 1.5:
                            if drop_from_high >= 8:
                                score -= 1
                                reasons.append("放量但從高點回落")
                            else:
                                score += 1
                                reasons.append(f"放量({vol_ratio:.1f}倍)")
                        elif vol_ratio < 0.5:
                            score -= 1
                            reasons.append(f"極度縮量({vol_ratio:.1f}倍)")

                        if vol_5ratio >= 1.3:
                            if big_vol_down >= 2:
                                reasons.append("近5日量放大但有出貨跡象(不加分)")
                            else:
                                score += 1
                                reasons.append("近5日量能放大")

                        if recent_5_chg > 5:
                            if drop_from_high >= 10:
                                score -= 1
                                reasons.append(f"近5日漲{recent_5_chg:+.1f}%但仍在高點下")
                            else:
                                score += 2
                                reasons.append(f"近5日強漲({recent_5_chg:+.1f}%)")
                        elif recent_5_chg > 2:
                            score += 1
                            reasons.append(f"近5日上漲({recent_5_chg:+.1f}%)")
                        elif recent_5_chg < -5:
                            score -= 2
                            reasons.append(f"近5日大跌({recent_5_chg:+.1f}%)")
                        elif recent_5_chg < -2:
                            score -= 1
                            reasons.append(f"近5日下跌({recent_5_chg:+.1f}%)")

                        if ma5 > ma20:
                            score += 1
                            reasons.append("均線多頭排列")
                        else:
                            score -= 1
                            reasons.append("均線空頭排列")

                        if gap_up > 3:
                            if vol_ratio < 1.0:
                                score -= 1
                                reasons.append("跳空高開但量縮(疑出貨)")
                            elif drop_from_high >= 10:
                                reasons.append("跳空高開但距高點仍遠")
                            else:
                                reasons.append("跳空高開帶量")

                        if up_days >= 4:
                            score += 1
                            reasons.append(f"近5日有{up_days}日上漲")
                        elif up_days <= 1:
                            reasons.append(f"近5日僅{up_days}日上漲")

                        if limit_up:
                            if vol_ratio < 1.2:
                                score -= 2
                                reasons.append("漲停但量縮(主力鎖碼/散戶追價)")
                            elif drop_from_high >= 10:
                                reasons.append("漲停但距高點仍遠(反彈)")
                            else:
                                reasons.append("漲停板")
                        elif limit_down:
                            score -= 1
                            reasons.append("跌停板(賣壓沉重)")

                        if score >= 4:
                            signal = "🔴 強力買超"
                        elif score >= 2:
                            signal = "🟠 偏多觀察"
                        elif score <= -4:
                            signal = "🟢 強力賣超"
                        elif score <= -2:
                            signal = "🟡 偏空觀察"
                        elif vol_ratio < 0.5:
                            signal = "⚪ 量縮觀望"
                        else:
                            signal = "⚪ 中性整理"

                        sector_results.append({
                            "market": market_name,
                            "sector": sector_name,
                            "code": code,
                            "name": name,
                            "price_end": price_end,
                            "daily_chg": daily_chg,
                            "price_chg": price_chg,
                            "recent_5_chg": recent_5_chg,
                            "vol_ratio": vol_ratio,
                            "signal": signal,
                            "score": score,
                            "reasons": reasons,
                        })
                    all_analysis[full_key] = sector_results

        if not any(all_analysis.values()):
            st.warning("無法取得資料")
        else:
            all_flat = [r for r_list in all_analysis.values() for r in r_list]
            buy_all = [r for r in all_flat if "買超" in r["signal"]]
            sell_all = [r for r in all_flat if "賣超" in r["signal"]]
            observe = [r for r in all_flat if "觀察" in r["signal"]]

            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("🔴 主力買超", f"{len(buy_all)} 檔")
            m2.metric("🟢 主力賣超", f"{len(sell_all)} 檔")
            m3.metric("👀 觀察區", f"{len(observe)} 檔")
            m4.metric("📊 總標的", f"{len(all_flat)} 檔")

            st.markdown("---")
            st.markdown("### 🏆 全市場主力訊號排行 TOP 20")
            top20 = sorted(all_flat, key=lambda x: x["score"], reverse=True)[:20]
            top20_records = []
            for r in top20:
                top20_records.append({
                    "訊號": r["signal"],
                    "市場": r["market"],
                    "產業": r["sector"],
                    "代碼": r["code"],
                    "名稱": r["name"],
                    "最新價": f"{r['price_end']:.2f}",
                    f"{inst_period_label}漲跌": f"{r['price_chg']:+.2f}%",
                    "量比": f"{r['vol_ratio']:.2f}倍",
                    "強度": r["score"],
                })
            st.dataframe(pd.DataFrame(top20_records), hide_index=True, use_container_width=True)

            st.markdown("### 📉 全市場賣超警示 TOP 20")
            bottom20 = sorted(all_flat, key=lambda x: x["score"])[:20]
            bottom20_records = []
            for r in bottom20:
                bottom20_records.append({
                    "訊號": r["signal"],
                    "市場": r["market"],
                    "產業": r["sector"],
                    "代碼": r["code"],
                    "名稱": r["name"],
                    "最新價": f"{r['price_end']:.2f}",
                    f"{inst_period_label}漲跌": f"{r['price_chg']:+.2f}%",
                    "量比": f"{r['vol_ratio']:.2f}倍",
                    "強度": r["score"],
                })
            st.dataframe(pd.DataFrame(bottom20_records), hide_index=True, use_container_width=True)

            for full_key, stocks in all_analysis.items():
                if not stocks:
                    continue

                st.markdown("---")
                sorted_stocks = sorted(stocks, key=lambda x: x["score"], reverse=True)

                buy_count = len([s for s in stocks if "買超" in s["signal"]])
                sell_count = len([s for s in stocks if "賣超" in s["signal"]])
                avg_score = np.mean([s["score"] for s in stocks])

                if avg_score >= 2:
                    sector_tag = "🔴 偏多"
                elif avg_score <= -2:
                    sector_tag = "🟢 偏空"
                else:
                    sector_tag = "⚪ 中性"

                with st.expander(f"**{full_key}** {sector_tag} — 買超{buy_count}檔 / 賣超{sell_count}檔 / 共{len(stocks)}檔", expanded=False):

                    fig_bar = go.Figure()
                    colors_bar = []
                    for r in sorted_stocks:
                        if "買超" in r["signal"]:
                            colors_bar.append("#ef5350")
                        elif "賣超" in r["signal"]:
                            colors_bar.append("#26a69a")
                        elif "觀察" in r["signal"]:
                            colors_bar.append("#FF9800")
                        else:
                            colors_bar.append("#9E9E9E")

                    fig_bar.add_trace(go.Bar(
                        x=[f"{r['name']}({r['code']})" for r in sorted_stocks],
                        y=[r["score"] for r in sorted_stocks],
                        marker_color=colors_bar,
                        customdata=[[r["signal"], r["price_end"], r["vol_ratio"]] for r in sorted_stocks],
                        hovertemplate="<b>%{x}</b><br>強度分數: %{y}<br>%{customdata[0]}<br>最新價: %{customdata[1]:.2f}<br>量比: %{customdata[2]:.2f}倍<extra></extra>",
                    ))
                    fig_bar.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig_bar.update_layout(
                        title=f"{full_key} — 主力訊號強度排行",
                        xaxis_title="股票",
                        yaxis_title="訊號強度",
                        height=350,
                        template="plotly_white",
                        showlegend=False,
                        margin=dict(l=50, r=30, t=50, b=60),
                    )
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"inst_chart_{full_key}")

                    table_records = []
                    for r in sorted_stocks:
                        table_records.append({
                            "訊號": r["signal"],
                            "代碼": r["code"],
                            "名稱": r["name"],
                            "最新價": f"{r['price_end']:.2f}",
                            "日漲跌": f"{r['daily_chg']:+.2f}%",
                            f"{inst_period_label}漲跌": f"{r['price_chg']:+.2f}%",
                            "近5日": f"{r['recent_5_chg']:+.2f}%",
                            "量比": f"{r['vol_ratio']:.2f}倍",
                            "強度": r["score"],
                            "理由": "、".join(r["reasons"]) if r["reasons"] else "-",
                        })
                    st.dataframe(pd.DataFrame(table_records), hide_index=True, use_container_width=True)

                    st.markdown("**點擊按鈕查看個股詳細技術分析：**")
                    btn_cols = st.columns(min(len(sorted_stocks), 6))
                    for idx, r in enumerate(sorted_stocks):
                        col = btn_cols[idx % len(btn_cols)]
                        with col:
                            if st.button(f"📊 {r['name']}({r['code']})", key=f"goto_{full_key}_{r['code']}"):
                                st.session_state["redirect_stock"] = r["code"]
                                st.session_state["redirect_name"] = r["name"]
                                st.session_state["input_mode"] = "手動輸入"
                                st.session_state["manual_symbol"] = r["code"]
                                st.rerun()

            st.markdown("---")
            st.markdown("#### 📖 判讀說明")
            st.markdown("""
| 訊號 | 總分 | 意義 |
|------|------|------|
| 🔴 **強力買超** | ≥ 4 分 | 多項量價訊號共振，主力積極佈局 |
| 🟠 **偏多觀察** | 2~3 分 | 有買盤跡象，持續追蹤 |
| ⚪ **中性整理** | -1~1 分 | 無明確方向，觀望為主 |
| 🟡 **偏空觀察** | -3~-2 分 | 有賣壓跡象，留意風險 |
| 🟢 **強力賣超** | ≤ -4 分 | 多項賣出訊號，主力出貨中 |
""")
            st.caption("⚠️ 以上分析基於價量技術面推估，並非實際法人進出場資料，僅供參考。")

# ═══════════════════════════════════════
# TAB 6: 持股監控
# ═══════════════════════════════════════
with tab6:
    st.subheader("🔔 持股監控 — 技術面訊號")

    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = auth.get_watchlist(st.session_state["username"])

    # ─── 新增持股 ───
    with st.expander("➕ 新增持股", expanded=True):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 2, 2, 2, 1])
        with c1:
            wl_symbol = st.text_input("股票代碼", "2330", key="wl_sym")
        with c2:
            wl_name = st.text_input("股票名稱", "台積電", key="wl_name")
        with c3:
            wl_price = st.number_input("買入均價", min_value=0.0, value=600.0, step=0.1, key="wl_price")
        with c4:
            wl_shares = st.number_input("購買股數", min_value=1, value=1000, step=100, key="wl_shares")
        with c5:
            wl_date = st.date_input("買入日期", key="wl_date")
        with c6:
            wl_strategy = st.selectbox("策略", ["短期", "長期"], key="wl_strat")

        if st.button("➕ 加入監控", type="primary", use_container_width=True):
            entry = {
                "symbol": wl_symbol.strip(),
                "name": wl_name.strip(),
                "buy_price": wl_price,
                "shares": wl_shares,
                "buy_date": wl_date.strftime("%Y-%m-%d"),
                "strategy": wl_strategy,
            }
            # 避免重複
            exists = any(w["symbol"] == entry["symbol"] and w["buy_price"] == entry["buy_price"] for w in st.session_state["watchlist"])
            if not exists:
                auth.add_to_watchlist(st.session_state["username"], entry)
                st.session_state["watchlist"] = auth.get_watchlist(st.session_state["username"])
                st.success(f"已加入 {entry['name']}({entry['symbol']})")
                st.rerun()
            else:
                st.warning("此持股已在監控列表中")

    # ─── 監控列表 ───
    if not st.session_state["watchlist"]:
        st.info("尚無監控持股，請先新增。")
    else:
        st.markdown(f"### 📋 監控列表（{len(st.session_state['watchlist'])} 檔）")

        # 批量取得資料
        all_data = {}
        symbols_needed = list(set(w["symbol"] for w in st.session_state["watchlist"]))
        with st.spinner("載入監控持股資料..."):
            for sym in symbols_needed:
                d = get_stock_data(sym, "6mo")
                if not d.empty:
                    all_data[sym] = d

        # 逐檔分析
        for idx, wl in enumerate(st.session_state["watchlist"]):
            sym = wl["symbol"]
            name = wl["name"]
            buy_price = wl["buy_price"]
            shares = wl.get("shares", 0)
            buy_date = wl["buy_date"]
            strategy = wl["strategy"]

            if sym not in all_data or all_data[sym].empty:
                st.warning(f"⚠️ {name}({sym}) 無法取得資料")
                continue

            df_wl = all_data[sym]
            df_wl = calc_all_indicators(df_wl)
            latest = df_wl.iloc[-1]
            cur_price = float(latest["close"])
            chg = cur_price - buy_price
            chg_pct = chg / buy_price * 100

            # ─── 賣出訊號判斷 ───
            sell_score = 0
            sell_reasons = []
            rsi_val = float(latest["rsi"]) if "rsi" in latest and not pd.isna(latest["rsi"]) else None
            stoch_k = float(latest["stoch_k"]) if "stoch_k" in latest and not pd.isna(latest["stoch_k"]) else None
            stoch_d = float(latest["stoch_d"]) if "stoch_d" in latest and not pd.isna(latest["stoch_d"]) else None
            ma20_val = float(latest["ma20"]) if "ma20" in latest and not pd.isna(latest["ma20"]) else None
            ma60_val = float(latest["ma60"]) if "ma60" in latest and not pd.isna(latest["ma60"]) else None
            vol = float(latest["volume"])
            vol_ma5 = float(latest["volume_ma5"]) if "volume_ma5" in latest and not pd.isna(latest["volume_ma5"]) else None
            bb_u = float(latest["bb_upper"]) if "bb_upper" in latest and not pd.isna(latest["bb_upper"]) else None
            bb_l = float(latest["bb_lower"]) if "bb_lower" in latest and not pd.isna(latest["bb_lower"]) else None

            if strategy == "短期":
                # 短期賣出訊號
                if rsi_val is not None and rsi_val > 75:
                    sell_score += 2
                    sell_reasons.append(f"⚠️ RSI={rsi_val:.1f} 超買，短线獲利了結訊號")
                if stoch_k is not None and stoch_k > 85:
                    sell_score += 2
                    sell_reasons.append(f"⚠️ KD K={stoch_k:.1f} 超買區")
                if vol_ma5 is not None and vol_ma5 > 0 and vol / vol_ma5 > 2.0 and chg < 0:
                    sell_score += 2
                    sell_reasons.append("⚠️ 爆量下跌，主力出貨")
                if bb_u is not None and bb_l is not None and (bb_u - bb_l) > 0:
                    bb_pos = (cur_price - bb_l) / (bb_u - bb_l)
                    if bb_pos > 0.95:
                        sell_score += 1
                        sell_reasons.append("⚠️ 觸及布林上軌")
                if chg_pct > 15:
                    sell_score += 2
                    sell_reasons.append(f"✅ 獲利 {chg_pct:.1f}%，可部分獲利了結")
                elif chg_pct > 8:
                    sell_score += 1
                    sell_reasons.append(f"✅ 獲利 {chg_pct:.1f}%，可考慮減碼")
                if stoch_k is not None and stoch_d is not None and stoch_k < stoch_d and stoch_k > 70:
                    sell_score += 1
                    sell_reasons.append("⚠️ KD 死亡交叉且高檔")
            else:
                # 長期賣出訊號
                if rsi_val is not None and rsi_val > 80:
                    sell_score += 2
                    sell_reasons.append(f"⚠️ RSI={rsi_val:.1f} 嚴重超買，長期高檔")
                if ma20_val is not None and ma60_val is not None and ma20_val < ma60_val:
                    sell_score += 2
                    sell_reasons.append("⚠️ MA20 < MA60，中期趨勢反轉向下")
                if chg_pct > 30:
                    sell_score += 2
                    sell_reasons.append(f"✅ 累積獲利 {chg_pct:.1f}%，可分批獲利了結")
                elif chg_pct > 15:
                    sell_score += 1
                    sell_reasons.append(f"✅ 累積獲利 {chg_pct:.1f}%，可考慮部分減碼")
                if chg_pct < -15:
                    sell_score -= 1
                    sell_reasons.append(f"⚠️ 虧損 {chg_pct:.1f}%，評估是否停損")
                if info and info.get("pe_ratio") and info["pe_ratio"] > 40:
                    sell_score += 1
                    sell_reasons.append(f"⚠️ 本益比 {info['pe_ratio']:.1f} 偏高，估值過熱")

            # 判斷建議
            if sell_score >= 4:
                action = "🔴 技術面偏空"
                action_color = "#ef5350"
            elif sell_score >= 2:
                action = "🟠 技術面轉弱"
                action_color = "#FF9800"
            elif sell_score >= 1:
                action = "🟡 技術面觀望"
                action_color = "#FFC107"
            elif chg_pct > 5:
                action = "🟢 技術面偏多"
                action_color = "#26a69a"
            else:
                action = "🟢 技術面中性"
                action_color = "#26a69a"

            # 顯示卡片
            profit_color = up_color if chg >= 0 else down_color
            strat_icon = "⚡" if strategy == "短期" else "📅"
            total_cost = buy_price * shares
            total_value = cur_price * shares
            total_pnl = total_value - total_cost
            pnl_color = up_color if total_pnl >= 0 else down_color

            with st.container():
                st.markdown(f"""
<div style="background:#1a1a2e;border-left:4px solid {action_color};border-radius:8px;padding:14px 18px;margin:8px 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
    <div>
      <span style="font-size:1.1em;font-weight:bold;">{name} ({sym})</span>
      <span style="font-size:0.8em;color:#888;margin-left:8px;">{strat_icon} {strategy}｜{shares:,} 股</span>
    </div>
    <div style="text-align:right;">
      <span style="font-size:1.3em;font-weight:bold;color:{profit_color};">{chg_pct:+.2f}%</span>
      <span style="font-size:0.85em;color:#aaa;margin-left:8px;">買 {buy_price:.2f} → 現 {cur_price:.2f}</span>
    </div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:6px;flex-wrap:wrap;">
    <div style="font-size:0.85em;color:#aaa;">成本 {total_cost:,.0f} → 現值 {total_value:,.0f}</div>
    <div style="font-size:0.9em;font-weight:bold;color:{pnl_color};">損益 {total_pnl:+,.0f} 元</div>
  </div>
  <div style="margin-top:4px;font-size:0.9em;color:{action_color};font-weight:bold;">{action}</div>
  <div style="font-size:0.8em;color:#888;margin-top:4px;">買入日期：{buy_date}</div>
</div>
""", unsafe_allow_html=True)

                if sell_reasons:
                    with st.expander(f"📋 技術訊號分析 — {name}", expanded=False):
                        for r in sell_reasons:
                            st.markdown(f"- {r}")
                        if sell_score < 1 and chg_pct <= 5:
                            st.markdown("- ℹ️ 目前無明顯技術面賣出訊號")

                # 刪除按鈕
                if st.button(f"🗑️ 移除 {name}", key=f"wl_del_{idx}"):
                    item_id = wl.get("id")
                    if item_id:
                        auth.remove_from_watchlist(st.session_state["username"], item_id)
                    st.session_state["watchlist"] = auth.get_watchlist(st.session_state["username"])
                    st.rerun()

        # 匯出功能
        if st.session_state["watchlist"]:
            st.divider()
            export_data = []
            for wl in st.session_state["watchlist"]:
                sym = wl["symbol"]
                shares = wl.get("shares", 0)
                if sym in all_data and not all_data[sym].empty:
                    d = all_data[sym]
                    d2 = calc_all_indicators(d)
                    latest = d2.iloc[-1]
                    cur = float(latest["close"])
                    chg_pct = (cur - wl["buy_price"]) / wl["buy_price"] * 100
                    total_cost = wl["buy_price"] * shares
                    total_value = cur * shares
                    total_pnl = total_value - total_cost
                else:
                    cur = "N/A"
                    chg_pct = "N/A"
                    total_cost = "N/A"
                    total_value = "N/A"
                    total_pnl = "N/A"
                export_data.append({
                    "股票代碼": wl["symbol"],
                    "股票名稱": wl["name"],
                    "策略": wl["strategy"],
                    "股數": shares,
                    "買入日期": wl["buy_date"],
                    "買入均價": wl["buy_price"],
                    "現價": cur,
                    "損益%": f"{chg_pct:.2f}%" if isinstance(chg_pct, float) else chg_pct,
                    "總成本": f"{total_cost:,.0f}" if isinstance(total_cost, float) else total_cost,
                    "現值": f"{total_value:,.0f}" if isinstance(total_value, float) else total_value,
                    "損益金額": f"{total_pnl:+,.0f}" if isinstance(total_pnl, float) else total_pnl,
                })
            export_df = pd.DataFrame(export_data)
            st.dataframe(export_df, use_container_width=True, hide_index=True)
