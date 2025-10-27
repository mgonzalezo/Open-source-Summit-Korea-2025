# Kepler Energy Monitoring & Carbon Compliance for Kubernetes

**Open Source Summit Korea 2025 - Demo Repository**

This repository demonstrates real-time energy monitoring and carbon compliance assessment for Kubernetes workloads using Kepler (Kubernetes Efficient Power Level Exporter) with Intel RAPL and Korean regulatory standards.

## Overview

This project provides a complete solution for:

1. **AWS Deployment** - Automated infrastructure for running Kepler on AWS bare-metal instances with Intel RAPL
2. **Carbon-Kepler MCP** - Model Context Protocol server for Korean carbon compliance assessments
3. **Claude Desktop Integration** - Natural language interface for compliance queries

Together, they enable real-time power measurement, carbon compliance assessment, and AI-assisted sustainability analysis for Kubernetes workloads.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Open Source Summit Korea 2025 Demo                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────┐     ┌──────────────────────────────────┐   │
│  │  AWS c5.metal Bare-Metal   │     │  Carbon-Kepler MCP Server        │   │
│  │                            │     │                                  │   │
│  │  K3s Kubernetes            │     │  FastMCP 2.12.5 (SSE)            │   │
│  │  Kepler v0.11.2            │────→│  8 Compliance Tools              │   │
│  │  Intel RAPL (4 zones)      │     │  Korean Standards                │   │
│  │  Real Power Measurement    │     │  Recommendations Engine          │   │
│  │                            │     │                                  │   │
│  │  Direct hardware energy    │     │  탄소중립법: 424 gCO2eq/kWh      │   │
│  │  counters in joules        │     │  에너지합리화법: PUE ≤ 1.4       │   │
│  └────────────────────────────┘     └──────────────────────────────────┘   │
│          Infrastructure                      Analysis & Compliance          │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Claude Desktop (Windows) + SSE Bridge                             │    │
│  │  Natural language queries: "Check compliance with Korean standards"│    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                        User Interface                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Features

### Real Hardware Power Measurement

- **Intel RAPL**: Direct hardware energy counters via `/sys/class/powercap/`
- **4 RAPL Zones**: 2 CPU packages + 2 DRAM zones
- **Accuracy**: Hardware-level precision
- **Metrics**: Real joules from hardware to watts conversion
- **Collection Method**: `/proc` and `/sys` filesystem analysis (Kepler v0.10.x+)

### Korean Regulatory Compliance

- **탄소중립 녹색성장 기본법** (Carbon Neutrality Act): 424 gCO2eq/kWh target
- **에너지이용 합리화법** (Energy Use Rationalization Act): PUE ≤ 1.4
- Automated compliance assessment with actionable recommendations

### AI-Assisted Analysis

- **Claude Desktop Integration**: Natural language compliance queries
- **MCP Protocol**: Standardized AI tool interface
- **8 Compliance Tools**: From single workload checks to cluster-wide analysis

### Fully Automated Deployment

- One-command CloudFormation deployment (~15 minutes)
- Auto-configured RAPL kernel modules
- Pre-deployed test workloads for demos

## Quick Start

### Prerequisites

- AWS Account with budget for c5.metal (~$4.50/hour in ap-northeast-1)
- AWS CLI configured with profile
- SSH key pair in AWS (for instance access)

### 1. Deploy the Stack

```bash
cd aws-deployment
./scripts/create-stack.sh
```

This will automatically deploy:

- AWS c5.metal bare-metal instance (ap-northeast-1)
- Intel RAPL kernel modules (msr, intel_rapl_common, intel_rapl_msr) - with AWS workaround
- K3s Kubernetes cluster
- Kepler v0.11.2 with RAPL (4 zones)
- Carbon-Kepler MCP Server (8 tools)
- Test workloads (nginx-light, redis-cache, stress-cpu)

**Deployment time**: ~15 minutes

### 2. Verify RAPL is Working

