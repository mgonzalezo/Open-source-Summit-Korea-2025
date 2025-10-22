# Kepler v0.11.2 with RAPL Architecture - Open Source Summit Korea 2025

**Date**: 2025-10-22
**Version**: 2.0 - RAPL-based Power Measurement
**Instance**: AWS c5.metal bare-metal in ap-northeast-1 (Tokyo)

## Complete System Architecture with RAPL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Windows Claude Desktop                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Natural Language Interface                                           │  │
│  │  "Check if my workload complies with Korean standards"                │  │
│  └────────────────────────────┬──────────────────────────────────────────┘  │
│                               │ stdio (JSON-RPC over stdin/stdout)          │
│                               ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  mcp-sse-bridge-windows.js (Node.js Protocol Bridge)                 │  │
│  │  • stdio ↔ HTTP/SSE translation                                       │  │
│  │  • Session management                                                 │  │
│  └────────────────────────────┬──────────────────────────────────────────┘  │
└─────────────────────────────────┼────────────────────────────────────────────┘
                                  │ Internet: HTTP/SSE
                                  │ Port: 30800
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          AWS EC2 c5.metal - Bare-Metal Instance (ap-northeast-1)            │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                 K3s Kubernetes Cluster                                │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Namespace: carbon-mcp                                          │  │  │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  carbon-mcp-server Deployment                            │  │  │  │
│  │  │  │  • FastMCP 2.12.5 (SSE Transport)                         │  │  │  │
│  │  │  │  • 8 MCP Tools for Korean compliance                      │  │  │  │
│  │  │  │  • Kepler Client (fetches RAPL-based metrics)             │  │  │  │
│  │  │  │  • Carbon/PUE compliance calculations                     │  │  │  │
│  │  │  └───────────────────────────────────────────────────────────┘  │  │  │
│  │  │  Service: NodePort 30800 (SSE endpoint)                         │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                               │                                        │  │
│  │                               │ HTTP GET /metrics                      │  │
│  │                               ▼                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Namespace: kepler-system                                       │  │  │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  Kepler v0.11.2 DaemonSet                                │  │  │  │
│  │  │  │  ┌─────────────────────────────────────────────────────┐  │  │  │  │
│  │  │  │  │  Metrics Collection (procfs/sysfs)                 │  │  │  │  │
│  │  │  │  │  - Reads /proc/<pid>/stat for CPU time             │  │  │  │  │
│  │  │  │  │  - Reads /proc/meminfo for memory stats            │  │  │  │  │
│  │  │  │  │  - Process-level resource tracking                 │  │  │  │  │
│  │  │  │  └─────────────────────────────────────────────────────┘  │  │  │  │
│  │  │  │  ┌─────────────────────────────────────────────────────┐  │  │  │  │
│  │  │  │  │  Intel RAPL Power Measurement                     │  │  │  │  │
│  │  │  │  │  ┌───────────────────────────────────────────────┐  │  │  │  │  │
│  │  │  │  │  │  RAPL Zone: package-0 (CPU socket 0)        │  │  │  │  │  │
│  │  │  │  │  │  Energy Counter: 1234567.89 joules          │  │  │  │  │  │
│  │  │  │  │  └───────────────────────────────────────────────┘  │  │  │  │  │
│  │  │  │  │  ┌───────────────────────────────────────────────┐  │  │  │  │  │
│  │  │  │  │  │  RAPL Zone: package-1 (CPU socket 1)        │  │  │  │  │  │
│  │  │  │  │  │  Energy Counter: 1234500.12 joules          │  │  │  │  │  │
│  │  │  │  │  └───────────────────────────────────────────────┘  │  │  │  │  │
│  │  │  │  │  ┌───────────────────────────────────────────────┐  │  │  │  │  │
│  │  │  │  │  │  RAPL Zone: dram-0 (Memory socket 0)        │  │  │  │  │  │
│  │  │  │  │  │  Energy Counter: 567890.45 joules           │  │  │  │  │  │
│  │  │  │  │  └───────────────────────────────────────────────┘  │  │  │  │  │
│  │  │  │  │  ┌───────────────────────────────────────────────┐  │  │  │  │  │
│  │  │  │  │  │  RAPL Zone: dram-1 (Memory socket 1)        │  │  │  │  │  │
│  │  │  │  │  │  Energy Counter: 567850.23 joules           │  │  │  │  │  │
│  │  │  │  │  └───────────────────────────────────────────────┘  │  │  │  │  │
│  │  │  │  │                                                     │  │  │  │  │
│  │  │  │  │  Power Calculation:                                 │  │  │  │  │
│  │  │  │  │  Watts = ΔJoules / ΔTime (5 second interval)        │  │  │  │  │
│  │  │  │  └─────────────────────────────────────────────────────┘  │  │  │  │
│  │  │  │  ┌─────────────────────────────────────────────────────┐  │  │  │  │
│  │  │  │  │  Prometheus Metrics Publisher                      │  │  │  │  │
│  │  │  │  │  • kepler_node_package_energy_joule{zone=...}     │  │  │  │  │
│  │  │  │  │  • kepler_node_dram_energy_joule{zone=...}        │  │  │  │  │
│  │  │  │  │  • kepler_container_joules_total{pod=...}         │  │  │  │  │
│  │  │  │  │  • kepler_container_cpu_joules_total{pod=...}     │  │  │  │  │
│  │  │  │  │  • kepler_container_dram_joules_total{pod=...}    │  │  │  │  │
│  │  │  │  └─────────────────────────────────────────────────────┘  │  │  │  │
│  │  │  └───────────────────────────────────────────────────────────┘  │  │  │
│  │  │  Services:                                                      │  │  │
│  │  │  • kepler (ClusterIP): http://kepler:28282/metrics             │  │  │
│  │  │  • kepler-http (NodePort): http://<IP>:30080/metrics           │  │  │
│  │  │  • kepler-https (NodePort): https://<IP>:30443/metrics         │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Namespace: workload-test (Test Workloads)                      │  │  │
│  │  │  • nginx-light: Low-power web server (COMPLIANT)                │  │  │
│  │  │  • redis-cache: Medium-power cache (COMPLIANT)                  │  │  │
│  │  │  • stress-cpu: High-power compute (2 replicas for testing)      │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Host OS: Ubuntu 24.04 (bare-metal, NOT virtualized!)                │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Intel RAPL Kernel Modules (loaded at boot)                    │  │  │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  msr                                                      │  │  │  │
│  │  │  │  Model-Specific Register driver                          │  │  │  │
│  │  │  │  Provides /dev/cpu/*/msr interface                       │  │  │  │
│  │  │  └───────────────────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  intel_rapl_common                                        │  │  │  │
│  │  │  │  Common RAPL infrastructure                               │  │  │  │
│  │  │  └───────────────────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  intel_rapl_msr (CRITICAL!)                              │  │  │  │
│  │  │  │  RAPL MSR interface - enables RAPL energy counters        │  │  │  │
│  │  │  │  Creates /sys/class/powercap/intel-rapl:* files           │  │  │  │
│  │  │  └───────────────────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Sysfs RAPL Interface (accessible to Kepler pod)               │  │  │
│  │  │  /sys/class/powercap/                                           │  │  │
│  │  │  ├── intel-rapl:0/ (package-0)                                  │  │  │
│  │  │  │   └── energy_uj (microjoules counter)                        │  │  │
│  │  │  ├── intel-rapl:1/ (package-1)                                  │  │  │
│  │  │  │   └── energy_uj                                              │  │  │
│  │  │  ├── intel-rapl:0:0/ (dram-0)                                   │  │  │
│  │  │  │   └── energy_uj                                              │  │  │
│  │  │  └── intel-rapl:1:0/ (dram-1)                                   │  │  │
│  │  │      └── energy_uj                                              │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Hardware: Intel Xeon Platinum 8275CL (Cascade Lake)                       │
│  • 2 CPU sockets (48 cores each = 96 vCPUs)                                │
│  • 192 GB RAM (96 GB per socket)                                           │
│  • RAPL support: Available on bare-metal                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Power Measurement Flow with RAPL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 1: Hardware Energy Measurement (Intel RAPL)                           │
│                                                                             │
│  Every 5 seconds, Kepler reads RAPL energy counters:                       │
│                                                                             │
│  T0 (timestamp 0):                                                          │
│    package-0: 1234567.89 J                                                 │
│    package-1: 1234500.12 J                                                 │
│    dram-0:     567890.45 J                                                 │
│    dram-1:     567850.23 J                                                 │
│                                                                             │
│  T1 (timestamp 5s):                                                         │
│    package-0: 1234793.89 J   ← Δ = 226.00 J                                │
│    package-1: 1234726.12 J   ← Δ = 226.00 J                                │
│    dram-0:     568002.45 J   ← Δ = 112.00 J                                │
│    dram-1:     567962.23 J   ← Δ = 112.00 J                                │
│                                                                             │
│  Total Energy Consumed: 676.00 J in 5 seconds                              │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 2: Power Calculation                                                  │
│                                                                             │
│  Power (Watts) = Energy (Joules) / Time (Seconds)                          │
│                                                                             │
│  Total Power = 676.00 J / 5 s = 135.2 W                                    │
│                                                                             │
│  Breakdown:                                                                 │
│    CPU Power:    (226.00 + 226.00) / 5 = 90.4 W                            │
│    Memory Power: (112.00 + 112.00) / 5 = 44.8 W                            │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 3: Per-Pod Energy Attribution (procfs + RAPL)                         │
│                                                                             │
│  Kepler analyzes /proc/<pid>/stat to track CPU time per container/pod:    │
│                                                                             │
│  Pod: nginx-light                                                           │
│    CPU cycles: 5% of total                                                 │
│    Attributed CPU energy: 90.4 W × 0.05 = 4.52 W                           │
│    Attributed DRAM energy: 44.8 W × 0.05 = 2.24 W                          │
│    Total: 6.76 W                                                            │
│                                                                             │
│  Pod: stress-cpu                                                            │
│    CPU cycles: 65% of total                                                │
│    Attributed CPU energy: 90.4 W × 0.65 = 58.76 W                          │
│    Attributed DRAM energy: 44.8 W × 0.65 = 29.12 W                         │
│    Total: 87.88 W                                                           │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 4: Prometheus Metrics Export                                          │
│                                                                             │
│  kepler_container_joules_total{pod="nginx-light"} 33.8                     │
│  kepler_container_joules_total{pod="stress-cpu"} 439.4                     │
│                                                                             │
│  kepler_node_package_energy_joule{zone="package-0"} 1234793.89             │
│  kepler_node_package_energy_joule{zone="package-1"} 1234726.12             │
│  kepler_node_dram_energy_joule{zone="dram-0"} 568002.45                    │
│  kepler_node_dram_energy_joule{zone="dram-1"} 567962.23                    │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 5: MCP Server Carbon Compliance Assessment                            │
│                                                                             │
│  For nginx-light (6.76 W):                                                  │
│    Energy per hour: 6.76 W × 1 h = 6.76 Wh = 0.00676 kWh                  │
│    Carbon emissions: 0.00676 kWh × 424 gCO2/kWh = 2.87 gCO2/h              │
│    Status: COMPLIANT                                                       │
│                                                                             │
│  For stress-cpu (87.88 W):                                                  │
│    Energy per hour: 87.88 W × 1 h = 87.88 Wh = 0.08788 kWh                │
│    Carbon emissions: 0.08788 kWh × 424 gCO2/kWh = 37.26 gCO2/h             │
│    Status: NON_COMPLIANT (exceeds threshold)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Korean Compliance Standards

### 탄소중립 녹색성장 기본법 (Carbon Neutrality Act)
- **Target**: 424 gCO2eq/kWh (Korea grid average)
- **Goal**: Carbon neutrality by 2050
- **Assessment**:
  ```
  Carbon Emissions (gCO2/h) = Power (kW) × 424 gCO2eq/kWh
  Status = (Emissions ≤ Threshold) ? COMPLIANT : NON_COMPLIANT
  ```

### 에너지이용 합리화법 (Energy Use Rationalization Act)
- **Target**: PUE ≤ 1.4 for Green Data Center certification
- **Calculation**:
  ```
  PUE = Total Facility Power / IT Equipment Power
  Status = (PUE ≤ 1.4) ? COMPLIANT : NON_COMPLIANT
  ```

## RAPL Module Configuration

### CloudFormation Template Setup

```yaml
# Enable RAPL for direct hardware power measurements
echo "Enabling RAPL (Running Average Power Limit)..."
apt-get install -y linux-modules-$(uname -r) linux-modules-extra-$(uname -r)

# Load RAPL modules (ORDER MATTERS!)
modprobe msr
modprobe intel_rapl_common
modprobe intel_rapl_msr  # THE CRITICAL MODULE!

# Make modules load on boot
echo "msr" >> /etc/modules
echo "intel_rapl_common" >> /etc/modules
echo "intel_rapl_msr" >> /etc/modules

# Verify RAPL is working
if [ -d "/sys/class/powercap/intel-rapl:0" ]; then
  echo "RAPL enabled successfully"
fi
```

### Kepler Helm Values (RAPL Configuration)

```yaml
config:
  rapl:
    zones: []  # Empty = auto-detect all RAPL zones
  dev:
    fake-cpu-meter:
      enabled: false  # Disabled - using RAPL!
  model:
    enabled: false  # Disabled - using RAPL!
```

### Verification Commands

```bash
# Verify RAPL modules are loaded
lsmod | grep rapl

# Expected output:
# intel_rapl_msr         16384  0
# intel_rapl_common      28672  1 intel_rapl_msr
# msr                    16384  1

# Check RAPL zones
ls -la /sys/class/powercap/

# Expected output:
# intel-rapl:0      (package-0)
# intel-rapl:1      (package-1)
# intel-rapl:0:0    (dram-0)
# intel-rapl:1:0    (dram-1)

# Read energy counter (microjoules)
cat /sys/class/powercap/intel-rapl:0/energy_uj
# Example: 1234567890123

# Test Kepler metrics with RAPL
curl -k https://<IP>:30443/metrics | grep kepler_node_package_energy_joule

# Expected output:
# kepler_node_package_energy_joule{instance="node1",zone="package-0"} 1234567.89
# kepler_node_package_energy_joule{instance="node1",zone="package-1"} 1234500.12
```

## Deployment Architecture

```
CloudFormation Stack: kepler-k3s-rapl
├── EC2 Instance: c5.metal
│   ├── OS: Ubuntu 24.04 (bare-metal)
│   ├── RAPL Modules: msr, intel_rapl_common, intel_rapl_msr
│   └── K3s: Lightweight Kubernetes
│
├── Namespace: kepler-system
│   ├── Kepler v0.11.2 DaemonSet (with RAPL)
│   ├── HTTPS Proxy (Nginx + cert-manager)
│   └── Services: ClusterIP (28282), NodePort (30080, 30443)
│
├── Namespace: carbon-mcp
│   ├── MCP Server Deployment (FastMCP 2.12.5)
│   ├── ConfigMap: korea-compliance-data
│   └── Service: NodePort (30800 SSE)
│
└── Namespace: workload-test
    ├── nginx-light (COMPLIANT)
    ├── redis-cache (COMPLIANT)
    └── stress-cpu × 2 (HIGH POWER)
```

## MCP Tools for Korean Compliance

1. **assess_workload_compliance** - Single workload compliance check
2. **list_workloads_by_compliance** - Namespace-wide compliance inventory
3. **compare_optimization_impact** - Before/after carbon analysis
4. **get_regional_comparison** - Multi-region carbon comparison
5. **calculate_optimal_schedule** - Time-based carbon-aware scheduling
6. **get_power_hotspots** - Identify high-power consumers
7. **analyze_workload_power_trend** - Power consumption trends
8. **get_cluster_carbon_summary** - Cluster-wide carbon overview

## Success Metrics

**RAPL Enabled**: 4 zones detected (package-0, package-1, dram-0, dram-1)
**Real Power Measurements**: Direct hardware counters (not estimated)
**Per-Pod Attribution**: procfs/sysfs-based energy distribution to containers
**Korean Compliance**: 탄소중립법 (424 gCO2/kWh) + 에너지합리화법 (PUE ≤ 1.4)
**MCP Integration**: 8 tools for carbon-aware workload management
**Claude Desktop**: Natural language compliance queries via SSE bridge

---

**Last Updated**: 2025-10-22
**Status**: Production Ready with RAPL
**Region**: ap-northeast-1 (Tokyo, Japan)
**Demo**: Open Source Summit Korea 2025
