"""One sampling loop, independent sources, atomic publication and clean shutdown."""

import json
import logging
import math
import platform
import re
import threading
import time
from dataclasses import asdict
from pathlib import Path
from queue import Empty, Full, Queue

from mactop.metrics_store import (
    M1CPUCluster,
    MetricsSnapshot,
    ProcessorType,
    Smc,
    metrics,
)
from .ioreg import parse_battery
from .ioreport import IOReport, component_power, decode_frequencies, residency_metrics
from .macos import IOKit, NativeError
from .sensors import Sensors
from .system import SystemCollector

logger = logging.getLogger(__name__)


def snapshot_json(snapshot):
    return json.dumps(
        asdict(snapshot), default=lambda value: value.value, allow_nan=False
    )


def frequency_table(tables, domain):
    keys = {
        "gpu": ("voltage-states9-sram", "voltage-states9"),
        "ecpu": ("voltage-states1-sram", "voltage-states1"),
        "pcpu": ("voltage-states5-sram", "voltage-states5"),
        "pcpu1": ("voltage-states13-sram", "voltage-states13"),
    }.get(domain, ())
    for key in keys:
        values = decode_frequencies(tables.get(key))
        if values and all(100_000 <= value <= 10_000_000 for value in values):
            values = [value * 1000 for value in values]  # Newer CPU tables use kHz.
        if values and all(100_000_000 <= value <= 10_000_000_000 for value in values):
            return values
    return []


def apply_soc(snapshot, channels, elapsed, tables):
    hardware = snapshot.hardware
    if elapsed is None:
        return
    hardware.power_watts.update(component_power(channels, elapsed))
    clusters = []
    for channel in channels:
        if (
            channel.group == "GPU Stats"
            and channel.subgroup == "GPU Performance States"
            and channel.name == "GPUPH"
        ):
            hardware.m1_gpu.idle_ratio, hardware.m1_gpu.freq_hz = residency_metrics(
                channel.states, frequency_table(tables, "gpu")
            )
        elif (
            channel.group == "CPU Stats"
            and channel.subgroup == "CPU Complex Performance States"
            and re.fullmatch(r"[EP]CPU\d*", channel.name)
        ):
            idle, hz = residency_metrics(
                channel.states, frequency_table(tables, channel.name.lower())
            )
            clusters.append(
                M1CPUCluster(name=channel.name, idle_ratio=idle, freq_hz=hz)
            )
    hardware.processor_m1.clusters = sorted(clusters, key=lambda cluster: cluster.name)
    if hardware.power_watts["cpu"] is None:
        snapshot.errors["cpu_power"] = "No usable CPU energy counter"
    if hardware.power_watts["gpu"] is None:
        snapshot.errors["gpu_power"] = "No usable GPU energy counter"


def append_histories(snapshot, previous):
    hardware, old = snapshot.hardware, previous.hardware
    for name, value in hardware.power_watts.items():
        # A gap clears history so a stale last reading is never displayed as current.
        hardware.power_history[name] = (
            (old.power_history.get(name, []) + [value])[-100:]
            if value is not None
            else []
        )
    for kind in ("disk", "network"):
        current, before = getattr(hardware, kind), getattr(old, kind)
        for name in vars(current):
            if name.endswith("_history"):
                value = getattr(current, name.removesuffix("_history"))
                history = getattr(before, name) or []
                setattr(
                    current,
                    name,
                    (history + [value])[-100:] if value is not None else [],
                )
    hardware.processor_intel.package_watts_history = hardware.power_history["cpu"]


