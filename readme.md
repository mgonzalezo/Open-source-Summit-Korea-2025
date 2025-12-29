# kepler energy monitoring & carbon compliance for kubernetes

**open source summit korea 2025 - demo repository**

this repository demonstrates real-time energy monitoring and carbon compliance assessment for kubernetes workloads using kepler (kubernetes efficient power level exporter) with intel rapl, amazon bedrock ai, and korean regulatory standards.

## overview

this project provides a complete enterprise-grade solution for:

1. **aws deployment** - automated infrastructure for running kepler on aws bare-metal instances with intel rapl
2. **amazon bedrock integration** - ai-powered compliance analysis using claude 3.5 sonnet
3. **korean government apis** - real-time carbon intensity data from official sources
4. **serverless mcp tools** - aws lambda functions for compliance assessment
5. **claude desktop integration** - natural language interface for compliance queries

together, they enable real-time power measurement, ai-powered carbon compliance assessment, and automated sustainability analysis for kubernetes workloads.

## architecture evolution

### current architecture (20% aws - fastmcp based)

```
claude desktop -> sse -> aws c5.metal -> k3s -> fastmcp server (8 tools) -> kepler v0.11.2 (rapl)
```

### target architecture (70%+ aws - bedrock powered)

see [aws-bedrock-migration-plan.md](aws-bedrock-migration-plan.md) for complete architecture details.

```
claude desktop
    |
    | https/iam auth
    v
amazon api gateway (rest api)
    |
    v
aws lambda functions (8 serverless mcp tools)
    |
    |-> amazon bedrock (claude 3.5 sonnet ai analysis)
    |-> korean gov apis (kpx, k-eco, kea, kma)
    |-> amazon dynamodb (compliance history)
    |-> amazon s3 (reports)
    |-> aws step functions (workflows)
    |
    v
kepler metrics (via cloudwatch or http)
    |
    v
aws c5.metal (intel rapl hardware measurement)
  - intel xeon platinum 8275cl (96 vcpus)
  - 192 gb ram
  - 4 rapl zones (2 cpu + 2 dram)
  - k3s + kepler v0.11.2
```

key aws services:

- amazon bedrock (ai-powered compliance analysis)
- aws lambda (serverless tools)
- amazon dynamodb (data storage)
- amazon api gateway (api management)
- aws step functions (workflow orchestration)
- amazon cloudwatch (observability)
- aws secrets manager (credentials)
- aws x-ray (tracing)

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

### 3. Test Compliance Queries

Access the MCP server via HTTP:

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
    ├── mcp-sse-bridge.js              # Universal MCP bridge (Mac/Linux/Windows)
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
ssh -i <your-key>.pem ubuntu@<PublicIP>

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

## aws bedrock integration (enterprise upgrade)

### migration to aws-powered architecture

for enterprise deployments requiring enhanced ai capabilities and integration with korean government apis, see the complete migration plan:

**[aws-bedrock-migration-plan.md](aws-bedrock-migration-plan.md)**

this upgrade transforms the solution from 20% to 70%+ aws service integration:

migration highlights:

- replace fastmcp with aws lambda serverless functions
- integrate amazon bedrock (claude 3.5 sonnet) for ai-powered compliance analysis
- connect to korean government apis (kpx, k-eco, kea, kma) for real-time carbon data
- implement amazon dynamodb for compliance history and analytics
- add aws step functions for automated workflows
- deploy amazon cloudwatch for comprehensive observability
- secure credentials with aws secrets manager

benefits:

- ai-powered compliance recommendations using claude 3.5 sonnet
- real-time carbon intensity from official korean government sources
- serverless architecture with auto-scaling
- comprehensive audit trails and compliance reporting
- reduced operational overhead
- enterprise-grade security and compliance

implementation timeline: 4 weeks (see migration plan for detailed phases)

## aws c5.metal bare-metal server specifications

### why bare-metal?

this solution requires aws c5.metal bare-metal instances because:

1. native rapl access - virtualized instances do not expose intel rapl hardware counters
2. accurate power measurement - korean compliance regulations require hardware-level precision
3. no hypervisor overhead - direct kernel access to msr (model-specific registers)
4. deterministic performance - dedicated resources without noisy neighbor issues

### hardware specifications

instance type: c5.metal
region: ap-northeast-1 (tokyo)
pricing: ~$4.08/hour on-demand (~$2,938/month)

processor:

- model: intel xeon platinum 8275cl (cascade lake)
- architecture: x86_64
- base frequency: 3.0 ghz
- turbo frequency: 3.6 ghz
- sockets: 2
- cores per socket: 48
- total vcpus: 96
- hyper-threading: enabled (192 threads)
- cache: l1 3mb, l2 48mb, l3 35.75mb per socket
- instruction sets: avx-512, aes-ni

memory:

