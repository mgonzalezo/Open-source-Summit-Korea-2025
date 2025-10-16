# Carbon-Aware Kepler MCP Server Architecture

**Version**: 1.0
**Date**: 2025-10-13
**Target**: OSS Korea 2025 Demo - Korean Regulatory Compliance Focus

## Executive Summary

This architecture describes a Model Context Protocol (MCP) server that integrates with Kepler energy monitoring to provide carbon compliance assessments for Kubernetes workloads running on AWS bare-metal instances. The system focuses on Korean regulatory standards:

- **PUE Target**: ≤ 1.4 (에너지이용 합리화법 - Energy Use Rationalization Act)
- **Carbon Neutrality**: 2050 net-zero goal (탄소중립 녹색성장 기본법 - Framework Act on Carbon Neutrality and Green Growth)
- **Grid Intensity**: 424 gCO2eq/kWh (Korea average)

## System Overview

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Layer 3: Clients                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Claude Desktop   │  │  HTTP Clients    │  │  FastAPI UI  │  │
│  │  (stdio/SSE)     │  │  (curl, Python)  │  │  (Web UI)    │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘  │
└───────────┼────────────────────┼────────────────────┼───────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                        JSON-RPC 2.0 / HTTP
                                 │
┌─────────────────────────────────┼───────────────────────────────┐
│              Layer 2: Carbon-Aware MCP Server                    │
│  ┌──────────────────────────────┴────────────────────────────┐  │
│  │               MCP Server (Python + FastMCP)                │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  MCP Tools (5 tools)                                  │ │  │
│  │  │  - assess_workload_compliance()                       │ │  │
│  │  │  - compare_optimization_impact()                      │ │  │
│  │  │  - list_workloads_by_compliance()                     │ │  │
│  │  │  - get_regional_comparison()                          │ │  │
│  │  │  - calculate_optimal_schedule()                       │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  MCP Resources (3 resources)                          │ │  │
│  │  │  - compliance-standards://korea                       │ │  │
│  │  │  - carbon-intensity://ap-northeast-2                  │ │  │
│  │  │  - workload-metrics://namespace/pod                   │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  Business Logic Modules                               │ │  │
│  │  │  ┌────────────────┐  ┌──────────────────────────┐    │ │  │
│  │  │  │ Kepler Client  │  │  Korea Compliance        │    │ │  │
│  │  │  │ - Fetch metrics│  │  - PUE calculations      │    │ │  │
│  │  │  │ - Parse Prom   │  │  - Carbon calculations   │    │ │  │
│  │  │  └────────────────┘  └──────────────────────────┘    │ │  │
│  │  │  ┌────────────────────────────────────────────────┐  │ │  │
│  │  │  │  Recommendation Engine                         │  │ │  │
│  │  │  │  - Compliance status (COMPLIANT/NON_COMPLIANT) │  │ │  │
│  │  │  │  - Actionable recommendations                  │  │ │  │
│  │  │  │  - Optimization suggestions                    │  │ │  │
│  │  │  └────────────────────────────────────────────────┘  │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ConfigMap: korea-compliance-data                               │
│  ├── carbon-intensity.json (424 gCO2/kWh)                       │
│  ├── regulations.json (PUE 1.4, Carbon Neutrality Act)          │
│  └── regions.json (ap-northeast-2, us-east-1, eu-north-1)       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                          HTTP GET /metrics
                                 │
┌─────────────────────────────────┼───────────────────────────────┐
│                 Layer 1: Kepler Monitoring                       │
│  ┌──────────────────────────────┴────────────────────────────┐  │
│  │  Kepler v0.11.2 (kepler-system namespace)                  │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  eBPF Metrics Collection                             │ │  │
│  │  │  - CPU cycles, instructions, cache misses            │ │  │
│  │  │  - Memory reads/writes                               │ │  │
│  │  │  - Process-level resource usage                      │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  Power Estimation                                     │ │  │
│  │  │  - Fake meter (initialization only)                  │ │  │
│  │  │  - Model Server (ML-based power for AWS)             │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  Prometheus Metrics Endpoint                          │ │  │
│  │  │  - https://<PUBLIC_IP>:30443/metrics                 │ │  │
│  │  │  - kepler_pod_cpu_watts                              │ │  │
│  │  │  - kepler_pod_memory_watts                           │ │  │
│  │  │  - kepler_node_cpu_usage_ratio                       │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Model Server (kepler-model-server namespace)                   │
│  ├── ec2-0.7.11 model (AWS EC2 power estimation)                │
│  └── specpower-0.7.11 model (SPECpower regression)              │
└─────────────────────────────────────────────────────────────────┘
                                 │
                        AWS c5.metal (96 vCPU)
