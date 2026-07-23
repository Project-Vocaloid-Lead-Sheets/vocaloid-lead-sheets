FROM python:3.13-slim AS base

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv

FROM base AS development
RUN uv sync --frozen --all-groups

COPY . .
CMD ["uv", "run", "python", "-m", "discord_bot"]


FROM base AS production
RUN uv sync --frozen --no-dev
COPY src ./src
CMD ["uv", "run", "python", "-m", "discord_bot"]
