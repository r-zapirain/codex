#!/usr/bin/env python3
"""A synthetic, paper-trading demo for meme-token launch signals."""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Launch:
    symbol: str
    narrative: str
    liquidity: float
    holder_growth: float
    buy_pressure: float
    mention_growth: float
    sentiment: float
    drift: float

    @property
    def onchain_score(self) -> float:
        return 0.45 * self.liquidity + 0.35 * self.holder_growth + 0.20 * self.buy_pressure

    @property
    def social_score(self) -> float:
        return 0.55 * self.mention_growth + 0.45 * self.sentiment

    @property
    def score(self) -> float:
        return 0.55 * self.onchain_score + 0.45 * self.social_score


@dataclass
class Position:
    launch: Launch
    entry_price: float
    quantity: float
    opened_at: int


@dataclass(frozen=True)
class Trade:
    symbol: str
    entry_price: float
    exit_price: float
    pnl: float
    reason: str


class PaperBot:
    def __init__(
        self,
        *,
        starting_balance: float = 1_000.0,
        threshold: float = 0.62,
        max_positions: int = 2,
        allocation_fraction: float = 0.10,
        take_profit: float = 0.20,
        stop_loss: float = 0.12,
        max_hold_ticks: int = 5,
    ) -> None:
        if not math.isfinite(starting_balance) or starting_balance <= 0:
            raise ValueError("starting balance must be positive")
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        if max_positions < 1:
            raise ValueError("max positions must be at least 1")
        if not 0 < allocation_fraction <= 1:
            raise ValueError("allocation fraction must be in (0, 1]")
        if (
            not math.isfinite(take_profit)
            or not math.isfinite(stop_loss)
            or take_profit <= 0
            or not 0 < stop_loss < 1
            or max_hold_ticks < 1
        ):
            raise ValueError("invalid exit or holding limits")

        self.cash = starting_balance
        self.threshold = threshold
        self.max_positions = max_positions
        self.allocation_fraction = allocation_fraction
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.max_hold_ticks = max_hold_ticks
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []

    def consider(self, launch: Launch, price: float, tick: int) -> bool:
        if (
            launch.score < self.threshold
            or launch.symbol in self.positions
            or len(self.positions) >= self.max_positions
            or price <= 0
        ):
            return False

        allocation = min(self.cash, self.cash * self.allocation_fraction)
        if allocation <= 0:
            return False
        self.cash -= allocation
        self.positions[launch.symbol] = Position(
            launch=launch,
            entry_price=price,
            quantity=allocation / price,
            opened_at=tick,
        )
        return True

    def update(self, prices: dict[str, float], tick: int) -> list[Trade]:
        closed: list[Trade] = []
        for symbol, position in list(self.positions.items()):
            price = prices[symbol]
            change = price / position.entry_price - 1
            age = tick - position.opened_at
            reason = None
            if change >= self.take_profit:
                reason = "take profit"
            elif change <= -self.stop_loss:
                reason = "stop loss"
            elif age >= self.max_hold_ticks:
                reason = "time limit"
            if reason is not None:
                trade = self._close(symbol, price, reason)
                closed.append(trade)
                self._learn(trade)
        return closed

    def _close(self, symbol: str, price: float, reason: str) -> Trade:
        position = self.positions.pop(symbol)
        proceeds = position.quantity * price
        pnl = proceeds - position.quantity * position.entry_price
        self.cash += proceeds
        trade = Trade(symbol, position.entry_price, price, pnl, reason)
        self.trades.append(trade)
        return trade

    def close_positions(self, prices: dict[str, float], reason: str) -> list[Trade]:
        closed = [
            self._close(symbol, prices[symbol], reason)
            for symbol in list(self.positions)
        ]
        for trade in closed:
            self._learn(trade)
        return closed

    def _learn(self, trade: Trade) -> None:
        # Favor more selective entries after losses; cautiously loosen after wins.
        adjustment = -0.01 if trade.pnl > 0 else 0.02
        self.threshold = min(0.85, max(0.45, self.threshold + adjustment))


