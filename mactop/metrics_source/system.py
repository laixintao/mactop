"""Kernel counters via psutil's macOS Mach/sysctl/libproc bindings."""

import time
from dataclasses import fields

import psutil

from mactop.metrics_store import CPUTimesPercent, LoadAvg, SwapMemory, VirtualMemory


def counter_rate(before, after, elapsed):
    if elapsed <= 0 or before is None or after is None or after < before:
        return None
    return (after - before) / elapsed


def cpu_percentages(before, after):
    if not before or len(before) != len(after):
        return None, None
    per_cpu = []
    totals = [0.0] * 4
    for old, new in zip(before, after):
        delta = [
            getattr(new, key) - getattr(old, key)
            for key in ("user", "nice", "system", "idle")
        ]
        if any(value < 0 for value in delta) or sum(delta) <= 0:
            return None, None
        per_cpu.append(CPUTimesPercent(*(value / sum(delta) * 100 for value in delta)))
        totals = [total + value for total, value in zip(totals, delta)]
    return per_cpu, CPUTimesPercent(*(value / sum(totals) for value in totals))


def device_rates(before, after, elapsed, names):
    """New/disappearing devices do not inject their lifetime counters into rates."""
    common = before.keys() & after.keys()
    if not common:
        return {name: None for name in names}
    result = {}
    for name in names:
        rates = [
            counter_rate(getattr(before[key], name), getattr(after[key], name), elapsed)
            for key in common
        ]
        result[name] = sum(rates) if all(rate is not None for rate in rates) else None
    return result


class SystemCollector:
    def __init__(self):
        self.previous_cpu = None
        self.previous_io = {}
        self.previous_processes = {}

    def cpu(self, snapshot):
        # psutil.cpu_times(percpu=True) calls host_processor_info on macOS.
        current = psutil.cpu_times(percpu=True)
        snapshot.system.cpu_percent_percpu, snapshot.system.cpu_percent = (
            cpu_percentages(self.previous_cpu, current)
        )
        self.previous_cpu = current
        snapshot.system.cpu_count = len(current) or snapshot.system.cpu_count

    def memory(self, snapshot):
        vm = psutil.virtual_memory()
        snapshot.system.virtual_memory = VirtualMemory(
            **{item.name: getattr(vm, item.name) for item in fields(VirtualMemory)}
        )

    def swap(self, snapshot):
        swap = psutil.swap_memory()
        snapshot.system.swap_memory = SwapMemory(
            swap.total, swap.used, swap.free, swap.percent, swap.sin, swap.sout
        )

    def load(self, snapshot):
        snapshot.system.loadavg = LoadAvg(*psutil.getloadavg())
        snapshot.system.boot_time = psutil.boot_time()

    def io(self, kind, snapshot):
        if kind == "network":
            current = psutil.net_io_counters(pernic=True, nowrap=False)
            mapping = {
                "bytes_recv": "ibyte_rate",
                "bytes_sent": "obyte_rate",
                "packets_recv": "ipacket_rate",
                "packets_sent": "opacket_rate",
            }
        else:
            current = psutil.disk_io_counters(perdisk=True, nowrap=False)
            mapping = {
                "read_bytes": "rbytes_per_s",
                "write_bytes": "wbytes_per_s",
                "read_count": "rops_per_s",
                "write_count": "wops_per_s",
            }
        now = time.monotonic()
        if not current:
            raise RuntimeError(f"No {kind} counters available")
        previous = self.previous_io.get(kind)
        self.previous_io[kind] = (now, current)
        if previous and current is not None:
            rates = device_rates(previous[1], current, now - previous[0], mapping)
            if any(value is None for value in rates.values()):
                snapshot.errors[kind] = (
                    "Counters reset or devices changed; establishing a new baseline"
                )
            target = getattr(snapshot.hardware, kind)
            for name, value in rates.items():
                setattr(target, mapping[name], value)

    def processes(self, snapshot):
        tasks = []
        current = {}
        for process in psutil.process_iter(
            attrs=["pid", "name", "create_time", "cpu_times", "memory_info"],
            ad_value=None,
        ):
            try:
                info = process.info
                times, memory = info["cpu_times"], info["memory_info"]
                cpu_seconds = times.user + times.system if times else None
                now = time.monotonic()
                identity = (info["pid"], info["create_time"])
                percent = None
                old = self.previous_processes.get(identity)
                if old and info["create_time"] is not None:
                    rate = counter_rate(old[1], cpu_seconds, now - old[0])
                    percent = rate * 100 if rate is not None else None
                current[identity] = (now, cpu_seconds)
                tasks.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"] or "?",
                        "cpu_percent": percent,
                        "rss_bytes": memory.rss if memory else None,
                        "vms_bytes": memory.vms if memory else None,
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        self.previous_processes = current
        snapshot.hardware.tasks = sorted(
            tasks, key=lambda item: (-(item["cpu_percent"] or 0), item["pid"])
        )

    def sample(self, snapshot):
        readers = {
            "cpu": self.cpu,
            "memory": self.memory,
            "swap": self.swap,
            "load": self.load,
            "processes": self.processes,
        }
        readers.update(
            {
                kind: lambda sample, kind=kind: self.io(kind, sample)
                for kind in ("network", "disk")
            }
        )
        for name, reader in readers.items():
            try:
                reader(snapshot)
            except (psutil.Error, OSError, RuntimeError) as error:
                snapshot.errors[name] = str(error)
                if name == "cpu":
                    self.previous_cpu = None
                elif name in ("network", "disk"):
                    self.previous_io.pop(name, None)
                elif name == "processes":
                    self.previous_processes.clear()