```

## Component Architecture

### Layer 1: Kepler Monitoring (Data Collection)

**Purpose**: Collect real hardware metrics and estimate power consumption

**Components**:
- **Kepler DaemonSet**: Deploys on bare-metal node, uses eBPF probes
- **Model Server**: Provides ML-based power estimation (ec2-0.7.11, specpower-0.7.11)
- **HTTPS Proxy**: Nginx proxy with TLS for secure metrics access

**Key Metrics Collected**:
```
kepler_pod_cpu_watts{pod="app", namespace="default"}
kepler_pod_memory_watts{pod="app", namespace="default"}
kepler_node_cpu_usage_ratio
kepler_node_cpu_watts
kepler_container_joules_total
```

**Why Kepler?**
- Real eBPF-based metrics (not simulated)
- ML-based power estimation works on AWS (RAPL unavailable)
- Process-level granularity
- Production-ready for cloud environments

### Layer 2: Carbon-Aware MCP Server (Compliance Logic)

**Purpose**: Assess compliance with Korean regulations and provide actionable recommendations

**Input**:
- MCP tool calls (JSON-RPC 2.0)
- Kepler metrics (Prometheus format)
- Compliance standards (ConfigMap data)

**Output**:
```json
{
  "workload": "ml-training-job",
  "namespace": "ai-team",
  "standard": "KR_CARBON_2050",
  "status": "NON_COMPLIANT",
  "current_power_watts": 45.2,
  "grid_carbon_intensity_gCO2eq_kWh": 424,
  "estimated_workload_intensity_gCO2eq_kWh": 510,
  "pue": 1.6,
  "pue_status": "NON_COMPLIANT",
  "carbon_emissions_gCO2eq_hour": 19.2,
  "recommendation": "️ NON-COMPLIANT: Workload exceeds Korea Carbon Neutrality 2050 target by 20%. PUE of 1.6 exceeds Green Data Center requirement of 1.4. Recommendations: 1) Reduce CPU-intensive operations during peak grid hours (10am-6pm KST). 2) Implement workload scheduling to shift to cleaner grid hours (2am-6am, ~380 gCO2/kWh). 3) Optimize container resource requests to reduce CPU waste.",
  "optimizations": [
    {
      "type": "temporal_shift",
      "description": "Reschedule workload to 2am-6am KST",
      "estimated_reduction_percent": 10,
      "estimated_new_intensity_gCO2eq_kWh": 459
    },
    {
      "type": "resource_optimization",
      "description": "Right-size CPU requests (reduce from 8 cores to 6 cores)",
      "estimated_reduction_percent": 15,
      "estimated_new_power_watts": 38.4
    }
  ],
  "timestamp": "2025-10-13T09:30:00Z",
  "region": "ap-northeast-2"
}
```

**Core Modules**:

1. **mcp_server.py** (~300 lines)
   - FastMCP server initialization
   - Tool registration
   - Resource registration
   - Error handling

2. **kepler_client.py** (~150 lines)
   - HTTP client for Kepler metrics endpoint
   - Prometheus text format parser
   - Metrics aggregation (pod-level, namespace-level, node-level)
   - Caching layer (60-second TTL)

3. **korea_compliance.py** (~200 lines)
   - PUE calculations
   - Carbon intensity calculations
   - Compliance status determination
   - Korean regulatory logic

4. **compliance_standards.py** (~150 lines)
   - Standard definitions (CarbonStandard, PUEStandard models)
   - Korea standards (KR_CARBON_2050, KR_PUE_GREEN_DC)
   - Global standards for comparison (US_EPA, EU_CODE_OF_CONDUCT)

5. **recommendation_engine.py** (~250 lines)
   - Status-based recommendations (COMPLIANT vs NON_COMPLIANT)
   - Optimization suggestions (temporal shift, resource right-sizing)
   - Korea-specific best practices
   - Action prioritization

6. **prometheus_parser.py** (~100 lines)
   - Parse Prometheus text format
   - Extract metric values by labels
   - Handle metric families (gauge, counter, histogram)

7. **carbon_calculator.py** (~80 lines)
   - Generic carbon calculations
   - PUE formulas
   - Unit conversions (watts → kWh, gCO2 → kg)

### Layer 3: Clients (User Interface)

**Purpose**: Provide multiple access methods to MCP server

**Client Options**:

1. **Claude Desktop** (stdio transport)
   - Native MCP integration
   - Natural language queries: "Is my ml-training-job compliant with Korean carbon standards?"
   - Returns structured data in chat

2. **HTTP Clients** (curl, Python requests)
   ```bash
   curl -X POST http://<NODE_IP>:30800/tools/assess_workload_compliance \
     -H "Content-Type: application/json" \
     -d '{
       "workload_name": "web-app",
       "namespace": "production",
       "standard": "KR_CARBON_2050"
     }'
   ```

3. **FastAPI Web UI** (Optional)
   - Swagger UI at `/docs`
   - Interactive tool testing
   - Response visualization

## Data Flow Architecture

### End-to-End Flow: Compliance Assessment

```
┌──────────────────────────────────────────────────────────────────┐
│ Step 1: User Request                                             │
│                                                                  │
│ User (Claude Desktop):                                           │
│   "Check if my ml-training-job in namespace ai-team complies    │
│    with Korean carbon neutrality standards"                     │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Step 2: MCP Protocol Translation                                │
│                                                                  │
│ Claude Desktop → JSON-RPC 2.0:                                  │
│ {                                                                │
│   "jsonrpc": "2.0",                                             │
│   "method": "tools/call",                                       │
│   "params": {                                                    │
│     "name": "assess_workload_compliance",                       │
│     "arguments": {                                              │
│       "workload_name": "ml-training-job",                       │
│       "namespace": "ai-team",                                   │
│       "standard": "KR_CARBON_2050",                             │
│       "region": "ap-northeast-2"                                │
│     }                                                            │
│   }                                                              │
│ }                                                                │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Step 3: MCP Server Processing                                   │
│                                                                  │
│ a) Fetch Kepler metrics                                         │
│    kepler_client.get_pod_metrics("ml-training-job", "ai-team")  │
│    → HTTP GET https://<IP>:30443/metrics                        │
│                                                                  │
│ b) Parse Prometheus response                                    │
│    prometheus_parser.parse(raw_text)                            │
│    → {                                                           │
│         "kepler_pod_cpu_watts": 45.2,                           │
│         "kepler_pod_memory_watts": 12.3                         │
│       }                                                          │
│                                                                  │
│ c) Load compliance standard                                     │
│    compliance_standards.get_standard("KR_CARBON_2050")          │
│    → target_carbon_intensity: 424 gCO2/kWh                      │
│                                                                  │
│ d) Calculate carbon metrics                                     │
│    korea_compliance.calculate_carbon_footprint(                 │
│      power_watts=45.2,                                          │
│      grid_intensity=424                                         │
│    )                                                             │
│    → workload_intensity: 510 gCO2/kWh                           │
│    → emissions: 19.2 gCO2/hour                                  │
│                                                                  │
│ e) Assess compliance                                            │
│    korea_compliance.assess_compliance(510, 424)                 │
│    → status: "NON_COMPLIANT" (exceeds by 20%)                   │
│                                                                  │
│ f) Generate recommendations                                     │
│    recommendation_engine.generate(                              │
│      status="NON_COMPLIANT",                                    │
│      workload_data=...,                                         │
│      standard="KR_CARBON_2050"                                  │
│    )                                                             │
│    → [temporal_shift, resource_optimization, ...]               │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Step 4: Return Structured Response                              │
│                                                                  │
│ JSON-RPC 2.0 Response:                                          │
│ {                                                                │
│   "jsonrpc": "2.0",                                             │
│   "result": {                                                    │
│     "workload": "ml-training-job",                              │
│     "namespace": "ai-team",                                     │
│     "standard": "KR_CARBON_2050",                               │
│     "status": "NON_COMPLIANT",                                  │
│     "current_power_watts": 45.2,                                │
│     "grid_carbon_intensity_gCO2eq_kWh": 424,                    │
│     "estimated_workload_intensity_gCO2eq_kWh": 510,             │
│     "recommendation": "️ NON-COMPLIANT: Workload exceeds...",  │
│     "optimizations": [...]                                      │
│   }                                                              │
│ }                                                                │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Step 5: User-Friendly Presentation                              │
│                                                                  │
│ Claude Desktop displays:                                        │
│                                                                  │
│ "Your ml-training-job workload is currently NON-COMPLIANT       │
│  with Korean Carbon Neutrality 2050 standards. The workload     │
│  emits 510 gCO2eq/kWh, which exceeds the target of 424 gCO2/kWh │
│  by 20%.                                                         │
│                                                                  │
│  Recommendations:                                               │
│  1. Reschedule to 2am-6am KST (cleaner grid, ~10% reduction)    │
│  2. Right-size CPU from 8 to 6 cores (~15% power reduction)     │
│  3. Consider regional migration to eu-north-1 (Sweden, 50%      │
│     cleaner grid)"                                              │
└──────────────────────────────────────────────────────────────────┘
```

## MCP Tools Architecture

### Tool 1: `assess_workload_compliance`

**Purpose**: Primary compliance check for a single workload

**Input**:
```python
{
  "workload_name": str,        # Pod or deployment name
  "namespace": str = "default", # Kubernetes namespace
  "standard": str = "KR_CARBON_2050",  # Compliance standard code
  "region": str = "ap-northeast-2"     # AWS region
}
```

**Output**:
```python
{
  "workload": str,
  "namespace": str,
  "standard": str,
  "status": Literal["COMPLIANT", "NON_COMPLIANT"],
  "current_power_watts": float,
  "grid_carbon_intensity_gCO2eq_kWh": float,
  "estimated_workload_intensity_gCO2eq_kWh": float,
  "pue": float,
  "pue_status": Literal["COMPLIANT", "NON_COMPLIANT"],
  "carbon_emissions_gCO2eq_hour": float,
  "recommendation": str,
  "optimizations": List[OptimizationSuggestion],
  "timestamp": str,
  "region": str
}
```

**Logic**:
1. Fetch Kepler metrics for workload
2. Load compliance standard from ConfigMap
3. Calculate carbon intensity and PUE
4. Compare against standard thresholds
5. Generate compliance status
6. Provide actionable recommendations

### Tool 2: `compare_optimization_impact`

**Purpose**: Compare before/after carbon impact of optimizations

**Input**:
```python
{
  "workload_name": str,
  "namespace": str,
  "optimizations": List[str],  # ["temporal_shift", "resource_rightsizing"]
  "standard": str = "KR_CARBON_2050"
}
```

**Output**:
```python
{
  "workload": str,
  "current_status": str,
  "current_emissions_gCO2eq_hour": float,
  "optimized_emissions_gCO2eq_hour": float,
  "reduction_percent": float,
  "optimized_status": str,
  "estimated_cost_savings_usd_month": float,
  "implementation_steps": List[str]
}
```

### Tool 3: `list_workloads_by_compliance`

**Purpose**: Inventory all workloads in a namespace by compliance status

**Input**:
```python
{
  "namespace": str = "default",
  "standard": str = "KR_CARBON_2050",
  "status_filter": Optional[str] = None  # "COMPLIANT" | "NON_COMPLIANT"
}
```

**Output**:
```python
{
  "namespace": str,
  "standard": str,
  "total_workloads": int,
  "compliant_count": int,
  "non_compliant_count": int,
  "workloads": List[WorkloadSummary]
}
```

### Tool 4: `get_regional_comparison`

**Purpose**: Compare carbon impact across AWS regions

**Input**:
```python
{
  "workload_name": str,
  "namespace": str,
  "current_region": str = "ap-northeast-2",
  "comparison_regions": List[str] = ["us-east-1", "eu-north-1"]
}
```

**Output**:
```python
{
  "workload": str,
  "comparisons": List[RegionalComparison],
  "best_region": str,
  "best_region_savings_percent": float,
  "migration_recommendation": str
}
```

### Tool 5: `calculate_optimal_schedule`

**Purpose**: Find best time windows for carbon-efficient workload scheduling

**Input**:
```python
{
  "workload_name": str,
  "namespace": str,
  "duration_hours": int,
  "region": str = "ap-northeast-2"
}
```

**Output**:
```python
{
  "workload": str,
  "current_schedule": str,
  "current_carbon_intensity": float,
  "optimal_schedule": str,  # "2025-10-14 02:00 KST - 06:00 KST"
  "optimal_carbon_intensity": float,
  "reduction_percent": float,
  "recommendation": str
}
```

## MCP Resources Architecture

### Resource 1: `compliance-standards://korea`

