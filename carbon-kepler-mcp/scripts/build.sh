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
echo "Build complete: $FULL_IMAGE"
echo ""

# Import into K3s containerd if K3s is available
if command -v k3s &> /dev/null; then
    echo "Importing image into K3s containerd..."
    docker save "$FULL_IMAGE" | sudo k3s ctr images import -
    echo "Image imported into K3s containerd"
    echo ""
else
    echo "K3s not found - skipping containerd import"
    echo "If deploying to K3s, run this manually:"
    echo "  sudo docker save $FULL_IMAGE | sudo k3s ctr images import -"
    echo ""
fi

echo "To push to registry:"
echo "  docker push $FULL_IMAGE"
echo ""
echo "To run locally:"
echo "  docker run -e KEPLER_ENDPOINT=https://YOUR_IP:30443/metrics $FULL_IMAGE"
