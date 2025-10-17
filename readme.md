# Kepler - Kubernetes Efficient Power Level Exporter

Energy monitoring for Kubernetes workloads using eBPF technology.

**Open Source Summit Korea 2025**

##  What is Kepler?

Kepler (Kubernetes Efficient Power Level Exporter) is a CNCF Sandbox project that uses eBPF to probe energy-related system stats and exports Prometheus metrics to help you monitor the energy consumption of Kubernetes workloads in real-time.

### Key Features

- **Real-time Energy Monitoring** - Track power consumption of containers, pods, and nodes
- **eBPF-based** - Low-overhead system stats collection
- **Prometheus Integration** - Export metrics for visualization and alerting
- **Hardware Support** - RAPL (Running Average Power Limit) for accurate measurements on bare-metal
- **Model-based Estimation** - Power estimates for virtualized environments

### Architecture

```
┌─────────────────────────────────────────────────┐
│           Kubernetes Cluster                    │
├─────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐   │
│  │  Kepler DaemonSet (runs on each node)    │   │
│  │  ┌────────────────────────────────────┐  │   │
│  │  │  eBPF Probes                       │  │   │
│  │  │  - CPU cycles                      │  │   │
│  │  │  - Memory access                   │  │   │
│  │  │  - Network I/O                     │  │   │
│  │  └────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────┐  │   │
│  │  │  Power Monitoring                  │  │   │
│  │  │  - RAPL (bare-metal)               │  │   │
│  │  │  - Model estimation (VM)           │  │   │
│  │  └────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────┐  │   │
│  │  │  Prometheus Exporter :28282        │  │   │
│  │  └────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  Prometheus → Grafana → Dashboards              │
└──────────────────────────────────────────────────┘
```

##  Quick Start

### Prerequisites

- **Kubernetes cluster** (Kind, minikube, or production)
- **Helm 3.x** installed
- **kubectl** configured
- **cert-manager** v1.18.0+ (for Kepler Operator)

### Option 1: Local Kind Cluster (Recommended for Testing)

Create a Kind cluster optimized for Kepler:

```bash
# Install Kind (if not already installed)
curl -Lo scripts/kind https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64
chmod +x scripts/kind
sudo mv scripts/kind /usr/local/bin/kind

# Create Kind cluster with host mounts for system access
cat <<EOF | kind create cluster --name kepler-demo --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraMounts:
  - hostPath: /sys
    containerPath: /sys
    readOnly: true
  - hostPath: /proc
    containerPath: /proc
    readOnly: true
EOF

# Wait for cluster to be ready
kubectl wait --for=condition=ready node --all --timeout=300s
```

### Option 2: Existing Kubernetes Cluster

If you already have a cluster, ensure you have proper access:

```bash
kubectl cluster-info
kubectl get nodes
```

### Install Kepler

#### Method 1: Using Kepler Operator (Recommended)

```bash
# 1. Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.18.2/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=300s

# 2. Install Kepler Operator
helm install kepler-operator \
  oci://quay.io/sustainable_computing_io/charts/kepler-operator \
  --namespace kepler-operator \
  --create-namespace \
  --wait

# 3. Verify installation
kubectl get pods -n kepler-operator
```

#### Method 2: Using Helm Chart Directly

For testing in containerized environments (like Kind):

```bash
# Download Kepler v0.11.0
wget https://github.com/sustainable-computing-io/kepler/archive/refs/tags/v0.11.0.tar.gz
tar -xzf v0.11.0.tar.gz
cd kepler-0.11.0

# Install using simple configuration
helm install kepler scripts/manifests/helm/kepler \
  --namespace kepler-system \
  --create-namespace \
  -f .scripts/kepler-simple.yaml
```

### Verify Installation

```bash
# Check if Kepler pods are running
kubectl get pods -n kepler-operator
# or for direct Helm installation:
kubectl get pods -n kepler-system

# Port forward to access metrics
kubectl port-forward -n kepler-operator svc/kepler-operator 28282:28282 &
# or for direct Helm installation:
kubectl port-forward -n kepler-system service/kepler 28282:28282 &

# Check Kepler metrics
curl http://localhost:28282/metrics | grep kepler
```

##  Available Metrics

Kepler exposes energy consumption metrics via Prometheus:

### Container-level Metrics
- `kepler_container_cpu_joules_total` - CPU energy consumption per container
- `kepler_container_dram_joules_total` - Memory energy consumption per container
- `kepler_container_other_joules_total` - Other component energy per container
- `kepler_container_gpu_joules_total` - GPU energy consumption per container (if available)

### Node-level Metrics
- `kepler_node_cpu_joules_total` - Node CPU energy consumption
- `kepler_node_dram_joules_total` - Node memory energy consumption
- `kepler_node_other_joules_total` - Other node component energy
- `kepler_node_platform_joules_total` - Total platform energy

### Process-level Metrics
- `kepler_process_cpu_joules_total` - CPU energy per process
- `kepler_process_dram_joules_total` - Memory energy per process

### Example Queries

```bash
# Total energy consumption by namespace
curl http://localhost:28282/metrics | grep 'kepler_container.*joules_total' | grep 'namespace="default"'

# Node-level power consumption
curl http://localhost:28282/metrics | grep 'kepler_node.*joules_total'
```

##  Configuration

### For Testing/Demo Environments (Kind, minikube)

