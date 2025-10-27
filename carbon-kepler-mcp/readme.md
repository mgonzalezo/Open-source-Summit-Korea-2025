# Carbon-Aware Kepler MCP Server

**Model Context Protocol (MCP) server for Korean regulatory carbon compliance assessments**

Integrates Kepler energy monitoring with Korean regulatory standards to provide carbon footprint assessments for Kubernetes workloads.

## Overview

This MCP server provides tools for assessing Kubernetes workload compliance with Korean regulatory standards:

- **탄소중립 녹색성장 기본법** (Carbon Neutrality Act 2050) - 424 gCO2eq/kWh target
- **에너지이용 합리화법** (Energy Use Rationalization Act) - PUE ≤ 1.4 target

### Features

 **Real-time compliance assessment** - Fetch live metrics from Kepler
 **Korean regulatory focus** - PUE and carbon neutrality standards
 **Actionable recommendations** - Temporal shifting, resource optimization, regional migration
 **MCP protocol support** - Native Claude Desktop integration
 **Multi-transport** - stdio, SSE, HTTP

## Architecture

### Complete System Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                      Windows (Demo Machine)                           │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     Claude Desktop                              │  │
│  │  • Natural language queries                                     │  │
│  │  • MCP client (stdio transport)                                 │  │
│  └─────────────────────┬───────────────────────────────────────────┘  │
│                        │ stdio (JSON-RPC over stdin/stdout)           │
│  ┌─────────────────────▼───────────────────────────────────────────┐  │
│  │              mcp-sse-bridge.js (Node.js)                        │  │
│  │  • Translates stdio ↔ SSE                                       │  │
│  │  • Handles session management                                   │  │
│  │  • URL encoding for query parameters                            │  │
│  └─────────────────────┬───────────────────────────────────────────┘  │
└────────────────────────┼───────────────────────────────────────────────┘
                         │ HTTP + SSE
                         │ (Server-Sent Events over port 30800)
                         │
┌────────────────────────▼───────────────────────────────────────────────┐
│                  AWS EC2 (K3s Kubernetes Cluster)                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │           MCP Server (carbon-mcp namespace)                     │  │
│  │  ┌───────────────────────────────────────────────────────────┐  │  │
│  │  │  FastMCP Framework (SSE Transport)                        │  │  │
│  │  │  • Exposes: http://0.0.0.0:8000/sse (NodePort 30800)      │  │  │
│  │  │  • Transport: Server-Sent Events (SSE)                    │  │  │
│  │  │  • Protocol: JSON-RPC 2.0 over SSE                        │  │  │
│  │  └───────────────────────────────────────────────────────────┘  │  │
│  │  ┌───────────────────────────────────────────────────────────┐  │  │
│  │  │  8 MCP Tools:                                             │  │  │
│  │  │  • assess_workload_compliance                             │  │  │
│  │  │  • compare_optimization_impact                            │  │  │
│  │  │  • list_workloads_by_compliance                           │  │  │
│  │  │  • get_regional_comparison                                │  │  │
│  │  │  • calculate_optimal_schedule                             │  │  │
│  │  │  • identify_power_hotspots                                │  │  │
│  │  │  • list_top_power_consumers                               │  │  │
│  │  │  • get_power_consumption_summary                          │  │  │
│  │  └───────────────────────────────────────────────────────────┘  │  │
│  │                        ↓                                          │  │
│  │  ┌───────────────────────────────────────────────────────────┐  │  │
│  │  │  Kepler Client → Prometheus Parser                        │  │  │
│  │  │  • Fetches: http://kepler.kepler-system:28282/metrics     │  │  │
│  │  │  • Parses: Prometheus text format                         │  │  │
│  │  └───────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                        ↓                                               │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │         Kepler v0.11.2 (kepler-system namespace)                │  │
│  │  • ClusterIP: http://kepler:28282/metrics (internal)            │  │
│  │  • NodePort: http://<IP>:30080/metrics (external)               │  │
│  │  • Metrics: kepler_pod_cpu_watts, kepler_pod_memory_watts       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### What is SSE (Server-Sent Events)?

