import os, json, subprocess, time

CRED_FILE = "/config/credentials.json"
DANTE_CONF = "/config/danted.conf"

class ProxyManager:
    def __init__(self):
        self.creds = {"username": "", "password": ""}
        self.loaded = False

    def load(self):
        if os.path.exists(CRED_FILE):
            with open(CRED_FILE) as f:
                self.creds = json.load(f)
            self.loaded = True

    def info(self):
        return {
            "socks5": ":1080",
            "http": ":8080",
            "username": self.creds.get("username"),
            "password": self.creds.get("password"),
        }

    def set_external(self, iface):
        if not os.path.exists(DANTE_CONF):
            return
        with open(DANTE_CONF) as f:
            lines = f.readlines()
        with open(DANTE_CONF, "w") as f:
            for line in lines:
                if line.strip().startswith("external:"):
                    f.write(f"external: {iface}\n")
                else:
                    f.write(line)
        subprocess.run(["pkill", "danted"], capture_output=True)
        time.sleep(2)
