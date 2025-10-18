# Kepler Energy Monitoring & Carbon Compliance for Kubernetes

**Open Source Summit Korea 2025**

This repository demonstrates energy monitoring and carbon compliance assessment for Kubernetes workloads using Kepler (Kubernetes Efficient Power Level Exporter) and Korean regulatory standards.

## Overview

This project combines two main components:

1. **AWS Deployment** - Automated infrastructure for running Kepler on AWS bare-metal instances
2. **Carbon-Kepler MCP** - Model Context Protocol server for Korean carbon compliance assessments

Together, they provide a complete solution for monitoring energy consumption in Kubernetes and assessing compliance with Korean environmental regulations.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  Open Source Summit Korea 2025                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────┐  ┌──────────────────────┐   │
│  │   aws-deployment/            │  │  carbon-kepler-mcp/  │   │
│  │                              │  │                      │   │
│  │  AWS CloudFormation          │  │  MCP Server          │   │
│  │  ├─ c5.metal instance        │  │  ├─ Compliance tools │   │
│  │  ├─ K3s cluster              │  │  ├─ Korean standards │   │
│  │  ├─ Kepler v0.11.2         ──┼──┼─→│  ├─ Carbon Act    │   │
│  │  ├─ Model Server             │  │  │  └─ PUE targets   │   │
│  │  └─ HTTPS metrics endpoint   │  │  └─ Recommendations  │   │
│  │                              │  │                      │   │
│  │  Real-time energy metrics    │  │  Compliance reports  │   │
│  └──────────────────────────────┘  └──────────────────────┘   │
│           Infrastructure                   Analysis            │
└────────────────────────────────────────────────────────────────┘
```

## Project Components

### 1. AWS Deployment (`aws-deployment/`)

Automated CloudFormation-based deployment of Kepler on AWS bare-metal infrastructure.

**Goal:** Provide a production-ready Kepler environment that works around AWS bare-metal limitations (no RAPL access) using ML-based power estimation.

**Architecture:**

- **Infrastructure:** AWS c5.metal bare-metal EC2 instance
- **Kubernetes:** K3s lightweight distribution
- **Monitoring:** Kepler v0.11.2 with eBPF metrics collection
- **Power Estimation:** Kepler Model Server with AWS EC2 models
- **Access:** HTTPS/HTTP metrics endpoints with TLS
- **Automation:** Fully automated deployment (~15 minutes)

**Key Features:**

- Zero-configuration deployment
- Real eBPF metrics for CPU, memory, processes
- ML-based power estimation when hardware RAPL unavailable
- Cost-efficient stop/start capability
- Complete CloudFormation automation

**Quick Start:**

```bash
cd aws-deployment/scripts
./create-stack.sh
```

**Use Cases:**

- Production Kepler deployments on AWS
- Energy monitoring in cloud environments
- Testing power estimation models
- Kubernetes energy observability

See [aws-deployment/readme.md](aws-deployment/readme.md) for complete documentation.

---

### 2. Carbon-Kepler MCP (`carbon-kepler-mcp/`)

Model Context Protocol (MCP) server that integrates Kepler metrics with Korean regulatory compliance standards.

**Goal:** Assess Kubernetes workload compliance with Korean carbon neutrality and energy efficiency regulations through an AI-accessible interface.

**Architecture:**

- **Protocol:** MCP (Model Context Protocol) for Claude AI integration
- **Standards:** Korean Carbon Neutrality Act 2050 & Energy Use Rationalization Act
- **Data Source:** Kepler metrics via Prometheus endpoint
- **Deployment:** Kubernetes-native with ConfigMaps and RBAC
- **Output:** Compliance assessments and actionable recommendations

**Key Features:**

- **5 MCP Tools:**
  - `assess_workload_compliance` - Check single workload compliance
  - `compare_optimization_impact` - Before/after carbon analysis
  - `list_workloads_by_compliance` - Namespace-wide inventory
  - `get_regional_comparison` - Multi-region carbon comparison
  - `calculate_optimal_schedule` - Time-based optimization

- **Korean Regulatory Standards:**
  - Carbon Neutrality Act 2050: 424 gCO2eq/kWh target
  - Energy Use Rationalization Act: PUE ≤ 1.4 for Green Data Centers

- **Actionable Recommendations:**
  - Temporal shifting to low-carbon time windows
  - Resource rightsizing and optimization
  - Regional migration for lower carbon intensity

**Quick Start:**

```bash
cd carbon-kepler-mcp
./scripts/build.sh
./scripts/deploy.sh
```

**Use Cases:**

- Carbon compliance reporting for Korean regulations
- AI-assisted sustainability analysis
- Workload optimization for carbon reduction
- Multi-cloud carbon comparison

See [carbon-kepler-mcp/readme.md](carbon-kepler-mcp/readme.md) for complete documentation.

## Integration Flow

```text
1. AWS Infrastructure Setup
   └─> deploy aws-deployment/
       └─> Creates c5.metal instance with K3s + Kepler
           └─> Exposes HTTPS metrics endpoint

