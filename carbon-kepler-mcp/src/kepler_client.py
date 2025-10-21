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
        Get metrics for a specific pod

        Args:
            pod_name: Pod name
            namespace: Kubernetes namespace

        Returns:
            Dictionary of metric values
        """
        metrics = self.fetch_metrics()

        # Kepler v0.11.2 uses pod_name and pod_namespace labels
        labels = {"pod_name": pod_name, "pod_namespace": namespace}

        return {
            "cpu_watts": get_metric_value(metrics, "kepler_pod_cpu_watts", labels),
            "cpu_joules_total": get_metric_value(metrics, "kepler_pod_cpu_joules_total", labels),
            # Note: Kepler v0.11.2 only exposes CPU metrics at pod level
            # Memory, GPU, and other metrics are only available at container level
        }

    def get_namespace_metrics(self, namespace: str = "default") -> Dict[str, float]:
        """
        Get aggregated metrics for all pods in a namespace

        Args:
            namespace: Kubernetes namespace

        Returns:
            Dictionary of aggregated metric values
        """
        metrics = self.fetch_metrics()

        # Kepler v0.11.2 uses pod_namespace label
        labels = {"pod_namespace": namespace}

        return {
            "total_cpu_watts": aggregate_metrics(
                metrics, "kepler_pod_cpu_watts", labels, "sum"
            ),
            # Note: Only CPU metrics available at pod level in Kepler v0.11.2
            "pod_count": len(
                set(m.labels.get("pod_name", "") for m in filter_metrics(metrics, labels=labels))
            ),
        }

    def get_node_metrics(self) -> Dict[str, float]:
        """
        Get node-level metrics

        Returns:
            Dictionary of node metric values
        """
        metrics = self.fetch_metrics()

        return {
            "cpu_watts": get_metric_value(metrics, "kepler_node_cpu_watts"),
            "cpu_active_watts": get_metric_value(metrics, "kepler_node_cpu_active_watts"),
            "cpu_idle_watts": get_metric_value(metrics, "kepler_node_cpu_idle_watts"),
            "cpu_usage_ratio": get_metric_value(metrics, "kepler_node_cpu_usage_ratio"),
            "cpu_joules_total": get_metric_value(metrics, "kepler_node_cpu_joules_total"),
            # Note: Kepler v0.11.2 on AWS c5.metal only exposes CPU metrics
            # Memory and GPU metrics require hardware support (RAPL, NVIDIA, etc.)
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

    def get_total_power(self, namespace: Optional[str] = None) -> float:
        """
        Get total power consumption

        Args:
            namespace: Limit to specific namespace (optional)

        Returns:
            Total power in watts
        """
        if namespace:
            ns_metrics = self.get_namespace_metrics(namespace)
            # Kepler v0.11.2 only provides CPU watts at pod level
            return ns_metrics.get("total_cpu_watts", 0.0)
        else:
            node_metrics = self.get_node_metrics()
            # Return total node CPU power
            return node_metrics.get("cpu_watts", 0.0)