**Purpose**: Expose Korean compliance standards as queryable resource

**URI Format**: `compliance-standards://korea/{standard_code}`

**Examples**:
- `compliance-standards://korea/KR_CARBON_2050`
- `compliance-standards://korea/KR_PUE_GREEN_DC`

**Response**:
```json
{
  "code": "KR_CARBON_2050",
  "name": "Framework Act on Carbon Neutrality and Green Growth",
  "name_local": "탄소중립 녹색성장 기본법",
  "target_carbon_intensity_gco2_kwh": 424,
  "grid_carbon_intensity_gco2_kwh": 424,
  "enforcement_date": "2021-09-24",
  "description": "South Korea's commitment to achieve carbon neutrality by 2050, with interim targets of 35% reduction by 2030 (compared to 2018 baseline).",
  "reference_url": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613"
}
```

### Resource 2: `carbon-intensity://ap-northeast-2`

**Purpose**: Provide regional carbon intensity data (hourly profile)

**URI Format**: `carbon-intensity://{region}/{timestamp?}`

**Examples**:
- `carbon-intensity://ap-northeast-2` (current average)
- `carbon-intensity://ap-northeast-2/2025-10-13T14:00:00Z` (specific time)

**Response**:
```json
{
  "region": "ap-northeast-2",
  "average_gCO2eq_kWh": 424,
  "current_gCO2eq_kWh": 450,
  "hourly_profile": [
    {"hour": 0, "intensity": 380},
    {"hour": 1, "intensity": 375},
    {"hour": 2, "intensity": 370},
    ...
    {"hour": 14, "intensity": 450},
    ...
  ],
  "cleanest_hours": [2, 3, 4, 5],
  "dirtiest_hours": [10, 11, 12, 13, 14, 15, 16, 17, 18],
  "grid_mix": {
    "coal": 35,
    "natural_gas": 28,
    "nuclear": 25,
    "renewable": 12
  }
}
```

