# Kepler v0.11.0 - Energy Monitoring for Kubernetes

This repository contains everything needed to deploy **Kepler** (Kubernetes Efficient Power Level Exporter) v0.11.0 using the official Helm chart for the **Open Source Summit Korea 2025** presentation.

## 📋 What is Kepler?

Kepler is a CNCF Sandbox project that uses eBPF to probe energy-related system stats and exports Prometheus metrics to help users monitor the energy consumption of Kubernetes workloads in real-time.

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (kind, minikube, or production)
- Helm 3.x installed
- kubectl configured

### 1. Download Kepler v0.11.0
```bash
wget https://github.com/sustainable-computing-io/kepler/archive/refs/tags/v0.11.0.tar.gz
tar -xzf v0.11.0.tar.gz
cd kepler-0.11.0
```

### 2. Deploy Kepler (Simple Configuration)
For testing in containerized environments like kind:

```bash
# Use the simple configuration provided
helm install kepler ./manifests/helm/kepler \
  --namespace kepler-system \
  --create-namespace \
  -f kepler-simple.yaml
```

### 3. Verify Installation
```bash
# Check if Kepler pods are running
kubectl get pods -n kepler-system

# Port forward to access metrics
kubectl port-forward -n kepler-system service/kepler 8080:28282 &

# Check Kepler metrics
curl http://localhost:8080/metrics | grep kepler
```

## 📊 Available Metrics

Kepler exposes various energy consumption metrics:
- `kepler_container_cpu_joules_total` - CPU energy consumption per container
- `kepler_container_dram_joules_total` - Memory energy consumption
- `kepler_container_other_joules_total` - Other component energy consumption
- `kepler_node_cpu_joules_total` - Node-level CPU energy consumption

## 📁 Repository Files

- **`kepler-simple.yaml`** - Simple configuration for testing/demo environments
- **`kepler-production.yaml`** - Production-ready configuration with security settings
- **`deployment-guide.md`** - Detailed step-by-step deployment guide
- **`README.md`** - This file with quick start instructions

## 🔧 Configuration Options

### Simple Configuration (Testing)
- Disables Kubernetes integration for compatibility
- Enables fake CPU meter for containerized environments
- Minimal security restrictions

### Production Configuration
- Full Kubernetes integration enabled
- Proper security contexts and privileges
- RBAC and service monitor configurations
- Hardware power monitoring (RAPL) enabled

## 🛠 Troubleshooting

### Common Issues

**1. CrashLoopBackOff in containerized environments**
- Use `kepler-simple.yaml` configuration
- Ensures fake CPU meter is enabled when RAPL is unavailable

**2. Permission denied errors**
- Verify RBAC permissions
- Check security context settings
- Ensure proper node access for system metrics

**3. No metrics available**
- Verify port-forward is working: `kubectl port-forward -n kepler-system service/kepler 8080:28282`
- Check pod logs: `kubectl logs -n kepler-system -l app.kubernetes.io/name=kepler`

## 📚 Additional Resources

- [Kepler Official Documentation](https://sustainable-computing.io/)
- [Kepler GitHub Repository](https://github.com/sustainable-computing-io/kepler)
- [CNCF Kepler Project Page](https://landscape.cncf.io/project=kepler)

## 🎯 Production Considerations

⚠️ **Important**: The simple configuration is designed for testing and demo purposes. For production deployments:

1. Use `kepler-production.yaml` configuration
2. Enable proper security contexts
3. Configure resource limits and requests
4. Set up proper monitoring and alerting
5. Ensure hardware compatibility (RAPL support)

## 🤝 Contributing

This repository is part of the Open Source Summit Korea 2025 presentation. For contributions to Kepler itself, please visit the [official Kepler repository](https://github.com/sustainable-computing-io/kepler).

## 📄 License

This project follows the same license as Kepler - Apache License 2.0. 