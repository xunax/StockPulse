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

st.set_page_config(
    page_title="股票分析系統",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "PingFang TC", "Heiti TC", "Noto Sans TC", "Source Han Sans TC", "Microsoft YaHei", "SimHei", sans-serif;
    }
    .main > div { padding: 0 0.5rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 1px; overflow-x: auto; flex-wrap: nowrap; }
    .stTabs [data-baseweb="tab"] { padding: 6px 10px; font-size: 0.8rem; white-space: nowrap; }
    div[data-testid="stMetricValue"] { font-size: 1.2rem; }
    [data-baseweb="select"] { font-family: "Microsoft JhengHei", "PingFang TC", "Heiti TC", "Noto Sans TC", sans-serif !important; }
    .stButton button { min-height: 44px; }
    .stTextInput input { min-height: 44px; }
    .stSelectbox div[data-baseweb="select"] { min-height: 44px; }
    .stSlider div[data-baseweb="slider"] { padding-top: 0.5rem; padding-bottom: 0.5rem; }
    @media (max-width: 768px) {
        .main > div { padding: 0 0.25rem; }
        .stMarkdown h1 { font-size: 1.3rem !important; }
        .stMarkdown h2 { font-size: 1.1rem !important; }
        .stMarkdown h3 { font-size: 1.0rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.0rem; }
        .stTabs [data-baseweb="tab"] { padding: 4px 6px; font-size: 0.7rem; }
    }
    .stApp header { display: none; }
    .st-emotion-cache-1avcm0n { padding-top: 1rem; }
    .row-widget.stRadio { display: flex; flex-wrap: wrap; }
    .row-widget.stRadio label { font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ─── 登入系統 ───
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""

if not st.session_state["logged_in"]:
    st.title("📈 股票分析系統")

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
col_logo, col_user = st.columns([3, 1])
with col_logo:
    st.title("📈 股票分析")
with col_user:
    st.markdown(f"<div style='text-align:right;padding-top:1rem;'><small>👤 {st.session_state['username']}</small></div>", unsafe_allow_html=True)
    if st.button("🚪 登出", key="btn_logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.rerun()

# ─── Sidebar (params via expander on mobile) ───
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

    st.divider()
    st.header("🔧 技術指標")
    show_ma5 = st.checkbox("5日均線", True, key="ma5")
    show_ma10 = st.checkbox("10日均線", True, key="ma10")
    show_ma20 = st.checkbox("20日均線", True, key="ma20")
    show_ma60 = st.checkbox("60日均線", False, key="ma60")
    show_ma120 = st.checkbox("120日均線", False, key="ma120")
    show_bb = st.checkbox("布林通道", True, key="bb")
    show_kd = st.checkbox("KD 指標", True, key="kd")
    show_volume_profile = st.checkbox("成交量分布圖", False, key="vp")

    st.divider()
    st.header("⚙️ 指標參數")
    rsi_period = st.slider("RSI 計算天數", 6, 30, 14, key="rsi_period")
    bb_period = st.slider("布林通道天數", 10, 40, 20, key="bb_period")
    bb_std = st.slider("布林標準差倍數", 1.0, 3.0, 2.0, 0.1, key="bb_std")
    kd_period = st.slider("KD 計算天數", 5, 30, 14, key="kd_period")

    st.divider()
    st.header("🔄 回測設定")
    strategy_name = st.selectbox("交易策略", list(STRATEGIES.keys()), key="strategy")
    bt_initial = st.number_input("初始資金", 100000, 10000000, 1000000, step=100000, key="bt_init")

    st.divider()
    st.header("⚙️ 策略參數")
    strategy_info = STRATEGIES[strategy_name]
    strategy_params = {}
    for p in strategy_info["params"]:
        strategy_params[p["name"]] = st.slider(
            p["label"], p["min"], p["max"], p["default"],
            step=p["step"], key=f"sp_{p['name']}"
        )

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 技術", "💰 回測", "📋 資料", "📈 對比", "🏛️ 主力", "🔔 監控"])

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
        st.success(f"已從主力動向導向至 **{r_name}({r_code})** 的技術分析頁面")
        st.session_state["redirect_stock"] = None

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    chg = latest["close"] - prev["close"]
    chg_pct = chg / prev["close"] * 100

    all_stocks = {k: v for cat in STOCKS.values() for k, v in cat.items()}
    stock_display_name = all_stocks.get(symbol, symbol)

    st.markdown(f"### 📌 {stock_display_name} ({symbol}) — {df.index[-1].strftime('%m-%d')}")

    col1, col2 = st.columns(2)
    price_color = up_color if chg >= 0 else down_color
    col1.markdown(f"**現價**<br><span style='font-size:1.4em;color:{price_color}'>{latest['close']:.2f}</span><br><small style='color:{price_color}'>{chg:+.2f} ({chg_pct:+.2f}%)</small>", unsafe_allow_html=True)
    col2.markdown(f"**開/高/低/量**<br><span style='font-size:0.95em'>開 {latest['open']:.2f} 高 {latest['high']:.2f} 低 {latest['low']:.2f}</span><br><span style='font-size:0.85em'>量 {latest['volume']:,.0f}</span>", unsafe_allow_html=True)

    if info and info.get("pe_ratio"):
        c1, c2 = st.columns(2)
        c1.markdown(f"**本益比**<br>{info['pe_ratio']:.2f}" if info['pe_ratio'] else "**本益比**<br>N/A", unsafe_allow_html=True)
        c2.markdown(f"**EPS**<br>{info['eps']:.2f}" if info['eps'] else "**EPS**<br>N/A", unsafe_allow_html=True)

    if info and info.get("high_52w") and info.get("low_52w"):
        high_52w = info["high_52w"]
        low_52w = info["low_52w"]
        cur_price = float(latest["close"])
        if high_52w > low_52w:
            pct_52w = (cur_price - low_52w) / (high_52w - low_52w) * 100
            pct_52w = max(0, min(100, pct_52w))
            bar_color = up_color if pct_52w >= 50 else down_color
            theme = st.session_state.get("color_theme", "紅漲綠跌 (台股)")
            bg_color = "#333333" if theme == "紅漲綠跌 (台股)" else "#444444"
            st.markdown(f"""
**📊 52 週股價區間**
<div style="background:{bg_color};border-radius:8px;padding:4px 0;width:100%;position:relative;height:24px;border:1px solid #555;">
  <div style="background:{bar_color};width:{pct_52w:.1f}%;height:100%;border-radius:8px;opacity:0.9;"></div>
  <span style="position:absolute;top:50%;left:0;transform:translateY(-50%);padding-left:8px;font-size:0.7em;color:#ccc;">低 {low_52w:.2f}</span>
  <span style="position:absolute;top:50%;right:0;transform:translateY(-50%);padding-right:8px;font-size:0.7em;color:#ccc;">高 {high_52w:.2f}</span>
  <span style="position:absolute;top:50%;left:{pct_52w:.1f}%;transform:translate(-50%,-50%);font-size:0.7em;color:#fff;background:rgba(0,0,0,0.7);padding:2px 6px;border-radius:4px;">{cur_price:.2f} ({pct_52w:.0f}%)</span>
</div>
""", unsafe_allow_html=True)

    # ─── 預先定義評分所需變數 ───
    close = float(latest["close"])
    vol = float(latest["volume"])
    rsi_val = float(latest["rsi"]) if "rsi" in latest and not pd.isna(latest["rsi"]) else None
    ma5_val = float(latest["ma5"]) if "ma5" in latest and not pd.isna(latest["ma5"]) else None
    ma10_val = float(latest["ma10"]) if "ma10" in latest and not pd.isna(latest["ma10"]) else None
    ma20_val = float(latest["ma20"]) if "ma20" in latest and not pd.isna(latest["ma20"]) else None
    ma60_val = float(latest["ma60"]) if "ma60" in latest and not pd.isna(latest["ma60"]) else None
    ma120_val = float(latest["ma120"]) if "ma120" in latest and not pd.isna(latest["ma120"]) else None
    bb_u = float(latest["bb_upper"]) if "bb_upper" in latest and not pd.isna(latest["bb_upper"]) else None
    bb_l = float(latest["bb_lower"]) if "bb_lower" in latest and not pd.isna(latest["bb_lower"]) else None
    vol_ma5 = float(latest["volume_ma5"]) if "volume_ma5" in latest and not pd.isna(latest["volume_ma5"]) else None
    stoch_k = float(latest["stoch_k"]) if "stoch_k" in latest and not pd.isna(latest["stoch_k"]) else None
    stoch_d = float(latest["stoch_d"]) if "stoch_d" in latest and not pd.isna(latest["stoch_d"]) else None

    s_score = 0
    s_reasons = []

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

    if ma5_val is not None and ma10_val is not None:
        if ma5_val > ma10_val:
            s_score += 5
            s_reasons.append("✅ MA5 > MA10，短線多頭排列")
        else:
            s_score -= 5
            s_reasons.append("⚠️ MA5 < MA10，短線空頭排列")

    l_score = 0
    l_reasons = []

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

    def get_verdict(score):
        if score >= 20:
            return "🟢 強烈建議買入", "#26a69a"
        elif score >= 10:
            return "🟢 偏多，可考慮買入", "#26a69a"
        elif score >= 0:
            return "🟡 中性，建議觀望", "#FF9800"
        elif score >= -15:
            return "🔴 偏空，不建議追高", "#ef5350"
        else:
            return "🔴 強烈不建議買入", "#ef5350"

    s_verdict, s_color = get_verdict(s_score)
    l_verdict, l_color = get_verdict(l_score)

    col_s, col_l = st.columns(2)
    with col_s:
        st.markdown(f"""
<div style="background:#1a1a2e;border:2px solid {s_color};border-radius:12px;padding:10px 14px;margin:8px 0;">
  <div style="font-size:0.95em;font-weight:bold;color:{s_color};">⚡ 短期</div>
  <div style="font-size:0.85em;color:{s_color};">{s_verdict}</div>
  <div style="font-size:0.75em;color:#aaa;">評分：<b style="color:#fff">{s_score}</b></div>
</div>
""", unsafe_allow_html=True)
        with st.expander("📋 短期評估", expanded=False):
            for r in s_reasons:
                st.markdown(f"- {r}")

    with col_l:
        st.markdown(f"""
<div style="background:#1a1a2e;border:2px solid {l_color};border-radius:12px;padding:10px 14px;margin:8px 0;">
  <div style="font-size:0.95em;font-weight:bold;color:{l_color};">📅 長期</div>
  <div style="font-size:0.85em;color:{l_color};">{l_verdict}</div>
  <div style="font-size:0.75em;color:#aaa;">評分：<b style="color:#fff">{l_score}</b></div>
</div>
""", unsafe_allow_html=True)
        with st.expander("📋 長期評估", expanded=False):
            for r in l_reasons:
                st.markdown(f"- {r}")

    indicators = []
    if show_ma5: indicators.append("ma5")
    if show_ma10: indicators.append("ma10")
    if show_ma20: indicators.append("ma20")
    if show_ma60: indicators.append("ma60")
    if show_ma120: indicators.append("ma120")

    fig = plot_candlestick(df, stock_display_name, indicators + ["volume", "rsi", "macd", "kd"], up_color=up_color, down_color=down_color)
    if fig:
        st.plotly_chart(fig, use_container_width=True, key=f"kline_{symbol}_{period}", config={
            "scrollZoom": True,
            "displayModeBar": True,
            "responsive": True,
            "doubleClick": "reset",
            "displaylogo": False,
            "modeBarButtonsToRemove": ["sendDataToCloud", "lasso2d", "select2d", "zoom2d", "pan2d"],
            "modeBarButtonsToAdd": ["drawrect", "eraseshape"],
        })

    if stoch_k is not None and stoch_d is not None:
        kd_icon = "🔴" if stoch_k > 80 else "🟢" if stoch_k < 20 else "🟡"
        kd_label = "超買" if stoch_k > 80 else "超賣" if stoch_k < 20 else "正常"
        cross = "↑ 黃金交叉" if stoch_k > stoch_d and stoch_k < 30 else "↓ 死亡交叉" if stoch_k < stoch_d and stoch_k > 70 else ""
        st.markdown(f"""
<div style="display:flex;gap:8px;flex-wrap:wrap;font-size:0.75rem;margin:4px 0;">
  <span><b>KD</b></span>
  <span>K <b>{stoch_k:.1f}</b></span>
  <span>D <b>{stoch_d:.1f}</b></span>
  <span style="color:{'#ef5350' if stoch_k > 80 else '#26a69a' if stoch_k < 20 else '#FF9800'};">{kd_icon} {kd_label}</span>
  <span style="color:#888;">{cross}</span>
</div>""", unsafe_allow_html=True)

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

    st.markdown("### 📖 指標解讀")
    with st.expander("🔵 K線", expanded=False):
        st.markdown(f"""
- 🔴 紅 K：**收盤 > 開盤**（上漲） 🟢 綠 K：**收盤 < 開盤**（下跌）
- 當前收盤：**{close:.2f}**，距 20日高點 {resistance:.2f}（{resistance-close:.2f}），低點 {support:.2f}（{close-support:.2f}）
""")

    with st.expander("📈 均線（MA）", expanded=False):
        ma_texts = []
        if ma5_val is not None and ma20_val is not None:
            if ma5_val > ma20_val:
                ma_texts.append(f"✅ 5日({ma5_val:.1f}) > 20日({ma20_val:.1f}) — 短線偏多")
            else:
                ma_texts.append(f"⚠️ 5日({ma5_val:.1f}) < 20日({ma20_val:.1f}) — 短線偏空")
        if ma20_val is not None and ma60_val is not None:
            if ma20_val > ma60_val:
                ma_texts.append(f"✅ 20日({ma20_val:.1f}) > 60日({ma60_val:.1f}) — 中期向上")
            else:
                ma_texts.append(f"⚠️ 20日({ma20_val:.1f}) < 60日({ma60_val:.1f}) — 中期向下")
        st.markdown(chr(10).join(ma_texts) if ma_texts else "資料不足")

    with st.expander(f"📊 RSI（{rsi_period}日）", expanded=False):
        if rsi_val is not None:
            if rsi_val >= 70:
                zone = "⚠️ 超買區（70↑）"
                strategy = "不建議追高"
            elif rsi_val <= 30:
                zone = "💡 超賣區（30↓）"
                strategy = "可分批進場"
            elif rsi_val >= 50:
                zone = "✅ 偏多區（50-70）"
                strategy = "順勢操作"
            else:
                zone = "⚠️ 偏空區（30-50）"
                strategy = "觀望為主"
            st.markdown(f"**當前值：{rsi_val:.1f} — {zone}**\n\n📌 建議：{strategy}")

    with st.expander("📉 MACD", expanded=False):
        if macd_val is not None and macd_sig is not None:
            if macd_val > macd_sig and macd_hist is not None and macd_hist > 0:
                state = "✅ 多頭訊號"
            elif macd_val < macd_sig and macd_hist is not None and macd_hist < 0:
                state = "⚠️ 空頭訊號"
            elif macd_val > macd_sig:
                state = "🔄 轉強中"
            else:
                state = "🔄 轉弱中"
            st.markdown(f"**{state}**")

    with st.expander("🔀 KD（0~100）", expanded=False):
        if stoch_k is not None and stoch_d is not None:
            if stoch_k >= 80:
                kd_zone = "⚠️ 超買區"
                kd_strategy = "不建議追高"
            elif stoch_k <= 20:
                kd_zone = "💡 超賣區"
                kd_strategy = "可留意反彈"
            elif stoch_k > stoch_d:
                kd_zone = "✅ 偏多"
                kd_strategy = "順勢操作"
            else:
                kd_zone = "⚠️ 偏空"
                kd_strategy = "觀望為主"
            st.markdown(f"K={stoch_k:.1f} D={stoch_d:.1f} — {kd_zone}\n\n📌 {kd_strategy}")

    with st.expander("📦 布林通道", expanded=False):
        if bb_u is not None and bb_l is not None:
            bb_width = (bb_u - bb_l) / close * 100
            bb_pct = (close - bb_l) / (bb_u - bb_l) * 100 if (bb_u - bb_l) > 0 else 50
            if close >= bb_u * 0.99:
                bb_zone = "🔴 接近上軌（過熱）"
            elif close <= bb_l * 1.01:
                bb_zone = "🟢 接近下軌（超跌）"
            elif bb_pct > 50:
                bb_zone = "✅ 上半部（偏多）"
            else:
                bb_zone = "⚠️ 下半部（偏空）"
            st.markdown(f"上軌 {bb_u:.2f} 下軌 {bb_l:.2f} | 寬度 {bb_width:.1f}%\n位置 {bb_pct:.0f}% — {bb_zone}")

    with st.expander("📊 成交量", expanded=False):
        if vol_ma5 is not None:
            vol_ratio = vol / vol_ma5 if vol_ma5 > 0 else 1
            if vol_ratio >= 1.5:
                vol_text = "🔥 爆量"
            elif vol_ratio >= 0.8:
                vol_text = "✅ 正常量"
            else:
                vol_text = "⚠️ 縮量"
            st.markdown(f"今日 {vol:,.0f} | 5日均 {vol_ma5:,.0f} | 量比 {vol_ratio:.2f} 倍\n{vol_text}")

    with st.expander("📌 支撐與壓力", expanded=False):
        dist_to_res = (resistance - close) / close * 100
        dist_to_sup = (close - support) / close * 100
        st.markdown(f"🔴 **壓力：{resistance:.2f}**（距現價 {dist_to_res:+.2f}%）\n🟢 **支撐：{support:.2f}**（距現價 {dist_to_sup:+.2f}%）")

    st.markdown("### 🔮 綜合分析")
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
            signals.append(("中期", "偏多", "20日線在60日線之上"))
            bullish += 1
        else:
            signals.append(("中期", "偏空", "20日線在60日線之下"))
            bearish += 1

    if rsi_val is not None:
        if rsi_val >= 70:
            signals.append(("RSI", "過熱", f"{rsi_val:.1f} 超買區"))
            bearish += 1
        elif rsi_val <= 30:
            signals.append(("RSI", "超跌", f"{rsi_val:.1f} 超賣區"))
            bullish += 1
        elif rsi_val >= 50:
            signals.append(("RSI", "偏多", f"{rsi_val:.1f} 偏多區"))
            bullish += 1
        else:
            signals.append(("RSI", "偏空", f"{rsi_val:.1f} 偏空區"))
            bearish += 1

    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig:
            signals.append(("MACD", "偏多", "MACD在信號線之上"))
            bullish += 1
        else:
            signals.append(("MACD", "偏空", "MACD在信號線之下"))
            bearish += 1

    if stoch_k is not None and stoch_d is not None:
        if stoch_k >= 80:
            signals.append(("KD", "過熱", f"K={stoch_k:.1f} 超買區"))
            bearish += 1
        elif stoch_k <= 20:
            signals.append(("KD", "超跌", f"K={stoch_k:.1f} 超賣區"))
            bullish += 1
        elif stoch_k > stoch_d:
            signals.append(("KD", "偏多", f"K={stoch_k:.1f} > D={stoch_d:.1f}"))
            bullish += 1
        else:
            signals.append(("KD", "偏空", f"K={stoch_k:.1f} < D={stoch_d:.1f}"))
            bearish += 1

    if vol_ma5 is not None:
        vol_ratio = vol / vol_ma5 if vol_ma5 > 0 else 1
        prev_close = float(df.iloc[-2]["close"])
        if vol_ratio >= 1.5 and close > prev_close:
            signals.append(("量能", "偏多", "價漲量增"))
            bullish += 1
        elif vol_ratio >= 1.5 and close < prev_close:
            signals.append(("量能", "偏空", "價跌量增"))
            bearish += 1
        elif vol_ratio < 0.8 and close > prev_close:
            signals.append(("量能", "偏空", "價漲量縮"))
            bearish += 1
        elif vol_ratio < 0.8 and close < prev_close:
            signals.append(("量能", "偏多", "價跌量縮"))
            bullish += 1

    if close >= resistance * 0.98:
        signals.append(("位置", "接近壓力", f"距壓力 {resistance:.2f} 不到 2%"))
    elif close <= support * 1.02:
        signals.append(("位置", "接近支撐", f"距支撐 {support:.2f} 不到 2%"))

    total = bullish + bearish
    if total == 0:
        overall = "⚪ **訊號不明**"
    elif bullish >= bearish + 2:
        overall = "🟢 **強烈偏多**"
    elif bullish > bearish:
        overall = "🟢 **偏多**"
    elif bearish > bullish + 1:
        overall = "🔴 **強烈偏空**"
    else:
        overall = "🔴 **偏空**"

    st.markdown(f"**{overall}** ｜ 多 {bullish} 票 / 空 {bearish} 票")

    signal_df_rows = []
    for name, verdict, detail in signals:
        if "偏多" in verdict or "超跌" in verdict:
            color = "🟢"
        elif "偏空" in verdict or "過熱" in verdict:
            color = "🔴"
        else:
            color = "🟡"
        signal_df_rows.append([color, name, verdict, detail])
    st.dataframe(
        pd.DataFrame(signal_df_rows, columns=["", "指標", "訊號", "說明"]),
        hide_index=True, use_container_width=True,
    )

    st.caption("⚠️ 以上分析僅基於技術指標，非投資建議。")

    if show_volume_profile:
        fig_vp = plot_volume_profile(df)
        if fig_vp:
            st.plotly_chart(fig_vp, use_container_width=True, key=f"vp_{symbol}_{period}")

    with st.expander("📊 最新技術指標數值", expanded=False):
        latest_indicators = {
            f"RSI({rsi_period}日)": f"{latest['rsi']:.2f}" if "rsi" in latest and not pd.isna(latest['rsi']) else "N/A",
            "MACD": f"{latest['macd']:.2f}" if "macd" in latest and not pd.isna(latest['macd']) else "N/A",
            "KD K值": f"{latest['stoch_k']:.2f}" if "stoch_k" in latest and not pd.isna(latest['stoch_k']) else "N/A",
            "KD D值": f"{latest['stoch_d']:.2f}" if "stoch_d" in latest and not pd.isna(latest['stoch_d']) else "N/A",
            "布林上軌": f"{latest['bb_upper']:.2f}" if "bb_upper" in latest and not pd.isna(latest['bb_upper']) else "N/A",
            "布林下軌": f"{latest['bb_lower']:.2f}" if "bb_lower" in latest and not pd.isna(latest['bb_lower']) else "N/A",
        }
        st.dataframe(
            pd.DataFrame(list(latest_indicators.items()), columns=["指標", "數值"]),
            use_container_width=True, hide_index=True,
        )

# ═══════════════════════════════════════
# TAB 2: 回測系統
# ═══════════════════════════════════════
with tab2:
    st.subheader(f"📈 策略回測 - {strategy_name}")

    col_params = st.columns(2)
    with col_params[0]:
        bt_start = st.date_input("開始日", df.index[0].date() if len(df) > 0 else datetime.now() - timedelta(days=365))
    with col_params[1]:
        bt_end = st.date_input("結束日", df.index[-1].date() if len(df) > 0 else datetime.now())

    bt_commission = st.number_input("手續費率", 0.0, 0.01, 0.001425, format="%.6f")

    if st.button("🚀 開始回測", type="primary", use_container_width=True):
        bt_df = df[(df.index >= pd.Timestamp(bt_start)) & (df.index <= pd.Timestamp(bt_end))]
        if len(bt_df) < 50:
            st.warning("資料筆數不足，請選擇更長的區間")
        else:
            strategy_fn = strategy_info["fn"]
            result = backtest(bt_df, strategy_fn, initial_cash=bt_initial,
                              commission=bt_commission, strategy_params=strategy_params)

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
            key_metrics = ["total_return", "annual_return", "sharpe_ratio", "max_drawdown", "win_rate", "total_trades", "final_value"]
            rows = [[metric_names.get(k, k), fmt_map.get(k, str(v))]
                    for k in key_metrics if k in mt]
            st.dataframe(pd.DataFrame(rows, columns=["指標", "數值"]), hide_index=True, use_container_width=True)

            with st.expander("📈 權益曲線", expanded=True):
                ec = result.equity_curve
                fig_ec = go.Figure()
                fig_ec.add_trace(go.Scatter(
                    x=ec.index, y=ec.values,
                    mode="lines", name="權益曲線",
                    line=dict(color="#2196F3", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(33, 150, 243, 0.1)",
                ))
                rolling_max = ec.expanding().max()
                fig_ec.add_trace(go.Scatter(
                    x=ec.index, y=rolling_max,
                    mode="lines", name="歷史高點",
                    line=dict(color="rgba(255,0,0,0.3)", width=1, dash="dash"),
                ))
                fig_ec.add_hline(y=bt_initial, line_dash="dash", line_color="gray")
                fig_ec.update_layout(height=300, template="plotly_white", hovermode="x unified", margin=dict(l=30, r=30, t=20, b=20))
                st.plotly_chart(fig_ec, use_container_width=True)

            with st.expander("📉 回撤曲線", expanded=False):
                ec = result.equity_curve
                rolling_max = ec.expanding().max()
                drawdown = (ec - rolling_max) / rolling_max * 100
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(
                    x=ec.index, y=drawdown,
                    mode="lines", name="回撤",
                    line=dict(color="#ef5350", width=1.5),
                    fill="tozeroy",
                    fillcolor="rgba(239, 83, 80, 0.1)",
                ))
                fig_dd.update_layout(height=200, template="plotly_white", hovermode="x unified", margin=dict(l=30, r=30, t=20, b=20))
                st.plotly_chart(fig_dd, use_container_width=True)

            if result.trades:
                with st.expander("🔄 逐筆交易", expanded=False):
                    trade_records = []
                    for t in result.trades:
                        trade_records.append({
                            "買日": t.buy_date.strftime("%m-%d"),
                            "賣日": t.sell_date.strftime("%m-%d"),
                            "買價": f"{t.buy_price:.2f}",
                            "賣價": f"{t.sell_price:.2f}",
                            "報酬率": f"{t.return_pct:+.2f}%",
                            "持有": f"{t.holding_days}天",
                        })
                    st.dataframe(pd.DataFrame(trade_records), hide_index=True, use_container_width=True)

            if result.orders:
                with st.expander("📋 交易流水帳", expanded=False):
                    records = []
                    for o in result.orders:
                        records.append({
                            "日期": o.date.strftime("%m-%d"),
                            "動作": "買" if o.action == Action.BUY else "賣",
                            "價格": f"{o.price:.2f}",
                            "股數": f"{o.shares:.0f}",
                            "金額": f"{o.value:,.0f}",
                        })
                    st.dataframe(pd.DataFrame(records), hide_index=True, use_container_width=True)
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
    df_display.index = pd.to_datetime(df_display.index).strftime("%m-%d")

    st.dataframe(
        df_display.sort_index(ascending=False),
        use_container_width=True,
        height=400,
    )

    csv = df_display.to_csv().encode("utf-8-sig")
    st.download_button(
        label="📥 下載 CSV",
        data=csv,
        file_name=f"{symbol}_data.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ═══════════════════════════════════════
# TAB 4: 多股走勢對比
# ═══════════════════════════════════════
with tab4:
    st.subheader("📈 多股累計報酬率對比")

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
        compare_period_label = st.selectbox("區間", list(compare_period_map.keys()), index=3, key="compare_period")
        compare_period = compare_period_map[compare_period_label]
    with col_c2:
        normalize_start = st.checkbox("從起始日歸一化", value=True, key="normalize_start")

    if st.button("🔍 開始比較", type="primary", use_container_width=True, key="btn_compare"):
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
                st.warning(f"無法取得：{', '.join(failed)}")

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
                        mode="lines", name=name_label,
                        line=dict(color=color, width=2),
                    ))

                y_title = "累計報酬率 (%)" if normalize_start else "股價"
                fig_compare.update_layout(
                    title=f"多股走勢對比 — {compare_period_label}",
                    template="plotly_white",
                    hovermode="x unified",
                    height=350,
                    margin=dict(l=30, r=30, t=40, b=20),
                    legend=dict(font=dict(size=10)),
                )
                if normalize_start:
                    fig_compare.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_compare, use_container_width=True)

                summary_records = []
                for idx, (sym, d) in enumerate(all_data.items()):
                    name_label = f"{all_names[sym]} ({sym})"
                    prices = d["close"].values
                    start_price = prices[0]
                    end_price = prices[-1]
                    total_return = (end_price / start_price - 1) * 100
                    summary_records.append({
                        "股票": name_label,
                        "報酬": f"{total_return:+.2f}%",
                    })
                st.dataframe(pd.DataFrame(summary_records), hide_index=True, use_container_width=True)

