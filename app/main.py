from fastapi import FastAPI, HTTPException, Header, Query
from app.vpn import VPNManager
from app.proxy import ProxyManager
from app.auth import get_api_token

app = FastAPI(title="VPX", version="1.0.0")
vpn = VPNManager()
proxy = ProxyManager()

@app.on_event("startup")
async def startup():
    proxy.load()

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

@app.post("/connect")
async def connect(country: str = Query(None), authorization: str = Header(None)):
    _check_auth(authorization)
    result = await vpn.connect(country)
    if result.get("status") == "connected":
        proxy.set_external("tun0")
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
