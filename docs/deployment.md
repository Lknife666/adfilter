# Deployment Guide

This guide covers deploying adfilter in production environments.

## Deployment Options

| Method | Best For | Complexity |
|--------|----------|-----------|
| GitHub Actions (Fork) | Zero-infra, personal use | Low |
| Docker Compose | Home server, NAS | Low |
| Kubernetes (Helm) | Production, multi-tenant | Medium |
| Bare metal + cron | Lightweight VPS | Low |

---

## GitHub Actions (Fork)

The simplest deployment — no server needed:

1. Fork the repository
2. Edit `config/application.yaml`
3. Enable Actions in Settings
4. Rules auto-publish to the `release` branch every 8 hours

Subscribe URL: `https://raw.githubusercontent.com/<you>/adfilter/release/<file>`

---

## Docker Compose

### Basic Setup

```yaml
services:
  adfilter:
    image: ghcr.io/lknife666/adfilter:latest
    volumes:
      - ./config:/app/config:ro
      - rule_data:/app/rule
      - cache_data:/app/.cache
    environment:
      - TZ=Asia/Shanghai
    ports:
      - "8787:8787"
    command: >
      serve --dir /app/rule --host 0.0.0.0
      --auto-refresh --refresh-interval 480
      --config /app/config/application.yaml
    healthcheck:
      test: ["CMD", "adfilter", "doctor", "--config", "/app/config/application.yaml"]
      interval: 60s
    restart: unless-stopped

volumes:
  rule_data:
  cache_data:
```

### With Notifications

```yaml
services:
  adfilter:
    image: ghcr.io/lknife666/adfilter:latest
    environment:
      - TZ=Asia/Shanghai
      - TELEGRAM_BOT_TOKEN=your_token
      - TELEGRAM_CHAT_ID=your_chat_id
    # ... rest of config
```

### Resource Limits

```yaml
services:
  adfilter:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

---

## Kubernetes (Helm)

### Install

```bash
helm install adfilter ./charts/adfilter \
  --namespace adfilter \
  --create-namespace \
  -f my-values.yaml
```

### Custom Values

```yaml
# my-values.yaml
image:
  tag: "v1.0.0"

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: adfilter.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: adfilter-tls
      hosts:
        - adfilter.example.com

persistence:
  size: 5Gi
  storageClass: fast-ssd

cronjob:
  schedule: "0 */6 * * *"  # Every 6 hours

resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Upgrade

```bash
helm upgrade adfilter ./charts/adfilter -f my-values.yaml
```

### Uninstall

```bash
helm uninstall adfilter --namespace adfilter
```

---

## Bare Metal + Cron

### Setup

```bash
git clone https://github.com/Lknife666/adfilter.git
cd adfilter
uv sync --no-dev

# Or use the interactive setup
bash setup.sh
```

### Cron Schedule

```bash
# Update every 8 hours
0 */8 * * * cd /opt/adfilter && uv run adfilter run -c config/application.yaml --report rule/build-report.json 2>&1 | logger -t adfilter
```

### Systemd Service (Optional)

```ini
# /etc/systemd/system/adfilter-serve.service
[Unit]
Description=adfilter rule server
After=network.target

[Service]
Type=simple
User=adfilter
WorkingDirectory=/opt/adfilter
ExecStart=/opt/adfilter/.venv/bin/adfilter serve --dir rule/ --host 0.0.0.0 --port 8787
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Reverse Proxy

### Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name adfilter.example.com;

    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_valid 200 1h;
    }
}
```

### Caddy

```
adfilter.example.com {
    reverse_proxy localhost:8787
}
```

---

## Monitoring

### Health Check

```bash
curl -f http://localhost:8787/ || echo "Service down"
```

### Build Report

```bash
# Check last build status
cat rule/build-report.json | python -m json.tool
```

### Prometheus Metrics (Future)

Planned for v1.1 — expose `/metrics` endpoint with:
- `adfilter_rules_total` — total rules generated
- `adfilter_build_duration_seconds` — build time
- `adfilter_source_failures_total` — source fetch failures

---

## Security Considerations

1. **Run as non-root**: Docker image uses unprivileged user by default
2. **Read-only config**: Mount config volumes as `:ro`
3. **Network isolation**: Only expose port 8787 to trusted networks
4. **Secret management**: Use environment variables for tokens (never hardcode)
5. **SSRF protection**: Built-in — fetcher blocks private IP ranges
6. **Regular updates**: Enable Dependabot for dependency security patches