```bash
# SSH to the instance (get IP from CloudFormation outputs)
ssh -i <your-key>.pem ubuntu@<PublicIP>

# Check RAPL modules are loaded
lsmod | grep rapl
# Expected: intel_rapl_msr, intel_rapl_common, msr

# Check RAPL zones
ls -la /sys/class/powercap/
# Expected: intel-rapl:0, intel-rapl:1, intel-rapl:0:0, intel-rapl:1:0

# Test Kepler RAPL metrics
curl -k https://<PublicIP>:30443/metrics | grep kepler_node_package_energy_joule
# Expected: Real joule measurements from 4 RAPL zones
```

### 3. Configure Claude Desktop (Windows)

```bash
# 1. Copy bridge script to Windows
scp carbon-kepler-mcp/mcp-sse-bridge-windows.js user@windows-machine:C:\Users\<username>\

# 2. Update claude_desktop_config.json on Windows
# File location: %APPDATA%\Claude\claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "carbon-kepler": {
      "command": "node",
      "args": [
        "C:\\Users\\<username>\\mcp-sse-bridge-windows.js",
        "http://<PublicIP>:30800/sse"
      ]
    }
  }
}
```

### 4. Test Compliance Queries

Open Claude Desktop and try:

```
"What is the total power consumption of my Kubernetes cluster?"

"Check if the nginx-light pod complies with Korean environmental standards"

"Analyze all workloads in the workload-test namespace for Korean compliance"

"Which workloads are consuming the most power?"
```

## Documentation

### Essential Architecture Documentation

1. **[rapl-architecture-diagram.md](rapl-architecture-diagram.md)** - Complete RAPL-based architecture
   - System architecture with all RAPL zones
   - Power measurement flow (joules → watts → carbon)
   - Configuration and verification commands

2. **[carbon-kepler-mcp/architecture-roles.md](carbon-kepler-mcp/architecture-roles.md)** - Layer roles and responsibilities
   - Layer 1: Kepler Monitoring (eBPF + RAPL)
   - Layer 2: Carbon-Aware MCP Server (Compliance Logic)
   - Layer 3: Clients (User Interface)

3. **[aws-deployment/carbon-mcp-architecture.md](aws-deployment/carbon-mcp-architecture.md)** - Detailed component architecture
   - MCP tools architecture
   - Korean compliance standards
   - Data flow and integration

### Component Documentation

4. **[aws-deployment/readme.md](aws-deployment/readme.md)** - AWS deployment guide
   - CloudFormation stack details
   - RAPL module configuration
   - Troubleshooting and verification

5. **[carbon-kepler-mcp/readme.md](carbon-kepler-mcp/readme.md)** - MCP server documentation
   - Tool descriptions
   - Korean standards implementation
   - Development and testing

## Why RAPL on AWS?

- **c5.metal is bare-metal**: Not virtualized, exposes hardware counters
- **Intel processors**: Support RAPL energy measurement
- **Real measurements**: Direct hardware energy consumption
- **Production accuracy**: Suitable for compliance reporting
- **4 RAPL Zones**: Complete visibility into CPU package and DRAM energy consumption

