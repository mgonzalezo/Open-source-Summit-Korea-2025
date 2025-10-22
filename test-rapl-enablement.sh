#!/bin/bash
#
# RAPL Enablement Test Script for AWS c5.metal
# Based on: https://github.com/sustainable-computing-io/kepler-model-training-playbook
#

set -e

echo "=================================================="
echo "RAPL + MSR Enablement for Kepler on AWS c5.metal"
echo "=================================================="
echo ""

echo "📋 System Information:"
echo "   Kernel: $(uname -r)"
echo "   CPU: $(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)"
echo "   Architecture: $(uname -m)"
echo ""

echo "=================================================="
echo "Phase 1: Kernel Modules Installation"
echo "=================================================="
echo ""

echo "📦 Installing kernel modules..."
sudo apt-get update -qq
sudo apt-get install -y linux-modules-$(uname -r) linux-modules-extra-$(uname -r)
echo "   ✅ Kernel modules installed"
echo ""

echo "📦 Installing MSR tools..."
sudo apt-get install -y msr-tools
echo "   ✅ MSR tools installed"
echo ""

echo "=================================================="
echo "Phase 2: Load Kernel Modules"
echo "=================================================="
echo ""

echo "🔌 Loading intel_rapl_common module..."
sudo modprobe intel_rapl_common
RAPL_EXIT=$?
echo "   Exit code: $RAPL_EXIT"
if [ $RAPL_EXIT -eq 0 ]; then
  echo "   ✅ intel_rapl_common loaded successfully"
else
  echo "   ❌ intel_rapl_common failed to load"
fi
echo ""

echo "🔌 Loading MSR module..."
sudo modprobe msr
MSR_EXIT=$?
echo "   Exit code: $MSR_EXIT"
if [ $MSR_EXIT -eq 0 ]; then
  echo "   ✅ MSR module loaded successfully"
else
  echo "   ❌ MSR module failed to load"
fi
echo ""

echo "=================================================="
echo "Phase 3: Verify RAPL Availability"
echo "=================================================="
echo ""

echo "🔍 Checking /sys/class/powercap/..."
if [ -d "/sys/class/powercap" ]; then
  POWERCAP_CONTENTS=$(ls /sys/class/powercap/ 2>&1)
  if [ -n "$POWERCAP_CONTENTS" ]; then
    echo "   ✅ Powercap directory has contents:"
    ls -la /sys/class/powercap/
  else
    echo "   ⚠️  Powercap directory exists but is empty"
    ls -la /sys/class/powercap/
  fi
else
  echo "   ❌ /sys/class/powercap/ does not exist"
fi
echo ""

echo "🔍 Checking for RAPL zones..."
if [ -d "/sys/class/powercap/intel-rapl:0" ]; then
  echo "   ✅ RAPL zones found!"
  RAPL_AVAILABLE=true
  echo ""
  echo "   📊 RAPL Zones:"
  for zone in /sys/class/powercap/intel-rapl:*; do
    if [ -f "$zone/name" ]; then
      zone_name=$(cat $zone/name 2>/dev/null)
      zone_energy=$(cat $zone/energy_uj 2>/dev/null || echo "N/A")
      zone_max=$(cat $zone/max_energy_range_uj 2>/dev/null || echo "N/A")
      echo "      $(basename $zone):"
      echo "         Name: $zone_name"
      echo "         Current Energy: $zone_energy µJ"
      echo "         Max Range: $zone_max µJ"
    fi
  done
else
  echo "   ❌ No RAPL zones found in /sys/class/powercap/"
  RAPL_AVAILABLE=false
fi
echo ""

echo "=================================================="
echo "Phase 4: MSR Register Access Test"
echo "=================================================="
echo ""

echo "🔍 Checking MSR device..."
if [ -c "/dev/cpu/0/msr" ]; then
  echo "   ✅ MSR device exists: /dev/cpu/0/msr"
  ls -la /dev/cpu/0/msr
else
  echo "   ❌ MSR device not found"
fi
echo ""

echo "⚡ Testing RAPL MSR register access (0x611)..."
RAPL_MSR=$(sudo rdmsr 0x611 2>&1)
RDMSR_EXIT=$?
if [ $RDMSR_EXIT -eq 0 ]; then
  echo "   ✅ Successfully read RAPL MSR 0x611"
  echo "   Value: $RAPL_MSR"
else
  echo "   ❌ Failed to read RAPL MSR 0x611"
  echo "   Error: $RAPL_MSR"
fi
echo ""

echo "=================================================="
echo "Phase 5: Loaded Modules Check"
echo "=================================================="
echo ""

echo "🔍 Power-related kernel modules loaded:"
lsmod | grep -E "rapl|msr|power" || echo "   ⚠️  No power-related modules found"
echo ""

echo "=================================================="
echo "Phase 6: Alternative RAPL Locations"
echo "=================================================="
echo ""

echo "🔍 Searching for RAPL in /sys filesystem..."
RAPL_PATHS=$(find /sys -name "*rapl*" 2>/dev/null)
if [ -n "$RAPL_PATHS" ]; then
  echo "   Found RAPL-related paths:"
  echo "$RAPL_PATHS"
else
  echo "   ⚠️  No RAPL paths found in /sys"
fi
echo ""

echo "=================================================="
echo "Phase 7: Make Changes Permanent"
echo "=================================================="
echo ""

if [ "$RAPL_AVAILABLE" = true ]; then
  echo "💾 Making modules load on boot..."

  if ! grep -q "intel_rapl_common" /etc/modules 2>/dev/null; then
    echo "intel_rapl_common" | sudo tee -a /etc/modules
    echo "   ✅ Added intel_rapl_common to /etc/modules"
  else
    echo "   ℹ️  intel_rapl_common already in /etc/modules"
  fi

  if ! grep -q "^msr$" /etc/modules 2>/dev/null; then
    echo "msr" | sudo tee -a /etc/modules
    echo "   ✅ Added msr to /etc/modules"
  else
    echo "   ℹ️  msr already in /etc/modules"
  fi
  echo ""
fi

echo "=================================================="
echo "FINAL RESULT"
echo "=================================================="
echo ""

if [ "$RAPL_AVAILABLE" = true ]; then
  echo "🎉 SUCCESS! RAPL is available on this instance!"
  echo ""
  echo "✅ Next Steps:"
  echo "   1. Update Kepler configuration to use RAPL"
  echo "   2. Remove Model Server configuration"
  echo "   3. Remove fake CPU bootstrap"
  echo "   4. Deploy Kepler with estimator: rapl"
  echo ""
  exit 0
else
  echo "❌ RAPL is NOT available on this AWS c5.metal instance"
  echo ""
  echo "📋 Details:"
  echo "   - Kernel modules: Installed ✅"
  echo "   - intel_rapl_common: Loaded ✅"
  echo "   - MSR module: Loaded ✅"
  echo "   - RAPL interface: Not accessible ❌"
  echo ""
  echo "⚠️  Possible reasons:"
  echo "   1. AWS hypervisor blocks RAPL access (most likely)"
  echo "   2. Nitro system security restrictions"
  echo "   3. Instance type doesn't expose RAPL"
  echo ""
  echo "💡 Recommendations:"
  echo "   1. Continue using Model Server approach"
  echo "   2. Try different instance type (m5.metal, m6i.metal)"
  echo "   3. Contact AWS support about RAPL access"
  echo "   4. Consider physical hardware for RAPL access"
  echo ""
  exit 1
fi
