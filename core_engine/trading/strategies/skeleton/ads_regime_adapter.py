"""
Skeleton adapter for ADS continuous regime vectors (Rule 7).

Provides a reusable, strategy-agnostic wrapper around ADSRegimeVector.from_regime_context
with per-symbol "previous vector" memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Tuple

from core_engine.alpha.ads_regime_vector import ADSRegimeVector


@dataclass
class ADSRegimeVectorCache:
    """
    Maintains per-symbol previous ADSRegimeVector to enable smooth regime transitions.
    """

    prev: Dict[str, ADSRegimeVector] = field(default_factory=dict)

    def get_vector(
        self,
        *,
        symbol: str,
        get_regime_context: Callable[[], Any],
    ) -> Tuple[ADSRegimeVector, Dict[str, Any]]:
        """
        Best-effort adapter: fetch current regime context and convert to ADSRegimeVector.
        """
        regime_context = None
        try:
            regime_context = get_regime_context()
        except Exception:
            regime_context = None

        prev = self.prev.get(symbol)
        r, diag = ADSRegimeVector.from_regime_context(regime_context, prev=prev)
        self.prev[symbol] = r
        return r, diag

