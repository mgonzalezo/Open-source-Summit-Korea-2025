#!/bin/bash
#
# Build Docker image for Carbon-Aware Kepler MCP Server
#

set -e

# Configuration
IMAGE_NAME="carbon-kepler-mcp"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-localhost:5000}"

FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "========================================="
echo "Building Carbon-Aware Kepler MCP Server"
echo "========================================="
echo "Image: $FULL_IMAGE"
echo ""

# Build image
docker build -t "$FULL_IMAGE" .

echo ""
echo "✅ Build complete: $FULL_IMAGE"
echo ""
echo "To push to registry:"
echo "  docker push $FULL_IMAGE"
echo ""
echo "To run locally:"
echo "  docker run -e KEPLER_ENDPOINT=https://YOUR_IP:30443/metrics $FULL_IMAGE"
