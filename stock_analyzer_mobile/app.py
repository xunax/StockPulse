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
    .main > div { padding: 0 1rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; overflow-x: auto; flex-wrap: nowrap; margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab"] { padding: 8px 14px; font-size: 0.85rem; white-space: nowrap; border-radius: 8px 8px 0 0; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
    div[data-testid="stMetricDelta"] { font-size: 0.85rem; }
    div[data-testid="stMetricLabel"] { font-size: 0.8rem; }
    [data-baseweb="select"] { font-family: "Microsoft JhengHei", "PingFang TC", "Heiti TC", "Noto Sans TC", sans-serif !important; }
    .stButton button { min-height: 48px; border-radius: 12px; font-size: 1rem; }
    .stTextInput input { min-height: 48px; border-radius: 12px; font-size: 1rem; }
    .stSelectbox div[data-baseweb="select"] { min-height: 48px; border-radius: 12px; }
    .stSlider div[data-baseweb="slider"] { padding-top: 0.8rem; padding-bottom: 0.8rem; }
    @media (max-width: 768px) {
        .main > div { padding: 0 0.75rem; }
        .stMarkdown h1 { font-size: 1.5rem !important; }
        .stMarkdown h2 { font-size: 1.2rem !important; }
        .stMarkdown h3 { font-size: 1.1rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.3rem; }
        .stTabs [data-baseweb="tab"] { padding: 6px 10px; font-size: 0.75rem; }
    }
    .stApp header { display: none; }
    .st-emotion-cache-1avcm0n { padding-top: 1rem; }
    .element-container { margin-bottom: 0.5rem; }
    div.stMarkdown p { line-height: 1.6; }
    .card { background: #1a1a2e; border-radius: 16px; padding: 16px 20px; margin: 12px 0; }
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

# ─── 初始化預設值 ───
if "init_defaults" not in st.session_state:
    st.session_state.init_defaults = True
    st.session_state.input_mode = "下拉選擇"
    st.session_state.color_theme = "紅漲綠跌"
    st.session_state.cat = "台股"
    st.session_state.stock_select = "2330"
    st.session_state.manual_symbol = "2330"
    st.session_state.period = "1 年"
    st.session_state.ma5 = True
    st.session_state.ma10 = True
    st.session_state.ma20 = True
    st.session_state.bb = True
    st.session_state.kd = True
    st.session_state.rsi_period = 14
    st.session_state.bb_period = 20
    st.session_state.bb_std = 2.0
    st.session_state.kd_period = 14
    st.session_state.strategy = "均線黃金交叉"

tab_select, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 選擇", "📊 技術", "💰 回測", "📋 資料", "📈 對比", "🏛️ 主力", "🔔 監控"])

# ─── 讀取 session_state 中的選擇值 ───
input_mode = st.session_state.get("input_mode", "下拉選擇")
color_theme = st.session_state.get("color_theme", "紅漲綠跌")
up_color = "#ef5350" if color_theme == "紅漲綠跌" else "#26a69a"
down_color = "#26a69a" if color_theme == "紅漲綠跌" else "#ef5350"

if input_mode == "下拉選擇":
    cat = st.session_state.get("cat", "台股")
    stock_options = STOCKS.get(cat, {})
    code_list = list(stock_options.keys())
    sym = st.session_state.get("stock_select", "2330")
    symbol = sym if sym in code_list else (code_list[0] if code_list else "2330")
    stock_name = stock_options.get(symbol, symbol)
else:
    symbol = st.session_state.get("manual_symbol", "2330").strip()
    stock_name = symbol

period_map = {"1 個月": "1mo", "3 個月": "3mo", "6 個月": "6mo", "1 年": "1y", "2 年": "2y", "5 年": "5y"}
period_label = st.session_state.get("period", "1 年")
period = period_map.get(period_label, "1y")

strategy_name = st.session_state.get("strategy", "均線黃金交叉")
strategy_info = STRATEGIES[strategy_name]
strategy_params = {}
for p in strategy_info["params"]:
    strategy_params[p["name"]] = st.session_state.get(f"sp_{p['name']}", p["default"])

rsi_period = st.session_state.get("rsi_period", 14)
bb_period = st.session_state.get("bb_period", 20)
bb_std = st.session_state.get("bb_std", 2.0)
kd_period = st.session_state.get("kd_period", 14)

show_ma5 = st.session_state.get("ma5", True)
show_ma10 = st.session_state.get("ma10", True)
show_ma20 = st.session_state.get("ma20", True)
show_ma60 = st.session_state.get("ma60", False)
show_ma120 = st.session_state.get("ma120", False)
show_bb = st.session_state.get("bb", True)
show_kd = st.session_state.get("kd", True)
show_volume_profile = st.session_state.get("vp", False)
bt_initial = st.session_state.get("bt_init", 1000000)

# ─── Load data（共用） ───
with st.spinner("載入資料中..."):
    df = get_stock_data(symbol, period)
    info = get_stock_info(symbol)

if df.empty:
    st.error("無法取得股票資料，請確認代碼是否正確")
    st.stop()

df = calc_all_indicators(df, rsi_period=rsi_period, bb_period=bb_period, bb_std=bb_std, kd_period=kd_period)

all_stocks_flat = {k: v for cat in STOCKS.values() for k, v in cat.items()}
stock_display_name = all_stocks_flat.get(symbol, symbol)

# ═══════════════════════════════════════
# TAB 1: 技術分析
# ═══════════════════════════════════════
# ═══════════════════════════════════════
# TAB 0: 選擇股票
# ═══════════════════════════════════════
with tab_select:
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = True

    btn_label = "🔍 收起設定" if st.session_state.show_settings else "🔍 展開設定"
    if st.button(btn_label, use_container_width=True, type="secondary"):
        st.session_state.show_settings = not st.session_state.show_settings

    if st.session_state.show_settings:
        st.radio("輸入方式", ["下拉選擇", "手動輸入"], horizontal=True, key="input_mode")
        st.radio("漲跌配色", ["紅漲綠跌", "綠漲紅跌"], horizontal=True, key="color_theme")

        if st.session_state.input_mode == "下拉選擇":
            col_a, col_b = st.columns(2)
            with col_a:
                st.selectbox("分類", list(STOCKS.keys()), key="cat")
                stock_options_ui = STOCKS.get(st.session_state.cat, {})
                code_list_ui = list(stock_options_ui.keys())
            with col_b:
                if st.session_state.get("stock_select") not in code_list_ui:
                    st.session_state.stock_select = code_list_ui[0] if code_list_ui else "2330"
                st.selectbox("標的", code_list_ui, key="stock_select", format_func=lambda c: stock_options_ui.get(c, c))
        else:
            st.text_input("股票代碼", "2330", key="manual_symbol")

        st.selectbox("資料區間", list(period_map.keys()), index=3, key="period")

        st.divider()
        st.markdown("**🔧 技術指標**")
        col_x1, col_x2 = st.columns(2)
        with col_x1:
            st.checkbox("5日均線", True, key="ma5")
            st.checkbox("10日均線", True, key="ma10")
            st.checkbox("20日均線", True, key="ma20")
            st.checkbox("60日均線", False, key="ma60")
            st.checkbox("120日均線", False, key="ma120")
            st.checkbox("布林通道", True, key="bb")
            st.checkbox("KD 指標", True, key="kd")
            st.checkbox("成交量分布圖", False, key="vp")
        with col_x2:
            st.markdown("**⚙️ 指標參數**")
            st.slider("RSI 天數", 6, 30, 14, key="rsi_period")
            st.slider("布林天數", 10, 40, 20, key="bb_period")
            st.slider("布林標準差", 1.0, 3.0, 2.0, 0.1, key="bb_std")
            st.slider("KD 天數", 5, 30, 14, key="kd_period")
        st.divider()
        st.markdown("**🔄 回測設定**")
        st.selectbox("交易策略", list(STRATEGIES.keys()), key="strategy")
        st.number_input("初始資金", 100000, 10000000, 1000000, step=100000, key="bt_init")
        strategy_info_ui = STRATEGIES[st.session_state.strategy]
        for p in strategy_info_ui["params"]:
            st.slider(p["label"], p["min"], p["max"], p["default"], step=p["step"], key=f"sp_{p['name']}")

        st.info("💡 設定完成後，請切換到其他 Tab 查看分析結果")
    else:
        st.info("👆 點擊上方按鈕展開設定")

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
    macd_val = float(latest["macd"]) if "macd" in latest and not pd.isna(latest["macd"]) else None
    macd_sig = float(latest["macd_signal"]) if "macd_signal" in latest and not pd.isna(latest["macd_signal"]) else None
    macd_hist = float(latest["macd_hist"]) if "macd_hist" in latest and not pd.isna(latest["macd_hist"]) else None

    price_color = up_color if chg >= 0 else down_color
    arrow = "▲" if chg >= 0 else "▼"
    st.markdown(f"""
<div class="card" style="text-align:center;">
  <div style="font-size:0.85rem;color:#888;">{stock_display_name} ({symbol})</div>
  <div style="font-size:2.5rem;font-weight:bold;color:{price_color};">{arrow} {latest['close']:.2f}</div>
  <div style="font-size:1rem;color:{price_color};">{chg:+.2f} ({chg_pct:+.2f}%)</div>
</div>""", unsafe_allow_html=True)

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("開盤", f"{latest['open']:.2f}")
    col_m2.metric("最高", f"{latest['high']:.2f}")
    col_m3.metric("最低", f"{latest['low']:.2f}")
    col_m4.metric("成交量", f"{latest['volume']:,.0f}")

    if info:
        col_i1, col_i2, col_i3, col_i4 = st.columns(4)
        if info.get("pe_ratio"):
            col_i1.metric("本益比", f"{info['pe_ratio']:.1f}")
        if info.get("eps"):
            col_i2.metric("EPS", f"{info['eps']:.1f}")
        if info.get("dividend_yield"):
            col_i3.metric("殖利率", f"{info['dividend_yield']*100:.1f}%")
        if info.get("market_cap"):
            col_i4.metric("市值", f"{info['market_cap']/1e8:.1f}億")

    if info and info.get("high_52w") and info.get("low_52w"):
        h52, l52 = float(info["high_52w"]), float(info["low_52w"])
        if h52 > l52:
            pct_52w = max(0, min(100, (close - l52) / (h52 - l52) * 100))
            bar_color = up_color if pct_52w >= 50 else down_color
            st.markdown(f"""
<div style="margin: 1rem 0;">
  <div style="font-size:0.8rem;color:#888;margin-bottom:4px;">📊 52週區間</div>
  <div style="background:#333;border-radius:8px;height:24px;position:relative;">
    <div style="background:{bar_color};width:{pct_52w}%;height:100%;border-radius:8px;"></div>
    <span style="position:absolute;top:50%;left:8px;transform:translateY(-50%);font-size:0.65rem;color:#ccc;">{l52:.1f}</span>
    <span style="position:absolute;top:50%;right:8px;transform:translateY(-50%);font-size:0.65rem;color:#ccc;">{h52:.1f}</span>
    <span style="position:absolute;top:50%;left:{pct_52w}%;transform:translate(-50%,-50%);font-size:0.65rem;color:#fff;background:rgba(0,0,0,0.7);padding:2px 6px;border-radius:4px;">{close:.1f}</span>
  </div>
</div>""", unsafe_allow_html=True)

    # ─── 買入評分 ───
    s_score = 0; s_reasons = []
    if rsi_val is not None:
        if rsi_val > 80: s_score -= 15; s_reasons.append(f"⚠️ RSI={rsi_val:.1f} 嚴重超買")
        elif rsi_val > 70: s_score -= 10; s_reasons.append(f"⚠️ RSI={rsi_val:.1f} 超買")
        elif rsi_val > 55: s_score += 10; s_reasons.append(f"✅ RSI={rsi_val:.1f} 多頭動能充足")
        elif rsi_val > 40: s_score += 5; s_reasons.append(f"✅ RSI={rsi_val:.1f} 中性偏多")
        elif rsi_val < 25: s_score -= 5; s_reasons.append(f"⚠️ RSI={rsi_val:.1f} 超賣")
        elif rsi_val < 35: s_score += 5; s_reasons.append(f"✅ RSI={rsi_val:.1f} 低檔區")
    if vol_ma5 and vol_ma5 > 0:
        vr = vol / vol_ma5
        if vr > 2.5 and chg > 0: s_score += 15; s_reasons.append(f"✅ 量能爆發({vr:.1f}倍)")
        elif vr > 2.0 and chg < 0: s_score -= 15; s_reasons.append(f"⚠️ 爆量下跌出貨")
        elif vr > 1.5 and chg > 0: s_score += 10; s_reasons.append(f"✅ 量增價漲({vr:.1f}倍)")
        elif vr > 1.5 and chg < 0: s_score -= 5; s_reasons.append(f"⚠️ 量增價跌({vr:.1f}倍)")
    if len(df) >= 6:
        fdc = (close - float(df.iloc[-6]["close"])) / float(df.iloc[-6]["close"]) * 100
        if fdc > 15: s_score -= 15; s_reasons.append(f"⚠️ 近5日暴漲{fdc:.1f}%")
        elif fdc > 8: s_score -= 5; s_reasons.append(f"⚠️ 近5日漲幅{fdc:.1f}%偏大")
        elif fdc > 2: s_score += 10; s_reasons.append(f"✅ 近5日溫和上漲{fdc:.1f}%")
        elif fdc < -10: s_score -= 5; s_reasons.append(f"⚠️ 近5日大跌{fdc:.1f}%")
        elif fdc < -3: s_score += 5; s_reasons.append(f"✅ 近5日回檔{fdc:.1f}%可觀察")
    if stoch_k is not None and stoch_d is not None:
        if stoch_k > 85 and stoch_d > 80: s_score -= 10; s_reasons.append(f"⚠️ KD超買區 K={stoch_k:.1f}")
        elif stoch_k < 20 and stoch_d < 25: s_score += 10; s_reasons.append(f"✅ KD超賣區 K={stoch_k:.1f}")
        if stoch_k > stoch_d and stoch_k < 50: s_score += 5; s_reasons.append("✅ KD黃金交叉低位")
        elif stoch_k < stoch_d and stoch_k > 50: s_score -= 5; s_reasons.append("⚠️ KD死亡交叉高位")
    if bb_u is not None and bb_l is not None and (bb_u - bb_l) > 0:
        bp = (close - bb_l) / (bb_u - bb_l)
        if bp > 0.95: s_score -= 10; s_reasons.append("⚠️ 觸及布林上軌")
        elif bp > 0.8: s_score += 5; s_reasons.append("✅ 強勢區接近上軌")
        elif bp < 0.05: s_score -= 5; s_reasons.append("⚠️ 觸及布林下軌")
        elif bp < 0.2: s_score += 5; s_reasons.append("✅ 弱勢區接近下軌")
    if ma5_val is not None and ma10_val is not None:
        if ma5_val > ma10_val: s_score += 5; s_reasons.append("✅ MA5>MA10 短線多頭")
        else: s_score -= 5; s_reasons.append("⚠️ MA5<MA10 短線空頭")

    l_score = 0; l_reasons = []
    if info and info.get("high_52w") and info.get("low_52w"):
        h52, l52 = float(info["high_52w"]), float(info["low_52w"])
        if h52 > l52:
            pos = (close - l52) / (h52 - l52)
            if pos >= 0.85: l_score -= 20; l_reasons.append(f"⚠️ 股價在52週高點{pos*100:.0f}%")
            elif pos >= 0.6: l_score += 5; l_reasons.append(f"✅ 52週中高段{pos*100:.0f}%")
            elif pos >= 0.3: l_score += 15; l_reasons.append(f"✅ 52週中低段{pos*100:.0f}%佈局空間")
            else: l_score += 10; l_reasons.append(f"✅ 52週低位{pos*100:.0f}%估值修復")
    if ma20_val is not None and ma60_val is not None:
        if ma20_val > ma60_val: l_score += 10; l_reasons.append("✅ MA20>MA60 中期向上")
        else: l_score -= 10; l_reasons.append("⚠️ MA20<MA60 中期向下")
    if ma60_val is not None and ma120_val is not None:
        if ma60_val > ma120_val: l_score += 10; l_reasons.append("✅ MA60>MA120 長期向上")
        else: l_score -= 10; l_reasons.append("⚠️ MA60<MA120 長期偏空")
    if info and info.get("pe_ratio") and info["pe_ratio"] > 0:
        pe = info["pe_ratio"]
        if pe < 12: l_score += 10; l_reasons.append(f"✅ 本益比{pe:.1f}偏低")
        elif pe < 20: l_score += 5; l_reasons.append(f"✅ 本益比{pe:.1f}合理")
        elif pe > 40: l_score -= 10; l_reasons.append(f"⚠️ 本益比{pe:.1f}偏高")
        elif pe > 25: l_score -= 5; l_reasons.append(f"⚠️ 本益比{pe:.1f}偏高")
    if info and info.get("dividend_yield") and info["dividend_yield"] > 0:
        dy = info["dividend_yield"] * 100
        if dy > 5: l_score += 10; l_reasons.append(f"✅ 殖利率{dy:.1f}%優")
        elif dy > 3: l_score += 5; l_reasons.append(f"✅ 殖利率{dy:.1f}%穩定")

    def verdict(sc):
        if sc >= 20: return "🟢 強烈買入", "#26a69a"
        elif sc >= 10: return "🟢 偏多買入", "#26a69a"
        elif sc >= 0: return "🟡 中性觀望", "#FF9800"
        elif sc >= -15: return "🔴 偏空", "#ef5350"
        else: return "🔴 強烈不建議", "#ef5350"
    sv, sc = verdict(s_score)
    lv, lc = verdict(l_score)

    col_s, col_l = st.columns(2)
    with col_s:
        st.markdown(f"<div style='background:#1a1a2e;border:2px solid {sc};border-radius:12px;padding:10px;text-align:center;'>"
                    f"<div style='font-size:0.8rem;color:#888;'>⚡ 短期</div>"
                    f"<div style='font-size:1rem;font-weight:bold;color:{sc};'>{sv}</div>"
                    f"<div style='font-size:0.75rem;color:#aaa;'>評分 {s_score}</div></div>", unsafe_allow_html=True)
        with st.expander("📋 詳細評估", expanded=False):
            for r in s_reasons:
                st.markdown(f"- {r}")
    with col_l:
        st.markdown(f"<div style='background:#1a1a2e;border:2px solid {lc};border-radius:12px;padding:10px;text-align:center;'>"
                    f"<div style='font-size:0.8rem;color:#888;'>📅 長期</div>"
                    f"<div style='font-size:1rem;font-weight:bold;color:{lc};'>{lv}</div>"
                    f"<div style='font-size:0.75rem;color:#aaa;'>評分 {l_score}</div></div>", unsafe_allow_html=True)
        with st.expander("📋 詳細評估", expanded=False):
            for r in l_reasons:
                st.markdown(f"- {r}")

    st.markdown("### 📈 股價走勢")
    try:
        fig_px = go.Figure()
        fig_px.add_trace(go.Scatter(x=df.index, y=df["close"], mode="lines",
            line=dict(color="#2196F3", width=2), name="收盤價"))
        fig_px.update_layout(height=250, margin=dict(l=5, r=5, t=5, b=5),
            template="plotly_dark", showlegend=False, dragmode=False, hovermode=False)
        fig_px.update_xaxes(showgrid=False, visible=False)
        fig_px.update_yaxes(showgrid=False, visible=False)
        st.plotly_chart(fig_px, use_container_width=True,
            config={"scrollZoom": False, "displayModeBar": False, "staticPlot": True, "responsive": True})
    except Exception:
        st.line_chart(df[["close"]], use_container_width=True, height=250)
    st.markdown("### 📊 成交量")
    try:
        fig_vx = go.Figure()
        vc = [up_color if df.iloc[i]["close"] >= df.iloc[i]["open"] else down_color for i in range(len(df))]
        fig_vx.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color=vc, name="成交量"))
        fig_vx.update_layout(height=150, margin=dict(l=5, r=5, t=5, b=5),
            template="plotly_dark", showlegend=False, dragmode=False, hovermode=False)
        fig_vx.update_xaxes(showgrid=False, visible=False)
        fig_vx.update_yaxes(showgrid=False, visible=False)
        st.plotly_chart(fig_vx, use_container_width=True,
            config={"scrollZoom": False, "displayModeBar": False, "staticPlot": True, "responsive": True})
    except Exception:
        st.bar_chart(df[["volume"]], use_container_width=True, height=150)

    if show_volume_profile:
        st.markdown("### 📊 價格 vs 成交量")
        df_vp = df[["close", "volume"]].rename(columns={"close": "價格", "volume": "成交量"})
        st.line_chart(df_vp, use_container_width=True, height=200)

    # 指標摘要
    st.markdown("##")
    st.markdown("### 📋 技術指標摘要")
    ind_rows = []
    if rsi_val is not None:
        icon = "🟢" if rsi_val > 50 else "🔴"
        ind_rows.append({"指標": f"RSI({rsi_period})", "數值": f"{rsi_val:.1f}", "訊號": icon})
    if macd_val is not None and macd_sig is not None:
        icon = "🟢" if macd_val > macd_sig else "🔴"
        ind_rows.append({"指標": "MACD", "數值": f"{macd_val:.2f}", "訊號": icon})
    if stoch_k is not None and stoch_d is not None:
        icon = "🟢" if stoch_k > stoch_d else "🔴"
        ind_rows.append({"指標": f"KD({kd_period})", "數值": f"K={stoch_k:.1f}", "訊號": icon})
    if bb_u is not None and bb_l is not None:
        bb_pos = (close - bb_l) / (bb_u - bb_l) * 100
        icon = "🟢" if bb_pos > 50 else "🔴"
        ind_rows.append({"指標": "布林", "數值": f"{bb_pos:.0f}%位置", "訊號": icon})
    if vol_ma5 is not None and vol_ma5 > 0:
        vr = vol / vol_ma5
        icon = "🔥" if vr > 1.5 else "✅" if vr > 0.8 else "⚠️"
        ind_rows.append({"指標": "量比", "數值": f"{vr:.2f}倍", "訊號": icon})
    if ma5_val is not None and ma20_val is not None:
        icon = "🟢" if ma5_val > ma20_val else "🔴"
        ind_rows.append({"指標": "均線", "數值": f"MA5={ma5_val:.1f}", "訊號": icon})
    if ind_rows:
        st.dataframe(pd.DataFrame(ind_rows), hide_index=True, use_container_width=True)

    st.caption("⚠️ 以上分析僅基於技術指標，非投資建議。")

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
