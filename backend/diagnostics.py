"""Auditable portfolio and signal diagnostics; never generates trade orders."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import sqrt
from typing import Mapping


def technical_indicators(closes: list[float]) -> dict:
    """RSI(14), 50/200-session moving averages; use only observed prices."""
    if len(closes) < 201 or any(p <= 0 for p in closes):
        return {"status": "INSUFFICIENT_DATA"}
    changes = [b - a for a, b in zip(closes, closes[1:])]
    window = changes[-14:]
    gain = sum(max(d, 0) for d in window) / 14
    loss = sum(max(-d, 0) for d in window) / 14
    rsi = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    ma50 = sum(closes[-50:]) / 50
    ma200 = sum(closes[-200:]) / 200
    return {
        "status": "OK", "rsi_14": round(rsi, 2),
        "sma_50": round(ma50, 4), "sma_200": round(ma200, 4),
        "above_sma_50": closes[-1] > ma50,
        "above_sma_200": closes[-1] > ma200,
    }


def stale_signal(export_date: str | None, as_of: date, max_age_days: int = 45) -> dict:
    if not export_date:
        return {"status": "UNKNOWN", "age_days": None}
    try:
        age = (as_of - date.fromisoformat(export_date[:10])).days
    except ValueError:
        return {"status": "INVALID_DATE", "age_days": None}
    return {"status": "STALE" if age > max_age_days else "CURRENT", "age_days": age}


def portfolio_risk(weights: Mapping[str, float], sectors: Mapping[str, str],
                   max_stock: float = 0.10, max_sector: float = 0.25) -> dict:
    """Long-only weights must sum to 1. Sector exposures are descriptive, not forecasts."""
    if not weights or any(w < 0 for w in weights.values()):
        raise ValueError("Weights must be non-negative and nonempty")
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError("Weights must sum to 1")
    exposure = defaultdict(float)
    for ticker, weight in weights.items():
        exposure[sectors.get(ticker, "UNKNOWN")] += weight
    return {
        "effective_number_of_holdings": round(1 / sum(w*w for w in weights.values()), 2),
        "single_stock_breaches": {t: round(w, 4) for t, w in weights.items() if w > max_stock},
        "sector_exposure": {s: round(w, 4) for s, w in sorted(exposure.items())},
        "sector_breaches": {s: round(w, 4) for s, w in exposure.items() if w > max_sector},
        "unknown_sector_weight": round(exposure.get("UNKNOWN", 0), 4),
    }


def weighted_score(signals: Mapping[str, float | None],
                   weights: Mapping[str, float]) -> dict:
    """Do not silently redistribute weight when an input is missing or stale."""
    if not weights or any(w < 0 for w in weights.values()) or abs(sum(weights.values()) - 1) > 1e-6:
        raise ValueError("Weights must be nonnegative and sum to 1")
    missing = [k for k in weights if signals.get(k) is None]
    if missing:
        return {"status": "INCOMPLETE", "score": None, "missing": missing}
    if any(not 0 <= float(signals[k]) <= 100 for k in weights):
        raise ValueError("Scores must be between 0 and 100")
    return {"status": "OK", "score": round(sum(float(signals[k])*w for k, w in weights.items()), 2),
            "weights": dict(weights)}
