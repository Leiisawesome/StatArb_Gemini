"""Risk controls for the L1 microstructure framework."""

from __future__ import annotations

from dataclasses import dataclass

from .config import RiskConfig
from .decision import TradeAction, TradeIntent
from .execution import ExecutionReport
from .features import ObservedState


@dataclass(slots=True)
class RiskDecision:
    approved: bool
    quantity: int
    reason: str


@dataclass(slots=True)
class OpenPosition:
    symbol: str
    side: TradeAction
    quantity: int
    entry_price: float
    entry_timestamp_ns: int


class RiskEngine:
    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()
        self.starting_equity = self.config.starting_equity
        self.peak_equity = self.config.starting_equity
        self.realized_pnl = 0.0
        self.trade_count = 0
        self.halted = False

    def authorize(
        self,
        intent: TradeIntent,
        state: ObservedState,
        *,
        target_fraction: float | None = None,
        current_position: OpenPosition | None = None,
        current_gross_exposure: float = 0.0,
    ) -> RiskDecision:
        if self.halted:
            return RiskDecision(False, 0, "kill switch active")
        if intent.action not in {TradeAction.BUY, TradeAction.SELL}:
            return RiskDecision(False, 0, "no actionable trade")

        equity = self.equity
        price = max(state.book.midpoint, 1e-6)
        volatility = max(state.realized_volatility, 1e-5)
        target_fraction_limit = min(self.config.max_position_fraction, self.config.volatility_target / volatility)
        if target_fraction is not None:
            target_fraction_limit = min(target_fraction_limit, max(float(target_fraction), 0.0))

        target_notional = equity * target_fraction_limit
        target_quantity = int(max(target_notional / price, 0.0))
        if target_quantity <= 0:
            return RiskDecision(False, 0, "volatility scaled quantity collapsed")

        incremental_quantity = target_quantity
        if current_position is not None:
            if current_position.side is intent.action:
                incremental_quantity = max(target_quantity - current_position.quantity, 0)
            else:
                incremental_quantity = target_quantity + current_position.quantity

        if incremental_quantity <= 0:
            return RiskDecision(False, 0, "already at target size")

        gross_after = current_gross_exposure + incremental_quantity * price / max(equity, 1e-6)
        if gross_after > self.config.max_gross_exposure:
            return RiskDecision(False, 0, "gross exposure limit breached")
        return RiskDecision(True, incremental_quantity, "approved")

    def process_fill(self, report: ExecutionReport) -> None:
        if report.status != "filled" or report.fill_price is None:
            return
        self.trade_count += 1
        self.peak_equity = max(self.peak_equity, self.equity)
        self.halted = self.drawdown >= self.config.daily_drawdown_limit

    def register_realized_pnl(self, pnl: float) -> None:
        self.realized_pnl += pnl
        self.peak_equity = max(self.peak_equity, self.equity)
        self.halted = self.drawdown >= self.config.daily_drawdown_limit

    @property
    def equity(self) -> float:
        return self.starting_equity + self.realized_pnl

    @property
    def drawdown(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, (self.peak_equity - self.equity) / self.peak_equity)