### Resource 3: `workload-metrics://namespace/pod`

**Purpose**: Direct access to Kepler metrics for a specific workload

**URI Format**: `workload-metrics://{namespace}/{pod_name}`

**Response**:
```json
{
  "namespace": "ai-team",
  "pod": "ml-training-job",
  "metrics": {
    "cpu_watts": 45.2,
    "memory_watts": 12.3,
    "total_watts": 57.5,
    "cpu_usage_ratio": 0.65,
    "joules_total": 207000
  },
  "timestamp": "2025-10-13T09:30:00Z",
  "collection_method": "ebpf"
}
```

## Compliance Standards Architecture

### Standard Definitions

```python
from pydantic import BaseModel
from typing import Optional

class CarbonStandard(BaseModel):
    """Carbon intensity compliance standard"""
    code: str
    name: str
    name_local: Optional[str] = None
    target_carbon_intensity_gco2_kwh: float
    grid_carbon_intensity_gco2_kwh: float
    enforcement_date: Optional[str] = None
    description: str
    reference_url: Optional[str] = None

class PUEStandard(BaseModel):
    """Power Usage Effectiveness standard"""
    code: str
    name: str
    name_local: Optional[str] = None
    target_pue: float
    baseline_pue: float
    certification_level: Optional[str] = None
    description: str
    reference_url: Optional[str] = None
```