**SSE (Server-Sent Events)** is a standard HTTP-based protocol for real-time server-to-client streaming communication.

**How SSE works:**
1. Client opens HTTP connection to server endpoint (e.g., `/sse`)
2. Server keeps connection open and sends events as text:
   ```
   event: endpoint
   data: /messages/?session_id=abc123

   : ping - 1

   data: {"jsonrpc":"2.0","result":{...}}
   ```
3. Client receives events in real-time without polling

**Why we use SSE for MCP:**
- **Unidirectional streaming**: Server can push tool results to client
- **Standard HTTP**: Works through firewalls, proxies, load balancers
- **Lightweight**: No WebSocket complexity, just HTTP with persistent connection
- **Auto-reconnect**: Browser/client automatically reconnects if connection drops

**SSE vs Other Protocols:**
| Feature | SSE | WebSocket | HTTP Polling |
|---------|-----|-----------|--------------|
| Direction | Server → Client | Bidirectional | Client → Server |
| Protocol | HTTP | TCP | HTTP |
| Complexity | Low | Medium | Low |
| Firewall | Easy | Sometimes blocked | Easy |
| Use case | Real-time updates | Chat, games | Simple requests |

**Our Implementation:**
```
Windows (Claude Desktop)
    ↓ stdio (JSON-RPC)
Bridge (mcp-sse-bridge.js)
    ↓ HTTP POST (send requests)
    ↑ SSE stream (receive responses)
MCP Server (FastMCP on K8s)
```

The bridge translates between:
- **Inbound**: stdin → HTTP POST to `/messages/?session_id=...`
- **Outbound**: SSE stream → stdout (JSON-RPC messages)

## Quick Start

### 1. Prerequisites

- Kepler v0.11.2 deployed with HTTPS metrics endpoint
- K3s or Kubernetes cluster
- kubectl configured
- Docker (for building image)

### 2. Build Docker Image

```bash
cd carbon-kepler-mcp
scripts/scripts/build.sh
```

Or specify custom registry:

```bash
REGISTRY=your-registry.io scripts/scripts/build.sh
```

### 3. Deploy to Kubernetes

```bash
# Update deployment.yaml with your Kepler endpoint and registry
# Then deploy:
scripts/scripts/deploy.sh
```

### 4. Test MCP Server

```bash
# Get public IP
PUBLIC_IP=$(kubectl get svc carbon-mcp-server -n carbon-mcp -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test compliance assessment
MCP_ENDPOINT="http://$PUBLIC_IP:30800" \
WORKLOAD="kepler" \
NAMESPACE="kepler-system" \
scripts/scripts/test-mcp.sh
```

## MCP Tools

### 1. `assess_workload_compliance`

Primary compliance check for a single workload.

```json
{
  "workload_name": "ml-training-job",
  "namespace": "ai-team",
  "standard": "KR_CARBON_2050",
  "region": "ap-northeast-2"
}
```

**Returns:**
```json
{
  "status": "NON_COMPLIANT",
  "carbon_status": "NON_COMPLIANT",
  "pue_status": "COMPLIANT",
  "current_carbon_intensity_gCO2eq_kWh": 510,
  "target_carbon_intensity_gCO2eq_kWh": 424,
  "recommendation": "NON-COMPLIANT: Workload exceeds...",
  "optimizations": [...]
}
```

### 2. `compare_optimization_impact`

Compare before/after carbon impact of optimizations.

```json
{
  "workload_name": "ml-training-job",
  "namespace": "ai-team",
  "optimizations": ["temporal_shift", "resource_rightsizing"]
}
```

### 3. `list_workloads_by_compliance`

Inventory all workloads in a namespace.

```json
{
  "namespace": "production",
  "standard": "KR_CARBON_2050",
  "status_filter": "NON_COMPLIANT"
}
```

### 4. `get_regional_comparison`

Compare carbon impact across AWS regions.

```json
{
  "workload_name": "batch-job",
  "current_region": "ap-northeast-2",
  "comparison_regions": ["us-east-1", "eu-north-1"]
}
```

### 5. `calculate_optimal_schedule`