**Important**: AWS bare-metal instances require a workaround to enable RAPL. See [RAPL Workaround Documentation](rapl-architecture-diagram.md#aws-bare-metal-rapl-workaround) for the critical module loading steps adapted from the [Kepler Model Training Playbook](https://github.com/sustainable-computing-io/kepler-model-training-playbook/blob/main/roles/instance_collect_role/files/install_package.sh).

## Power Measurement Flow

```
1. Intel RAPL Hardware Counters (via sysfs)
   ↓
   Kepler reads /sys/class/powercap/intel-rapl:*/energy_uj every 5 seconds
   package-0: 1234567890123 µJ
   package-1: 1234500120456 µJ
   dram-0:     567890450789 µJ
   dram-1:     567850230123 µJ

2. Calculate Power (Watts)
   ↓
   Power = ΔEnergy / ΔTime
   CPU Power:    (226.00 + 226.00) J / 5s = 90.4 W
   Memory Power: (112.00 + 112.00) J / 5s = 44.8 W
   Total: 135.2 W

3. Per-Pod Energy Attribution (procfs analysis)
   ↓
   Kepler analyzes /proc/<pid>/stat for CPU time per container
   nginx-light:  5% of CPU time → 6.76 W
   stress-cpu:  65% of CPU time → 87.88 W

4. Carbon Compliance Assessment
   ↓
   nginx-light: 6.76 W × 424 gCO2/kWh = 2.87 gCO2/h → COMPLIANT
   stress-cpu:  87.88 W × 424 gCO2/kWh = 37.26 gCO2/h → NON_COMPLIANT
```

## MCP Tools (8 Total)

1. **assess_workload_compliance** - Single workload compliance check
2. **list_workloads_by_compliance** - Namespace-wide compliance inventory
3. **compare_optimization_impact** - Before/after carbon impact analysis
4. **get_regional_comparison** - Multi-region carbon comparison
5. **calculate_optimal_schedule** - Time-based carbon-aware scheduling
6. **get_power_hotspots** - Identify high-power consumers
7. **analyze_workload_power_trend** - Power consumption trends
8. **get_cluster_carbon_summary** - Cluster-wide carbon overview

## Test Workloads

Automatically deployed to the `workload-test` namespace:

1. **nginx-light** (1 replica) - Low-power web server
   - CPU: 50m-100m
   - Memory: 64Mi-128Mi
   - Status: COMPLIANT

2. **redis-cache** (1 replica) - Medium-power cache
   - CPU: 100m-200m
   - Memory: 128Mi-256Mi
   - Status: COMPLIANT

3. **stress-cpu** (2 replicas) - High-power compute
   - CPU: 500m-1000m
   - Memory: 128Mi-256Mi
   - Status: NON_COMPLIANT (for testing)

## Korean Regulatory Standards

### 탄소중립 녹색성장 기본법 (Carbon Neutrality Act)

- **Enacted**: September 24, 2021
- **Goal**: Carbon neutrality by 2050
- **Interim Target**: 35% reduction by 2030 (vs 2018 baseline)
- **Current Grid**: 424 gCO2eq/kWh
- **Reference**: [법령정보](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613)

**Compliance Formula**:
```
Carbon Emissions (gCO2/h) = Power (kW) × 424 gCO2eq/kWh
Status = (Emissions ≤ Threshold) ? COMPLIANT : NON_COMPLIANT
```

### 에너지이용 합리화법 (Energy Use Rationalization Act)

- **Authority**: MOTIE (Ministry of Trade, Industry and Energy)
- **Target**: PUE ≤ 1.4 for Green Data Center certification
- **Current Baseline**: PUE 1.8 (typical)
- **Reference**: [법령정보](https://www.law.go.kr/법령/에너지이용합리화법)

**PUE Formula**:
```
PUE = Total Facility Power / IT Equipment Power
Status = (PUE ≤ 1.4) ? COMPLIANT : NON_COMPLIANT
```

## Repository Structure

```
Open-source-Summit-Korea-2025/
├── readme.md                          # This file
├── rapl-architecture-diagram.md       # Complete RAPL architecture
│
├── aws-deployment/                    # AWS Infrastructure
│   ├── readme.md                      # Deployment guide
│   ├── carbon-mcp-architecture.md     # Detailed architecture
│   ├── scripts/
│   │   ├── create-stack.sh            # Deploy stack
│   │   ├── delete-stack.sh            # Cleanup
│   │   ├── start-instance.sh          # Start stopped instance
│   │   └── stop-instance.sh           # Stop instance (save costs)
│   └── templates/
│       └── kepler-k3s-automated-stack.yaml  # CloudFormation template
│
└── carbon-kepler-mcp/                 # MCP Server
    ├── readme.md                      # MCP documentation
    ├── architecture-roles.md          # Layer roles
    ├── mcp-sse-bridge-windows.js      # Windows Claude Desktop bridge
    ├── mcp-sse-bridge.js              # Linux/Mac bridge
    ├── src/                           # Python MCP implementation
    │   ├── mcp_server.py              # FastMCP server
    │   ├── kepler_client.py           # Kepler metrics client
    │   ├── korea_compliance.py        # Compliance logic
    │   └── power_hotspot_tools.py     # Additional analysis tools
    ├── k8s/                           # Kubernetes manifests
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── configmap.yaml
    │   └── test-workloads.yaml        # Demo workloads
    └── scripts/
        ├── build.sh                   # Build Docker image
        └── deploy.sh                  # Deploy to K3s
```

## Cost Management

**AWS Infrastructure Costs (ap-northeast-1)**:

- **c5.metal**: ~$4.50/hour
- **Budget**: $344.70 ≈ 76 hours of runtime
- **Cost-saving**: Stop instance when not in use
  - Stopped: Only EBS storage (~$10/month)
  - Running: Full instance + storage costs

**Stop/Start Commands**:
```bash
# Stop instance to save costs
cd aws-deployment
./scripts/stop-instance.sh

# Start instance when needed
./scripts/start-instance.sh
```

## Demo Flow

### 1. Infrastructure Demo (5 minutes)
```bash
# SSH to instance
ssh -i <key>.pem ubuntu@<PublicIP>

# Show RAPL modules
lsmod | grep rapl

# Show RAPL zones
ls -la /sys/class/powercap/

# Show Kepler pods
kubectl get pods -n kepler-system

# Show test workloads
kubectl get pods -n workload-test

# Show MCP server
kubectl get pods -n carbon-mcp
```

### 2. Metrics Demo (5 minutes)
```bash
# Show real RAPL measurements
curl -k https://<PublicIP>:30443/metrics | grep kepler_node_package_energy_joule

# Show per-container attribution
curl -k https://<PublicIP>:30443/metrics | grep kepler_container_joules_total
```

### 3. Claude Desktop Demo (10 minutes)

**Natural language queries**:
1. "What is the total power consumption of my cluster?"
2. "List all workloads and check compliance with Korean regulations"
3. "Which pods are consuming the most power?"
4. "Check if nginx-light complies with Korean environmental standards"
5. "Analyze all workloads in workload-test namespace for compliance"

### 4. Compliance Report Demo (5 minutes)

Show detailed compliance assessment with:
- Current power consumption
- Carbon emissions calculation
- PUE estimation
- Compliance status (COMPLIANT/NON_COMPLIANT)
- Actionable recommendations

## Resources

### Kepler Project
- [Official Website](https://sustainable-computing.io/)
- [GitHub Repository](https://github.com/sustainable-computing-io/kepler)
- [CNCF Project Page](https://landscape.cncf.io/project=kepler)

### MCP Protocol
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Claude Desktop Integration](https://docs.anthropic.com/claude/docs/model-context-protocol)

### Korean Regulations
- [Carbon Neutrality Act (탄소중립법)](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613)
- [Energy Rationalization Act (에너지합리화법)](https://www.law.go.kr/법령/에너지이용합리화법)

### RAPL Documentation
- [Intel RAPL Overview](https://www.kernel.org/doc/html/latest/power/powercap/powercap.html)
- [Linux Powercap Documentation](https://docs.kernel.org/power/powercap/powercap.html)

## License

Apache License 2.0

## Author

Marco Gonzalez (margonza@redhat.com)

**Event**: Open Source Summit Korea 2025
**Location**: Seoul, South Korea
**Date**: December 2025

---

**Technology Stack**: AWS CloudFormation, K3s, Kepler v0.11.2, Intel RAPL, procfs/sysfs, Prometheus, FastMCP, Python, Korean Regulatory Standards

**Keywords**: Energy Monitoring, Carbon Compliance, Kubernetes, RAPL, Korean Regulations, 탄소중립, Sustainability, Green Computing
