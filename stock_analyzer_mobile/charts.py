import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def plot_candlestick(df, stock_name="", indicators=None, show_sr=True, up_color="#ef5350", down_color="#26a69a"):
    if df.empty or len(df) < 10:
        return None

    if indicators is None:
        indicators = ["ma5", "ma10", "ma20", "volume", "rsi", "macd"]

    rows = 1
    row_heights = [0.45]
    specs = [[{"secondary_y": False}]]

    if "volume" in indicators and "volume" in df.columns:
        rows += 1
        row_heights.append(0.13)
        specs.append([{"secondary_y": False}])

    if "rsi" in indicators:
        rows += 1
        row_heights.append(0.14)
        specs.append([{"secondary_y": False}])

    if "macd" in indicators:
        rows += 1
        row_heights.append(0.14)
        specs.append([{"secondary_y": False}])

    if "kd" in indicators:
        rows += 1
        row_heights.append(0.14)
        specs.append([{"secondary_y": False}])

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=row_heights,
        specs=specs,
    )

    row_idx = 1

    # ─── Row 1: Candlestick + MA + BB + Support/Resistance ───
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="K線",
        showlegend=False,
        increasing_line_color=up_color,
        decreasing_line_color=down_color,
    ), row=row_idx, col=1, secondary_y=False)

    colors = {"ma5": "#FF6B35", "ma10": "#2196F3", "ma20": "#4CAF50", "ma60": "#9C27B0", "ma120": "#FF9800"}
    widths = {"ma5": 1, "ma10": 1, "ma20": 1.5, "ma60": 1.5, "ma120": 1.5}
    for ind in indicators:
        if ind in colors and ind in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[ind],
                mode="lines",
                name=ind.upper(),
                line=dict(color=colors[ind], width=widths.get(ind, 1)),
            ), row=row_idx, col=1, secondary_y=False)

    if "bb_upper" in df.columns and "bb_lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["bb_upper"],
            mode="lines", name="BB上軌",
            line=dict(color="rgba(0,0,0,0.2)", width=0.5),
            showlegend=False,
        ), row=row_idx, col=1, secondary_y=False)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["bb_lower"],
            mode="lines", name="BB下軌",
            line=dict(color="rgba(0,0,0,0.2)", width=0.5),
            fill="tonexty",
            fillcolor="rgba(0,0,0,0.05)",
            showlegend=False,
        ), row=row_idx, col=1, secondary_y=False)

    if show_sr and len(df) >= 20:
        recent = df.tail(20)
        resistance = float(recent["high"].max())
        support = float(recent["low"].min())
        x_range = [df.index[0], df.index[-1]]
        fig.add_trace(go.Scatter(
            x=x_range, y=[resistance, resistance],
            mode="lines", name=f"壓力線 {resistance:.2f}",
            line=dict(color=up_color, width=1, dash="dot"),
        ), row=row_idx, col=1, secondary_y=False)
        fig.add_trace(go.Scatter(
            x=x_range, y=[support, support],
            mode="lines", name=f"支撐線 {support:.2f}",
            line=dict(color=down_color, width=1, dash="dot"),
        ), row=row_idx, col=1, secondary_y=False)

    # ─── Row 2: Volume ───
    if "volume" in indicators and "volume" in df.columns:
        row_idx += 1
        vol_colors = [up_color if c > o else down_color
                      for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(
            x=df.index, y=df["volume"],
            name="成交量",
            marker_color=vol_colors,
            opacity=0.6,
        ), row=row_idx, col=1, secondary_y=False)
        fig.update_yaxes(title_text="成交量", row=row_idx, col=1, rangemode="nonnegative")

    # ─── Row 3: RSI ───
    if "rsi" in indicators:
        row_idx += 1
        if "rsi" in df.columns:
            rsi_data = df["rsi"].dropna()
            if not rsi_data.empty:
                fig.add_trace(go.Scatter(
                    x=rsi_data.index, y=rsi_data,
                    mode="lines", name="RSI",
                    line=dict(color="#FF6B35", width=1.5),
                ), row=row_idx, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=down_color,
                       row=row_idx, col=1, annotation_text="超買")
        fig.add_hline(y=30, line_dash="dash", line_color=up_color,
                       row=row_idx, col=1, annotation_text="超賣")
        fig.update_yaxes(title_text="RSI", row=row_idx, col=1, range=[0, 100])

    # ─── Row 4: MACD ───
    if "macd" in indicators and "macd_hist" in df.columns and "macd" in df.columns:
        row_idx += 1
        macd_colors = [up_color if h >= 0 else down_color
                       for h in df["macd_hist"]]
        fig.add_trace(go.Bar(
            x=df.index, y=df["macd_hist"],
            name="MACD Hist",
            marker_color=macd_colors,
            opacity=0.6,
        ), row=row_idx, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["macd"],
            mode="lines", name="MACD",
            line=dict(color="#2196F3", width=1.5),
        ), row=row_idx, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["macd_signal"],
            mode="lines", name="Signal",
            line=dict(color="#FF9800", width=1.5),
        ), row=row_idx, col=1)
        fig.update_yaxes(title_text="MACD", row=row_idx, col=1)

    # ─── Row 5: KD ───
    if "kd" in indicators and "stoch_k" in df.columns and "stoch_d" in df.columns:
        row_idx += 1
        fig.add_trace(go.Scatter(
            x=df.index, y=df["stoch_k"],
            mode="lines", name="K 值",
            line=dict(color="#2196F3", width=1.5),
        ), row=row_idx, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["stoch_d"],
            mode="lines", name="D 值",
            line=dict(color="#FF9800", width=1.5),
        ), row=row_idx, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color=down_color,
                       row=row_idx, col=1, annotation_text="超買")
        fig.add_hline(y=20, line_dash="dash", line_color=up_color,
                       row=row_idx, col=1, annotation_text="超賣")
        fig.update_yaxes(title_text="KD", row=row_idx, col=1, range=[0, 100])

    # ─── Layout ───
    title = f"{stock_name}"
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=14)),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        template="plotly_white",
        height=180 * rows,
        margin=dict(l=20, r=20, t=30, b=10),
        dragmode=False,
        font=dict(size=10),
        legend=dict(font=dict(size=9), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # 統一套用 xaxis 設定至所有子圖
    for i in range(1, rows + 1):
        xaxis_key = f"xaxis{i}" if i > 1 else "xaxis"
        fig.update_xaxes(
            rangebreaks=[dict(bounds=["sat", "mon"])],
            rangeslider_visible=False,
            type="date",
            matches="x",
            showticklabels=(i == rows),
        )

    # 隱藏主圖 x 軸標籤（由最後一張子圖負責顯示）
    fig.update_xaxes(showticklabels=False, row=1, col=1)

    return fig

def plot_volume_profile(df, bins=24):
    if df.empty:
        return None
    price_range = np.linspace(df["low"].min(), df["high"].max(), bins)
    volume_at_price = np.zeros(bins - 1)
    for i in range(len(df)):
        bar_low, bar_high, vol = df.iloc[i]["low"], df.iloc[i]["high"], df.iloc[i]["volume"]
        mask = (price_range[:-1] < bar_high) & (price_range[1:] > bar_low)
        overlap = np.minimum(price_range[1:], bar_high) - np.maximum(price_range[:-1], bar_low)
        overlap = np.maximum(overlap, 0)
        total_overlap = overlap.sum()
        if total_overlap > 0:
            volume_at_price += (overlap / total_overlap) * vol

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=volume_at_price,
        y=price_range[:-1],
        orientation="h",
        marker_color="#2196F3",
        opacity=0.6,
        name="成交量分布",
    ))
    fig.add_trace(go.Scatter(
        x=[df["close"].iloc[-1]] * 2,
        y=[price_range[0], price_range[-1]],
        mode="lines",
        name=f"現價 {df['close'].iloc[-1]:.2f}",
        line=dict(color="red", width=2, dash="dash"),
    ))

    fig.update_layout(
        title="成交量分布",
        xaxis_title="成交量",
        yaxis_title="價格",
        height=300,
        template="plotly_white",
        hovermode="y unified",
        margin=dict(l=20, r=20, t=30, b=20),
        font=dict(size=10),
    )
    return fig