2. Kepler Metrics Collection
   └─> eBPF probes collect real-time metrics
       └─> Model Server estimates power consumption
           └─> Prometheus metrics at https://<IP>:30443/metrics

3. Carbon Compliance Assessment
   └─> deploy carbon-kepler-mcp/
       └─> MCP server fetches Kepler metrics
           └─> Applies Korean regulatory standards
               └─> Generates compliance reports + recommendations

4. AI-Assisted Analysis
   └─> Claude Desktop integration via MCP
       └─> Natural language queries
           └─> "Check if my ml-training-job complies with Korean standards"
```

## Repository Structure

```text
Open-source-Summit-Korea-2025/
├── readme.md                      # This file - High-level overview
│
├── aws-deployment/                # AWS Infrastructure
│   ├── readme.md                 # Complete AWS deployment guide
│   ├── quick-start.md            # One-page quick reference
│   ├── automated-deployment.md   # Automation details
│   ├── kepler-deployment-summary.md  # Technical deep dive
│   ├── scripts/
│   │   ├── create-stack.sh       # Deploy CloudFormation stack
│   │   └── delete-stack.sh       # Clean up resources
│   └── templates/
│       └── kepler-k3s-automated-stack.yaml  # CloudFormation template
│
└── carbon-kepler-mcp/             # Carbon Compliance MCP Server
    ├── readme.md                 # Complete MCP documentation
    ├── src/                      # Python MCP server implementation
    │   ├── mcp_server.py         # Main MCP server
    │   ├── kepler_client.py      # Kepler integration
    │   ├── korea_compliance.py   # Korean standards logic
    │   └── recommendation_engine.py  # Optimization suggestions
    ├── config/                   # Korean regulatory data
    │   ├── carbon-intensity.json # Hourly carbon intensity
    │   ├── regulations.json      # Korean regulations
    │   └── regions.json          # Regional carbon data
    ├── k8s/                      # Kubernetes manifests
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   └── configmap.yaml
    └── scripts/
        ├── build.sh              # Build Docker image
        ├── deploy.sh             # Deploy to Kubernetes
        └── test-mcp.sh           # Test MCP tools