### Korean Standards

```python
# Carbon Neutrality Standard
KOREA_CARBON_NEUTRALITY = CarbonStandard(
    code="KR_CARBON_2050",
    name="Framework Act on Carbon Neutrality and Green Growth",
    name_local="탄소중립 녹색성장 기본법",
    target_carbon_intensity_gco2_kwh=424,  # Korea grid average
    grid_carbon_intensity_gco2_kwh=424,
    enforcement_date="2021-09-24",
    description="South Korea's commitment to achieve carbon neutrality by 2050, with interim targets of 35% reduction by 2030 (compared to 2018 baseline).",
    reference_url="https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=230613"
)

# PUE Standard
KOREA_PUE_TARGET = PUEStandard(
    code="KR_PUE_GREEN_DC",
    name="Energy Use Rationalization Act - Green Data Center",
    name_local="에너지이용 합리화법 - 그린 데이터센터",
    target_pue=1.4,
    baseline_pue=1.8,
    certification_level="Green Data Center Certification",
    description="Korean Ministry of Trade, Industry and Energy (MOTIE) requires PUE ≤ 1.4 for Green Data Center certification under the Energy Use Rationalization Act.",
    reference_url="https://www.law.go.kr/법령/에너지이용합리화법"
)
```

### Global Standards (for comparison)

```python
# US EPA Standard
US_EPA_ENERGY_STAR = CarbonStandard(
    code="US_EPA_ENERGY_STAR",
    name="EPA Energy Star Data Center",
    target_carbon_intensity_gco2_kwh=450,  # US grid average
    grid_carbon_intensity_gco2_kwh=450,
    description="US EPA Energy Star certification for data centers"
)

# EU Code of Conduct
EU_CODE_OF_CONDUCT = PUEStandard(
    code="EU_COC_DC",
    name="EU Code of Conduct for Data Centres",
    target_pue=1.3,
    baseline_pue=2.0,
    description="EU voluntary standard for energy-efficient data centers"
)
```

