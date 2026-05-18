# https://github.com/kubernetes-client/python/issues/2394
FROM python:3.12.13-alpine

RUN adduser -S -u 1000 py

WORKDIR /app

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev

COPY src .

USER py

ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "main.py"]