Find optimal time window for workload scheduling.

```json
{
  "workload_name": "ml-training-job",
  "duration_hours": 4,
  "region": "ap-northeast-2"
}
```

### 6. `identify_power_hotspots`

Identify high-power consuming containers/pods and recommend preventive actions.

```json
{
  "namespace": "production",
  "power_threshold_watts": 1.0,
  "include_compliance_check": true
}
```

### 7. `list_top_power_consumers`

List top power-consuming workloads ranked by power usage or efficiency.

```json
{
  "namespace": "default",
  "limit": 10,
  "sort_by": "power"
}
```

### 8. `get_power_consumption_summary`

Get overall power consumption summary for namespace or entire cluster.

```json
{
  "namespace": "production"
}
```

## MCP Resources

### `compliance-standards://korea/{standard_code}`

Get Korean compliance standard details.

```
compliance-standards://korea/KR_CARBON_2050
compliance-standards://korea/KR_PUE_GREEN_DC
```

### `carbon-intensity://{region}`

Get regional carbon intensity data.

```
carbon-intensity://ap-northeast-2
carbon-intensity://us-east-1
```

### `workload-metrics://{namespace}/{pod_name}`

Get Kepler metrics for a specific workload.

```
workload-metrics://default/my-app
workload-metrics://kepler-system/kepler
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KEPLER_ENDPOINT` | `https://localhost:30443/metrics` | Kepler metrics endpoint |
| `KOREA_CARBON_INTENSITY` | `424` | Korea grid carbon intensity (gCO2eq/kWh) |
| `KOREA_PUE_TARGET` | `1.4` | Korea PUE target for Green Data Center |

### ConfigMap Data

The `korea-compliance-data` ConfigMap contains:

- **carbon-intensity.json** - Hourly carbon intensity profile for Korea
- **regulations.json** - Korean regulatory standards
- **regions.json** - Regional carbon intensity data

## Local Development

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export KEPLER_ENDPOINT="https://YOUR_IP:30443/metrics"
export KOREA_CARBON_INTENSITY="424"
export KOREA_PUE_TARGET="1.4"

# Run MCP server
python -m src.mcp_server
```

### Run Tests

```bash
pytest tests/
```

## Claude Desktop Integration

### Remote SSE Connection (Recommended for Kubernetes Deployment)

When the MCP server is deployed on Kubernetes, use the SSE bridge to connect Claude Desktop to the remote server.

**Windows Configuration** (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kepler-carbon-mcp": {
      "command": "node",
      "args": [
        "C:\\Users\\YourUsername\\mcp-sse-bridge.js",
        "http://YOUR_SERVER_IP:30800/sse"
      ]
    }
  }
}
```

**macOS/Linux Configuration** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kepler-carbon-mcp": {
      "command": "node",
      "args": [
        "/path/to/mcp-sse-bridge.js",
        "http://YOUR_SERVER_IP:30800/sse"
      ]
    }
  }
}
```

**Bridge Script Setup:**

1. Copy `mcp-sse-bridge.js` from this repository
2. Place it in your home directory or any accessible location
3. Update the path in the config above
4. Ensure Node.js is installed (`node --version` should show v18+)

**Important**: The bridge script includes critical URL encoding fixes for session endpoints. Use the version from this repository, not a generic SSE client.

### Local Development (stdio)

For local development, run the MCP server directly:

```json
{
  "mcpServers": {
    "carbon-kepler": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "env": {
        "KEPLER_ENDPOINT": "http://YOUR_IP:28282/metrics",
        "KOREA_CARBON_INTENSITY": "424",
        "KOREA_PUE_TARGET": "1.4"
      }
    }
  }
}
```

### Example Queries

Once connected, ask Claude Desktop:

```
1. "List all Kubernetes workloads and check their compliance with Korean environmental regulations"

2. "Which pods in my cluster are consuming the most power?"

3. "Check if the ml-training-job in the ai-team namespace complies with Korean carbon neutrality standards"

4. "Show me the top 5 power-consuming workloads and suggest optimizations"