Use **kepler-simple.yaml** configuration:
- Disables Kubernetes integration for compatibility
- Enables fake CPU meter when RAPL unavailable
- Minimal security restrictions
- Lower resource limits

### For Production Environments

Use **kepler-production.yaml** configuration:
- Full Kubernetes integration enabled
- Proper security contexts and privileges
- RBAC and ServiceMonitor for Prometheus
- Hardware power monitoring (RAPL) enabled
- Health checks and disruption budgets

## ️ AWS Bare-Metal Deployment

For **real hardware power monitoring (RAPL)** on AWS bare-metal instances:

** See [aws-deployment/](aws-deployment/) folder**

Features:
- Automated CloudFormation deployment
- c5.metal instance with real RAPL support
- Pre-configured Kind cluster
- Cost management scripts
- ~$4-6/hour (~84 hours with $344 credits)

Quick start:
```bash
cd aws-deployment/scripts
scripts/create-stack.sh
```

##  Repository Structure

```
.
├── README.md                   # This file - Kepler basics and setup
├── kepler-simple.yaml          # Config for testing/demo environments
├── kepler-production.yaml      # Config for production environments
├── deployment-guide.md         # Detailed manual deployment guide
│
└── aws-deployment/             # AWS bare-metal deployment
    ├── README.md              # Complete AWS deployment guide
    ├── QUICKSTART.md          # 15-minute quick start
    ├── scripts/               # Management scripts
    └── templates/             # CloudFormation templates
```

##  Troubleshooting

### Common Issues

**1. CrashLoopBackOff in containerized environments**
- **Cause:** RAPL hardware monitoring unavailable in containers
- **Solution:** Use `kepler-simple.yaml` with fake CPU meter enabled

**2. Permission denied errors**
- **Cause:** Insufficient security context or volume mounts
- **Solution:** Verify security context and ensure proper host path mounts

**3. No metrics available**
- **Cause:** Service not accessible or monitoring not initialized
- **Solution:**
  ```bash
  # Check pod logs
  kubectl logs -n kepler-operator -l app.kubernetes.io/name=kepler-operator

  # Verify port-forward
  kubectl port-forward -n kepler-operator svc/kepler-operator 28282:28282

  # Test metrics endpoint
  curl http://localhost:28282/metrics
  ```

**4. High resource usage**
- **Cause:** Aggressive monitoring intervals or debug logging
- **Solution:** Adjust monitoring interval in configuration (increase from 3s to 5s or 10s)

### Debug Commands

```bash
# Get detailed pod information
kubectl describe pod -n kepler-operator -l app.kubernetes.io/name=kepler-operator

# Check events
kubectl get events -n kepler-operator --sort-by=.metadata.creationTimestamp

# Check if RAPL is available (on bare-metal only)
kubectl exec -n kepler-operator -l app.kubernetes.io/name=kepler-operator -- ls -la /sys/class/powercap/
```

##  Visualization with Grafana

### Import Kepler Dashboard

1. **Install Grafana** (if not already installed):
   ```bash
   helm repo add grafana https://grafana.github.io/helm-charts
   helm install grafana grafana/grafana --namespace monitoring --create-namespace
   ```

2. **Access Grafana**:
   ```bash
   kubectl port-forward -n monitoring svc/grafana 3000:80
   ```
   Default credentials: admin / (get password with below command)
   ```bash
   kubectl get secret --namespace monitoring grafana -o jsonpath="{.data.admin-password}" | base64 --decode
   ```

3. **Import Kepler Dashboard**:
   - Dashboard ID: **15174** (Kepler Energy Dashboard)
   - Or import from: https://grafana.com/grafana/dashboards/15174

##  Use Cases

### 1. Cost Optimization
Monitor energy consumption to identify power-hungry workloads and optimize resource allocation.

### 2. Sustainability Reporting
Track and report on the carbon footprint of your Kubernetes workloads.

### 3. Capacity Planning
Understand power requirements for scaling decisions and infrastructure planning.

### 4. Anomaly Detection
Detect unusual power consumption patterns that may indicate issues or inefficiencies.

##  Additional Resources

### Kepler Documentation
- [Official Website](https://sustainable-computing.io/)
- [GitHub Repository](https://github.com/sustainable-computing-io/kepler)
- [CNCF Project Page](https://landscape.cncf.io/project=kepler)
- [Kepler Slack Channel](https://cloud-native.slack.com/archives/C05V82F7PPF)

### Related Projects
- [Prometheus](https://prometheus.io/) - Metrics collection
- [Grafana](https://grafana.com/) - Visualization
- [cert-manager](https://cert-manager.io/) - Certificate management
- [Kind](https://kind.sigs.k8s.io/) - Local Kubernetes clusters

### Research Papers
- [Kepler: A Framework for Kubernetes Energy Metrics](https://arxiv.org/abs/2303.03187)
- [Sustainable Computing](https://www.sustainable-computing.io/research/)

##  Contributing

This repository contains Kepler deployment configurations and Carbon-Aware MCP server implementation.

For contributions to Kepler itself, please visit:
- [Kepler GitHub Repository](https://github.com/sustainable-computing-io/kepler)
- [Kepler Community Guide](https://sustainable-computing.io/community/)

##  License

This project follows the same license as Kepler - **Apache License 2.0**

##  Documentation

**Questions?** Check the [deployment-guide.md](deployment-guide.md) for detailed instructions or the [aws-deployment/](aws-deployment/) folder for AWS-specific setup.
