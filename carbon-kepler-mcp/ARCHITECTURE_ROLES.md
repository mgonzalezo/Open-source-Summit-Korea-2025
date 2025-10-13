# Architecture Roles and Actions by Layer

**Carbon-Aware Kepler MCP Server - OSS Korea 2025**

---

## Layer 1: Kepler Monitoring (Data Collection Layer)

### 🎯 Primary Role
**Real-time Energy Metrics Collection & Power Estimation**

### 👥 Contributing Roles

| Role | Responsibility | Technology |
|------|----------------|------------|
| **eBPF Probe** | Collect hardware performance counters | Linux eBPF |
| **Metrics Collector** | Aggregate CPU cycles, cache misses, memory I/O | Kepler DaemonSet |
| **Power Estimator** | ML-based power consumption estimation | Model Server (ec2-0.7.11) |
| **Metrics Publisher** | Expose metrics in Prometheus format | Prometheus Exporter |
| **HTTPS Proxy** | Secure external metrics access | Nginx + TLS |

### 🔄 Key Actions

1. **Collect Hardware Metrics**
   - Monitor CPU cycles, instructions, cache misses
   - Track memory read/write operations
   - Capture process-level resource usage
   - **Output:** Raw eBPF performance counters

2. **Estimate Power Consumption**
   - Use fake meter for initialization (first 15s)
   - Apply ML models (ec2-0.7.11) for AWS instances
   - Calculate per-pod and per-node power
   - **Output:** `kepler_pod_cpu_watts`, `kepler_pod_memory_watts`

3. **Publish Metrics**
   - Format data in Prometheus text format
   - Expose via HTTPS endpoint `:30443/metrics`
   - Include labels (pod, namespace, container)
   - **Output:** Queryable metrics endpoint

### 📊 Metrics Produced

```
kepler_pod_cpu_watts{pod="app",namespace="default"} 25.5
kepler_pod_memory_watts{pod="app",namespace="default"} 12.3
kepler_node_cpu_watts 125.8
kepler_node_cpu_usage_ratio 0.35
```

### 🎯 Success Criteria
- ✅ Real eBPF metrics (not simulated)
- ✅ ML-based power estimation on AWS (no RAPL)
- ✅ Per-pod granularity
- ✅ Accessible via HTTPS

---

## Layer 2: Carbon-Aware MCP Server (Intelligence Layer)

### 🎯 Primary Role
**Korean Regulatory Compliance Assessment & Optimization Recommendations**

### 👥 Contributing Roles

| Role | Responsibility | Component |
|------|----------------|-----------|
| **MCP Protocol Handler** | Handle JSON-RPC 2.0 requests/responses | FastMCP Framework |
| **Tool Orchestrator** | Coordinate 5 MCP tools | `mcp_server.py` |
| **Resource Provider** | Serve 3 MCP resources | MCP Resources |
| **Metrics Client** | Fetch & parse Kepler metrics | `kepler_client.py` |
| **Compliance Analyst** | Assess against Korean standards | `korea_compliance.py` |
| **Recommendation Engine** | Generate actionable advice | `recommendation_engine.py` |
| **Configuration Manager** | Load Korean regulatory data | ConfigMap |

### 🔄 Key Actions

#### **Action Group 1: Tool Execution**

1. **assess_workload_compliance**
   - Fetch pod metrics from Kepler
   - Calculate carbon intensity (gCO2eq/kWh)
   - Estimate PUE from node metrics
   - Compare against Korean standards
   - **Output:** `COMPLIANT` or `NON_COMPLIANT` status

2. **compare_optimization_impact**
   - Model temporal shift (2am-6am scheduling)
   - Calculate resource right-sizing impact
   - Estimate emissions & cost savings
   - **Output:** Before/after comparison

3. **list_workloads_by_compliance**
   - Scan namespace for all pods
   - Assess each workload
   - Categorize by compliance status
   - **Output:** Compliance inventory

4. **get_regional_comparison**
   - Compare current region vs alternatives
   - Calculate carbon intensity differences
   - Identify cleanest region
   - **Output:** Migration recommendation

5. **calculate_optimal_schedule**
   - Analyze hourly grid intensity profile
   - Find cleanest time windows
   - Calculate emissions reduction
   - **Output:** Optimal schedule (2am-6am KST)

#### **Action Group 2: Compliance Analysis**

6. **Carbon Neutrality Assessment**
   - Standard: 탄소중립 녹색성장 기본법
   - Target: 424 gCO2eq/kWh
   - Calculate gap percentage
   - **Output:** Carbon compliance status

