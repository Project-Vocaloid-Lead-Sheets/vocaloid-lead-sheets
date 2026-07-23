FROM python:3.13-slim AS base

WORKDIR /app

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./

FROM base AS development
RUN uv sync --frozen --all-groups --no-install-project

COPY . .

RUN uv sync --frozen --all-groups
CMD ["uv", "run", "watchfiles", "python -m discord_bot", "src"]
