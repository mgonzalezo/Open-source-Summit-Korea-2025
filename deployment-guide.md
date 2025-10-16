# Kepler v0.11.0 Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Configuration Options](#configuration-options)
5. [Verification and Testing](#verification-and-testing)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)
8. [Limitations and Considerations](#limitations-and-considerations)

## Overview

Kepler (Kubernetes Efficient Power Level Exporter) is a CNCF Sandbox project that monitors energy consumption in Kubernetes clusters using eBPF technology. This guide covers deploying Kepler v0.11.0 using the official Helm chart.

### Key Features
- **Real-time energy monitoring** of containers, pods, and nodes
- **eBPF-based** system stats collection
- **Prometheus metrics** export
- **Kubernetes-native** deployment
- **Hardware power monitoring** (RAPL support)

## Prerequisites

### System Requirements
- **Operating System**: Linux (kernel 4.18+ for eBPF support)
- **Kubernetes**: v1.20+ (tested with v1.31.0)
- **Helm**: v3.x
- **Docker**: v20.x+ or compatible container runtime

### Hardware Requirements
- **For testing**: Any Linux system with containerization support
- **For production**: Bare-metal nodes with Intel/AMD processors supporting RAPL

### Tools Installation

```bash
# Install kubectl (if not already installed)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (if not already installed)
curl https://get.helm.sh/helm-v3.13.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# Verify installations
kubectl version --client
helm version
```

## Installation Steps

### Step 1: Download Kepler v0.11.0

```bash
# Download the official release
wget https://github.com/sustainable-computing-io/kepler/archive/refs/tags/v0.11.0.tar.gz

# Extract the archive
tar -xzf v0.11.0.tar.gz
cd kepler-0.11.0

# Verify the Helm chart exists
ls manifests/helm/kepler/
```

### Step 2: Choose Configuration

#### For Testing/Demo (Containerized environments like kind, minikube)
```bash
# Use the simple configuration
cp /path/to/kepler-simple.yaml .
```

#### For Production (Bare-metal clusters)
```bash
# Use the production configuration
cp /path/to/kepler-production.yaml .
```

### Step 3: Deploy Kepler

#### Testing Deployment
```bash
# Deploy with simple configuration
helm install kepler ./manifests/helm/kepler \
  --namespace kepler-system \
  --create-namespace \
  -f kepler-simple.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=kepler -n kepler-system --timeout=300s
```

#### Production Deployment
```bash
# Deploy with production configuration
helm install kepler ./manifests/helm/kepler \
  --namespace kepler-system \
  --create-namespace \
  -f kepler-production.yaml

# Monitor deployment
kubectl get pods -n kepler-system -w
```

### Step 4: Verify Installation

```bash
# Check pod status
kubectl get pods -n kepler-system

# Check logs
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler

# Port forward to access metrics
kubectl port-forward -n kepler-system service/kepler 8080:28282 &

# Test metrics endpoint
curl -s http://localhost:8080/metrics | head -20
```

## Configuration Options

### Simple Configuration (kepler-simple.yaml)
- **Use case**: Testing, demos, containerized environments
- **Kubernetes integration**: Disabled for compatibility
- **Fake CPU meter**: Enabled when hardware monitoring unavailable
- **Security**: Minimal restrictions
- **Resource usage**: Conservative limits

### Production Configuration (kepler-production.yaml)
- **Use case**: Production bare-metal clusters
- **Kubernetes integration**: Fully enabled
- **Hardware monitoring**: RAPL zones configured
- **Security**: Comprehensive security contexts and RBAC
- **Monitoring**: Prometheus ServiceMonitor enabled
- **Reliability**: Health checks and disruption budgets

## Verification and Testing

### 1. Pod Health Check
```bash
# Verify all pods are running
kubectl get pods -n kepler-system

# Expected output:
# NAME           READY   STATUS    RESTARTS   AGE
# kepler-xxxxx   1/1     Running   0          2m
```

### 2. Metrics Verification
```bash
# Port forward to metrics endpoint
kubectl port-forward -n kepler-system service/kepler 8080:28282 &

# Check available metrics
curl -s http://localhost:8080/metrics | grep kepler | head -10

# Key metrics to look for:
# - kepler_container_cpu_joules_total
# - kepler_container_dram_joules_total  
# - kepler_node_cpu_joules_total
```

### 3. Log Analysis
```bash
# Check for any errors
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler | grep -i error

# Monitor real-time logs
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler -f
```

## Production Deployment

### Security Considerations

1. **RBAC Permissions**
   - Minimal required permissions for node and pod access
   - Separate service account with specific roles

2. **Security Contexts**
   - Privileged access required for hardware monitoring
   - Read-only root filesystem where possible
   - Capability restrictions

3. **Network Security**
   - TLS configuration for metrics endpoint
   - Network policies for traffic isolation

### Monitoring Integration

#### Prometheus Integration
```yaml
# ServiceMonitor for Prometheus Operator
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kepler
  namespace: kepler-system
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: kepler
  endpoints:
  - port: http-metrics
    interval: 30s
    path: /metrics
```

#### Grafana Dashboard
- Import dashboard ID: 15174 (Kepler Energy Dashboard)
- Configure data source to point to your Prometheus instance

### Resource Planning

#### Cluster Sizing
- **CPU**: 200m request, 1000m limit per node
- **Memory**: 256Mi request, 1Gi limit per node
- **Storage**: Minimal (metrics are exported, not stored)

#### Scaling Considerations
- DaemonSet runs one pod per node
- Resource usage scales linearly with node count
- Network bandwidth for metrics export

## Troubleshooting

### Common Issues

#### 1. CrashLoopBackOff in Containerized Environments
**Symptoms**: Pods restart continuously
**Cause**: RAPL hardware monitoring unavailable in containers
**Solution**: Use `kepler-simple.yaml` with fake CPU meter enabled

```bash
# Check if using correct configuration
kubectl get configmap kepler -n kepler-system -o yaml | grep fake-cpu-meter
```

#### 2. Permission Denied Errors
**Symptoms**: Logs show permission errors accessing `/proc` or `/sys`
**Cause**: Insufficient security context or volume mounts
**Solution**: Verify security context and volume mounts

```bash
# Check security context
kubectl get daemonset kepler -n kepler-system -o yaml | grep -A 10 securityContext

# Verify volume mounts
kubectl describe pod -n kepler-system -l app.kubernetes.io/name=kepler
```

#### 3. No Metrics Available
**Symptoms**: `/metrics` endpoint returns empty or minimal data
**Cause**: Monitoring components not initialized properly
**Solutions**:

```bash
# Check if fake CPU meter is enabled (for testing)
kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler | grep "fake-cpu-meter"

# Verify RAPL availability (for production)
kubectl exec -n kepler-system -l app.kubernetes.io/name=kepler -- ls -la /sys/class/powercap/
```

#### 4. High Resource Usage
**Symptoms**: High CPU/memory consumption
**Cause**: Aggressive monitoring intervals or debug logging
**Solutions**:

```bash
# Check current configuration
kubectl get configmap kepler -n kepler-system -o yaml

# Adjust monitoring interval if needed
# Edit ConfigMap to increase interval from 3s to 5s or 10s
```

### Debug Commands

```bash
# Get detailed pod information
kubectl describe pod -n kepler-system -l app.kubernetes.io/name=kepler

# Check events
kubectl get events -n kepler-system --sort-by=.metadata.creationTimestamp

# Exec into pod for debugging
kubectl exec -it -n kepler-system -l app.kubernetes.io/name=kepler -- /bin/sh

# Check system capabilities
kubectl exec -n kepler-system -l app.kubernetes.io/name=kepler -- cat /proc/self/status | grep Cap
```

## Limitations and Considerations

### Testing Environment Limitations

1. **No Real Power Monitoring**: Containerized environments (kind, minikube) cannot access hardware power monitoring features
2. **Fake Metrics**: Uses simulated CPU meter for demonstration purposes
3. **Limited Accuracy**: Energy estimates may not reflect real hardware consumption

### Production Environment Requirements

1. **Bare-Metal Nodes**: Requires direct hardware access for RAPL monitoring
2. **Privileged Access**: Needs privileged containers and host system access
3. **Hardware Compatibility**: 
   - Intel processors with RAPL support
   - AMD processors with equivalent power monitoring
   - ARM processors have limited support

### Security Implications

1. **Privileged Containers**: Required for hardware monitoring poses security risks
2. **Host System Access**: Mounts sensitive host directories (`/proc`, `/sys`)
3. **Root Privileges**: Runs as root user for system-level access

### Platform Compatibility

| Platform | Support Level | Notes |
|----------|---------------|-------|
| Bare-metal Intel/AMD |  Full | Complete RAPL support |
| Cloud VMs (AWS, GCP, Azure) | ️ Limited | No direct hardware access |
| ARM64 | ️ Limited | Basic support, limited power monitoring |
| Containerized (kind, minikube) |  Testing only | Fake CPU meter for demo |

### Performance Impact

- **Minimal overhead**: eBPF-based monitoring with low system impact
- **Configurable intervals**: Adjust monitoring frequency based on requirements
- **Resource usage**: Scales with cluster size and monitoring frequency

## Best Practices

### For Testing
1. Use `kepler-simple.yaml` configuration
2. Enable fake CPU meter for demonstration
3. Monitor resource usage during testing
4. Test with various workload types

### For Production
1. Start with pilot deployment on subset of nodes
2. Monitor system performance impact
3. Configure appropriate resource limits
4. Set up comprehensive monitoring and alerting
5. Regular security audits of privileged access
6. Plan for updates and maintenance windows

### Monitoring and Observability
1. Set up Prometheus alerts for pod health
2. Monitor resource consumption trends
3. Create dashboards for energy consumption patterns
4. Regular log analysis for errors or warnings

---

## Support and Resources

- **Official Documentation**: [https://sustainable-computing.io/](https://sustainable-computing.io/)
- **GitHub Repository**: [https://github.com/sustainable-computing-io/kepler](https://github.com/sustainable-computing-io/kepler)
- **CNCF Project Page**: [https://landscape.cncf.io/project=kepler](https://landscape.cncf.io/project=kepler)
- **Community Slack**: Join CNCF Slack and find #kepler channel 