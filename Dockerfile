FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install -U pip && pip install uv

WORKDIR /app

RUN uv pip install --system fastmcp pillow requests

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

COPY ./src ./src

EXPOSE 8000

CMD ["uv", "run", "src/server.py"]