def _new_launch(rng: random.Random, index: int) -> Launch:
    narratives = ("AI", "animals", "gaming", "politics", "internet culture")
    liquidity = rng.uniform(0.2, 1)
    holder_growth = rng.random()
    buy_pressure = rng.random()
    mention_growth = rng.random()
    sentiment = rng.random()
    score = 0.55 * (
        0.45 * liquidity + 0.35 * holder_growth + 0.20 * buy_pressure
    ) + 0.45 * (0.55 * mention_growth + 0.45 * sentiment)
    # Signals are only weakly predictive in this toy market, with substantial noise.
    drift = (score - 0.5) * 0.035 + rng.gauss(0, 0.018)
    return Launch(
        symbol=f"MEME{index:02d}",
        narrative=rng.choice(narratives),
        liquidity=liquidity,
        holder_growth=holder_growth,
        buy_pressure=buy_pressure,
        mention_growth=mention_growth,
        sentiment=sentiment,
        drift=drift,
    )


def run_simulation(ticks: int, seed: int, starting_balance: float) -> tuple[PaperBot, list[str]]:
    if ticks < 1:
        raise ValueError("ticks must be at least 1")

    rng = random.Random(seed)
    bot = PaperBot(starting_balance=starting_balance)
    prices: dict[str, float] = {}
    launches: dict[str, Launch] = {}
    log: list[str] = []

    for tick in range(1, ticks + 1):
        launch = _new_launch(rng, tick)
        launches[launch.symbol] = launch
        prices[launch.symbol] = 1.0
        log.append(
            f"[{tick:02d}] {launch.symbol} ({launch.narrative}) "
            f"on-chain={launch.onchain_score:.2f} social={launch.social_score:.2f} "
            f"score={launch.score:.2f}"
        )
        if bot.consider(launch, prices[launch.symbol], tick):
            log.append(
                f"     PAPER BUY {launch.symbol} at 1.0000 "
                f"(threshold {bot.threshold:.2f})"
            )
        else:
            log.append(f"     SKIP {launch.symbol}")

        for symbol, position in list(bot.positions.items()):
            market_shock = rng.gauss(0, 0.055)
            prices[symbol] *= max(0.05, 1 + launches[symbol].drift + market_shock)

        for trade in bot.update(prices, tick):
            log.append(
                f"     PAPER SELL {trade.symbol} at {trade.exit_price:.4f} "
                f"({trade.reason}; P&L {trade.pnl:+.2f}; "
                f"new threshold {bot.threshold:.2f})"
            )

    for trade in bot.close_positions(prices, "simulation ended"):
        log.append(
            f"[end] PAPER SELL {trade.symbol} at {trade.exit_price:.4f} "
            f"(P&L {trade.pnl:+.2f}; new threshold {bot.threshold:.2f})"
        )
    return bot, log


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a synthetic meme-token paper simulation.")
    parser.add_argument("--ticks", type=int, default=20, help="number of simulated launches")
    parser.add_argument("--seed", type=int, default=7, help="random seed for repeatable runs")
    parser.add_argument(
        "--balance", type=float, default=1_000.0, help="starting virtual balance"
    )
    args = parser.parse_args()
    try:
        bot, log = run_simulation(args.ticks, args.seed, args.balance)
    except ValueError as error:
        parser.error(str(error))

    print("PAPER SNIPE BOT — synthetic market only; no real orders or wallet access")
    for entry in log:
        print(entry)
    total_pnl = sum(trade.pnl for trade in bot.trades)
    wins = sum(trade.pnl > 0 for trade in bot.trades)
    print(
        f"\nClosed trades: {len(bot.trades)} | Wins: {wins} | "
        f"Realized P&L: {total_pnl:+.2f} | Virtual cash: {bot.cash:.2f} | "
        f"Final threshold: {bot.threshold:.2f}"
    )


if __name__ == "__main__":
    main()
