# Model governance and optimization notes

## Confirmed from repository
- Daily workflow refreshes prices and tracks forecasts. It does not call `apply_rev2_model`.
- The Rev 2 model metadata has export timestamp 2026-09-07; a model artifact is not proof of current predictions.
- The current price refresh preserves historical analyst and fundamental *absolute target prices*, and recomputes their implied upside. It does not refresh the underlying analyst/fundamental estimates.
- Backtest data declares current-constituent survivorship bias and absence of historical analyst/fundamental snapshots. Its headline returns must not be treated as unbiased forward performance.

## Implemented in this branch
- Do not forward-fill failed tickers into the latest price session.
- Stamp successful quotes with the market session date; exclude failed refreshes from forecast tracking.
- Standalone diagnostics: model age, incomplete weighted scores, simple technical indicators, sector and stock concentration.
- Unit tests and CI workflow.

## Before production
1. Verify that the latest market session is not stale for the whole download; reject the run if all quotes are old.
2. Store per-ticker *actual quote timestamps* when available and account for suspended/illiquid securities.
3. Validate the complete JSON schema, uniqueness of tickers, finite prices, missing ticker coverage, and minimum success ratio before replacing published snapshots.
4. Implement monthly ML inference as a separately scheduled, explicitly versioned job. Preserve each forecast's immutable start date, model version, and price at creation.
5. Source and timestamp fundamental and analyst inputs separately. Mark unavailable or stale inputs rather than presenting old targets as fresh.
6. Compute technical scores from reproducible, point-in-time data and expose indicator values and dates to the dashboard.
7. Rebuild backtests from point-in-time constituent membership, delistings, corporate actions, realistic costs, and walk-forward retraining. Compare against SPY with confidence intervals and sector exposure.
8. Introduce a transparent configurable scoring policy; never silently redistribute missing components. Evaluate weights out-of-sample before recommending allocations.
9. Add portfolio risk limits, benchmark overlap, scenario analysis and a paper-trading evaluation period.
10. Only merge after CI and manual review of market-session edge cases.

## Reproducibility
Run `python -m unittest discover -s tests -v`. This branch does not retrain models or publish revised investment recommendations.
