import ctypes
import json
import struct
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mactop.metrics_source.collector import (
    MetricsCollector,
    MetricsManager,
    append_histories,
    apply_soc,
    frequency_table,
    snapshot_json,
)
from mactop.metrics_source.ioreg import parse_battery
from mactop.metrics_source.ioreport import (
    Channel,
    IOReport,
    component_power,
    decode_frequencies,
    energy_to_watts,
    residency_metrics,
)
from mactop.metrics_source.macos import NativeError
from mactop.metrics_source.sensors import Sensors, average_temperature, decode_smc
from mactop.metrics_source.system import (
    SystemCollector,
    counter_rate,
    cpu_percentages,
    device_rates,
)
from mactop.metrics_store import IORegMetrics, Metrics, MetricsSnapshot


@pytest.mark.parametrize(
    "unit,energy",
    [
        ("J", 2),
        ("mJ", 2000),
        ("uJ", 2_000_000),
        ("µJ", 2_000_000),
        ("nJ", 2_000_000_000),
    ],
)
def test_energy_uses_actual_elapsed_time(unit, energy):
    assert energy_to_watts(energy, unit, 0.5) == pytest.approx(4)


@pytest.mark.parametrize(
    "energy,unit,elapsed",
    [
        (-1, "mJ", 1),
        (1, "unknown", 1),
        (1, "", 1),
        (1, "mJ", 0),
        (1, "mJ", float("nan")),
        (None, "mJ", 1),
    ],
)
def test_invalid_energy_is_unavailable(energy, unit, elapsed):
    assert energy_to_watts(energy, unit, elapsed) is None


def test_zero_power_and_component_aggregation_without_double_counting():
    channels = [
        Channel("Energy Model", "", "CPU Energy", "mJ", 200),
        Channel("Energy Model", "", "ECPU Energy", "mJ", 100),
        Channel("Energy Model", "", "ANE", "mJ", 0),
        Channel("Energy Model", "", "GPU Energy", "invalid", 100),
    ]
    assert component_power(channels, 0.5) == {"cpu": 0.4, "ane": 0.0}


def test_gpu_residency_excludes_idle_and_weights_active_frequency():
    states = [("OFF", 10), ("IDLE", 20), ("DOWN", 10), ("P1", 20), ("P2", 40)]
    idle, hz = residency_metrics(states, [300_000_000, 600_000_000])
    assert idle == pytest.approx(0.4)
    assert hz == pytest.approx(500_000_000)
    assert residency_metrics(states, [300_000_000]) == (idle, None)
    assert residency_metrics([("OFF", 100), ("P1", 0)], [300_000_000]) == (1.0, None)
    assert residency_metrics([("OFF", 0)]) == (None, None)
    assert residency_metrics([("P1", -1)]) == (None, None)


def test_frequency_table_units_and_unknown_mapping():
    def table(*values):
        return b"".join(struct.pack("<II", value, 0) for value in values)

    tables = {
        "voltage-states1-sram": table(1_020_000, 2_592_000),
        "voltage-states9": table(338_000_000, 618_000_000),
        "voltage-states5": table(52012, 43343),
    }
    assert frequency_table(tables, "ecpu") == [1_020_000_000, 2_592_000_000]
    assert frequency_table(tables, "gpu") == [338_000_000, 618_000_000]
    assert frequency_table(tables, "pcpu") == []
    assert frequency_table(tables, "unknown") == []
    assert decode_frequencies(b"bad") == []


@pytest.mark.parametrize(
    "kind,data,expected",
    [
        ("flt ", struct.pack("<f", 42.5), 42.5),
        ("sp78", b"\x2a\x80", 42.5),
        ("sp78", b"\xff\x00", -1),
        ("fpe2", b"\x1f\x40", 2000),
        ("ui32", b"\x00\x00\x01\x00", 256),
        ("flt ", struct.pack("<f", float("nan")), None),
        ("xxxx", b"\0", None),
    ],
)
def test_smc_numeric_types(kind, data, expected):
    assert decode_smc(kind, data) == expected


