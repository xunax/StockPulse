import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

class Action(Enum):
    BUY = 1
    SELL = -1
    HOLD = 0

@dataclass
class Order:
    date: pd.Timestamp
    action: Action
    price: float
    shares: float
    value: float
    fee: float = 0.0

@dataclass
class Trade:
    buy_date: pd.Timestamp
    sell_date: pd.Timestamp
    buy_price: float
    sell_price: float
    shares: int
    cost: float
    revenue: float
    profit: float
    return_pct: float
    holding_days: int

@dataclass
class StrategyResult:
    orders: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    metrics: dict = field(default_factory=dict)

class Portfolio:
    def __init__(self, initial_cash=1_000_000, commission=0.001425, tax=0.003):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.shares = 0
        self.orders = []
        self.equity = []
        self.commission = commission
        self.tax = tax

    def buy(self, date, price, shares=None, pct=None):
        if shares is None and pct is None:
            pct = 1.0
        if pct is not None:
            shares = (self.cash * pct) / price
        shares = int(shares)
        if shares <= 0:
            return
        cost = shares * price
        fee = cost * self.commission
        total_cost = cost + fee
        if total_cost > self.cash:
            return
        self.cash -= total_cost
        self.shares += shares
        self.orders.append(Order(date, Action.BUY, price, shares, cost, fee))

    def sell(self, date, price, shares=None, pct=None):
        if shares is None and pct is None:
            pct = 1.0
        if pct is not None:
            shares = int(self.shares * pct)
        if shares <= 0 or shares > self.shares:
            shares = self.shares
        revenue = shares * price
        fee = revenue * self.commission
        tax = revenue * self.tax
        net_revenue = revenue - fee - tax
        self.cash += net_revenue
        self.shares -= shares
        self.orders.append(Order(date, Action.SELL, price, shares, revenue, fee + tax))

    def total_value(self, price=0):
        return self.cash + self.shares * price

def pair_trades(orders):
    trades = []
    buy_queue = []
    for o in orders:
        if o.action == Action.BUY:
            buy_queue.append(o)
        elif o.action == Action.SELL and buy_queue:
            buy = buy_queue.pop(0)
            shares = min(buy.shares, o.shares)
            cost = shares * buy.price + buy.fee * (shares / buy.shares)
            revenue = shares * o.price - o.fee * (shares / o.shares)
            profit = revenue - cost
            return_pct = (o.price / buy.price - 1) * 100
            holding_days = (o.date - buy.date).days
            trades.append(Trade(
                buy_date=buy.date,
                sell_date=o.date,
                buy_price=buy.price,
                sell_price=o.price,
                shares=shares,
                cost=round(cost, 0),
                revenue=round(revenue, 0),
                profit=round(profit, 0),
                return_pct=round(return_pct, 2),
                holding_days=holding_days,
            ))
    return trades

def backtest(df, strategy_fn: Callable, initial_cash=1_000_000,
             commission=0.001425, tax=0.003, strategy_params=None):
    pf = Portfolio(initial_cash, commission=commission, tax=tax)
    equity_curve = []

    if strategy_params is not None:
        signals = strategy_fn(df, **strategy_params)
    else:
        signals = strategy_fn(df)
    df = df.copy()
    df["signal"] = signals

    for i in range(len(df)):
        row = df.iloc[i]
        date = row.name
        price = float(row["close"])
        signal = row["signal"]
        position = pf.shares

        if signal == Action.BUY and position == 0:
            pf.buy(date, price, pct=0.95)

        elif signal == Action.SELL and position > 0:
            pf.sell(date, price, pct=1.0)

        equity_curve.append({
            "date": date,
            "price": price,
            "position": pf.shares,
            "cash": pf.cash,
            "total": pf.total_value(price),
        })

    ec = pd.DataFrame(equity_curve).set_index("date")["total"]
    trades = pair_trades(pf.orders)
    metrics = calc_metrics(ec, initial_cash, pf, trades)
    return StrategyResult(orders=pf.orders, trades=trades, equity_curve=ec, metrics=metrics)

def calc_metrics(equity_curve, initial_cash, pf, trades):
    if len(equity_curve) < 2:
        return {"error": "not enough data"}

    final_value = equity_curve.iloc[-1]
    total_return = (final_value - initial_cash) / initial_cash * 100

    daily_returns = equity_curve.pct_change().dropna()
    if len(daily_returns) == 0:
        return {"total_return": total_return}

    n_days = len(equity_curve)
    n_years = n_days / 252
    annual_return = ((1 + total_return / 100) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0

    sharpe = np.nan
    if daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

    rolling_max = equity_curve.expanding().max()
    drawdown = (equity_curve - rolling_max) / rolling_max * 100
    max_dd = drawdown.min()

    n_trades = len(trades)
    win_trades = [t for t in trades if t.profit > 0]
    lose_trades = [t for t in trades if t.profit <= 0]
    win_rate = len(win_trades) / n_trades * 100 if n_trades > 0 else 0

    avg_profit = np.mean([t.profit for t in trades]) if trades else 0
    avg_return = np.mean([t.return_pct for t in trades]) if trades else 0
    avg_holding = np.mean([t.holding_days for t in trades]) if trades else 0

    max_single_profit = max([t.profit for t in trades]) if trades else 0
    max_single_loss = min([t.profit for t in trades]) if trades else 0
    max_single_return = max([t.return_pct for t in trades]) if trades else 0
    max_single_loss_pct = min([t.return_pct for t in trades]) if trades else 0

    gross_profit = sum(t.profit for t in win_trades)
    gross_loss = abs(sum(t.profit for t in lose_trades))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    max_consecutive_loss = 0
    current_streak = 0
    for t in trades:
        if t.profit <= 0:
            current_streak += 1
            max_consecutive_loss = max(max_consecutive_loss, current_streak)
        else:
            current_streak = 0

    total_fees = sum(o.fee for o in pf.orders)

    return {
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "win_rate": round(win_rate, 1),
        "total_trades": n_trades,
        "final_value": round(final_value, 0),
        "initial_cash": initial_cash,
        "avg_profit": round(avg_profit, 0),
        "avg_return": round(avg_return, 2),
        "avg_holding_days": round(avg_holding, 1),
        "max_single_profit": round(max_single_profit, 0),
        "max_single_loss": round(max_single_loss, 0),
        "max_single_return": round(max_single_return, 2),
        "max_single_loss_pct": round(max_single_loss_pct, 2),
        "profit_factor": round(profit_factor, 2),
        "max_consecutive_loss": max_consecutive_loss,
        "total_fees": round(total_fees, 0),
    }

def format_metrics(m):
    if "error" in m:
        return m["error"]
    lines = [
        f"總報酬率: {m['total_return']:+.2f}%",
        f"年化報酬率: {m['annual_return']:+.2f}%",
        f"夏普比率: {m['sharpe_ratio']}",
        f"最大回撤: {m['max_drawdown']:.2f}%",
        f"勝率: {m['win_rate']}%",
        f"交易次數: {m['total_trades']}",
        f"最終資產: ${m['final_value']:,.0f}",
        f"初始資產: ${m['initial_cash']:,.0f}",
    ]
    return "\n".join(lines)
