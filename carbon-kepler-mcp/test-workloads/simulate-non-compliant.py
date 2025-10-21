#!/usr/bin/env python3
"""
Simulate non-compliant power scenarios for demo purposes.

This script creates a mock scenario where workloads violate Korean regulatory
standards, triggering preventive actions.
"""

import asyncio
from dataclasses import dataclass
from typing import List

# Import our compliance tools - using absolute imports from src package
import sys
sys.path.insert(0, '/app')

from src.korea_compliance import WorkloadMetrics, assess_korea_compliance, KoreaComplianceAssessment
from src.power_hotspot_tools import PowerHotspotDetector, PowerConsumer, PreventiveAction
from src.compliance_standards import get_regional_carbon_intensity


@dataclass
class MockPod:
    """Mock pod with simulated high power consumption"""
    name: str
    namespace: str
    cpu_watts: float
    description: str


async def simulate_non_compliant_scenarios():
    """Simulate various non-compliant power scenarios"""

    print("\n" + "="*80)
    print("SIMULATED NON-COMPLIANT POWER SCENARIOS")
    print("Demo for Open Source Summit Korea 2025")
    print("="*80 + "\n")

    # Define mock high-power workloads
    mock_pods = [
        MockPod("high-power-cpu-burner-1", "demo-workloads", 15.5, "CPU stress test (3 replicas)"),
        MockPod("high-power-cpu-burner-2", "demo-workloads", 15.2, "CPU stress test"),
        MockPod("high-power-cpu-burner-3", "demo-workloads", 15.0, "CPU stress test"),
        MockPod("crypto-miner-simulation", "demo-workloads", 12.8, "Simulated mining workload"),
        MockPod("memory-intensive-app-1", "demo-workloads", 8.5, "Memory stress test"),
        MockPod("memory-intensive-app-2", "demo-workloads", 8.2, "Memory stress test"),
        MockPod("inefficient-fibonacci-1", "demo-workloads", 5.3, "Inefficient recursive code"),
        MockPod("inefficient-fibonacci-2", "demo-workloads", 5.1, "Inefficient recursive code"),
        MockPod("ml-training-job", "production", 22.4, "ML model training (NON-COMPLIANT)"),
        MockPod("data-processing-batch", "production", 18.7, "Batch processing (NON-COMPLIANT)"),
    ]

    # Korean standards
    grid_carbon_intensity = 424.0  # gCO2eq/kWh for Seoul
    pue_target = 1.4

    print("Scenario: Data center in Seoul, Korea (ap-northeast-2)")
    print(f"Grid Carbon Intensity: {grid_carbon_intensity} gCO2eq/kWh")
    print(f"PUE Target (Green DC): ≤ {pue_target}")
    print(f"\nAssessing {len(mock_pods)} high-power workloads...\n")

    # Assess each workload
    compliant_count = 0
    non_compliant_count = 0
    total_power = 0
    total_monthly_emissions = 0

    assessments = []

    for pod in mock_pods:
        # Create workload metrics
        workload_metrics = WorkloadMetrics(
            cpu_watts=pod.cpu_watts,
            memory_watts=0.0,
            gpu_watts=0.0,
            other_watts=0.0
        )

        # Assess compliance
        assessment = assess_korea_compliance(
            workload_name=pod.name,
            namespace=pod.namespace,
            region="ap-northeast-2",
            workload_metrics=workload_metrics,
            node_total_power_watts=100.0,  # Assume 100W total node power
            grid_carbon_intensity_gco2_kwh=grid_carbon_intensity
        )

        assessments.append((pod, assessment))
        total_power += pod.cpu_watts
        total_monthly_emissions += assessment.carbon.monthly_emissions_kg

        if assessment.carbon.status == "COMPLIANT" and assessment.pue.status == "COMPLIANT":
            compliant_count += 1
        else:
            non_compliant_count += 1

    # Display results
    print("="*80)
    print("COMPLIANCE ASSESSMENT RESULTS")
    print("="*80 + "\n")

    print(f"{'Workload':<40} {'Power':<12} {'Emissions':<15} {'Status'}")
    print("-" * 80)

    for pod, assessment in assessments:
        status_icon = "✅" if (assessment.carbon.status == "COMPLIANT" and
                              assessment.pue.status == "COMPLIANT") else "❌"

        print(f"{pod.name[:39]:<40} {pod.cpu_watts:>6.2f}W     "
              f"{assessment.carbon.monthly_emissions_kg:>6.2f} kg/mo   {status_icon} {assessment.carbon.status}")

    print("-" * 80)
    print(f"{'TOTAL':<40} {total_power:>6.2f}W     {total_monthly_emissions:>6.2f} kg/mo")
    print()

    # Summary
    print(f"Compliant Workloads:     {compliant_count}/{len(mock_pods)} (✅)")
    print(f"Non-Compliant Workloads: {non_compliant_count}/{len(mock_pods)} (❌)")
    print(f"Compliance Rate:         {(compliant_count/len(mock_pods)*100):.1f}%")

    # Generate preventive actions
    print("\n" + "="*80)
    print("PREVENTIVE ACTIONS RECOMMENDED")
    print("="*80 + "\n")

    actions = []

    for pod, assessment in assessments:
        # Action 1: Alert for high power
        if pod.cpu_watts > 10.0:
            actions.append({
                "type": "ALERT",
                "priority": "HIGH",
                "resource": f"{pod.namespace}/{pod.name}",
                "reason": f"Extreme power consumption: {pod.cpu_watts:.1f}W",
                "savings_watts": 0,
                "savings_co2_kg": 0,
                "steps": [
                    "Immediate investigation required",
                    "Check for runaway processes or resource leaks",
                    "Review application logs and metrics",
                    "Consider emergency throttling if necessary"
                ]
            })

        # Action 2: Rightsizing for inefficient workloads
        if pod.cpu_watts > 5.0:
            estimated_savings_watts = pod.cpu_watts * 0.3  # 30% reduction
            estimated_savings_co2 = (estimated_savings_watts * 730 * grid_carbon_intensity) / 1000

            actions.append({
                "type": "RIGHTSIZING",
                "priority": "MEDIUM",
                "resource": f"{pod.namespace}/{pod.name}",
                "reason": f"Optimize resource allocation for {pod.cpu_watts:.1f}W workload",
                "savings_watts": estimated_savings_watts,
                "savings_co2_kg": estimated_savings_co2,
                "steps": [
                    f"Current power: {pod.cpu_watts:.1f}W",
                    f"Target power: {pod.cpu_watts * 0.7:.1f}W (30% reduction)",
                    "Analyze actual vs requested CPU/memory",
                    "Implement vertical pod autoscaling (VPA)",
                    "Update resource requests and limits"
                ]
            })

        # Action 3: Temporal shift for non-compliant
        if assessment.carbon.status == "NON_COMPLIANT" or pod.cpu_watts > 15.0:
            co2_reduction = assessment.carbon.monthly_emissions_kg * 0.15  # 15% reduction

            actions.append({
                "type": "TEMPORAL_SHIFT",
                "priority": "MEDIUM",
                "resource": f"{pod.namespace}/{pod.name}",
                "reason": "Schedule during cleaner grid hours",
                "savings_watts": 0,
                "savings_co2_kg": co2_reduction,
                "steps": [
                    "Identify if workload is deferrable/batch processing",
                    "Schedule for 2am-6am KST (cleanest grid period)",
                    "Implement Kubernetes CronJob for automation",
                    f"Estimated reduction: {co2_reduction:.2f} kg CO2/month"
                ]
            })

        # Action 4: Regional migration for high emitters
        if assessment.carbon.monthly_emissions_kg > 15.0:
            # Seoul (424) vs Stockholm (50) = 88% reduction potential
            co2_reduction = assessment.carbon.monthly_emissions_kg * 0.88

            actions.append({
                "type": "REGIONAL_MIGRATION",
                "priority": "LOW",
                "resource": f"{pod.namespace}/{pod.name}",
                "reason": f"High monthly emissions: {assessment.carbon.monthly_emissions_kg:.1f} kg",
                "savings_watts": 0,
                "savings_co2_kg": co2_reduction,
                "steps": [
                    "Evaluate latency tolerance for this workload",
                    "Consider migration to eu-north-1 (Stockholm, 50 gCO2/kWh)",
                    f"Potential reduction: {co2_reduction:.1f} kg CO2/month (88%)",
                    "Implement multi-region deployment strategy"
                ]
            })

    # Display top 10 actions
    print(f"Generated {len(actions)} preventive actions\n")

    # Sort by priority and impact
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    actions_sorted = sorted(actions, key=lambda x: (priority_order[x["priority"]], -x["savings_co2_kg"]))

    for i, action in enumerate(actions_sorted[:10], 1):
        print(f"Action {i}: {action['type']} [{action['priority']} PRIORITY]")
        print(f"  Resource: {action['resource']}")
        print(f"  Reason: {action['reason']}")

        if action['savings_watts'] > 0 or action['savings_co2_kg'] > 0:
            print(f"  Estimated Savings:")
            if action['savings_watts'] > 0:
                print(f"    • Power: {action['savings_watts']:.2f}W")
            if action['savings_co2_kg'] > 0:
                print(f"    • CO2: {action['savings_co2_kg']:.2f} kg/month")

        print(f"  Implementation Steps:")
        for step in action['steps'][:3]:
            print(f"    • {step}")
        print()

    # Calculate total potential savings
    total_power_savings = sum(a['savings_watts'] for a in actions)
    total_co2_savings = sum(a['savings_co2_kg'] for a in actions)

    print("="*80)
    print("TOTAL POTENTIAL SAVINGS")
    print("="*80)
    print(f"  Power Reduction: {total_power_savings:.2f}W")
    print(f"  CO2 Reduction: {total_co2_savings:.2f} kg/month")
    print(f"  Cost Savings: ~${total_power_savings * 730 * 0.12 / 1000:.2f}/month")
    print(f"    (Assuming $0.12/kWh electricity cost)")
    print()

    # Korean regulatory context
    print("="*80)
    print("KOREAN REGULATORY COMPLIANCE")
    print("="*80 + "\n")

    print("🇰🇷 탄소중립 녹색성장 기본법 (Carbon Neutrality Act 2050)")
    print(f"   Target: 424 gCO2eq/kWh grid carbon intensity")
    print(f"   Current: {grid_carbon_intensity} gCO2eq/kWh")
    print(f"   Status: ⚠️  {non_compliant_count} workloads may contribute to compliance violations\n")

    print("🇰🇷 에너지이용 합리화법 (Energy Use Rationalization Act)")
    print(f"   Green Data Center PUE Target: ≤ {pue_target}")
    print(f"   Impact: High-power workloads increase overall data center PUE")
    print(f"   Recommendation: Optimize inefficient workloads to meet green DC standards\n")

    print("="*80)
    print("✅ SIMULATION COMPLETE")
    print("="*80)
    print("\nThis simulation demonstrates:")
    print("  ✓ Power hotspot identification")
    print("  ✓ Korean regulatory compliance assessment")
    print("  ✓ Preventive action generation (4 types)")
    print("  ✓ Estimated savings calculation")
    print("\nReady for Open Source Summit Korea 2025 demo! 🚀\n")


if __name__ == "__main__":
    asyncio.run(simulate_non_compliant_scenarios())
