# Multi-stage build producing a ~40 MB runtime image.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS build
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev --no-install-project \
 && uv pip install --no-deps --system .

FROM python:3.14-slim
COPY --from=build /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=build /usr/local/bin/adfilter /usr/local/bin/adfilter
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["adfilter"]
CMD ["run", "--config", "/work/config/application.yaml"]
