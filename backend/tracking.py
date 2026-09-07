from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def expected_price(start_price: float, target_price: float, elapsed_months: float) -> float:
    elapsed = min(max(elapsed_months, 0), 12)
    return start_price * (target_price / start_price) ** (elapsed / 12)


def monthly_accuracy(actual: float, expected: float) -> float:
    if expected <= 0:
        return 0.0
    return max(0.0, 100 - abs(actual - expected) / expected * 100)


def target_progress(actual: float, start: float, target: float) -> float | None:
    distance = target - start
    if distance == 0:
        return None
    return (actual - start) / distance * 100


def update_forecast_tracking(forecast_file: Path, prices: dict[str, float], today: date | None = None):
    today = today or date.today()
    if not forecast_file.exists():
        forecast_file.parent.mkdir(parents=True, exist_ok=True)
        forecast_file.write_text("[]", encoding="utf-8")
    forecasts = json.loads(forecast_file.read_text(encoding="utf-8"))
    for forecast in forecasts:
        ticker = forecast["ticker"]
        if ticker not in prices or forecast.get("status") == "COMPLETED":
            continue
        start_date = date.fromisoformat(forecast["forecast_date"])
        elapsed_months = (today - start_date).days / 30.4375
        expected = expected_price(forecast["start_price"], forecast["ml_target_price_12m"], elapsed_months)
        actual = prices[ticker]
        point = {
            "date": today.isoformat(),
            "month_number": round(elapsed_months, 2),
            "expected_price": round(expected, 2),
            "actual_price": round(actual, 2),
            "monthly_accuracy_pct": round(monthly_accuracy(actual, expected), 2),
            "target_progress_pct": round(target_progress(actual, forecast["start_price"], forecast["ml_target_price_12m"]), 2),
        }
        history = forecast.setdefault("monthly_tracking", [])
        history = [row for row in history if row["date"] != today.isoformat()]
        history.append(point)
        forecast["monthly_tracking"] = history
        if elapsed_months >= 12:
            forecast["status"] = "COMPLETED"
            forecast["final_accuracy_pct"] = point["monthly_accuracy_pct"]
    forecast_file.write_text(json.dumps(forecasts, ensure_ascii=False, indent=2), encoding="utf-8")
    return forecasts


def add_monthly_forecasts(forecast_file: Path, predictions: list[dict], today: date | None = None):
    """Her hisse için ayda en fazla bir yeni tahmin kaydı oluşturur."""
    today = today or date.today()
    forecast_file.parent.mkdir(parents=True, exist_ok=True)
    forecasts = json.loads(forecast_file.read_text(encoding="utf-8")) if forecast_file.exists() else []
    existing = {(row["ticker"], row["forecast_date"][:7]) for row in forecasts}
    for prediction in predictions:
        key = (prediction["ticker"], today.isoformat()[:7])
        if key in existing:
            continue
        maturity = date(today.year + 1, today.month, min(today.day, 28))
        forecasts.append({
            "forecast_id": f"{prediction['ticker']}_{today.isoformat()}",
            "ticker": prediction["ticker"],
            "forecast_date": today.isoformat(),
            "maturity_date": maturity.isoformat(),
            "start_price": round(float(prediction["start_price"]), 4),
            "ml_target_price_12m": round(float(prediction["ml_target_price_12m"]), 4),
            "predicted_return_12m_pct": round(float(prediction["predicted_return_12m_pct"]), 2),
            "status": "ACTIVE",
            "monthly_tracking": []
        })
    forecast_file.write_text(json.dumps(forecasts, ensure_ascii=False, indent=2), encoding="utf-8")
    return forecasts
