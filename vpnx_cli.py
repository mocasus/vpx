"""VPNX CLI — start the VPNX Docker container with one command."""
import subprocess, sys, secrets

VERSION = "2.0.0"
IMAGE = "mocasus/vpnx:latest"

def main():
    token = sys.argv[1] if len(sys.argv) > 1 else secrets.token_hex(16)

    if subprocess.run(["which", "docker"], capture_output=True).returncode != 0:
        print("Docker not found. Install: https://docs.docker.com/get-docker/")
        sys.exit(1)

    subprocess.run(["docker", "rm", "-f", "vpnx"], capture_output=True)
    cmd = [
        "docker", "run", "-d", "--name", "vpnx",
        "--cap-add", "NET_ADMIN", "--device", "/dev/net/tun",
        "-p", "1080:1080", "-p", "8080:8080", "-p", "8000:8000",
        "-e", f"API_TOKEN={token}", "--restart", "unless-stopped",
        IMAGE,
    ]
    if subprocess.run(cmd).returncode == 0:
        print(f"""
╔══════════════════════════════════════════╗
║          VPNX v{VERSION} — Ready!             ║
╠══════════════════════════════════════════╣
║  API:     http://localhost:8000           ║
║  Token:   {token:<32}║
║  SOCKS5:  localhost:1080                 ║
║  HTTP:    localhost:8080                 ║
╠══════════════════════════════════════════╣
║  Endpoints:                              ║
║    POST /connect     — connect to VPN    ║
║    POST /disconnect  — disconnect VPN    ║
║    POST /rotate      — rotate server     ║
║    GET  /status      — check status      ║
║    GET  /locations   — list servers      ║
╚══════════════════════════════════════════╝
""")

if __name__ == "__main__":
    main()
