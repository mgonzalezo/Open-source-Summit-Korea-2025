"""
Prometheus Metrics Parser

Parses Prometheus text exposition format from Kepler metrics endpoint.
"""

import re
from typing import Dict, List, Optional, Any


class PrometheusMetric:
    """Represents a single Prometheus metric"""

    def __init__(self, name: str, labels: Dict[str, str], value: float, timestamp: Optional[int] = None):
        self.name = name
        self.labels = labels
        self.value = value
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return f"PrometheusMetric(name='{self.name}', labels={self.labels}, value={self.value})"


def parse_prometheus_text(text: str) -> List[PrometheusMetric]:
    """
    Parse Prometheus text exposition format

    Example input (RAPL joules metrics):
        # HELP kepler_container_joules_total Total energy consumed by container (joules)
        # TYPE kepler_container_joules_total counter
        kepler_container_joules_total{pod_name="nginx",pod_namespace="default",container_name="nginx"} 33800.45
        kepler_container_cpu_joules_total{pod_name="nginx",pod_namespace="default",container_name="nginx"} 25400.32
        kepler_container_dram_joules_total{pod_name="nginx",pod_namespace="default",container_name="nginx"} 8400.13

    Args:
        text: Prometheus text format metrics

    Returns:
        List of PrometheusMetric objects
    """
    metrics = []

    for line in text.strip().split('\n'):
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue

        # Parse metric line
        metric = _parse_metric_line(line)
        if metric:
            metrics.append(metric)

    return metrics


def _parse_metric_line(line: str) -> Optional[PrometheusMetric]:
    """
    Parse a single metric line

    Format: metric_name{label1="value1",label2="value2"} value [timestamp]
    """
    # Regex pattern to match metric lines
    # Handles both with and without labels
    pattern = r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(\{[^}]*\})?\s+([^\s]+)(?:\s+(\d+))?$'

    match = re.match(pattern, line)
    if not match:
        return None

    metric_name = match.group(1)
    labels_str = match.group(2)
    value_str = match.group(3)
    timestamp_str = match.group(4)

    # Parse labels
    labels = {}
    if labels_str:
        labels = _parse_labels(labels_str)

    # Parse value
    try:
        value = float(value_str)
    except ValueError:
        # Handle special values
        if value_str == "NaN":
            value = float('nan')
        elif value_str == "+Inf":
            value = float('inf')
        elif value_str == "-Inf":
            value = float('-inf')
        else:
            return None

    # Parse timestamp
    timestamp = int(timestamp_str) if timestamp_str else None

    return PrometheusMetric(metric_name, labels, value, timestamp)


def _parse_labels(labels_str: str) -> Dict[str, str]:
    """
    Parse label string

    Example: {pod="app",namespace="default"}
    """
    labels = {}

    # Remove curly braces
    labels_str = labels_str.strip('{}')

    if not labels_str:
        return labels

    # Split by comma (but not inside quotes)
    label_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"'
    matches = re.findall(label_pattern, labels_str)

    for key, value in matches:
        labels[key] = value

    return labels


def filter_metrics(
    metrics: List[PrometheusMetric],
    name: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None
) -> List[PrometheusMetric]:
    """
    Filter metrics by name and labels

    Args:
        metrics: List of metrics to filter
        name: Metric name to filter by (optional)
        labels: Labels to filter by (optional)

    Returns:
        Filtered list of metrics
    """
    filtered = metrics

    # Filter by name
    if name:
        filtered = [m for m in filtered if m.name == name]

    # Filter by labels
    if labels:
        filtered = [
            m for m in filtered
            if all(m.labels.get(k) == v for k, v in labels.items())
        ]

    return filtered


def get_metric_value(
    metrics: List[PrometheusMetric],
    name: str,
    labels: Optional[Dict[str, str]] = None,
    default: float = 0.0
) -> float:
    """
    Get a single metric value

    Args:
        metrics: List of metrics
        name: Metric name
        labels: Labels to match (optional)
        default: Default value if not found

    Returns:
        Metric value or default
    """
    filtered = filter_metrics(metrics, name=name, labels=labels)

    if not filtered:
        return default

    # Return first match
    return filtered[0].value


def aggregate_metrics(
    metrics: List[PrometheusMetric],
    name: str,
    labels: Optional[Dict[str, str]] = None,
    aggregation: str = "sum"
) -> float:
    """
    Aggregate metrics by name and labels

    Args:
        metrics: List of metrics
        name: Metric name
        labels: Labels to filter by (optional)
        aggregation: Aggregation method (sum, avg, min, max)

    Returns:
        Aggregated value
    """
    filtered = filter_metrics(metrics, name=name, labels=labels)

    if not filtered:
        return 0.0

    values = [m.value for m in filtered]

    if aggregation == "sum":
        return sum(values)
    elif aggregation == "avg":
        return sum(values) / len(values)
    elif aggregation == "min":
        return min(values)
    elif aggregation == "max":
        return max(values)
    else:
        raise ValueError(f"Unknown aggregation method: {aggregation}")


def metrics_to_dict(metrics: List[PrometheusMetric]) -> Dict[str, Any]:
    """
    Convert metrics to a dictionary for easier access

    Returns a nested dictionary:
    {
        "metric_name": {
            "pod=app,namespace=default": value,
            ...
        }
    }
    """
    result = {}

    for metric in metrics:
        if metric.name not in result:
            result[metric.name] = {}

        # Create label key
        label_key = ",".join(f"{k}={v}" for k, v in sorted(metric.labels.items()))
        if not label_key:
            label_key = "_"

        result[metric.name][label_key] = metric.value

    return result