# ═══════════════════════════════════════
# TAB 5: 主力動向分析
# ═══════════════════════════════════════
with tab5:
    st.subheader("🏛️ 主力買賣超動向")
    st.caption("透過價量結構分析，非實際法人進出場資料。")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        market_type = st.selectbox("市場", ["全部市場", "台股", "美股", "ETF"], key="inst_market")
    with col_f2:
        inst_period_map = {"1 個月": "1mo", "3 個月": "3mo", "6 個月": "6mo", "1 年": "1y"}
        inst_period_label = st.selectbox("區間", list(inst_period_map.keys()), index=1, key="inst_period")
        inst_period = inst_period_map[inst_period_label]

    if st.button("🔍 分析主力動向", type="primary", use_container_width=True, key="btn_inst"):
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
                            reasons.append(f"近期{big_vol_down}日放量大跌")
                        elif big_vol_down >= 1:
                            score -= 1
                            reasons.append(f"近期{big_vol_down}日放量下跌")

                        if big_down_days >= 3:
                            score -= 2
                            reasons.append(f"近10日{big_down_days}日大跌>3%")

                        if drop_from_high >= 15:
                            score -= 2
                            reasons.append(f"從高點回撤{drop_from_high:.1f}%")
                        elif drop_from_high >= 8:
                            score -= 1
                            reasons.append(f"從高點回撤{drop_from_high:.1f}%")

                        if vol_ratio >= 2.0:
                            if drop_from_high >= 8:
                                score -= 2
                                reasons.append("爆量但高點回落")
                            else:
                                score += 2
                                reasons.append(f"爆量({vol_ratio:.1f}倍)")
                        elif vol_ratio >= 1.5:
                            if drop_from_high >= 8:
                                score -= 1
                                reasons.append("放量但高點回落")
                            else:
                                score += 1
                                reasons.append(f"放量({vol_ratio:.1f}倍)")
                        elif vol_ratio < 0.5:
                            score -= 1
                            reasons.append(f"極度縮量({vol_ratio:.1f}倍)")

                        if vol_5ratio >= 1.3:
                            if big_vol_down >= 2:
                                reasons.append("近5日量放大但有出貨")
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
                            reasons.append("均線多頭")
                        else:
                            score -= 1
                            reasons.append("均線空頭")

                        if gap_up > 3:
                            if vol_ratio < 1.0:
                                score -= 1
                                reasons.append("跳空高開量縮")
                            elif drop_from_high >= 10:
                                reasons.append("跳空高開但距高點仍遠")
                            else:
                                reasons.append("跳空高開帶量")

                        if up_days >= 4:
                            score += 1
                            reasons.append(f"近5日{up_days}日上漲")
                        elif up_days <= 1:
                            reasons.append(f"近5日僅{up_days}日上漲")

                        if limit_up:
                            if vol_ratio < 1.2:
                                score -= 2
                                reasons.append("漲停量縮(主力鎖碼)")
                            elif drop_from_high >= 10:
                                reasons.append("漲停但距高點仍遠")
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
            m1.metric("🔴 買超", f"{len(buy_all)} 檔")
            m2.metric("🟢 賣超", f"{len(sell_all)} 檔")
            m3.metric("👀 觀察", f"{len(observe)} 檔")
            m4.metric("📊 總計", f"{len(all_flat)} 檔")

            st.markdown("### 🏆 TOP 10 買超")
            top10 = sorted(all_flat, key=lambda x: x["score"], reverse=True)[:10]
            st.dataframe(
                pd.DataFrame([{
                    "訊號": r["signal"], "代碼": r["code"], "名稱": r["name"],
                    "最新價": f"{r['price_end']:.2f}", "強度": r["score"],
                } for r in top10]),
                hide_index=True, use_container_width=True,
            )

            st.markdown("### 📉 TOP 10 賣超")
            bottom10 = sorted(all_flat, key=lambda x: x["score"])[:10]
            st.dataframe(
                pd.DataFrame([{
                    "訊號": r["signal"], "代碼": r["code"], "名稱": r["name"],
                    "最新價": f"{r['price_end']:.2f}", "強度": r["score"],
                } for r in bottom10]),
                hide_index=True, use_container_width=True,
            )

            for full_key, stocks in all_analysis.items():
                if not stocks:
                    continue
                sorted_stocks = sorted(stocks, key=lambda x: x["score"], reverse=True)
                buy_count = len([s for s in stocks if "買超" in s["signal"]])
                sell_count = len([s for s in stocks if "賣超" in s["signal"]])
                avg_score = np.mean([s["score"] for s in stocks])
                tag = "🔴 偏多" if avg_score >= 2 else "🟢 偏空" if avg_score <= -2 else "⚪ 中性"

                with st.expander(f"**{full_key}** {tag} — 買{buy_count}/賣{sell_count}/共{len(stocks)}", expanded=False):
                    table_records = []
                    for r in sorted_stocks:
                        table_records.append({
                            "訊號": r["signal"], "代碼": r["code"], "名稱": r["name"],
                            "最新價": f"{r['price_end']:.2f}",
                            "日漲跌": f"{r['daily_chg']:+.2f}%",
                            "量比": f"{r['vol_ratio']:.2f}倍",
                            "強度": r["score"],
                        })
                    st.dataframe(pd.DataFrame(table_records), hide_index=True, use_container_width=True)

                    st.markdown("**點擊查看詳細分析：**")
                    btn_cols = st.columns(min(len(sorted_stocks), 4))
                    for idx, r in enumerate(sorted_stocks):
                        col_idx = idx % len(btn_cols)
                        with btn_cols[col_idx]:
                            if st.button(f"📊 {r['name']}", key=f"goto_m_{full_key}_{r['code']}"):
                                st.session_state["redirect_stock"] = r["code"]
                                st.session_state["redirect_name"] = r["name"]
                                st.session_state["input_mode"] = "手動輸入"
                                st.session_state["manual_symbol"] = r["code"]
                                st.rerun()

            st.markdown("---")
            st.caption("⚠️ 以上分析基於價量技術面推估，非實際法人進出場資料。")

