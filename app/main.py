import os
import asyncio
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.vpn import VPNManager
from app.proxy import ProxyManager
from app.auth import get_api_token

app = FastAPI(title="VPNX", version="2.1.0", docs_url="/docs", redoc_url=None)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

vpn = VPNManager()
proxy = ProxyManager()

@app.on_event("startup")
async def startup():
    proxy.load()
    vpn.rotate_interval = int(os.environ.get("ROTATE_INTERVAL", 0))
    vpn.rotate_country = os.environ.get("ROTATE_COUNTRY", None)
    asyncio.create_task(vpn.watchdog(interval=30))
    # Auto-connect on startup
    asyncio.create_task(_auto_connect())

async def _auto_connect():
    await asyncio.sleep(5)  # wait for API to be ready
    country = os.environ.get("CONNECT_COUNTRY", None)
    result = await vpn.connect(country=country)
    if result.get("status") == "connected":
        proxy.set_external("tun0")

def _check_auth(authorization: str = Header(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token or token != get_api_token():
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/login")
async def login(authorization: str = Header(None)):
    _check_auth(authorization)
    return {"status": "ok", "proxy": proxy.info()}

@app.get("/status")
async def status(authorization: str = Header(None)):
    _check_auth(authorization)
    return {"vpn": vpn.status(), "proxy": proxy.info()}

@app.get("/health")
async def health():
    return {"status": "ok", "vpn": vpn.status()}

@app.get("/rotate-config")
async def get_rotate_config(authorization: str = Header(None)):
    _check_auth(authorization)
    return {
        "interval": vpn.rotate_interval,
        "country": vpn.rotate_country,
    }

@app.post("/rotate-config")
async def set_rotate_config(
    interval: int = Query(None),
    country: str = Query(None),
    authorization: str = Header(None),
):
    _check_auth(authorization)
    if interval is not None:
        vpn.rotate_interval = max(0, interval)
    if country is not None:
        vpn.rotate_country = country.upper() if country else None
    return {
        "interval": vpn.rotate_interval,
        "country": vpn.rotate_country,
    }

@app.post("/connect")
async def connect(country: str = Query(None), authorization: str = Header(None)):
    _check_auth(authorization)
    result = await vpn.connect(country)
    if result.get("status") == "connected":
        proxy.set_external("tun0")
    return result

@app.post("/disconnect")
async def disconnect(authorization: str = Header(None)):
    _check_auth(authorization)
    result = vpn.disconnect()
    proxy.set_external("eth0")
    return result

@app.post("/rotate")
async def rotate(country: str = Query(None), authorization: str = Header(None)):
    _check_auth(authorization)
    result = await vpn.rotate(country)
    if result.get("status") == "connected":
        proxy.set_external("tun0")
    return result

@app.get("/locations")
async def locations(country: str = Query(None), authorization: str = Header(None)):
    _check_auth(authorization)
    if not vpn.servers:
        await vpn.fetch_servers()
    return vpn.get_locations(country)

# Serve web dashboard
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    async def dashboard():
        return FileResponse(os.path.join(WEB_DIR, "index.html"))