### Standards Hierarchy

```
┌─────────────────────────────────────────┐
│       Compliance Standards              │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Korea Standards (Primary)        │  │
│  │  ├── KR_CARBON_2050              │  │
│  │  │   ├── Target: 424 gCO2/kWh    │  │
│  │  │   └── Law: 탄소중립법          │  │
│  │  └── KR_PUE_GREEN_DC             │  │
│  │      ├── Target: PUE ≤ 1.4       │  │
│  │      └── Law: 에너지이용합리화법  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Global Standards (Comparison)    │  │
│  │  ├── US_EPA_ENERGY_STAR          │  │
│  │  │   └── 450 gCO2/kWh            │  │
│  │  ├── EU_COC_DC                   │  │
│  │  │   └── PUE ≤ 1.3               │  │
│  │  └── ASHRAE_THERMAL_90_4         │  │
│  │      └── PUE ≤ 1.2               │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Regional Carbon Intensity        │  │
│  │  ├── ap-northeast-2: 424 gCO2/kWh│  │
│  │  ├── us-east-1: 450 gCO2/kWh     │  │
│  │  ├── eu-north-1: 50 gCO2/kWh     │  │
│  │  └── ap-southeast-1: 650 gCO2/kWh│  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Kubernetes Resource Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│  Namespace: carbon-mcp                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │ ConfigMap: korea-compliance-data                       ││
│  │ ├── carbon-intensity.json (424 gCO2/kWh)               ││
│  │ ├── regulations.json (PUE 1.4, Carbon Neutrality Act)  ││
│  │ └── regions.json (ap-northeast-2, us-east-1, ...)      ││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Deployment: carbon-mcp-server                          ││
│  │ ├── Replicas: 1                                        ││
│  │ ├── Image: your-registry/carbon-kepler-mcp:latest     ││
│  │ ├── Env:                                               ││
│  │ │   ├── KEPLER_ENDPOINT=https://<IP>:30443/metrics    ││
│  │ │   ├── KOREA_CARBON_INTENSITY=424                    ││
│  │ │   ├── KOREA_PUE_TARGET=1.4                          ││
│  │ │   └── MCP_TRANSPORT=stdio                           ││
│  │ ├── Ports:                                             ││
│  │ │   └── 8000 (HTTP for SSE/HTTP transports)           ││
│  │ └── Resources:                                         ││
│  │     ├── requests: cpu=100m, memory=128Mi              ││
│  │     └── limits: cpu=500m, memory=512Mi                ││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Service: carbon-mcp-server                             ││
│  │ ├── Type: ClusterIP                                    ││
│  │ ├── Port: 8000                                         ││
│  │ └── NodePort: 30800 (external access)                  ││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │ ServiceAccount: carbon-mcp-sa                          ││
│  │ ├── Role: carbon-mcp-reader                            ││
│  │ └── Permissions:                                       ││
│  │     ├── pods: get, list                                ││
│  │     ├── configmaps: get                                ││
│  │     └── namespaces: list                               ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Security & Network Architecture

### Port Mapping

```
┌──────────────────────────────────────────────────────────┐
│  External World                                          │
└────────────────┬─────────────────────────────────────────┘
                 │
                 │ HTTPS (443) / SSH (22)
                 ▼
┌──────────────────────────────────────────────────────────┐
│  AWS c5.metal Instance (Public IP)                       │
│  Security Group: kepler-k3s-sg                           │
│  ├── Port 22 (SSH)                                       │
│  ├── Port 6443 (K3s API)                                 │
│  ├── Port 30443 (Kepler HTTPS Metrics) ──┐               │
│  └── Port 30800 (MCP Server HTTP) ───────┼──┐            │
└────────────────┬─────────────────────────┼──┼────────────┘
                 │                         │  │
                 │ Localhost               │  │
                 ▼                         │  │
┌──────────────────────────────────────────┼──┼────────────┐
│  K3s Cluster                             │  │            │
│  ┌───────────────────────────────────────┼──┼──────────┐ │
│  │ Namespace: kepler-system              │  │          │ │
│  │ ┌─────────────────────────────────────┼──┘          │ │
│  │ │ Service: kepler-https-proxy        │             │ │
│  │ │ Type: NodePort                     │             │ │
│  │ │ Port: 30443 (external) → 443 (int) │             │ │
│  │ └─────────────────────────────────────┘             │ │
│  └─────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┬──────────────┐
│  │ Namespace: carbon-mcp                  │              │
│  │ ┌──────────────────────────────────────┼────────────┐ │
│  │ │ Service: carbon-mcp-server          │            │ │
│  │ │ Type: ClusterIP + NodePort          │            │ │
│  │ │ Port: 8000 (internal)               │            │ │
│  │ │ NodePort: 30800 (external) ◄────────┘            │ │
│  │ └───────────────────────────────────────────────────┘ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### RBAC Permissions