def test_hid_fallback_preserves_valid_smc_and_averages_all_valid_readings():
    assert average_temperature([None, 0, 50, 70, 180, float("nan")]) == 60
    sensors = Sensors.__new__(Sensors)
    sensors.smc = SimpleNamespace(
        cpu_keys=["Tp01"],
        gpu_keys=["Tg01"],
        read=lambda key: {"Tp01": 60, "F0Ac": 0, "PSTR": 12}.get(key),
    )
    sensors.hid = SimpleNamespace(temperatures=lambda: (90, 45))
    assert sensors.sample() == (60, 45, 0, 12)


def ticks(user, system, idle, nice=0):
    return SimpleNamespace(user=user, system=system, idle=idle, nice=nice)


def test_cpu_uses_tick_deltas_and_weighted_total():
    cores, total = cpu_percentages(
        [ticks(10, 20, 30), ticks(0, 0, 0)], [ticks(12, 21, 37), ticks(1, 1, 18)]
    )
    assert cores[0].user == 20
    assert cores[0].idle == 70
    assert cores[1].idle == 90
    assert total.idle == pytest.approx(25 / 30)
    assert cpu_percentages(None, [ticks(1, 2, 3)]) == (None, None)
    assert cpu_percentages([ticks(1, 2, 3)], [ticks(0, 2, 3)]) == (None, None)
    assert cpu_percentages([ticks(1, 2, 3)], [ticks(1, 2, 3)]) == (None, None)


def test_io_rates_reset_and_interface_churn():
    old = {
        "en0": SimpleNamespace(bytes_recv=100),
        "gone": SimpleNamespace(bytes_recv=1_000_000),
    }
    new = {
        "en0": SimpleNamespace(bytes_recv=500),
        "new": SimpleNamespace(bytes_recv=1_000_000),
    }
    assert device_rates(old, new, 2, ["bytes_recv"]) == {"bytes_recv": 200}
    assert counter_rate(100, 100, 0.5) == 0
    assert counter_rate(100, 50, 0.5) is None
    assert counter_rate(100, 500, 0) is None
    assert device_rates(old, {}, 2, ["bytes_recv"]) == {"bytes_recv": None}


def test_process_cpu_delta_pid_reuse_and_missing_permissions(monkeypatch):
    from mactop.metrics_source import system

    collector = SystemCollector()
    info = {
        "pid": 42,
        "name": "test",
        "create_time": 10,
        "cpu_times": ticks(1, 1, 0),
        "memory_info": SimpleNamespace(rss=2048, vms=4096),
    }
    monkeypatch.setattr(
        system.psutil, "process_iter", lambda **_: [SimpleNamespace(info=info)]
    )
    timer = iter([10, 12, 14, 16])
    monkeypatch.setattr(system.time, "monotonic", lambda: next(timer))
    sample = MetricsSnapshot()
    collector.processes(sample)
    assert sample.hardware.tasks[0]["cpu_percent"] is None
    info["cpu_times"] = ticks(3, 3, 0)
    collector.processes(sample)
    assert sample.hardware.tasks[0]["cpu_percent"] == 200
    assert sample.hardware.tasks[0]["rss_bytes"] == 2048
    info["create_time"] = 13
    collector.processes(sample)
    assert sample.hardware.tasks[0]["cpu_percent"] is None
    info["cpu_times"] = info["memory_info"] = None
    collector.processes(sample)
    assert sample.hardware.tasks[0]["rss_bytes"] is None


def test_missing_battery_and_bounded_history_do_not_mutate_prior_snapshot():
    prior = IORegMetrics()
    prior.apple_smart_battery.battery_capacity_history = [(0, 500)] * 3600
    result = parse_battery(
        {"AppleRawCurrentCapacity": 501, "ExternalConnected": True}, prior, 10
    )
    assert len(result.apple_smart_battery.battery_capacity_history) == 3600
    assert result.apple_smart_battery.battery_capacity_history[-1] == (10, 501)
    assert prior.apple_smart_battery.battery_capacity_history[-1] == (0, 500)
    assert result.apple_smart_battery.adapter_details.watts is None
    assert (
        parse_battery(None, prior).apple_smart_battery.apple_raw_current_capacity
        is None
    )


