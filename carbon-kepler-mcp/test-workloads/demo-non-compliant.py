#!/usr/bin/env python3
"""
Create actual non-compliant power scenarios by using power efficiency thresholds.

This demonstrates non-compliant scenarios based on:
1. Per-workload power thresholds (simulating inefficient workloads)
2. Carbon intensity targets stricter than grid average
"""

import sys
sys.path.insert(0, '/app')

from src.korea_compliance import WorkloadMetrics, assess_korea_compliance
from src.compliance_standards import CarbonStandard, PUEStandard

# Define STRICTER Korean standards for demo purposes
# This represents a "Green Cloud Initiative" target
KOREA_GREEN_CLOUD_TARGET = CarbonStandard(
    code="KR_GREEN_CLOUD_2025",
    name="Korean Green Cloud Initiative (Demo Target)",
    name_local="한국 그린 클라우드 이니셔티브",
    target_carbon_intensity_gco2_kwh=300,  # 30% better than grid average (424)
    grid_carbon_intensity_gco2_kwh=424,
    enforcement_date="2025-01-01",
    description=(
        "Stricter target for cloud providers: achieve 30% better efficiency than grid average "
        "through optimization, renewable energy procurement, and efficient workload scheduling."
    ),
    reference_url="https://example.com/green-cloud-kr"
)

# Strict PUE target for tier-1 data centers
KOREA_PUE_TIER1 = PUEStandard(
    code="KR_PUE_TIER1",
    name="Korean Tier-1 Data Center PUE Standard (Demo)",
    name_local="한국 1등급 데이터센터 PUE 기준",
    target_pue=1.2,  # Stricter than green DC (1.4)
    baseline_pue=1.8,
    certification_level="Tier-1 (Highest Efficiency)",
    description="Tier-1 certification requires PUE ≤ 1.2",
    reference_url="https://example.com/tier1-kr"
)


def assess_with_strict_standards(
    workload_name: str,
    namespace: str,
    cpu_watts: float,
    region: str = "ap-northeast-2"
):
    """Assess workload against STRICT standards to trigger non-compliance"""

    workload_metrics = WorkloadMetrics(
        cpu_watts=cpu_watts,
        memory_watts=0.0,
        gpu_watts=0.0,
        other_watts=0.0
    )

    # Use stricter carbon target
    grid_intensity = KOREA_GREEN_CLOUD_TARGET.grid_carbon_intensity_gco2_kwh

    # Calculate workload carbon intensity
    # For demo: workloads > 10W are considered "inefficient" with 50% overhead
    if cpu_watts > 10.0:
        # Simulate inefficiency: workload uses 50% more carbon per watt than grid average
        workload_carbon_intensity = grid_intensity * 1.5  # 636 gCO2/kWh (NON-COMPLIANT)
    elif cpu_watts > 5.0:
        # Moderate inefficiency: 25% overhead
        workload_carbon_intensity = grid_intensity * 1.25  # 530 gCO2/kWh (NON-COMPLIANT)
    else:
        # Efficient workload
        workload_carbon_intensity = grid_intensity  # 424 gCO2/kWh (NON-COMPLIANT vs 300 target)

    # Manual carbon compliance check
    carbon_compliant = workload_carbon_intensity <= KOREA_GREEN_CLOUD_TARGET.target_carbon_intensity_gco2_kwh
    carbon_gap_percent = ((workload_carbon_intensity - KOREA_GREEN_CLOUD_TARGET.target_carbon_intensity_gco2_kwh) /
                          KOREA_GREEN_CLOUD_TARGET.target_carbon_intensity_gco2_kwh * 100)

    # Calculate emissions
    hourly_emissions_gco2 = cpu_watts * workload_carbon_intensity  # gCO2
    monthly_emissions_kg = (hourly_emissions_gco2 * 730) / 1000  # kg

    # PUE assessment - high power workloads create datacenter inefficiency
    # Simulate: each 10W of workload power adds 0.1 to PUE
    estimated_pue = 1.2 + (cpu_watts / 10.0) * 0.1
    pue_compliant = estimated_pue <= KOREA_PUE_TIER1.target_pue
    pue_gap_percent = ((estimated_pue - KOREA_PUE_TIER1.target_pue) / KOREA_PUE_TIER1.target_pue * 100)

    return {
        "workload_name": workload_name,
        "namespace": namespace,
        "power_watts": cpu_watts,
        "carbon": {
            "status": "COMPLIANT" if carbon_compliant else "NON_COMPLIANT",
            "workload_intensity": workload_carbon_intensity,
            "target_intensity": KOREA_GREEN_CLOUD_TARGET.target_carbon_intensity_gco2_kwh,
            "grid_intensity": grid_intensity,
            "gap_percent": carbon_gap_percent,
            "monthly_emissions_kg": monthly_emissions_kg
        },
        "pue": {
            "status": "COMPLIANT" if pue_compliant else "NON_COMPLIANT",
            "estimated_pue": estimated_pue,
            "target_pue": KOREA_PUE_TIER1.target_pue,
            "gap_percent": pue_gap_percent
        }
    }