```yaml
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: carbon-mcp-sa
  namespace: carbon-mcp

---
# Role (namespace-scoped)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: carbon-mcp-reader
  namespace: carbon-mcp
rules:
- apiGroups: [""]
  resources: ["pods", "configmaps"]
  verbs: ["get", "list"]

---
# ClusterRole (for cross-namespace pod listing)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: carbon-mcp-cluster-reader
rules:
- apiGroups: [""]
  resources: ["pods", "namespaces"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get"]

---
# RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: carbon-mcp-reader-binding
  namespace: carbon-mcp
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: carbon-mcp-reader
subjects:
- kind: ServiceAccount
  name: carbon-mcp-sa
  namespace: carbon-mcp

---
# ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: carbon-mcp-cluster-reader-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: carbon-mcp-cluster-reader
subjects:
- kind: ServiceAccount
  name: carbon-mcp-sa
  namespace: carbon-mcp
```

## Module Architecture (Detailed)

### File Structure

```
carbon-kepler-mcp/
├── README.md
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── mcp_server.py                 # ~300 lines - Main MCP server
│   ├── kepler_client.py              # ~150 lines - Kepler integration
│   ├── prometheus_parser.py          # ~100 lines - Metrics parsing
│   ├── korea_compliance.py           # ~200 lines - Compliance calculations
│   ├── compliance_standards.py       # ~150 lines - Standards definitions
│   ├── recommendation_engine.py      # ~250 lines - Recommendations
│   └── carbon_calculator.py          # ~80 lines - Generic calculations
├── config/
│   ├── korea-compliance-data.yaml    # ConfigMap data
│   ├── carbon-intensity.json         # Hourly grid intensity
│   ├── regulations.json              # Korean regulations
│   └── regions.json                  # Regional data
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── rbac.yaml
│   └── kustomization.yaml
├── scripts/
│   ├── build.sh                      # Docker build
│   ├── deploy.sh                     # Deploy to K3s
│   ├── test-local.sh                 # Local testing
│   └── test-mcp.sh                   # MCP integration test
└── tests/
    ├── test_kepler_client.py
    ├── test_korea_compliance.py
    ├── test_recommendation_engine.py
    └── fixtures/
        └── sample_metrics.txt
```

### Total Line Count Estimate

```
src/mcp_server.py              300 lines
src/kepler_client.py           150 lines
src/prometheus_parser.py       100 lines
src/korea_compliance.py        200 lines
src/compliance_standards.py    150 lines
src/recommendation_engine.py   250 lines
src/carbon_calculator.py        80 lines
config/*.json                  200 lines
k8s/*.yaml                     250 lines
tests/*.py                     200 lines
scripts/*.sh                   100 lines
README.md                       50 lines
Dockerfile + requirements       20 lines
───────────────────────────────────────
TOTAL                         ~1,230 lines
```

## Implementation Phases

### Phase 1: Core Infrastructure (Day 1)
- [x] Kepler v0.11.2 deployed on AWS c5.metal
- [x] Model Server fixed and operational
- [x] HTTPS metrics endpoint accessible
- [ ] Create project structure
- [ ] Implement compliance_standards.py
- [ ] Implement carbon_calculator.py

### Phase 2: Kepler Integration (Day 2)
- [ ] Implement prometheus_parser.py
- [ ] Implement kepler_client.py with caching
- [ ] Test metrics fetching from Kepler
- [ ] Create sample test fixtures

### Phase 3: Compliance Logic (Day 3)
- [ ] Implement korea_compliance.py
- [ ] Implement recommendation_engine.py
- [ ] Create ConfigMap data files
- [ ] Test compliance calculations

### Phase 4: MCP Server (Day 4)
- [ ] Implement mcp_server.py with FastMCP
- [ ] Implement 5 MCP tools
- [ ] Implement 3 MCP resources
- [ ] Test local MCP server (stdio mode)

### Phase 5: Kubernetes Deployment (Day 5)
- [ ] Create Dockerfile
- [ ] Build and push container image
- [ ] Create Kubernetes manifests
- [ ] Deploy to carbon-mcp namespace
- [ ] Test HTTP and SSE transports

