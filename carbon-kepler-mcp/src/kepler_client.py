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

        # Power measurement cache: stores (timestamp, joules) for power calculation
        # Key format: "pod:{namespace}/{pod_name}" or "namespace:{namespace}"
        self._power_measurement_cache: Dict[str, tuple[datetime, float]] = {}

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

        # Kepler v0.11.2 with RAPL uses pod-level metrics with zone labels
        # Metrics: kepler_pod_cpu_joules_total{zone="package"|"dram"}
        labels = {"pod_name": pod_name, "pod_namespace": namespace}

        # Get package (CPU) energy
        package_labels = {**labels, "zone": "package"}
        package_joules = aggregate_metrics(
            metrics, "kepler_pod_cpu_joules_total", package_labels, "sum"
        )

        # Get DRAM energy
        dram_labels = {**labels, "zone": "dram"}
        dram_joules = aggregate_metrics(
            metrics, "kepler_pod_cpu_joules_total", dram_labels, "sum"
        )

        # Total is sum of all zones
        total_joules = package_joules + dram_joules

        return {
            # Total energy (sum of all zones)
            "total_joules": total_joules,
            # CPU package energy (socket)
            "cpu_joules_total": package_joules,
            # DRAM energy
            "dram_joules_total": dram_joules,
            # Package energy (same as cpu_joules_total for compatibility)
            "package_joules_total": package_joules,
        }

    def get_pod_power_watts(
        self,
        pod_name: str,
        namespace: str = "default",
        measurement_interval_seconds: float = 5.0
    ) -> Dict[str, float]:
        """
        Get pod power consumption in watts by calculating delta from previous measurement.

        This method stores the previous joule measurement and calculates power by:
        watts = (joules_t2 - joules_t1) / (time_t2 - time_t1)

        On first call for a pod, it returns 0.0 and stores the measurement.
        On subsequent calls, it returns the calculated power.

        Args:
            pod_name: Pod name
            namespace: Kubernetes namespace
            measurement_interval_seconds: Minimum interval between measurements (default: 5s)

        Returns:
            Dictionary with power metrics in watts:
            - cpu_watts: CPU power consumption
            - dram_watts: DRAM power consumption
            - total_watts: Total power (CPU + DRAM)
        """
        cache_key = f"pod:{namespace}/{pod_name}"
        current_time = datetime.now()

        # Get current energy measurement
        current_metrics = self.get_pod_metrics(pod_name, namespace)
        current_total_joules = current_metrics.get("total_joules", 0.0)
        current_cpu_joules = current_metrics.get("cpu_joules_total", 0.0)
        current_dram_joules = current_metrics.get("dram_joules_total", 0.0)

        # Check if we have a previous measurement
        if cache_key not in self._power_measurement_cache:
            # First measurement - store and return 0
            self._power_measurement_cache[cache_key] = (
                current_time,
                {
                    "total_joules": current_total_joules,
                    "cpu_joules": current_cpu_joules,
                    "dram_joules": current_dram_joules
                }
            )
            logger.debug(
                "power_first_measurement",
                pod=pod_name,
                namespace=namespace,
                joules=current_total_joules
            )
            return {
                "cpu_watts": 0.0,
                "dram_watts": 0.0,
                "total_watts": 0.0,
                "measurement_status": "initializing"
            }

        # Get previous measurement
        prev_time, prev_metrics = self._power_measurement_cache[cache_key]
        time_delta_seconds = (current_time - prev_time).total_seconds()

        # Check if enough time has elapsed
        if time_delta_seconds < measurement_interval_seconds:
            logger.debug(
                "power_measurement_too_soon",
                pod=pod_name,
                elapsed=time_delta_seconds,
                required=measurement_interval_seconds
            )
            # Return cached calculation or 0 if too soon
            return {
                "cpu_watts": 0.0,
                "dram_watts": 0.0,
                "total_watts": 0.0,
                "measurement_status": "waiting_for_interval"
            }

        # Calculate power from energy delta
        prev_total_joules = prev_metrics["total_joules"]
        prev_cpu_joules = prev_metrics["cpu_joules"]
        prev_dram_joules = prev_metrics["dram_joules"]

        total_watts = self.calculate_power_from_energy(
            prev_total_joules,
            current_total_joules,
            time_delta_seconds
        )

        cpu_watts = self.calculate_power_from_energy(
            prev_cpu_joules,
            current_cpu_joules,
            time_delta_seconds
        )

        dram_watts = self.calculate_power_from_energy(
            prev_dram_joules,
            current_dram_joules,
            time_delta_seconds
        )

        # Update cache with current measurement
        self._power_measurement_cache[cache_key] = (
            current_time,
            {
                "total_joules": current_total_joules,
                "cpu_joules": current_cpu_joules,
                "dram_joules": current_dram_joules
            }
        )

        logger.debug(
            "power_calculated_for_pod",
            pod=pod_name,
            namespace=namespace,
            total_watts=total_watts,
            cpu_watts=cpu_watts,
            dram_watts=dram_watts,
            time_delta=time_delta_seconds
        )

        return {
            "cpu_watts": cpu_watts,
            "dram_watts": dram_watts,
            "total_watts": total_watts,
            "measurement_status": "active"
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

        # Kepler v0.11.2 uses pod_namespace label at pod level with zones
        labels = {"pod_namespace": namespace}

        # Get package (CPU) energy across all pods
        package_labels = {**labels, "zone": "package"}
        package_joules = aggregate_metrics(
            metrics, "kepler_pod_cpu_joules_total", package_labels, "sum"
        )

        # Get DRAM energy across all pods
        dram_labels = {**labels, "zone": "dram"}
        dram_joules = aggregate_metrics(
            metrics, "kepler_pod_cpu_joules_total", dram_labels, "sum"
        )

        return {
            # Total energy across all pods in namespace
            "total_joules": package_joules + dram_joules,
            # CPU energy only
            "cpu_joules_total": package_joules,
            # DRAM energy only
            "dram_joules_total": dram_joules,
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
