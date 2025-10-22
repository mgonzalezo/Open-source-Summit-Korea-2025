"""
Kepler Client

HTTP client for fetching metrics from Kepler Prometheus endpoint.
Includes caching layer to reduce API calls.
"""

import httpx
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import structlog

from .prometheus_parser import (
    parse_prometheus_text,
    filter_metrics,
    get_metric_value,
    aggregate_metrics,
    PrometheusMetric
)

logger = structlog.get_logger()


class KeplerMetricsCache:
    """Simple time-based cache for Kepler metrics"""

    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[datetime, List[PrometheusMetric]]] = {}

    def get(self, key: str) -> Optional[List[PrometheusMetric]]:
        """Get cached metrics if still valid"""
        if key not in self._cache:
            return None

        timestamp, metrics = self._cache[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
            del self._cache[key]
            return None

        return metrics

    def set(self, key: str, metrics: List[PrometheusMetric]) -> None:
        """Cache metrics with current timestamp"""
        self._cache[key] = (datetime.now(), metrics)

    def clear(self) -> None:
        """Clear all cached data"""
        self._cache.clear()


class KeplerClient:
    """Client for fetching Kepler metrics"""

    def __init__(
        self,
        endpoint: str,
        verify_ssl: bool = False,
        timeout: int = 10,
        cache_ttl: int = 60
    ):
        """
        Initialize Kepler client

        Args:
            endpoint: Kepler metrics endpoint URL (e.g., https://IP:30443/metrics)
            verify_ssl: Verify SSL certificates (default: False for self-signed)
            timeout: HTTP request timeout in seconds
            cache_ttl: Cache time-to-live in seconds
        """
        self.endpoint = endpoint.rstrip('/')
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.cache = KeplerMetricsCache(ttl_seconds=cache_ttl)

        logger.info(
            "kepler_client_initialized",
            endpoint=self.endpoint,
            cache_ttl=cache_ttl
        )

    def fetch_metrics(self, use_cache: bool = True) -> List[PrometheusMetric]:
        """
        Fetch all metrics from Kepler endpoint

        Args:
            use_cache: Use cached metrics if available

        Returns:
            List of PrometheusMetric objects
        """
        cache_key = "all_metrics"

        # Check cache first
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("using_cached_metrics", count=len(cached))
                return cached

        # Fetch from Kepler
        try:
            logger.debug("fetching_kepler_metrics", endpoint=self.endpoint)

            with httpx.Client(verify=self.verify_ssl, timeout=self.timeout) as client:
                response = client.get(self.endpoint)
                response.raise_for_status()

            # Parse Prometheus text format
            metrics = parse_prometheus_text(response.text)

            # Cache results
            self.cache.set(cache_key, metrics)

            logger.info(
                "kepler_metrics_fetched",
                count=len(metrics),
                endpoint=self.endpoint
            )

            return metrics

        except httpx.HTTPError as e:
            logger.error(
                "kepler_fetch_failed",
                error=str(e),
                endpoint=self.endpoint
            )
            raise

    def get_pod_metrics(
        self,
        pod_name: str,
        namespace: str = "default"
    ) -> Dict[str, float]:
        """
        Get metrics for a specific pod (aggregated from container-level RAPL metrics)

        Args:
            pod_name: Pod name
            namespace: Kubernetes namespace

        Returns:
            Dictionary of metric values with joules (cumulative counters)

        Note: RAPL metrics are in joules (counters). To convert to watts:
              watts = (joules_t2 - joules_t1) / (timestamp_t2 - timestamp_t1)
        """
        metrics = self.fetch_metrics()

        # Kepler v0.11.2 with RAPL uses container-level metrics
        # Labels: pod_name, pod_namespace, container_name
        labels = {"pod_name": pod_name, "pod_namespace": namespace}

        return {
            # Total energy (all components: CPU + DRAM + other)
            "total_joules": aggregate_metrics(
                metrics, "kepler_container_joules_total", labels, "sum"
            ),
            # CPU energy only
            "cpu_joules_total": aggregate_metrics(
                metrics, "kepler_container_cpu_joules_total", labels, "sum"
            ),
            # DRAM energy only
            "dram_joules_total": aggregate_metrics(
                metrics, "kepler_container_dram_joules_total", labels, "sum"
            ),
            # Package energy (CPU socket)
            "package_joules_total": aggregate_metrics(
                metrics, "kepler_container_package_joules_total", labels, "sum"
            ),
        }

    def get_namespace_metrics(self, namespace: str = "default") -> Dict[str, float]:
        """
        Get aggregated metrics for all pods in a namespace (from RAPL container metrics)

        Args:
            namespace: Kubernetes namespace

        Returns:
            Dictionary of aggregated metric values in joules (counters)
        """
        metrics = self.fetch_metrics()

        # Kepler v0.11.2 uses pod_namespace label at container level
        labels = {"pod_namespace": namespace}

        return {
            # Total energy across all containers in namespace
            "total_joules": aggregate_metrics(
                metrics, "kepler_container_joules_total", labels, "sum"
            ),
            # CPU energy only
            "cpu_joules_total": aggregate_metrics(
                metrics, "kepler_container_cpu_joules_total", labels, "sum"
            ),
            # DRAM energy only
            "dram_joules_total": aggregate_metrics(
                metrics, "kepler_container_dram_joules_total", labels, "sum"
            ),
            # Pod count in namespace
            "pod_count": len(
                set(m.labels.get("pod_name", "") for m in filter_metrics(metrics, labels=labels))
            ),
        }

    def get_node_metrics(self) -> Dict[str, float]:
        """
        Get node-level RAPL metrics

        Returns:
            Dictionary of node metric values in joules (counters)

        Note: With RAPL, node metrics are cumulative energy counters.
              Kepler exposes RAPL zones at node level.
        """
        metrics = self.fetch_metrics()

        return {
            # Platform/total energy (all RAPL zones combined)
            "platform_joules_total": get_metric_value(
                metrics, "kepler_node_platform_joules_total"
            ),
            # CPU package energy (socket-level)
            "package_joules_total": get_metric_value(
                metrics, "kepler_node_package_joules_total"
            ),
            # CPU core energy
            "core_joules_total": get_metric_value(
                metrics, "kepler_node_core_joules_total"
            ),
            # DRAM energy
            "dram_joules_total": get_metric_value(
                metrics, "kepler_node_dram_joules_total"
            ),
            # Uncore energy (shared components)
            "uncore_joules_total": get_metric_value(
                metrics, "kepler_node_uncore_joules_total"
            ),
        }

    def list_pods(self, namespace: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List all pods with metrics

        Args:
            namespace: Filter by namespace (optional)

        Returns:
            List of pod information dicts
        """
        metrics = self.fetch_metrics()

        # Extract unique pod/namespace combinations
        # Kepler v0.11.2 uses pod_name and pod_namespace labels
        pods = set()
        for metric in metrics:
            if "pod_name" in metric.labels and "pod_namespace" in metric.labels:
                pod_ns = (metric.labels["pod_name"], metric.labels["pod_namespace"])
                if namespace is None or metric.labels["pod_namespace"] == namespace:
                    pods.add(pod_ns)

        return [
            {"pod": pod, "namespace": ns}
            for pod, ns in sorted(pods)
        ]

    def calculate_power_from_energy(
        self,
        energy_joules_t1: float,
        energy_joules_t2: float,
        time_seconds: float
    ) -> float:
        """
        Calculate power (watts) from energy delta over time

        Args:
            energy_joules_t1: Energy at time t1 (joules)
            energy_joules_t2: Energy at time t2 (joules)
            time_seconds: Time interval between measurements (seconds)

        Returns:
            Average power consumption in watts

        Formula: watts = (joules_t2 - joules_t1) / time_seconds
        """
        if time_seconds <= 0:
            logger.warning("calculate_power_invalid_time", time_seconds=time_seconds)
            return 0.0

        energy_delta = energy_joules_t2 - energy_joules_t1

        if energy_delta < 0:
            logger.warning(
                "calculate_power_negative_delta",
                t1=energy_joules_t1,
                t2=energy_joules_t2
            )
            return 0.0

        watts = energy_delta / time_seconds
        logger.debug(
            "power_calculated",
            energy_delta_joules=energy_delta,
            time_seconds=time_seconds,
            watts=watts
        )

        return watts

    def get_total_power(self, namespace: Optional[str] = None) -> Dict[str, float]:
        """
        Get total energy consumption in joules (counters)

        Note: This returns joules, not watts. To get watts, you need to:
        1. Call this method twice with a time interval
        2. Use calculate_power_from_energy() to convert to watts

        Args:
            namespace: Limit to specific namespace (optional)

        Returns:
            Dictionary with energy metrics in joules
        """
        if namespace:
            return self.get_namespace_metrics(namespace)
        else:
            return self.get_node_metrics()