5. "Compare the carbon impact of running my batch-job in Seoul vs Tokyo"
```

### Troubleshooting Connection

**Test the bridge manually:**

```bash
# Windows PowerShell
node C:\Users\YourUsername\mcp-sse-bridge.js http://YOUR_SERVER_IP:30800/sse

# macOS/Linux
node /path/to/mcp-sse-bridge.js http://YOUR_SERVER_IP:30800/sse
```

**Expected output:**
```
[MCP Bridge] Starting bridge to http://YOUR_SERVER_IP:30800/sse
[MCP Bridge] Connected to SSE server
[MCP Bridge] Session endpoint: /messages/?session_id=...
[MCP Bridge] POST response (202): Accepted
```

**If you see errors**, check:

- Server is accessible: `curl http://YOUR_SERVER_IP:30800/sse`
- Bridge script is the correct version (should have URL encoding fix)
- Node.js version is 18+ (`node --version`)

For detailed setup instructions, see [CLAUDE_DESKTOP_WINDOWS_SETUP.md](../CLAUDE_DESKTOP_WINDOWS_SETUP.md)

## Project Structure

```
carbon-kepler-mcp/
├── src/
│   ├── mcp_server.py              # Main MCP server (300 lines)
│   ├── kepler_client.py           # Kepler integration (150 lines)
│   ├── prometheus_parser.py       # Metrics parsing (100 lines)
│   ├── korea_compliance.py        # Compliance logic (200 lines)
│   ├── compliance_standards.py    # Standards definitions (150 lines)
│   ├── recommendation_engine.py   # Recommendations (250 lines)
│   └── carbon_calculator.py       # Calculations (80 lines)
├── config/
│   ├── carbon-intensity.json      # Korea hourly profile
│   ├── regulations.json           # Korean regulations
│   └── regions.json               # Regional data
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── rbac.yaml
│   └── kustomization.yaml
├── scripts/
│   ├── build.sh                   # Docker build
│   ├── deploy.sh                  # K8s deployment
│   ├── test-local.sh              # Local testing
│   └── test-mcp.sh                # MCP tool testing
├── Dockerfile
├── requirements.txt
└── README.md
```

## Korean Regulatory Standards

### 탄소중립 녹색성장 기본법 (Carbon Neutrality Act)

**Target:** Carbon neutrality by 2050
**Interim:** 35% reduction by 2030 (vs 2018 baseline)
**Grid Intensity:** 424 gCO2eq/kWh
**Reference:** [법령정보 LSW](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613)

### 에너지이용 합리화법 (Energy Use Rationalization Act)

**Target PUE:** ≤ 1.4
**Certification:** Green Data Center
**Ministry:** MOTIE (Ministry of Trade, Industry and Energy)
**Reference:** [법령정보](https://www.law.go.kr/법령/에너지이용합리화법)

## Troubleshooting

### MCP server can't connect to Kepler

Check that Kepler HTTPS endpoint is accessible:

```bash
curl -k https://YOUR_IP:30443/metrics | grep kepler_pod_cpu_watts
```

### Deployment fails

Check pod logs:

```bash
kubectl logs -n carbon-mcp -l app=carbon-mcp-server
```

Check RBAC permissions:

```bash
kubectl auth can-i get pods --as=system:serviceaccount:carbon-mcp:carbon-mcp-sa
```

### No metrics for workload

Verify workload exists and has metrics:

```bash
kubectl get pods -n YOUR_NAMESPACE
curl -k https://YOUR_IP:30443/metrics | grep "pod=\"YOUR_POD\""
```

## Future Enhancements

- [ ] Carbon Aware SDK integration for real-time grid data
- [ ] Automatic workload scheduling based on carbon intensity
- [ ] Multi-cloud support (GCP, Azure)
- [ ] Cost optimization integration
- [ ] Grafana dashboard for compliance visualization

## License

Apache 2.0

## Author

Marco Gonzalez
Open Source Summit Korea 2025

## References

- [Kepler Project](https://sustainable-computing.io/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Korean Carbon Neutrality Act](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613)
- [Energy Use Rationalization Act](https://www.law.go.kr/법령/에너지이용합리화법)
