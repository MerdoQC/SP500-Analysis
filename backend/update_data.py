from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np
import yfinance as yf
import joblib

from backend.tracking import update_forecast_tracking

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LATEST_JSON = DATA_DIR / "latest_results.json"
HISTORY_DIR = DATA_DIR / "history"
FORECAST_FILE = DATA_DIR / "forecasts" / "forecasts.json"
MODEL_DIR = ROOT / "backend" / "models"


def _safe_number(value):
    try:
        return None if value is None or pd.isna(value) else float(value)
    except (TypeError, ValueError):
        return None


def _target_from_upside(price, upside):
    if price is None or upside is None:
        return None
    return price * (1 + upside / 100)


def refresh_market_prices(rows: list[dict]) -> list[dict]:
    """Hafif güncelleme: güncel fiyatı çeker, mevcut hedeflerin dolar karşılığını korur.

    Tam temel/analist yeniden hesaplaması Rev 2 notebook kodundan bu modüle
    taşındığında burada genişletilecektir.
    """
    tickers = [row["yf_ticker"] for row in rows]
    prices = yf.download(tickers, period="5d", interval="1d", auto_adjust=False, progress=False, threads=True)
    close = prices["Close"] if isinstance(prices.columns, pd.MultiIndex) else prices[["Close"]]
    latest = close.ffill().iloc[-1]
    if not isinstance(latest, pd.Series):
        latest = pd.Series({tickers[0]: latest})
    refreshed = []
    for row in rows:
        item = dict(row)
        old_price = _safe_number(item.get("current_price"))
        new_price = _safe_number(latest.get(item["yf_ticker"]))
        analyst_upside = _safe_number(item.get("analyst_upside_pct"))
        fundamental_upside = _safe_number(item.get("fundamental_upside_pct"))
        # İlk snapshot'taki mutlak hedefleri fiyat değişince kaybetmemek için sabitle.
        item.setdefault("analyst_target_price", _target_from_upside(old_price, analyst_upside))
        item.setdefault("fundamental_target_price", _target_from_upside(old_price, fundamental_upside))
        if new_price is not None:
            item["current_price"] = round(new_price, 4)
            if item.get("analyst_target_price"):
                item["analyst_upside_pct"] = round((item["analyst_target_price"] / new_price - 1) * 100, 2)
            if item.get("fundamental_target_price"):
                item["fundamental_upside_pct"] = round((item["fundamental_target_price"] / new_price - 1) * 100, 2)
        item["last_market_update_utc"] = datetime.now(timezone.utc).isoformat()
        refreshed.append(item)
    return refreshed


def _series(download, field: str, ticker: str):
    if isinstance(download.columns, pd.MultiIndex):
        try:
            return download[field][ticker].dropna()
        except KeyError:
            return pd.Series(dtype=float)
    if len(download.columns) and ticker in download.columns:
        return download[ticker].dropna()
    return download[field].dropna() if field in download else pd.Series(dtype=float)


def build_latest_ml_features(rows: list[dict]):
    tickers = [row["yf_ticker"] for row in rows]
    raw = yf.download(tickers + ["SPY"], period="15mo", interval="1d", auto_adjust=True, progress=False, threads=True)
    spy_close = _series(raw, "Close", "SPY")
    spy_monthly = spy_close.resample("ME").last()
    spy_returns = {months: (spy_monthly.iloc[-1] / spy_monthly.iloc[-1-months] - 1) * 100 for months in (3, 6, 12)}
    sectors = {row["yf_ticker"]: row.get("sector_sp500") for row in rows}
    features = []
    for ticker in tickers:
        close = _series(raw, "Close", ticker)
        volume = _series(raw, "Volume", ticker)
        if len(close) < 260:
            continue
        monthly = close.resample("ME").last()
        if len(monthly) < 13:
            continue
        daily_returns = close.pct_change().dropna().tail(252)
        running_max = close.tail(252).cummax()
        drawdown = close.tail(252) / running_max - 1
        volume_monthly = volume.resample("ME").mean() if len(volume) else pd.Series(dtype=float)
        recent_volume = volume_monthly.tail(3).mean() if len(volume_monthly) >= 6 else np.nan
        prior_volume = volume_monthly.iloc[-6:-3].mean() if len(volume_monthly) >= 6 else np.nan
        return_12m = (monthly.iloc[-1] / monthly.iloc[-13] - 1) * 100
        features.append({
            "yf_ticker": ticker,
            "sector_sp500": sectors.get(ticker),
            "return_1m_pct": (monthly.iloc[-1] / monthly.iloc[-2] - 1) * 100,
            "return_3m_pct": (monthly.iloc[-1] / monthly.iloc[-4] - 1) * 100,
            "return_6m_pct": (monthly.iloc[-1] / monthly.iloc[-7] - 1) * 100,
            "return_12m_pct": return_12m,
            "relative_return_sp500_pct": return_12m - spy_returns[12],
            "volatility_12m_pct": daily_returns.std() * np.sqrt(252) * 100,
            "max_drawdown_12m_pct": drawdown.min() * 100,
            "volume_change_3m_pct": (recent_volume / prior_volume - 1) * 100 if prior_volume and not pd.isna(prior_volume) else np.nan,
            "spy_return_3m_pct": spy_returns[3],
            "spy_return_6m_pct": spy_returns[6],
            "spy_return_12m_pct": spy_returns[12],
        })
    return pd.DataFrame(features)


def apply_rev2_model(rows: list[dict]):
    model_path = MODEL_DIR / "regression_model_v2.joblib"
    metadata_path = MODEL_DIR / "model_metadata_v2.json"
    if not model_path.exists() or not metadata_path.exists():
        return rows, []
    model = joblib.load(model_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    features = build_latest_ml_features(rows)
    if features.empty:
        return rows, []
    feature_columns = metadata["numeric_features"] + metadata["categorical_features"]
    features["predicted_return_12m_pct"] = model.predict(features[feature_columns])
    prediction_map = features.set_index("yf_ticker")["predicted_return_12m_pct"].to_dict()
    forecasts = []
    for item in rows:
        prediction = _safe_number(prediction_map.get(item["yf_ticker"]))
        price = _safe_number(item.get("current_price"))
        if prediction is None or price is None:
            continue
        target = price * (1 + prediction / 100)
        item["ml_predicted_return_12m_pct"] = round(prediction, 2)
        item["ml_start_price"] = round(price, 4)
        item["ml_target_price_12m"] = round(target, 4)
        forecasts.append({
            "ticker": item["ticker"], "start_price": price,
            "ml_target_price_12m": target, "predicted_return_12m_pct": prediction
        })
    return rows, forecasts


def run_refresh():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    rows = json.loads(LATEST_JSON.read_text(encoding="utf-8"))
    refreshed = refresh_market_prices(rows)
    timestamp = datetime.now(timezone.utc)
    snapshot = HISTORY_DIR / f"{timestamp:%Y-%m-%d}.json"
    payload = json.dumps(refreshed, ensure_ascii=False, indent=2)
    LATEST_JSON.write_text(payload, encoding="utf-8")
    snapshot.write_text(payload, encoding="utf-8")
    current_prices = {row["ticker"]: row["current_price"] for row in refreshed if row.get("current_price") is not None}
    update_forecast_tracking(FORECAST_FILE, current_prices, timestamp.date())
    return {"status": "completed", "company_count": len(refreshed), "updated_at": timestamp.isoformat()}


if __name__ == "__main__":
    print(run_refresh())
