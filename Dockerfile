FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.13-slim AS runtime

ARG JELLYSCOPE_VERSION=dev
LABEL org.opencontainers.image.version="${JELLYSCOPE_VERSION}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/home/jellyscope/.cache/huggingface

RUN groupadd --system --gid 1000 jellyscope \
    && useradd --system --uid 1000 --gid jellyscope --create-home --shell /usr/sbin/nologin jellyscope

WORKDIR /app

COPY --from=builder --chown=jellyscope:jellyscope /app/.venv /app/.venv
COPY --from=builder --chown=jellyscope:jellyscope /app/src /app/src

RUN mkdir -p /data && chown -R jellyscope:jellyscope /data

USER jellyscope

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/').read()"

ENTRYPOINT ["jellyscope"]
CMD ["--host", "0.0.0.0", "--port", "5000", "--data-dir", "/data"]