# ═══════════════════════════════════════
# TAB 6: 持股監控
# ═══════════════════════════════════════
with tab6:
    st.subheader("🔔 持股監控")

    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = auth.get_watchlist(st.session_state["username"])

    with st.expander("➕ 新增持股", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            wl_symbol = st.text_input("股票代碼", "2330", key="wl_sym")
            wl_price = st.number_input("買入均價", min_value=0.0, value=600.0, step=0.1, key="wl_price")
            wl_date = st.date_input("買入日期", key="wl_date")
        with c2:
            wl_name = st.text_input("股票名稱", "台積電", key="wl_name")
            wl_shares = st.number_input("購買股數", min_value=1, value=1000, step=100, key="wl_shares")
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
            exists = any(w["symbol"] == entry["symbol"] and w["buy_price"] == entry["buy_price"] for w in st.session_state["watchlist"])
            if not exists:
                auth.add_to_watchlist(st.session_state["username"], entry)
                st.session_state["watchlist"] = auth.get_watchlist(st.session_state["username"])
                st.success(f"已加入 {entry['name']}({entry['symbol']})")
                st.rerun()
            else:
                st.warning("此持股已在監控列表中")

    if not st.session_state["watchlist"]:
        st.info("尚無監控持股，請先新增。")
    else:
        st.markdown(f"### 📋 監控列表（{len(st.session_state['watchlist'])} 檔）")
        all_data = {}
        symbols_needed = list(set(w["symbol"] for w in st.session_state["watchlist"]))
        with st.spinner("載入監控持股資料..."):
            for sym in symbols_needed:
                d = get_stock_data(sym, "6mo")
                if not d.empty:
                    all_data[sym] = d

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

            sell_score = 0
            sell_reasons = []
            rsi_val_wl = float(latest["rsi"]) if "rsi" in latest and not pd.isna(latest["rsi"]) else None
            stoch_k_wl = float(latest["stoch_k"]) if "stoch_k" in latest and not pd.isna(latest["stoch_k"]) else None
            stoch_d_wl = float(latest["stoch_d"]) if "stoch_d" in latest and not pd.isna(latest["stoch_d"]) else None
            ma20_val_wl = float(latest["ma20"]) if "ma20" in latest and not pd.isna(latest["ma20"]) else None
            ma60_val_wl = float(latest["ma60"]) if "ma60" in latest and not pd.isna(latest["ma60"]) else None
            vol_wl = float(latest["volume"])
            vol_ma5_wl = float(latest["volume_ma5"]) if "volume_ma5" in latest and not pd.isna(latest["volume_ma5"]) else None
            bb_u_wl = float(latest["bb_upper"]) if "bb_upper" in latest and not pd.isna(latest["bb_upper"]) else None
            bb_l_wl = float(latest["bb_lower"]) if "bb_lower" in latest and not pd.isna(latest["bb_lower"]) else None

            if strategy == "短期":
                if rsi_val_wl is not None and rsi_val_wl > 75:
                    sell_score += 2
                    sell_reasons.append(f"⚠️ RSI={rsi_val_wl:.1f} 超買")
                if stoch_k_wl is not None and stoch_k_wl > 85:
                    sell_score += 2
                    sell_reasons.append(f"⚠️ KD K={stoch_k_wl:.1f} 超買")
                if vol_ma5_wl is not None and vol_ma5_wl > 0 and vol_wl / vol_ma5_wl > 2.0 and chg < 0:
                    sell_score += 2
                    sell_reasons.append("⚠️ 爆量下跌")
                if bb_u_wl is not None and bb_l_wl is not None and (bb_u_wl - bb_l_wl) > 0:
                    bb_pos = (cur_price - bb_l_wl) / (bb_u_wl - bb_l_wl)
                    if bb_pos > 0.95:
                        sell_score += 1
                        sell_reasons.append("⚠️ 觸及布林上軌")
                if chg_pct > 15:
                    sell_score += 2
                    sell_reasons.append(f"✅ 獲利 {chg_pct:.1f}%")
                elif chg_pct > 8:
                    sell_score += 1
                    sell_reasons.append(f"✅ 獲利 {chg_pct:.1f}%")
                if stoch_k_wl is not None and stoch_d_wl is not None and stoch_k_wl < stoch_d_wl and stoch_k_wl > 70:
                    sell_score += 1
                    sell_reasons.append("⚠️ KD 死亡交叉")
            else:
                if rsi_val_wl is not None and rsi_val_wl > 80:
                    sell_score += 2
                    sell_reasons.append(f"⚠️ RSI={rsi_val_wl:.1f} 嚴重超買")
                if ma20_val_wl is not None and ma60_val_wl is not None and ma20_val_wl < ma60_val_wl:
                    sell_score += 2
                    sell_reasons.append("⚠️ MA20 < MA60，趨勢翻空")
                if chg_pct > 30:
                    sell_score += 2
                    sell_reasons.append(f"✅ 獲利 {chg_pct:.1f}%")
                elif chg_pct > 15:
                    sell_score += 1
                    sell_reasons.append(f"✅ 獲利 {chg_pct:.1f}%")
                if chg_pct < -15:
                    sell_score -= 1
                    sell_reasons.append(f"⚠️ 虧損 {chg_pct:.1f}%")
                if info and info.get("pe_ratio") and info["pe_ratio"] > 40:
                    sell_score += 1
                    sell_reasons.append(f"⚠️ 本益比 {info['pe_ratio']:.1f} 偏高")

            if sell_score >= 4:
                action = "🔴 強烈建議賣出"
                action_color = "#ef5350"
            elif sell_score >= 2:
                action = "🟠 建議考慮賣出"
                action_color = "#FF9800"
            elif sell_score >= 1:
                action = "🟡 可觀察賣出"
                action_color = "#FFC107"
            elif chg_pct > 5:
                action = "🟢 繼續持有"
                action_color = "#26a69a"
            else:
                action = "🟢 觀望持有"
                action_color = "#26a69a"

            profit_color = up_color if chg >= 0 else down_color
            strat_icon = "⚡" if strategy == "短期" else "📅"
            total_cost = buy_price * shares
            total_value = cur_price * shares
            total_pnl = total_value - total_cost
            pnl_color = up_color if total_pnl >= 0 else down_color

            with st.container():
                st.markdown(f"""
<div style="background:#1a1a2e;border-left:4px solid {action_color};border-radius:8px;padding:10px 14px;margin:6px 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
    <div>
      <span style="font-size:1em;font-weight:bold;">{name} ({sym})</span>
      <span style="font-size:0.75em;color:#888;margin-left:6px;">{strat_icon} {shares:,}股</span>
    </div>
    <div style="text-align:right;">
      <span style="font-size:1.2em;font-weight:bold;color:{profit_color};">{chg_pct:+.2f}%</span>
    </div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:4px;flex-wrap:wrap;">
    <div style="font-size:0.8em;color:#aaa;">買 {buy_price:.2f} → 現 {cur_price:.2f}</div>
    <div style="font-size:0.85em;font-weight:bold;color:{pnl_color};">{total_pnl:+,.0f} 元</div>
  </div>
  <div style="margin-top:2px;font-size:0.85em;color:{action_color};font-weight:bold;">{action}</div>
</div>
""", unsafe_allow_html=True)

                if sell_reasons:
                    with st.expander(f"📋 訊號分析", expanded=False):
                        for r in sell_reasons:
                            st.markdown(f"- {r}")

                if st.button(f"🗑️ 移除 {name}", key=f"wl_del_{idx}", use_container_width=True):
                    item_id = wl.get("id")
                    if item_id:
                        auth.remove_from_watchlist(st.session_state["username"], item_id)
                    st.session_state["watchlist"] = auth.get_watchlist(st.session_state["username"])
                    st.rerun()