7. **PUE Assessment**
   - Standard: 에너지이용 합리화법
   - Target: PUE ≤ 1.4
   - Estimate from node overhead (40%)
   - **Output:** PUE compliance status

#### **Action Group 3: Recommendation Generation**

8. **Generate Optimizations**
   - Temporal shift (10% reduction)
   - Resource right-sizing (15% reduction)
   - Regional migration (up to 88% reduction)
   - PUE improvement strategies
   - **Output:** Prioritized action list

9. **Cost-Benefit Analysis**
   - Calculate monthly emissions (kg CO2eq)
   - Estimate cost savings ($/month)
   - Assess implementation complexity
   - **Output:** ROI estimates

### 📊 Data Structures Produced

```json
{
  "workload": "ml-training-job",
  "status": "NON_COMPLIANT",
  "carbon_status": "NON_COMPLIANT",
  "pue_status": "COMPLIANT",
  "current_carbon_intensity_gCO2eq_kWh": 510,
  "target_carbon_intensity_gCO2eq_kWh": 424,
  "gap_percent": 20.3,
  "recommendation": "⚠️ NON-COMPLIANT: Workload exceeds...",
  "optimizations": [
    {
      "type": "temporal_shift",
      "estimated_reduction_percent": 10,
      "description": "Reschedule to 2am-6am KST"
    }
  ]
}
```

### 🎯 Success Criteria
- ✅ Accurate compliance assessment
- ✅ Clear COMPLIANT/NON_COMPLIANT status
- ✅ Actionable recommendations
- ✅ Korean regulatory focus

---

## Layer 3: Clients (User Interface Layer)

### 🎯 Primary Role
**Multi-Channel Access to Compliance Intelligence**

### 👥 Contributing Roles

| Role | Responsibility | Technology |
|------|----------------|------------|
| **Natural Language Interface** | Accept conversational queries | Claude Desktop (MCP stdio) |
| **HTTP API Consumer** | Programmatic tool access | curl, Python requests |
| **Web UI** | Interactive testing & visualization | FastAPI Swagger UI |
| **Protocol Translator** | Convert requests to JSON-RPC 2.0 | MCP Client Library |

### 🔄 Key Actions

#### **Client 1: Claude Desktop (stdio Transport)**

1. **Natural Language Query Processing**
   - User: "Check if my ml-training-job complies with Korean standards"
   - Claude translates to MCP tool call
   - **Output:** Conversational response with structured data

2. **Interactive Exploration**
   - Follow-up questions
   - Multi-turn dialogue
   - Context retention
   - **Output:** Guided compliance journey

**Example Flow:**
```
User: "Check compliance of heavy-app"
↓
Claude Desktop → MCP Server (assess_workload_compliance)
↓
MCP Response: {status: "NON_COMPLIANT", gap: 20%}
↓
Claude: "Your workload is NON-COMPLIANT by 20%.
         Would you like me to show optimization options?"
```

#### **Client 2: HTTP Clients (HTTP Transport)**

3. **Direct API Calls**
   ```bash
   curl -X POST http://<IP>:30800/tools/assess_workload_compliance \
     -d '{"workload_name": "app", "namespace": "prod"}'
   ```
   - **Output:** JSON response

4. **Programmatic Integration**
   ```python
   import requests
   response = requests.post(
       "http://mcp-server:8000/tools/assess_workload_compliance",
       json={"workload_name": "app", "namespace": "prod"}
   )
   status = response.json()["status"]
   ```
   - **Output:** Integration with CI/CD pipelines

#### **Client 3: FastAPI Web UI (Browser)**

5. **Interactive Testing**
   - Navigate to `/docs`
   - Select tool from dropdown
   - Fill parameters in form
   - Execute and view response
   - **Output:** Visual API exploration

6. **Response Visualization**
   - JSON formatting
   - Schema validation
   - Error messages
   - **Output:** Developer-friendly interface

### 📊 User Interactions

| Client Type | Use Case | Input Format | Output Format |
|-------------|----------|--------------|---------------|
| Claude Desktop | Natural language queries | "Check if app complies" | Conversational + structured data |
| curl/Python | Automation, CI/CD | JSON payload | JSON response |
| Web UI | Testing, debugging | Web form | Formatted JSON |

### 🎯 Success Criteria
- ✅ Multiple access methods (stdio, HTTP, Web)
- ✅ Natural language support via Claude
- ✅ Programmatic API access
- ✅ Interactive web interface

---

