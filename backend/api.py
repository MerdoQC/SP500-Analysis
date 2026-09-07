import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.update_data import run_refresh

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "latest_results.json"

app = FastAPI(title="S&P 500 Analysis API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Refresh-Token"],
)


@app.get("/health")
def health():
    return {"status": "ok", "results_available": RESULTS.exists()}


@app.get("/results")
def results():
    if not RESULTS.exists():
        raise HTTPException(404, "Sonuç dosyası bulunamadı.")
    return FileResponse(RESULTS, media_type="application/json")


@app.post("/refresh")
def refresh(background_tasks: BackgroundTasks, x_refresh_token: str | None = Header(default=None)):
    expected = os.getenv("REFRESH_TOKEN")
    if not expected or x_refresh_token != expected:
        raise HTTPException(403, "Güncelleme yalnızca panel sahibine açıktır.")
    background_tasks.add_task(run_refresh)
    return {"status": "started", "message": "Güncelleme başlatıldı."}

