FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV KEPLER_ENDPOINT=https://localhost:30443/metrics
ENV KOREA_CARBON_INTENSITY=424
ENV KOREA_PUE_TARGET=1.4

# Expose port for HTTP transport (optional)
EXPOSE 8000

# Run MCP server
CMD ["python", "-m", "src.mcp_server"]
