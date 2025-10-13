#!/bin/bash
#
# Test Carbon-Aware Kepler MCP Server locally
#

set -e

KEPLER_ENDPOINT="${KEPLER_ENDPOINT:-https://localhost:30443/metrics}"

echo "========================================="
echo "Testing MCP Server Locally"
echo "========================================="
echo "Kepler Endpoint: $KEPLER_ENDPOINT"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found"
    exit 1
fi

# Install dependencies if needed
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Running MCP server in test mode..."
echo ""

# Run server
export KEPLER_ENDPOINT="$KEPLER_ENDPOINT"
export KOREA_CARBON_INTENSITY="424"
export KOREA_PUE_TARGET="1.4"

python3 -m src.mcp_server
