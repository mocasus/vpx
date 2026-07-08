FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openvpn dante-server tinyproxy supervisor curl iproute2 procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY scripts/ scripts/
COPY supervisord.conf /etc/supervisord.conf

RUN mkdir -p /config/vpn

EXPOSE 1080 8080 8000

ENTRYPOINT ["scripts/entrypoint.sh"]
