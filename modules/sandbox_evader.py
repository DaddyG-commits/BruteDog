#!/usr/bin/env python3
"""
SANDBOX_EVADER.PY v8.6 — Runtime Environment & Diagnostics Inspector
"""
import asyncio
import hashlib
import json
import os
import platform
import sys
import time

from modules.behavioral_mimic import apply_behavioral_jitter
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

_background_tasks: set[asyncio.Task] = set()


def terminal(message):
    sys.stdout.write(str(message) + "\n")
    sys.stdout.flush()


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Schedules non-blocking notifications when invoked from synchronous contexts."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


class SandboxEvader:
    """Collects non-blocking runtime/host diagnostics for stability awareness."""

    def __init__(self):
        self.evasion_triggered = False
        self.indicators: list[str] = []

    def check_debugger(self):
        is_traced = sys.gettrace() is not None
        if is_traced:
            self.indicators.append("Active trace hook present (sys.gettrace)")
            return True

        try:
            import urllib.request

            if getattr(urllib.request.urlopen, "__name__", "") != "urlopen":
                self.indicators.append("Custom wrapper detected on urllib.request.urlopen")
                return True
        except Exception:
            pass

        return False

    def check_timing_acceleration(self):
        try:
            start_time = time.perf_counter()
            _ = sum(i * i for i in range(500_000))
            elapsed = time.perf_counter() - start_time
            if elapsed < 0.00001:
                self.indicators.append(f"Short timing delta observed ({elapsed:.6f}s)")
                return True
        except Exception:
            pass
        return False

    def check_container_artifacts(self):
        artifacts = []

        if os.path.exists("/.dockerenv") or os.path.exists("/runenv"):
            artifacts.append("Container marker file present")

        try:
            if os.path.exists("/proc/self/cgroup"):
                with open("/proc/self/cgroup", "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if any(sig in content for sig in ("docker", "kubepods", "lxc", "containerd", "podman")):
                        artifacts.append("Container cgroup entry detected")
        except Exception:
            pass

        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    for hv in ("vmware", "qemu", "kvm", "virtualbox", "xen", "hyperv"):
                        if hv in content:
                            artifacts.append(f"Virtualization CPU tag: {hv}")
        except Exception:
            pass

        if artifacts:
            self.indicators.extend(artifacts)
            return True
        return False

    def check_resource_constraints(self):
        constraints = []

        cpu_count = os.cpu_count() or 1
        if cpu_count <= 1:
            constraints.append(f"Single-core environment ({cpu_count})")

        try:
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            parts = line.split()
                            if len(parts) >= 2 and parts[1].isdigit():
                                kb_total = int(parts[1])
                                if kb_total < 2_097_152:
                                    constraints.append(f"Constrained RAM ({kb_total // 1024} MB)")
                            break
        except Exception:
            pass

        if constraints:
            self.indicators.extend(constraints)
            return True
        return False

    def inspect_environment(self, persist_artifacts: bool = False):
        terminal(f"{COLORS['MAGENTA']}[*] Inspecting runtime environment diagnostics...{COLORS['RESET']}")
        self.indicators = []

        apply_behavioral_jitter()

        dbg = self.check_debugger()
        tmg = self.check_timing_acceleration()
        cnt = self.check_container_artifacts()
        res = self.check_resource_constraints()

        diagnostics_noted = dbg or tmg or cnt or res
        self.evasion_triggered = diagnostics_noted

        report = {
            "analysis_environment_detected": diagnostics_noted,
            "debugger_active": dbg,
            "timing_anomaly": tmg,
            "container_artifacts": cnt,
            "resource_constraints": res,
            "indicators": list(self.indicators),
            "platform": platform.platform(),
        }

        if diagnostics_noted:
            terminal(
                f"{COLORS['YELLOW']}[~] Runtime environment notes recorded ({len(self.indicators)} items).{COLORS['RESET']}"
            )
            for ind in self.indicators:
                terminal(f"  └── Note: {ind}")

            report_str = json.dumps(report, default=str)
            report["integrity_hash"] = hashlib.sha256(report_str.encode("utf-8", errors="ignore")).hexdigest()

            if persist_artifacts:
                broadcast_tg_alert_sync("Runtime Environment Diagnostics", report)
                stream_proof("RUNTIME_DIAGNOSTICS", "local_runtime", {}, f"Notes: {len(self.indicators)}", report)
                save_session_loot(
                    target="localhost",
                    endpoint="runtime_diagnostics",
                    finding_type="RUNTIME_DIAGNOSTICS",
                    status=200,
                    headers={},
                    body=report_str,
                    extra_loot=report,
                )
        else:
            terminal(f"{COLORS['GREEN']}[+] Standard runtime environment confirmed.{COLORS['RESET']}")

        return report


async def run_sandbox_evader(*args, **kwargs):
    terminal(f"\n{COLORS['CYAN']}[***] BRUTEDOG RUNTIME ENVIRONMENT INSPECTOR (V8.6) [***]{COLORS['RESET']}")
    evader = SandboxEvader()
    persist = bool(kwargs.get("persist_artifacts", False))
    try:
        return await asyncio.to_thread(evader.inspect_environment, persist)
    except Exception as exc:
        return {
            "analysis_environment_detected": False,
            "indicators": [],
            "platform": platform.platform(),
            "error": str(exc),
        }


async def evade_sandbox(*args, **kwargs):
    return await run_sandbox_evader(*args, **kwargs)


if __name__ == "__main__":
    asyncio.run(run_sandbox_evader())