## 🔄 End-to-End Data Flow

### Complete Journey: "Is my workload compliant?"

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: User Query                                         │
│ "Check if ml-training-job complies with Korean standards"  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3 → Layer 2: Protocol Translation                    │
│ JSON-RPC 2.0:                                               │
│ {                                                            │
│   "method": "tools/call",                                   │
│   "params": {                                               │
│     "name": "assess_workload_compliance",                   │
│     "arguments": {                                          │
│       "workload_name": "ml-training-job",                   │
│       "namespace": "ai-team",                               │
│       "standard": "KR_CARBON_2050"                          │
│     }                                                        │
│   }                                                          │
│ }                                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2 → Layer 1: Metrics Request                         │
│ HTTP GET https://<IP>:30443/metrics                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: eBPF Collection & Power Estimation                │
│ - eBPF probes collect CPU cycles                           │
│ - Model Server estimates power (45.2W)                     │
│ - Prometheus format: kepler_pod_cpu_watts{...} 45.2        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Compliance Analysis                               │
│ - Parse metrics: 45.2W CPU + 12.3W memory = 57.5W total   │
│ - Calculate carbon: 57.5W × 424 gCO2/kWh = 510 gCO2/kWh   │
│ - Compare: 510 > 424 → NON_COMPLIANT (20% over)           │
│ - Estimate PUE: 1.6 > 1.4 → NON_COMPLIANT (14% over)      │
│ - Generate recommendations                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2 → Layer 3: Structured Response                     │
│ {                                                            │
│   "status": "NON_COMPLIANT",                                │
│   "carbon_status": "NON_COMPLIANT",                         │
│   "pue_status": "NON_COMPLIANT",                            │
│   "current_carbon_intensity_gCO2eq_kWh": 510,               │
│   "target_carbon_intensity_gCO2eq_kWh": 424,                │
│   "gap_percent": 20.3,                                      │
│   "recommendation": "⚠️ NON-COMPLIANT...",                  │
│   "optimizations": [...]                                    │
│ }                                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: User-Friendly Response                            │
│                                                              │
│ "Your ml-training-job is NON-COMPLIANT:                    │
│                                                              │
│  ⚠️  Carbon: 510 gCO2/kWh (20% over 424 target)            │
│  ⚠️  PUE: 1.6 (14% over 1.4 target)                        │
│                                                              │
│  Recommendations:                                           │
│  1. Reschedule to 2am-6am KST → 10% reduction              │
│  2. Right-size CPU 8→6 cores → 15% reduction               │
│  3. Combined effect: COMPLIANT ✓                           │
│                                                              │
│  Estimated savings: 3.6 kg CO2/month, $5.20/month"         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Presentation Summary: Roles by Layer

### **Layer 1: Kepler Monitoring**
**"The Sensor"**
- **Collects** real hardware metrics via eBPF
- **Estimates** power consumption with ML models
- **Publishes** Prometheus metrics

### **Layer 2: Carbon-Aware MCP Server**
**"The Brain"**
- **Analyzes** compliance against Korean standards
- **Calculates** carbon footprint and PUE
- **Recommends** optimizations

### **Layer 3: Clients**
**"The Interface"**
- **Translates** natural language to tool calls
- **Presents** compliance status clearly
- **Enables** multiple access methods

---

## 📊 Key Metrics Flow

```
eBPF Counters → Power (Watts) → Carbon (gCO2/kWh) → Compliance (✅/⚠️)
     ↓              ↓                  ↓                    ↓
  CPU cycles     45.2W              510            NON_COMPLIANT
  Cache miss     12.3W           vs 424              (20% over)
  Memory I/O       ↓                  ↓                    ↓
                 57.5W           Recommendations      Action Plan
```

---

## 🎬 Presentation Talking Points

### Layer 1 Slide
**"Real Metrics, Real Impact"**
- ✅ eBPF-based collection (not simulated)
- ✅ ML power estimation (AWS-compatible)
- ✅ Per-pod granularity

### Layer 2 Slide
**"Korean Regulatory Intelligence"**
- ✅ 탄소중립 녹색성장 기본법 (424 gCO2/kWh)
- ✅ 에너지이용 합리화법 (PUE 1.4)
- ✅ Actionable recommendations

### Layer 3 Slide
**"Ask in Natural Language"**
- ✅ Claude Desktop integration
- ✅ HTTP API for automation
- ✅ Clear COMPLIANT/NON_COMPLIANT status

---

**Total Architecture:** 3 Layers × ~3 Roles each = 9 specialized components working together
