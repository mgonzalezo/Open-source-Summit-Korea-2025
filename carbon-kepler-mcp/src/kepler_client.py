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
            cache_ttl=cache_ttl,
            note="Using native Kepler watts metrics (not joules conversion)"
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

    def get_pod_power_watts(
        self,
        pod_name: str,
        namespace: str = "default"
    ) -> Dict[str, float]:
        """
        Get power consumption for a specific pod using native Kepler watts metrics.

        Kepler v0.11.2+ natively exposes watts metrics calculated from RAPL joules.
        This method reads those watts metrics directly - no conversion needed!

        Args:
            pod_name: Pod name
            namespace: Kubernetes namespace

        Returns:
            Dictionary with power metrics in watts:
            - cpu_watts: CPU package power (zone=package)
            - dram_watts: Memory power (zone=dram)
            - total_watts: Total power (CPU + DRAM)
            - measurement_status: Always "active" (native metrics)
        """
        metrics = self.fetch_metrics()

        # Kepler v0.11.2 exposes: kepler_pod_cpu_watts{zone="package"|"dram"}
        labels = {"pod_name": pod_name, "pod_namespace": namespace}

        # Get CPU package power (watts)
        package_labels = {**labels, "zone": "package"}
        cpu_watts = aggregate_metrics(
            metrics, "kepler_pod_cpu_watts", package_labels, "sum"
        )

        # Get DRAM power (watts)
        dram_labels = {**labels, "zone": "dram"}
        dram_watts = aggregate_metrics(
            metrics, "kepler_pod_cpu_watts", dram_labels, "sum"
        )

        # Total power is sum of all zones
        total_watts = cpu_watts + dram_watts

        return {
            "cpu_watts": cpu_watts,
            "dram_watts": dram_watts,
            "total_watts": total_watts,
            "measurement_status": "active"  # Always active with native watts
        }

    def get_node_metrics(self) -> Dict[str, float]:
        """
        Get node-level power metrics using native Kepler watts.

        Kepler v0.11.2+ exposes node-level watts metrics calculated from RAPL.

        Returns:
            Dictionary of node power metrics in watts with zones:
            - cpu_watts_package: CPU socket power
            - cpu_watts_dram: Memory power
            - cpu_watts_total: Total CPU power (package + dram)
        """
        metrics = self.fetch_metrics()

        # Get CPU package power (zone=package)
        package_watts = aggregate_metrics(
            metrics, "kepler_node_cpu_watts", {"zone": "package"}, "sum"
        )

        # Get DRAM power (zone=dram)
        dram_watts = aggregate_metrics(
            metrics, "kepler_node_cpu_watts", {"zone": "dram"}, "sum"
        )

        return {
            "cpu_watts_package": package_watts,
            "cpu_watts_dram": dram_watts,
            "cpu_watts_total": package_watts + dram_watts,
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