def test_histories_are_bounded_and_failed_samples_clear_stale_values():
    before, current = MetricsSnapshot(), MetricsSnapshot()
    before.hardware.power_history = {"cpu": [1] * 100}
    current.hardware.power_watts["cpu"] = 0
    append_histories(current, before)
    assert current.hardware.power_history["cpu"] == [1] * 99 + [0]
    assert before.hardware.power_history["cpu"] == [1] * 100
    missing = MetricsSnapshot()
    append_histories(missing, current)
    assert missing.hardware.power_history["cpu"] == []
    assert json.loads(snapshot_json(missing))["hardware"]["power_watts"]["cpu"] is None


def test_metrics_stores_have_independent_snapshots():
    first, second = Metrics(), Metrics()
    updated = MetricsSnapshot(timestamp=1)
    updated.hardware.power_watts["cpu"] = 4
    first.publish(updated)
    assert first.get_hardware().power_watts["cpu"] == 4
    assert second.get_hardware().power_watts["cpu"] is None
    assert (
        first.get_ioregmetrics().apple_smart_battery.apple_raw_current_capacity is None
    )


def test_ioreport_failure_releases_baseline_and_recovery_does_not_fake_delta():
    report = IOReport.__new__(IOReport)
    report.cf = SimpleNamespace(release=Mock())
    report.lib = SimpleNamespace(IOReportCreateSamples=Mock(side_effect=[None, 123]))
    report.subscription, report.channels = 1, ctypes.c_void_p(2)
    report.previous, report.timestamp = 99, 0
    with pytest.raises(NativeError, match="sample failed"):
        report.sample()
    report.cf.release.assert_called_with(99)
    assert report.sample() == ([], None)
    report.close()
    assert (
        report.previous is None and report.subscription is None and not report.channels
    )


def test_source_failure_does_not_stop_other_collectors(monkeypatch):
    from mactop.metrics_source import system

    monkeypatch.setattr(system.psutil, "cpu_times", Mock(side_effect=OSError("denied")))
    collector = SystemCollector()
    for method in ("memory", "swap", "load", "processes", "io"):
        monkeypatch.setattr(collector, method, Mock())
    sample = MetricsSnapshot()
    collector.sample(sample)
    assert sample.errors["cpu"] == "denied"
    assert sample.system.cpu_percent is None
    collector.memory.assert_called_once_with(sample)
    assert collector.io.call_count == 2


def test_ioreport_failure_still_publishes_system_and_battery():
    collector = MetricsCollector.__new__(MetricsCollector)
    collector.system = SimpleNamespace(
        sample=lambda sample: setattr(sample.system, "boot_time", 100)
    )
    collector.report = SimpleNamespace(
        sample=Mock(side_effect=NativeError("subscription lost"))
    )
    collector.kit = SimpleNamespace(battery=lambda: {"AppleRawCurrentCapacity": 500})
    collector.sensors = None
    collector.tables, collector.initial_errors = {}, {}
    collector.previous = MetricsSnapshot()
    sample = collector.sample()
    assert sample.errors == {"ioreport": "subscription lost"}
    assert sample.system.boot_time == 100
    assert sample.battery.apple_smart_battery.apple_raw_current_capacity == 500
    assert sample.hardware.power_watts["cpu"] is None


def test_manager_stop_interrupts_wait_and_closes_native_resources():
    primed, closed = threading.Event(), threading.Event()

    def sample():
        primed.set()
        return MetricsSnapshot()

    collector = SimpleNamespace(sample=sample, close=closed.set)
    manager = MetricsManager(
        interval=60, store=Metrics(), collector_factory=lambda: collector
    )
    manager.start()
    assert primed.wait(2)
    manager.stop()
    assert closed.is_set()
    assert not manager.thread.is_alive()


def test_manager_propagates_failure_to_json_reader_and_closes():
    closed = threading.Event()
    collector = SimpleNamespace(
        sample=Mock(side_effect=NativeError("failed")), close=closed.set
    )
    manager = MetricsManager(
        interval=0.01, store=Metrics(), collector_factory=lambda: collector
    )
    manager.start()
    try:
        with pytest.raises(RuntimeError, match="failed"):
            manager.next_sample()
    finally:
        manager.stop()
    assert closed.is_set()


@pytest.mark.parametrize("interval", [0, -1, float("inf"), float("nan")])
def test_invalid_interval(interval):
    with pytest.raises(ValueError):
        MetricsManager(interval)
