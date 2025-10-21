"""
Power Hotspot Detection and Preventive Action Tools

Inspired by Kepler PR #2250, these tools help identify which nodes/containers
are consuming the most power and recommend preventive actions based on Korean
regulatory compliance standards.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import structlog

from .kepler_client import KeplerClient
from .korea_compliance import WorkloadMetrics, assess_korea_compliance
from .compliance_standards import KOREA_CARBON_NEUTRALITY, KOREA_PUE_GREEN_DC

logger = structlog.get_logger()


@dataclass
class PowerConsumer:
    """Represents a power-consuming resource"""
    name: str
    namespace: str
    resource_type: str  # pod, container, node
    power_watts: float
    cpu_watts: float
    rank: int

    # Compliance metrics
    carbon_compliant: bool
    pue_compliant: bool
    monthly_emissions_kg: float

    # Efficiency metrics
    power_efficiency_score: float  # 0-100, higher is better


@dataclass
class PreventiveAction:
    """Recommended preventive action"""
    action_type: str  # alert, rightsizing, temporal_shift, regional_migration
    priority: str  # high, medium, low
    resource: str
    reason: str
    estimated_savings_watts: float
    estimated_co2_reduction_kg_month: float
    implementation_steps: List[str]


class PowerHotspotDetector:
    """
    Detects power consumption hotspots and recommends preventive actions.

    This class provides similar functionality to Kepler PR #2250's MCP tools,
    but enhanced with Korean compliance standards and carbon-aware recommendations.
    """

    def __init__(
        self,
        kepler_client: KeplerClient,
        carbon_intensity_gco2_kwh: float = 424.0,
        pue_target: float = 1.4
    ):
        self.kepler_client = kepler_client
        self.carbon_intensity = carbon_intensity_gco2_kwh
        self.pue_target = pue_target

    def list_top_power_consumers(
        self,
        namespace: Optional[str] = None,
        limit: int = 10,
        sort_by: str = "power"  # power or efficiency
    ) -> List[PowerConsumer]:
        """
        List top power consumers in the cluster.

        Similar to Kepler PR #2250's list_top_consumers tool, but enhanced
        with compliance assessment.

        Args:
            namespace: Filter by namespace (None for all)
            limit: Maximum number of results
            sort_by: Sort by "power" (highest first) or "efficiency" (lowest first)

        Returns:
            List of PowerConsumer objects sorted by criteria
        """
        logger.info("listing_top_power_consumers", namespace=namespace, limit=limit)

        # Get all pods with metrics
        all_pods = self.kepler_client.list_pods(namespace)

        consumers = []

        for idx, pod_info in enumerate(all_pods):
            pod_name = pod_info["pod"]
            pod_namespace = pod_info["namespace"]

            try:
                # Get pod metrics
                pod_metrics = self.kepler_client.get_pod_metrics(pod_name, pod_namespace)
                cpu_watts = pod_metrics.get("cpu_watts", 0.0)

                # Assess compliance
                workload_metrics = WorkloadMetrics(
                    cpu_watts=cpu_watts,
                    memory_watts=0.0,
                    gpu_watts=0.0,
                    other_watts=0.0
                )

                node_metrics = self.kepler_client.get_node_metrics()

                assessment = assess_korea_compliance(
                    workload_name=pod_name,
                    namespace=pod_namespace,
                    region="ap-northeast-2",
                    workload_metrics=workload_metrics,
                    node_total_power_watts=node_metrics.get("cpu_watts", 0.0),
                    grid_carbon_intensity_gco2_kwh=self.carbon_intensity
                )

                # Calculate efficiency score (0-100)
                # Higher score = more efficient (lower power, compliant)
                efficiency_score = 100.0
                if cpu_watts > 0:
                    # Penalize high power consumption
                    efficiency_score -= min(cpu_watts * 10, 50)
                if assessment.carbon.status != "COMPLIANT":
                    efficiency_score -= 25
                if assessment.pue.status != "COMPLIANT":
                    efficiency_score -= 25
                efficiency_score = max(0, efficiency_score)

                consumer = PowerConsumer(
                    name=pod_name,
                    namespace=pod_namespace,
                    resource_type="pod",
                    power_watts=cpu_watts,
                    cpu_watts=cpu_watts,
                    rank=idx + 1,
                    carbon_compliant=(assessment.carbon.status == "COMPLIANT"),
                    pue_compliant=(assessment.pue.status == "COMPLIANT"),
                    monthly_emissions_kg=assessment.carbon.monthly_emissions_kg,
                    power_efficiency_score=efficiency_score
                )

                consumers.append(consumer)

            except Exception as e:
                logger.warning("failed_to_assess_consumer", pod=pod_name, error=str(e))
                continue

        # Sort consumers
        if sort_by == "power":
            consumers.sort(key=lambda x: x.power_watts, reverse=True)
        else:  # efficiency
            consumers.sort(key=lambda x: x.power_efficiency_score)

        # Update ranks after sorting
        for idx, consumer in enumerate(consumers[:limit]):
            consumer.rank = idx + 1

        return consumers[:limit]

    def identify_power_hotspots(
        self,
        namespace: Optional[str] = None,
        power_threshold_watts: float = 1.0,
        compliance_check: bool = True
    ) -> Tuple[List[PowerConsumer], List[PreventiveAction]]:
        """
        Identify power hotspots and generate preventive action recommendations.

        This is the key function for answering "which containers are consuming
        the most power and what preventive actions should we take?"

        Args:
            namespace: Target namespace (None for all)
            power_threshold_watts: Minimum power to be considered a hotspot
            compliance_check: Include compliance violations in hotspot detection

        Returns:
            Tuple of (hotspots, recommended_actions)
        """
        logger.info(
            "identifying_power_hotspots",
            namespace=namespace,
            threshold=power_threshold_watts
        )

        # Get top consumers
        all_consumers = self.list_top_power_consumers(namespace=namespace, limit=50)

        # Identify hotspots
        hotspots = []
        for consumer in all_consumers:
            is_hotspot = False

            # Check power threshold
            if consumer.power_watts >= power_threshold_watts:
                is_hotspot = True

            # Check compliance if enabled
            if compliance_check:
                if not consumer.carbon_compliant or not consumer.pue_compliant:
                    is_hotspot = True

            if is_hotspot:
                hotspots.append(consumer)

        # Generate preventive actions
        actions = self._generate_preventive_actions(hotspots)

        logger.info(
            "hotspots_identified",
            total_hotspots=len(hotspots),
            total_actions=len(actions)
        )

        return hotspots, actions

    def _generate_preventive_actions(
        self,
        hotspots: List[PowerConsumer]
    ) -> List[PreventiveAction]:
        """Generate preventive action recommendations for hotspots"""
        actions = []

        for consumer in hotspots:
            # Action 1: Alert for high power consumption
            if consumer.power_watts > 5.0:
                actions.append(PreventiveAction(
                    action_type="alert",
                    priority="high",
                    resource=f"{consumer.namespace}/{consumer.name}",
                    reason=f"High power consumption: {consumer.power_watts:.2f}W",
                    estimated_savings_watts=0,
                    estimated_co2_reduction_kg_month=0,
                    implementation_steps=[
                        "Monitor pod resource utilization",
                        "Check for inefficient code or resource leaks",
                        "Review application logs for anomalies"
                    ]
                ))

            # Action 2: Rightsizing for inefficient workloads
            if consumer.power_efficiency_score < 50:
                estimated_savings = consumer.power_watts * 0.3  # Assume 30% reduction
                co2_reduction = (estimated_savings * 730 * self.carbon_intensity) / 1000  # kg/month

                actions.append(PreventiveAction(
                    action_type="rightsizing",
                    priority="medium",
                    resource=f"{consumer.namespace}/{consumer.name}",
                    reason=f"Low efficiency score: {consumer.power_efficiency_score:.1f}/100",
                    estimated_savings_watts=estimated_savings,
                    estimated_co2_reduction_kg_month=co2_reduction,
                    implementation_steps=[
                        "Analyze actual vs requested resources",
                        "Reduce CPU/memory requests if over-provisioned",
                        "Consider vertical pod autoscaling",
                        "Update deployment with optimized resource limits"
                    ]
                ))

            # Action 3: Temporal shift for non-compliant workloads
            if not consumer.carbon_compliant:
                co2_reduction = consumer.monthly_emissions_kg * 0.15  # 15% reduction

                actions.append(PreventiveAction(
                    action_type="temporal_shift",
                    priority="medium",
                    resource=f"{consumer.namespace}/{consumer.name}",
                    reason="Carbon non-compliant workload",
                    estimated_savings_watts=0,
                    estimated_co2_reduction_kg_month=co2_reduction,
                    implementation_steps=[
                        "Identify if workload is batch/deferrable",
                        "Schedule for off-peak hours (2am-6am KST) when grid is cleaner",
                        "Implement Kubernetes CronJob for automated scheduling",
                        "Monitor carbon intensity and adjust schedule dynamically"
                    ]
                ))

            # Action 4: Regional migration for high emissions
            if consumer.monthly_emissions_kg > 10.0:
                # Seoul: 424 gCO2/kWh, Stockholm: 50 gCO2/kWh
                co2_reduction = consumer.monthly_emissions_kg * 0.88  # 88% reduction

                actions.append(PreventiveAction(
                    action_type="regional_migration",
                    priority="low",
                    resource=f"{consumer.namespace}/{consumer.name}",
                    reason=f"High monthly emissions: {consumer.monthly_emissions_kg:.2f} kg",
                    estimated_savings_watts=0,
                    estimated_co2_reduction_kg_month=co2_reduction,
                    implementation_steps=[
                        "Evaluate if workload can tolerate higher latency",
                        "Consider migrating to eu-north-1 (Stockholm) for cleaner grid",
                        "Implement multi-region deployment strategy",
                        "Use carbon-aware load balancing"
                    ]
                ))

        # Sort actions by priority and potential impact
        priority_order = {"high": 0, "medium": 1, "low": 2}
        actions.sort(
            key=lambda x: (
                priority_order[x.priority],
                -x.estimated_co2_reduction_kg_month
            )
        )

        return actions

    def get_power_consumption_summary(
        self,
        namespace: Optional[str] = None
    ) -> Dict:
        """
        Get overall power consumption summary for a namespace or cluster.

        Returns:
            Summary statistics including total power, top consumers, compliance status
        """
        consumers = self.list_top_power_consumers(namespace=namespace, limit=100)

        if not consumers:
            return {
                "namespace": namespace or "all",
                "total_consumers": 0,
                "total_power_watts": 0,
                "message": "No consumers found"
            }

        total_power = sum(c.power_watts for c in consumers)
        compliant_count = sum(1 for c in consumers if c.carbon_compliant and c.pue_compliant)

        return {
            "namespace": namespace or "all",
            "total_consumers": len(consumers),
            "total_power_watts": total_power,
            "average_power_watts": total_power / len(consumers) if consumers else 0,
            "compliance_rate_percent": (compliant_count / len(consumers) * 100) if consumers else 0,
            "top_3_consumers": [
                {
                    "name": c.name,
                    "namespace": c.namespace,
                    "power_watts": c.power_watts,
                    "compliant": c.carbon_compliant and c.pue_compliant
                }
                for c in consumers[:3]
            ]
        }
