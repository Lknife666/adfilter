# ── Build stage ──
FROM python:3.14-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
RUN uv sync --frozen --no-dev --no-editable || uv sync --no-dev --no-editable

# ── Runtime stage ──
FROM python:3.14-slim AS runtime
RUN useradd -r -s /bin/false adfilter && \
    mkdir -p /app/rule /app/.cache && \
    chown -R adfilter:adfilter /app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY config/ config/
ENV PATH="/app/.venv/bin:$PATH"
USER adfilter
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
  CMD adfilter doctor --quiet || exit 1
ENTRYPOINT ["adfilter"]
CMD ["run", "--config", "config/application.yaml", "--progress"]