class MetricsCollector:
    def __init__(self):
        self.system = SystemCollector()
        self.kit = self.report = self.sensors = None
        self.tables = {}
        self.initial_errors = {}
        self.previous = MetricsSnapshot()
        try:
            self.kit = IOKit()
        except (NativeError, OSError, AttributeError) as error:
            self.initial_errors["iokit"] = str(error)
        if self.kit:
            try:
                self.report = IOReport(self.kit.cf)
            except (NativeError, OSError, AttributeError) as error:
                self.initial_errors["ioreport"] = str(error)
            try:
                self.tables = self.kit.frequency_tables()
            except (NativeError, OSError) as error:
                self.initial_errors["frequencies"] = str(error)
            self.sensors = Sensors(self.kit)

    def sample(self):
        snapshot = MetricsSnapshot(
            timestamp=time.time(), errors=dict(self.initial_errors)
        )
        snapshot.hardware.processor_type = (
            ProcessorType.M1 if platform.machine() == "arm64" else ProcessorType.INTEL
        )
        self.system.sample(snapshot)
        if self.report:
            try:
                channels, elapsed = self.report.sample()
                apply_soc(snapshot, channels, elapsed, self.tables)
            except (NativeError, OSError) as error:
                snapshot.errors["ioreport"] = str(error)
        if self.kit:
            try:
                snapshot.battery = parse_battery(
                    self.kit.battery(), self.previous.battery, snapshot.timestamp
                )
            except (NativeError, OSError) as error:
                snapshot.errors["battery"] = str(error)
        if self.sensors:
            try:
                cpu, gpu, fan, system = self.sensors.sample()
                snapshot.hardware.smc = Smc(cpu, gpu, fan)
                snapshot.hardware.power_watts["system"] = system
                if cpu is None or gpu is None:
                    snapshot.errors["temperature"] = (
                        "CPU/GPU temperature sensor unavailable"
                    )
                if system is None:
                    snapshot.errors["system_power"] = self.sensors.errors.get(
                        "smc", "PSTR unavailable"
                    )
            except (NativeError, OSError) as error:
                snapshot.errors["sensors"] = str(error)
        append_histories(snapshot, self.previous)
        for name, message in snapshot.errors.items():
            if self.previous.errors.get(name) != message:
                logger.warning("%s: %s", name, message)
        self.previous = snapshot
        return snapshot

    def close(self):
        try:
            if self.report:
                self.report.close()
        finally:
            if self.sensors:
                self.sensors.close()


class MetricsManager:
    def __init__(
        self,
        interval=1.0,
        debug=False,
        store=metrics,
        collector_factory=MetricsCollector,
    ):
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError("Refresh interval must be finite and positive")
        self.interval, self.debug, self.store = interval, debug, store
        self.collector_factory = collector_factory
        self.stop_event = threading.Event()
        self.samples = Queue(maxsize=1)
        self.thread = None
        self.failure = None

    def _run(self):
        collector = None
        try:
            collector = self.collector_factory()
            # Prime cumulative counters; the first published sample has a real interval.
            collector.sample()
            deadline = time.monotonic() + self.interval
            while not self.stop_event.wait(max(0, deadline - time.monotonic())):
                snapshot = collector.sample()
                self.store.publish(snapshot)
                if self.debug:
                    directory = Path("debug_json")
                    directory.mkdir(exist_ok=True)
                    (directory / f"mactop_{time.time_ns()}.json").write_text(
                        snapshot_json(snapshot)
                    )
                try:
                    self.samples.put_nowait(snapshot)
                except Full:
                    try:
                        self.samples.get_nowait()
                    except Empty:
                        pass
                    self.samples.put_nowait(snapshot)
                deadline += self.interval
                if deadline < time.monotonic():
                    deadline = time.monotonic() + self.interval
        except Exception as error:
            self.failure = error
            logger.exception("Metrics collector failed")
            snapshot = MetricsSnapshot(
                timestamp=time.time(), errors={"collector": str(error)}
            )
            self.store.publish(snapshot)
        finally:
            if collector:
                try:
                    collector.close()
                except Exception as error:
                    self.failure = self.failure or error
                    logger.exception("Could not close native metrics resources")

    def start(self):
        if self.thread is not None:
            raise RuntimeError("Metrics manager has already been started")
        self.thread = threading.Thread(
            target=self._run, name="mactop-metrics", daemon=True
        )
        self.thread.start()

    def next_sample(self):
        while True:
            try:
                return self.samples.get(timeout=0.1)
            except Empty:
                if self.failure:
                    raise RuntimeError(
                        f"Metrics collector failed: {self.failure}"
                    ) from self.failure
                if self.stop_event.is_set():
                    raise RuntimeError("Metrics collector stopped")
                if self.thread and not self.thread.is_alive():
                    raise RuntimeError("Metrics collector exited without a sample")

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                logger.warning("Metrics collector did not stop within 5 seconds")
