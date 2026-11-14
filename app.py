"""
VALORANT ACCOUNT CHECKER & DATABASE
FastAPI Ana Uygulama Sunucusu ve REST API
"""

import os
import logging
from pathlib import Path
from typing import Optional
import requests
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import ALL_CONTENT_ENDPOINTS, BASE_DIR, DEFAULT_REGION, SERVER_HOST, SERVER_PORT
from database.db import db
from services.checker_engine import checker_engine
from services.content_service import content_service
from services.html_exporter import generate_account_html_report
from services.riot_service import RiotClient

# Loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ValoChecker.App")

# FastAPI Uygulaması
app = FastAPI(
    title="VALORANT Account Checker & Database",
    description="Valorant hesap kontrolü, detaylı loglama, veritabanı ve tüm valorant-api.com uç noktaları",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dizinler
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ============================================================
# PYDANTIC MODELLERİ
# ============================================================
class CheckRequest(BaseModel):
    redirect_url: str
    region: Optional[str] = DEFAULT_REGION
    notes: Optional[str] = ""


# ============================================================
# SAYFA ROTALARI
# ============================================================
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon 404 uyarılarını önler."""
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Ana kontrol ve veritabanı paneli arayüzü."""
    return templates.TemplateResponse(request=request, name="index.html")



# ============================================================
# HESAP KONTROL VE LOGLAMA API'Sİ
# ============================================================
@app.post("/api/check")
async def check_account(req: CheckRequest):
    """
    Riot oturum URL'si ile hesabı kontrol eder, tüm uç noktaları tarar,
    veritabanına detaylı log kaydı atar ve tam snapshot döndürür.
    """
    region = (req.region or DEFAULT_REGION).lower().strip()
    client = None
    try:
        client = RiotClient(region=region)
        client.authenticate_url(req.redirect_url)

        snapshot = checker_engine.run_check(client, notes=req.notes or "")
        return JSONResponse(content=snapshot)

    except ValueError as ve:
        logger.warning(f"Doğrulama hatası: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as ce:
        logger.error(f"Riot bağlantı veya DNS hatası: {ce}")
        raise HTTPException(
            status_code=502,
            detail="Riot Games sunucularına bağlanırken geçici bir ağ veya DNS hatası oluştu. Lütfen bağlantınızı kontrol edip tekrar deneyin."
        )
    except requests.exceptions.HTTPError as he:
        status_code = he.response.status_code if he.response is not None else 400
        msg = "Oturum belirtecinin süresi dolmuş veya geçersiz. Lütfen Riot giriş sayfasından tekrar giriş yapıp bağlantıyı yapıştırın." if status_code in (401, 403) else f"Riot API isteği başarısız oldu (HTTP {status_code})."
        logger.error(f"Riot HTTP Hatası: {he}")
        raise HTTPException(status_code=status_code, detail=msg)
    except Exception as e:
        logger.error(f"Hesap kontrolü sırasında hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Kontrol sırasında hata oluştu: {str(e)}")
    finally:
        if client:
            client.close()


# ============================================================
# HESAPLAR VE LOGLAR VERİTABANI API'LERİ
# ============================================================
@app.get("/api/accounts")
async def list_accounts():
    """Veritabanında kayıtlı tüm hesapları listeler."""
    return db.get_accounts()


@app.get("/api/accounts/{puuid}")
async def get_account_detail(puuid: str):
    """Tek bir hesabın bilgilerini ve son snapshot logunu döndürür."""
    acc = db.get_account(puuid)
    if not acc:
        raise HTTPException(status_code=404, detail="Hesap bulunamadı.")
    return acc


@app.get("/api/accounts/{puuid}/logs")
async def get_account_logs(puuid: str, limit: int = Query(100, ge=1, le=500)):
    """Bir hesaba ait geçmiş kontrol loglarını kronolojik olarak listeler."""
    return db.get_account_logs(puuid, limit=limit)


@app.get("/api/logs/{log_id}")
async def get_log_detail(log_id: int):
    """Tek bir kontrol logunun tüm snapshot verilerini döndürür."""
    log_entry = db.get_log(log_id)
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log kaydı bulunamadı.")
    return log_entry


@app.delete("/api/accounts/{puuid}")
async def delete_account(puuid: str):
    """Hesabı ve tüm geçmiş kayıtlarını siler."""
    deleted = db.delete_account(puuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Hesap silinemedi veya bulunamadı.")
    return {"success": True, "message": "Hesap ve logları silindi."}


@app.delete("/api/logs/{log_id}")
async def delete_log(log_id: int):
    """Tek bir kontrol logunu siler."""
    deleted = db.delete_log(log_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Log bulunamadı.")
    return {"success": True, "message": "Log kaydı silindi."}


@app.get("/api/stats")
async def get_stats():
    """Veritabanı genel istatistiklerini döndürür."""
    return db.get_database_stats()


# ============================================================
# HTML RAPOR EXPORT API'LERİ
# ============================================================
@app.get("/api/export/html/{puuid}")
async def export_latest_html(puuid: str):
    """Hesabın en son kontrol verisini standalone HTML dosyası olarak üretir ve döndürür."""
    acc = db.get_account(puuid)
    if not acc or not acc.get("latest_log") or not acc["latest_log"].get("snapshot"):
        raise HTTPException(status_code=404, detail="Hesap veya log verisi bulunamadı.")

    snapshot = acc["latest_log"]["snapshot"]
    file_path = generate_account_html_report(snapshot, open_in_browser=False)

    return FileResponse(
        path=file_path,
        media_type="text/html",
        filename=os.path.basename(file_path)
    )


@app.get("/api/export/html/log/{log_id}")
async def export_log_html(log_id: int):
    """Belirli bir geçmiş logun HTML raporunu üretir ve döndürür."""
    log_entry = db.get_log(log_id)
    if not log_entry or not log_entry.get("snapshot"):
        raise HTTPException(status_code=404, detail="Log kaydı veya snapshot bulunamadı.")

    snapshot = log_entry["snapshot"]
    file_path = generate_account_html_report(snapshot, open_in_browser=False)

    return FileResponse(
        path=file_path,
        media_type="text/html",
        filename=os.path.basename(file_path)
    )


# ============================================================
# DASH.VALORANT-API.COM 30 UÇ NOKTA GEZGİNİ API'LERİ
# ============================================================
@app.get("/api/content/endpoints")
async def list_content_endpoints():
    """dash.valorant-api.com üzerindeki tüm 30 uç noktanın meta verilerini döndürür."""
    return content_service.get_endpoints_catalog()


@app.get("/api/content/{endpoint_id:path}")
async def get_content_endpoint_data(endpoint_id: str, language: Optional[str] = None):
    """Herhangi bir uç noktanın (30 uç nokta) verisini getirir ve önbellekler."""
    valid_ids = {ep["id"] for ep in ALL_CONTENT_ENDPOINTS}
    if endpoint_id not in valid_ids:
        raise HTTPException(status_code=404, detail=f"Bilinmeyen uç nokta: {endpoint_id}")

    data = content_service.fetch_endpoint(endpoint_id, language=language)
    return JSONResponse(content=data)