```

## What is Kepler?

Kepler (Kubernetes Efficient Power Level Exporter) is a CNCF Sandbox project that uses eBPF to probe energy-related system stats and exports Prometheus metrics for monitoring energy consumption of Kubernetes workloads.

**Key Capabilities:**

- Real-time energy monitoring at container, pod, and node levels
- eBPF-based low-overhead system metrics collection
- Hardware power monitoring (RAPL) on bare-metal
- ML-based power estimation for cloud/virtualized environments
- Prometheus integration for observability

**Why This Project?**

- **AWS Challenge:** Cloud environments don't expose hardware RAPL interfaces
- **Solution:** Kepler Model Server provides ML-based power estimation
- **Korean Context:** Compliance with national carbon neutrality and energy efficiency standards
- **AI Integration:** MCP protocol enables natural language compliance queries

## Korean Regulatory Standards

This project specifically addresses two Korean environmental regulations:

### 1. 탄소중립 녹색성장 기본법 (Carbon Neutrality Act)

- **Goal:** Carbon neutrality by 2050
- **Interim Target:** 35% reduction by 2030 (vs 2018 baseline)
- **Grid Intensity:** 424 gCO2eq/kWh
- **Reference:** [법령정보](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613)

### 2. 에너지이용 합리화법 (Energy Use Rationalization Act)

- **Goal:** Green Data Center certification
- **Target PUE:** ≤ 1.4
- **Authority:** MOTIE (Ministry of Trade, Industry and Energy)
- **Reference:** [법령정보](https://www.law.go.kr/법령/에너지이용합리화법)

## Getting Started

### Prerequisites

- AWS Account with ~$344 USD credits (for 84 hours on c5.metal)
- AWS CLI configured
- kubectl installed
- Docker (for building MCP server)
- Python 3.9+ (for local MCP development)

### Quick Deployment

**1. Deploy Kepler Infrastructure:**

```bash
cd aws-deployment/scripts
./create-stack.sh
# Wait ~15 minutes for complete deployment
```

**2. Verify Kepler Metrics:**

```bash
# Get public IP from stack output
PUBLIC_IP=$(aws cloudformation describe-stacks \
  --stack-name kepler-k3s-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
  --output text)

# Test metrics endpoint
curl -k https://$PUBLIC_IP:30443/metrics | grep kepler_node_cpu
```

**3. Deploy Carbon Compliance MCP:**

```bash
cd carbon-kepler-mcp

# Update k8s/deployment.yaml with your Kepler endpoint
# Then build and deploy
./scripts/build.sh
./scripts/deploy.sh
```

**4. Test Compliance Assessment:**

```bash
# Test MCP server
./scripts/test-mcp.sh
```

## Use Cases

### 1. Energy Monitoring

Monitor real-time energy consumption of Kubernetes workloads using eBPF and ML estimation.

### 2. Carbon Compliance

Assess compliance with Korean carbon neutrality and PUE targets for data centers.

### 3. Workload Optimization

Get AI-powered recommendations for:

- Temporal shifting to low-carbon time windows
- Resource rightsizing
- Regional migration

### 4. Sustainability Reporting

Generate compliance reports for Korean environmental regulations with actual metrics.

### 5. AI-Assisted Analysis

Natural language queries via Claude Desktop:

- "Which workloads exceed Korean carbon targets?"
- "What's the optimal time to run my ML training job?"
- "Compare carbon impact across AWS regions"

## Cost Management

**AWS Infrastructure Costs (us-east-1):**

- c5.metal: $4.08/hour (~84 hours with $344 budget)
- Stop instance when not in use to save costs
- Only EBS storage charges when stopped (~$10/month)

## Documentation

### AWS Deployment

- [aws-deployment/readme.md](aws-deployment/readme.md) - Complete guide
- [aws-deployment/quick-start.md](aws-deployment/quick-start.md) - Quick reference
- [aws-deployment/automated-deployment.md](aws-deployment/automated-deployment.md) - Automation details

### Carbon MCP

- [carbon-kepler-mcp/readme.md](carbon-kepler-mcp/readme.md) - Complete MCP documentation
- Korean regulatory standards implementation
- MCP tools reference

## Resources

### Kepler Project

- [Official Website](https://sustainable-computing.io/)
- [GitHub Repository](https://github.com/sustainable-computing-io/kepler)
- [Kepler Model Server](https://github.com/sustainable-computing-io/kepler-model-server)
- [CNCF Project Page](https://landscape.cncf.io/project=kepler)

### MCP Protocol

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Claude Desktop Integration](https://docs.anthropic.com/claude/docs/model-context-protocol)

### Korean Regulations

- [Carbon Neutrality Act](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613)
- [Energy Use Rationalization Act](https://www.law.go.kr/법령/에너지이용합리화법)

## License

Apache License 2.0

## Author

Marco Gonzalez (margonza@redhat.com)

---
**Technology Stack:**
CloudFormation, K3s, Kepler, eBPF, Prometheus, Python MCP, Korean Regulatory Standards