### Phase 6: Integration & Testing (Day 6)
- [ ] Test with Claude Desktop (stdio)
- [ ] Test with curl (HTTP)
- [ ] End-to-end compliance assessment
- [ ] Performance testing
- [ ] Documentation

### Phase 7: Demo Preparation (Day 7)
- [ ] Create demo workloads (compliant + non-compliant)
- [ ] Prepare demo script
- [ ] Create presentation slides
- [ ] Practice demo flow

## Demo Talking Points (OSS Korea 2025)

### Introduction (2 minutes)
"Today I'll demonstrate how we can make Kubernetes workloads compliant with Korean carbon neutrality standards using Kepler and AI-powered compliance checking."

### Problem Statement (3 minutes)
- Korea's Carbon Neutrality Act (탄소중립 녹색성장 기본법) requires 2050 net-zero
- Data centers must achieve PUE ≤ 1.4 for Green certification (에너지이용 합리화법)
- Korea's grid intensity: 424 gCO2eq/kWh (coal 35%, gas 28%, nuclear 25%)
- Challenge: How to monitor and optimize workload carbon footprint in real-time?

### Architecture Overview (5 minutes)
- **Layer 1: Kepler** - eBPF-based energy monitoring
  - Why Kepler? Real metrics, not simulations
  - Why bare-metal? Direct hardware access for accurate measurements
  - Why Model Server? AWS doesn't expose RAPL, need ML-based estimation

- **Layer 2: Carbon MCP Server** - Compliance intelligence
  - Korean regulatory standards
  - Real-time carbon calculations
  - Actionable recommendations

- **Layer 3: Claude Desktop** - Natural language interface
  - Ask: "Is my ML workload compliant with Korean standards?"
  - Get: Clear COMPLIANT/NON_COMPLIANT status with recommendations

### Live Demo (10 minutes)

**Demo 1: Non-Compliant Workload**
```
User: "Check if ml-training-job complies with Korean carbon standards"

Claude: "Your ml-training-job is NON-COMPLIANT:
- Current: 510 gCO2eq/kWh
- Target: 424 gCO2eq/kWh (20% over)
- PUE: 1.6 (exceeds 1.4 target)

Recommendations:
1. Reschedule to 2am-6am KST (10% cleaner grid)
2. Right-size CPU from 8 to 6 cores (15% power reduction)
3. Consider eu-north-1 (50% cleaner grid)"
```

**Demo 2: Optimization Impact**
```
User: "What's the impact of rescheduling to 2am?"

Claude: "Rescheduling ml-training-job to 2am-6am KST:
- Reduction: 10% (51 gCO2eq/kWh saved)
- New intensity: 459 gCO2eq/kWh
- Status: Still NON-COMPLIANT (need additional optimizations)
- Combined with CPU right-sizing: COMPLIANT (398 gCO2eq/kWh)"
```

**Demo 3: Regional Comparison**
```
User: "Compare carbon impact across AWS regions"

Claude: "Regional comparison for ml-training-job:
- ap-northeast-2 (Seoul): 510 gCO2eq/kWh - NON_COMPLIANT
- us-east-1 (Virginia): 540 gCO2eq/kWh - NON_COMPLIANT
- eu-north-1 (Stockholm): 60 gCO2eq/kWh - COMPLIANT 

Best region: eu-north-1 (88% reduction)
Migration recommendation: Consider for batch workloads"
```

### Technical Highlights (3 minutes)
- **Real eBPF metrics**: Not simulated, actual CPU cycles, cache misses, memory I/O
- **ML-based power estimation**: Works on AWS where RAPL unavailable
- **Korean regulatory focus**: PUE 1.4, Carbon Neutrality 2050, 424 gCO2/kWh
- **MCP protocol**: Standardized AI integration, works with Claude Desktop
- **Production-ready**: K8s deployment, RBAC, ConfigMaps, HTTPS

### Future Enhancements (2 minutes)
- **Carbon Aware SDK integration**: Real-time grid data instead of static averages
- **Temporal optimization**: Automatic workload scheduling based on grid cleanliness
- **Multi-cloud support**: GCP, Azure carbon footprint tracking
- **Cost optimization**: Combine carbon + cost for holistic optimization

---

**Total Estimated Lines of Code**: ~1,230 lines
**Deployment Time**: ~5 minutes (K8s manifests)
**Demo Duration**: 25 minutes
**Target Audience**: OSS Korea 2025 - Sustainability Track

---

**Next Steps**:
1. Review and approve this architecture
2. Generate implementation files (Phase 1-7)
3. Deploy to AWS K3s cluster
4. Test end-to-end flow
5. Prepare demo script for OSS Korea 2025
