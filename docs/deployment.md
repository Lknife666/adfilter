# Deployment Guide

This guide covers deploying adfilter in different environments.

---

## Deployment Options

| Method | Best For | Complexity |
|--------|----------|-----------|
| GitHub Actions (Fork) | Personal use, zero maintenance | Minimal |
| Docker Compose | Home server, LAN subscriptions | Low |
| Kubernetes (Helm) | Enterprise, high availability | Medium |
| Bare metal + cron | VPS, existing infrastructure | Low |

---

## 1. GitHub Actions (Recommended)

See the [README Fork Guide](../README.md#方案二fork-仓库--github-actions-自动构建强烈推荐) for step-by-step instructions.

**Advantages:**
- Zero infrastructure cost
- Automatic updates every 8 hours
- No maintenance required
- Private rules via private fork

---

## 2. Docker Compose

### Basic Setup

```yaml
# docker-compose.yml
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
      timeout: 10s
      retries: 3
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
    volumes:
      - ./config:/app/config:ro
      - rule_data:/app/rule
      - cache_data:/app/.cache
    environment:
      - TZ=Asia/Shanghai
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    ports:
      - "8787:8787"
    command: >
      serve --dir /app/rule --host 0.0.0.0
      --auto-refresh --refresh-interval 480
      --config /app/config/application.yaml
    restart: unless-stopped

volumes:
  rule_data:
  cache_data:
```

### One-Shot Build (CI/CD)

```bash
docker run --rm \
  -v ./config:/app/config:ro \
  -v ./rule:/app/rule \
  ghcr.io/lknife666/adfilter run \
  --config /app/config/application.yaml \
  --progress --report /app/rule/build-report.json
```

### Resource Limits

```yaml
services:
  adfilter:
    # ...
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
        reservations:
          memory: 128M
          cpus: '0.25'
```

---

## 3. Kubernetes (Helm Chart)

### Install

```bash
helm repo add adfilter https://lknife666.github.io/adfilter/charts
helm install adfilter adfilter/adfilter \
  --set config.preset=cn \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=rules.example.com
```

### Custom Values

```yaml
# values.yaml
replicaCount: 1

image:
  repository: ghcr.io/lknife666/adfilter
  tag: "latest"
  pullPolicy: Always

service:
  type: ClusterIP
  port: 8787

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: rules.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: rules-tls
      hosts:
        - rules.example.com

persistence:
  rules:
    enabled: true
    size: 1Gi
    storageClass: ""
  cache:
    enabled: true
    size: 2Gi
    storageClass: ""

cronJob:
  enabled: true
  schedule: "0 */8 * * *"
  resources:
    limits:
      memory: 512Mi
      cpu: 500m
    requests:
      memory: 128Mi
      cpu: 100m

config:
  # Inline config or reference a ConfigMap
  applicationYaml: |
    application:
      config:
        input:
          rule:
            default:
              - name: anti-ad
                type: easylist
                path: https://anti-ad.net/easylist.txt
        output:
          path: /data/rules
          files:
            - { name: dns.txt, type: dns }
            - { name: clash.yaml, type: clash }
            - { name: hosts.txt, type: hosts }
        optimizer:
          enable: true
          collapse_subdomains: true
```

### Architecture

```
┌─────────────────────────────────────────────────┐
│                  Kubernetes Cluster               │
│                                                   │
│  ┌──────────────┐       ┌────────────────────┐  │
│  │   CronJob    │       │   Deployment       │  │
│  │  (build)     │──────▶│   (serve + web)    │  │
│  │  every 8h    │       │   replicas: 1      │  │
│  └──────────────┘       └────────────────────┘  │
│         │                        │               │
│         ▼                        ▼               │
│  ┌────────────────────────────────────────────┐ │
│  │              PVC (shared)                   │ │
│  │  /data/rules/   /data/cache/               │ │
│  └────────────────────────────────────────────┘ │
│                                                   │
│  ┌──────────────┐       ┌────────────────────┐  │
│  │   Ingress    │──────▶│     Service        │  │
│  │  rules.xxx   │       │     :8787          │  │
│  └──────────────┘       └────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 4. Bare Metal + Cron

### Install

```bash
# Use the interactive setup script
curl -fsSL https://raw.githubusercontent.com/Lknife666/adfilter/main/setup.sh | bash
```

Or manually:

```bash
git clone --depth=1 https://github.com/Lknife666/adfilter.git
cd adfilter
uv sync --no-dev
uv run adfilter init --preset cn --output config/application.yaml
```

### Cron Setup

```bash
# Every 8 hours
0 */8 * * * cd /opt/adfilter && uv run adfilter run --config config/application.yaml --report rule/build-report.json

# With HTTP serve (run as systemd service instead)
```

### Systemd Service

```ini
# /etc/systemd/system/adfilter.service
[Unit]
Description=adfilter rule subscription server
After=network.target

[Service]
Type=simple
User=adfilter
WorkingDirectory=/opt/adfilter
ExecStart=/opt/adfilter/.venv/bin/adfilter serve --dir rule/ --host 0.0.0.0 --port 8787 --auto-refresh --refresh-interval 480 --config config/application.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now adfilter
```

---

## Reverse Proxy Configuration

### Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name rules.example.com;

    ssl_certificate /etc/letsencrypt/live/rules.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rules.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Cache rule files for 1 hour at edge
        proxy_cache_valid 200 1h;
        add_header X-Cache-Status $upstream_cache_status;
        add_header Access-Control-Allow-Origin *;
    }
}
```

### Caddy

```
rules.example.com {
    reverse_proxy localhost:8787
    header Access-Control-Allow-Origin *
}
```

---

## Monitoring

### Health Check

```bash
# CLI doctor command
adfilter doctor --config config/application.yaml

# HTTP health endpoint (when using serve)
curl http://localhost:8787/health
```

### Log Levels

```bash
# Structured JSON logs for production
adfilter run --json-logs --log-level INFO

# Verbose debug logs
adfilter run --log-level DEBUG
```

### Prometheus Metrics (v1.0+)

When `[metrics]` extra is installed:

```yaml
# Scrape config
- job_name: adfilter
  static_configs:
    - targets: ['localhost:8787']
  metrics_path: /metrics
```

Available metrics:
- `adfilter_build_duration_seconds` — build time histogram
- `adfilter_rules_total{format}` — rule count per format
- `adfilter_source_errors_total{source}` — fetch error counter
- `adfilter_last_build_timestamp` — Unix timestamp of last successful build

---

## Security Considerations

1. **Non-root execution** — Docker image runs as `adfilter` user
2. **Read-only config** — Mount config volume as `:ro`
3. **Network isolation** — Only expose port 8787, no admin endpoints
4. **SSRF protection** — Fetcher blocks requests to private IP ranges
5. **Secret management** — Use environment variables for tokens, never hardcode
6. **Rate limiting** — Add at reverse proxy layer (Nginx `limit_req`)

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs adfilter

# Validate config inside container
docker exec adfilter adfilter validate --config /app/config/application.yaml
```

### Rules not updating

```bash
# Check auto-refresh status
docker logs adfilter | grep "auto-refresh"

# Force a rebuild
docker exec adfilter adfilter run --config /app/config/application.yaml
```

### High memory usage

- Default ~128MB for typical rule sets (50-100K rules)
- If exceeding 512MB, check for unusually large source lists
- Consider reducing source count or enabling `min_source_votes > 1` to reduce rules

### Permission denied on rule directory

```bash
# Fix ownership
chown -R 1000:1000 ./rule

# Or in compose:
user: "1000:1000"
```