def main():
    print("\n" + "="*80)
    print("NON-COMPLIANT POWER SCENARIOS - STRICT STANDARDS DEMO")
    print("Open Source Summit Korea 2025")
    print("="*80 + "\n")

    print("Scenario: High-efficiency cloud provider in Seoul, Korea")
    print(f"Standard: {KOREA_GREEN_CLOUD_TARGET.name_local}")
    print(f"Carbon Target: {KOREA_GREEN_CLOUD_TARGET.target_carbon_intensity_gco2_kwh} gCO2eq/kWh")
    print(f"  (30% better than grid average: {KOREA_GREEN_CLOUD_TARGET.grid_carbon_intensity_gco2_kwh} gCO2eq/kWh)")
    print(f"\nPUE Standard: {KOREA_PUE_TIER1.name_local}")
    print(f"PUE Target: ≤ {KOREA_PUE_TIER1.target_pue} (Tier-1 certification)")
    print(f"\n{'='*80}\n")

    # Define test workloads
    workloads = [
        ("high-power-cpu-burner-1", "demo-workloads", 15.5),
        ("high-power-cpu-burner-2", "demo-workloads", 15.2),
        ("high-power-cpu-burner-3", "demo-workloads", 15.0),
        ("crypto-miner-simulation", "demo-workloads", 12.8),
        ("memory-intensive-app-1", "demo-workloads", 8.5),
        ("memory-intensive-app-2", "demo-workloads", 8.2),
        ("inefficient-fibonacci-1", "demo-workloads", 5.3),
        ("inefficient-fibonacci-2", "demo-workloads", 5.1),
        ("ml-training-job", "production", 22.4),
        ("data-processing-batch", "production", 18.7),
    ]

    results = []
    compliant_count = 0
    non_compliant_count = 0

    for name, ns, watts in workloads:
        result = assess_with_strict_standards(name, ns, watts)
        results.append(result)

        if result["carbon"]["status"] == "COMPLIANT" and result["pue"]["status"] == "COMPLIANT":
            compliant_count += 1
        else:
            non_compliant_count += 1

    # Display results
    print("COMPLIANCE ASSESSMENT RESULTS")
    print("="*80 + "\n")

    print(f"{'Workload':<40} {'Power':<10} {'Carbon':<18} {'PUE':<15} {'Status'}")
    print("-" * 80)

    for r in results:
        carbon_icon = "✅" if r["carbon"]["status"] == "COMPLIANT" else "❌"
        pue_icon = "✅" if r["pue"]["status"] == "COMPLIANT" else "❌"
        overall_icon = "✅" if (r["carbon"]["status"] == "COMPLIANT" and
                                r["pue"]["status"] == "COMPLIANT") else "❌"

        print(f"{r['workload_name'][:39]:<40} "
              f"{r['power_watts']:>6.2f}W   "
              f"{r['carbon']['workload_intensity']:>4.0f} gCO2/kWh {carbon_icon}   "
              f"PUE {r['pue']['estimated_pue']:>4.2f} {pue_icon}   "
              f"{overall_icon}")

    print("-" * 80)
    print(f"\nCompliance Summary:")
    print(f"  ✅ Compliant:     {compliant_count}/{len(workloads)}")
    print(f"  ❌ Non-Compliant: {non_compliant_count}/{len(workloads)}")
    print(f"  Compliance Rate:  {(compliant_count/len(workloads)*100):.1f}%\n")

    # Violations breakdown
    carbon_violations = [r for r in results if r["carbon"]["status"] == "NON_COMPLIANT"]
    pue_violations = [r for r in results if r["pue"]["status"] == "NON_COMPLIANT"]

    if carbon_violations:
        print(f"\n{'='*80}")
        print(f"CARBON INTENSITY VIOLATIONS ({len(carbon_violations)} workloads)")
        print(f"{'='*80}\n")
        print(f"Target: {KOREA_GREEN_CLOUD_TARGET.target_carbon_intensity_gco2_kwh} gCO2eq/kWh\n")

        for r in carbon_violations[:5]:
            print(f"  ❌ {r['namespace']}/{r['workload_name']}")
            print(f"     Current: {r['carbon']['workload_intensity']:.0f} gCO2/kWh")
            print(f"     Exceeds target by: {r['carbon']['gap_percent']:.1f}%")
            print(f"     Monthly emissions: {r['carbon']['monthly_emissions_kg']:.2f} kg CO2")
            print()

    if pue_violations:
        print(f"{'='*80}")
        print(f"PUE VIOLATIONS ({len(pue_violations)} workloads)")
        print(f"{'='*80}\n")
        print(f"Target: PUE ≤ {KOREA_PUE_TIER1.target_pue} (Tier-1 Data Center)\n")

        for r in pue_violations[:5]:
            print(f"  ❌ {r['namespace']}/{r['workload_name']}")
            print(f"     Estimated PUE: {r['pue']['estimated_pue']:.2f}")
            print(f"     Exceeds target by: {r['pue']['gap_percent']:.1f}%")
            print(f"     Power consumption: {r['power_watts']:.1f}W (high-power workloads reduce DC efficiency)")
            print()

    print("="*80)
    print("RECOMMENDED ACTIONS")
    print("="*80 + "\n")

    print("For Carbon Violations:")
    print("  1. Implement workload optimization (reduce CPU cycles)")
    print("  2. Use carbon-aware scheduling (run during clean grid hours)")
    print("  3. Migrate to regions with cleaner grids (e.g., eu-north-1: 50 gCO2/kWh)")
    print("  4. Procure renewable energy certificates (RECs)\n")

    print("For PUE Violations:")
    print("  1. Implement rightsizing (reduce over-provisioned resources)")
    print("  2. Consolidate workloads to reduce idle servers")
    print("  3. Improve cooling efficiency in data centers")
    print("  4. Use vertical pod autoscaling (VPA) to optimize resource requests\n")

    print("="*80)
    print("✅ DEMO COMPLETE - NON-COMPLIANT SCENARIOS IDENTIFIED")
    print("="*80)
    print(f"\nThis demonstrates how {non_compliant_count} out of {len(workloads)} workloads")
    print("violate strict green cloud standards and require remediation.\n")


if __name__ == "__main__":
    main()
