FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml MCP.md LICENSE-CODE ./
COPY src ./src
RUN pip install --no-cache-dir .
USER 65534:65534
ENTRYPOINT ["nextreset-mcp"]
