import subprocess, sys, secrets

def main():
    token = sys.argv[1] if len(sys.argv) > 1 else secrets.token_hex(16)
    if subprocess.run(["which", "docker"], capture_output=True).returncode != 0:
        print("Docker not found. Install: https://docs.docker.com/get-docker/")
        sys.exit(1)
    subprocess.run(["docker", "rm", "-f", "vpx"], capture_output=True)
    cmd = ["docker", "run", "-d", "--name", "vpx",
           "--cap-add", "NET_ADMIN", "--device", "/dev/net/tun",
           "-p", "1080:1080", "-p", "8080:8080", "-p", "8000:8000",
           "-e", f"API_TOKEN={token}", "--restart", "unless-stopped",
           "mocasus/vpx:latest"]
    if subprocess.run(cmd).returncode == 0:
        print(f"\nVPX started!\nAPI: http://localhost:8000\nToken: {token}"
              f"\nSOCKS5: localhost:1080\nHTTP: localhost:8080")

if __name__ == "__main__":
    main()
