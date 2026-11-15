FROM python:3.12-slim

LABEL io.modelcontextprotocol.server.name="io.github.rare-disease-atlas/orphan-disease-opportunity-mcp" \
      org.opencontainers.image.title="Orphan Disease Opportunity MCP Server" \
      org.opencontainers.image.description="Zero-dependency MCP server for high-tractability orphan disease startup blueprints, JAK2+ Myelofibrosis biology, non-dilutive grants, and ethical validation." \
      org.opencontainers.image.url="https://rare-disease-atlas.github.io" \
      org.opencontainers.image.source="https://github.com/rare-disease-atlas/orphan-disease-opportunity-mcp" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

# Create dedicated non-root user for hardened sandbox execution (Glama / Smithery / OCI)
RUN groupadd --gid 10001 mcpuser \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin mcpuser

COPY pyproject.toml MANIFEST.in LICENSE README.md openapi.yaml server.json ./
COPY orphan_disease_mcp ./orphan_disease_mcp
COPY data ./data

RUN pip install --no-cache-dir . \
    && chown -R mcpuser:mcpuser /app

USER mcpuser

# Default entrypoint runs standard MCP JSON-RPC 2.0 over stdio;
# pass `--transport http --host 0.0.0.0 --port 8080` for Streamable HTTP mode.
ENTRYPOINT ["orphan-disease-opportunity-mcp"]
