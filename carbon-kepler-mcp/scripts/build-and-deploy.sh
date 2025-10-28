#!/bin/bash
#
# Build and Deploy Carbon-Aware Kepler MCP Server to K3s
# This script combines build.sh and deploy.sh for convenience
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MCP_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================="
echo "Build and Deploy MCP Server"
echo "========================================="
echo ""

# Step 1: Build the Docker image
echo "Step 1: Building Docker image..."
echo ""
cd "$MCP_ROOT"
"$SCRIPT_DIR/build.sh"

echo ""
echo "========================================="
echo ""

# Step 2: Deploy to K3s
echo "Step 2: Deploying to K3s..."
echo ""
"$SCRIPT_DIR/deploy.sh"

echo ""
echo "========================================="
echo "Build and Deploy Complete"
echo "========================================="
echo ""
echo "Quick status check:"
sudo kubectl get pods -n carbon-mcp
echo ""
echo "To view logs:"
echo "  sudo kubectl logs -n carbon-mcp -l app=carbon-mcp-server -f"
echo ""
echo "To test MCP server:"
echo "  curl http://localhost:30800/sse --max-time 3"
echo ""