- total ram: 192 gb (ddr4)
- configuration: 96 gb per socket
- memory channels: 6 per socket
- speed: 2933 mt/s
- ecc: enabled

storage:

- ebs-optimized: yes
- max ebs bandwidth: 19 gbps
- max iops: 80,000
- storage type: gp3 ssd recommended

network:

- network performance: 25 gbps
- enhanced networking: enabled (ena)
- network interface cards: 4 x 25 gbps
- ipv6 support: yes
- placement groups: supported

power measurement (intel rapl):

- rapl support: native hardware support
- rapl zones: 4 active zones
  - package-0: cpu socket 0 (0-200w range)
  - package-1: cpu socket 1 (0-200w range)
  - dram-0: memory socket 0
  - dram-1: memory socket 1
- measurement precision: microjoule (μj)
- update frequency: ~1ms hardware, 5s kepler aggregation
- interface: /sys/class/powercap/intel-rapl:*/energy_uj

cost management:

- running: $4.08/hour ($2,938/month)
- stopped: only ebs storage (~$20/month)
- savings when stopped: ~$2,918/month
- recommendation: stop instance when not in active use

deployment:

- cloudformation stack deployment: ~15 minutes
- includes: k3s, kepler v0.11.2, rapl modules, test workloads
- fully automated via userdata script
- see [aws-deployment/](aws-deployment/) for details

### rapl architecture on c5.metal

```text
hardware layer:
  cpu package 0 (48 cores)
    msr 0x611 (pkg_energy_status)
    msr 0x619 (dram_energy_status)
  cpu package 1 (48 cores)
    msr 0x611 (pkg_energy_status)
    msr 0x619 (dram_energy_status)

kernel modules:
  msr (model-specific register access)
  intel_rapl_common (rapl framework)
  intel_rapl_msr (msr-based rapl interface)

sysfs interface:
  /sys/class/powercap/intel-rapl:0/ (package-0)
    energy_uj (cumulative microjoules)
    max_energy_range_uj (rollover threshold)
    name
  /sys/class/powercap/intel-rapl:1/ (package-1)
  /sys/class/powercap/intel-rapl:0:0/ (dram-0)
  /sys/class/powercap/intel-rapl:1:0/ (dram-1)

kepler access:
  reads energy_uj every 5 seconds
  calculates: power (w) = delta_energy (j) / delta_time (s)
```

## korean government api integration

### target apis for real-time compliance data

1. 전력거래소 (kpx - korea power exchange)
   - api: <https://openapi.kpx.or.kr/>
   - provides: real-time carbon intensity, grid composition, regional electricity pricing
   - update frequency: hourly
   - authentication: api key required

2. 한국환경공단 (k-eco - korea environment corporation)
   - api: <https://www.gir.go.kr/>
   - provides: carbon emission factors, greenhouse gas inventory data
   - update frequency: daily
   - authentication: registration required

3. 한국에너지공단 (kea - korea energy agency)
   - provides: energy efficiency standards, data center pue benchmarks
   - authentication: registration required

4. 기상청 (kma - korea meteorological administration)
   - api: <https://www.weather.go.kr/w/index.do>
   - provides: weather-based renewable energy forecasting, regional climate data
   - update frequency: 3-hour intervals
   - authentication: api key required

### integration approach

the aws bedrock migration includes aws lambda functions to:

- query government apis for real-time carbon intensity
- cache responses in amazon dynamodb (5-minute ttl for rate limiting)
- store api credentials in aws secrets manager
- validate data quality and fallback to static values if apis unavailable
- log all api interactions for compliance auditing

see [aws-bedrock-migration-plan.md](aws-bedrock-migration-plan.md) for implementation details.

## resources

### kepler project

- [official website](https://sustainable-computing.io/)
- [github repository](https://github.com/sustainable-computing-io/kepler)
- [cncf project page](https://landscape.cncf.io/project=kepler)

### mcp protocol

- [model context protocol](https://modelcontextprotocol.io/)
- [mcp specification](https://spec.modelcontextprotocol.io/)
- [claude desktop integration](https://docs.anthropic.com/claude/docs/model-context-protocol)

### amazon bedrock

- [amazon bedrock documentation](https://docs.aws.amazon.com/bedrock/)
- [anthropic claude models](https://www.anthropic.com/claude)
- [bedrock pricing](https://aws.amazon.com/bedrock/pricing/)

### korean regulations

- [carbon neutrality act (탄소중립법)](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613)
- [energy rationalization act (에너지합리화법)](https://www.law.go.kr/법령/에너지이용합리화법)
- [korean government open data portal](https://www.data.go.kr/)

### rapl documentation

- [intel rapl overview](https://www.kernel.org/doc/html/latest/power/powercap/powercap.html)
- [linux powercap documentation](https://docs.kernel.org/power/powercap/powercap.html)

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
