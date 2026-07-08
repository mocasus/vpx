#!/bin/bash
set -e

DEFAULT_IF=$(ip route show default 2>/dev/null | awk '{print $5}' | head -1)
DEFAULT_IF=${DEFAULT_IF:-eth0}

SOCKS_USER="vpx$(openssl rand -hex 4)"
SOCKS_PASS=$(openssl rand -hex 12)
API_TOKEN="${API_TOKEN:-$(openssl rand -hex 16)}"

mkdir -p /dev/net /config/vpn
[ ! -c /dev/net/tun ] && mknod /dev/net/tun c 10 200 && chmod 600 /dev/net/tun

useradd -r -s /bin/false "$SOCKS_USER" 2>/dev/null || true
echo "$SOCKS_USER:$SOCKS_PASS" | chpasswd

cat > /config/danted.conf << EOF
loglevel: error
internal: 0.0.0.0 port = 1080
external: $DEFAULT_IF
socksmethod: username
user.privileged: root
user.notprivileged: nobody
client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: error
}
socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: error
}
EOF

cat > /config/tinyproxy.conf << EOF
Port 8080
Listen 0.0.0.0
Timeout 30
BasicAuth $SOCKS_USER $SOCKS_PASS
ViaProxyName "vpx"
EOF

cat > /config/credentials.json << EOF
{"username":"$SOCKS_USER","password":"$SOCKS_PASS","api_token":"$API_TOKEN"}
EOF

echo "============================================"
echo "  VPX - VPN Proxy Exchange v1.0.0"
echo "============================================"
echo "API:    http://0.0.0.0:8000"
echo "Token:  $API_TOKEN"
echo "SOCKS5: $SOCKS_USER:$SOCKS_PASS @ :1080"
echo "HTTP:   $SOCKS_USER:$SOCKS_PASS @ :8080"
echo "============================================"

exec supervisord -c /etc/supervisord.conf
