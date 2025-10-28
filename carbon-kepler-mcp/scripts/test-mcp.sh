#!/bin/bash
#
# Simple MCP Server Test
#

# Get public IP
PUBLIC_IP="${PUBLIC_IP:-}"
if [ -z "$PUBLIC_IP" ]; then
    if command -v aws &> /dev/null; then
        PUBLIC_IP=$(aws cloudformation describe-stacks \
            --stack-name kepler-k3s-rapl \
            --region ap-northeast-1 \
            --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
            --output text 2>/dev/null || echo "")
    fi
fi

if [ -z "$PUBLIC_IP" ]; then
    echo "Please set PUBLIC_IP environment variable"
    echo "Example: export PUBLIC_IP=3.115.147.150"
    exit 1
fi

MCP_URL="http://${PUBLIC_IP}:30800/sse"

echo "========================================="
echo "Testing MCP Server"
echo "========================================="
echo "URL: $MCP_URL"
echo ""

# Test connection
echo "Testing connection (will timeout after 2 seconds)..."
RESPONSE=$(curl -s -m 2 -H "Accept: text/event-stream" "$MCP_URL" 2>&1 || true)

if echo "$RESPONSE" | grep -q "event:"; then
    echo "SUCCESS: MCP server is responding"
    echo ""
    echo "Sample response:"
    echo "$RESPONSE" | head -5
elif curl -s -m 2 -I "$MCP_URL" 2>&1 | grep -q "200 OK"; then
    echo "SUCCESS: MCP server is reachable (HTTP 200)"
    echo ""
    echo "Full connection test:"
    curl -v -m 2 "$MCP_URL" 2>&1 | head -20
else
    echo "FAILED: Cannot connect to MCP server"
    echo ""
    echo "Debug information:"
    curl -v -m 5 "$MCP_URL" 2>&1 | head -30
    exit 1
fi

echo ""
echo "========================================="
echo "MCP Server is operational"
echo "========================================="
echo ""
echo "Endpoint: $MCP_URL"
echo ""
