"""IOReport energy and performance-state counters, sampled without root.

ABI and channel conventions reference context-labs/mactop (MIT); see
THIRD_PARTY_NOTICES.md. All owned CF objects are released by this module.
"""

import ctypes as C
import math
import struct
import time
from dataclasses import dataclass, field

from .macos import CoreFoundation, NativeError, bind


@dataclass
class Channel:
    group: str
    subgroup: str
    name: str
    unit: str = ""
    value: int | None = None
    states: list[tuple[str, int]] = field(default_factory=list)


def energy_to_watts(energy, unit, elapsed):
    """Unknown units and counter resets are unavailable, not zero power."""
    scale = {"J": 1, "mJ": 1e-3, "uJ": 1e-6, "µJ": 1e-6, "nJ": 1e-9}.get(unit.strip())
    if (
        scale is None
        or energy is None
        or energy < 0
        or not math.isfinite(elapsed)
        or elapsed <= 0
    ):
        return None
    return energy * scale / elapsed


def decode_frequencies(data):
    if not data or len(data) % 8:
        return []
    # IORegistry stores little-endian (frequency in Hz, voltage) pairs.
    return [freq for freq, _ in struct.iter_unpack("<II", data) if freq > 0]


def residency_metrics(states, frequencies=()):
    """Return idle fraction and active-time-weighted Hz, preserving missing data."""
    if not states or any(ticks < 0 for _, ticks in states):
        return None, None
    total = sum(ticks for _, ticks in states)
    if total <= 0:
        return None, None
    active = [
        (name, ticks)
        for name, ticks in states
        if name.upper() not in {"OFF", "IDLE", "DOWN"}
    ]
    active_time = sum(ticks for _, ticks in active)
    idle = 1 - active_time / total
    if not active_time:
        return idle, None
    # Only use a table when every active state has an unambiguous counterpart.
    if len(active) != len(frequencies):
        return idle, None
    return (
        idle,
        sum(ticks * freq for (_, ticks), freq in zip(active, frequencies))
        / active_time,
    )


def component_power(channels, elapsed):
    values = {}
    invalid = set()
    has_cpu_total = any(
        channel.group == "Energy Model" and channel.name == "CPU Energy"
        for channel in channels
    )
    for channel in channels:
        if channel.group != "Energy Model":
            continue
        name = channel.name
        component = None
        if "CPU Energy" in name:
            if has_cpu_total and name != "CPU Energy":
                continue
            component = "cpu"
        elif name == "GPU Energy":
            component = "gpu"
        elif name.startswith("ANE"):
            component = "ane"
        elif name.startswith("DRAM"):
            component = "dram"
        elif name.startswith("GPU SRAM"):
            component = "gpu_sram"
        if component:
            watts = energy_to_watts(channel.value, channel.unit, elapsed)
            if watts is None:
                invalid.add(component)
            else:
                values[component] = values.get(component, 0.0) + watts
    return {name: value for name, value in values.items() if name not in invalid}


class IOReport:
    def __init__(self, cf=None):
        self.cf = cf or CoreFoundation()
        self.lib = C.CDLL("/usr/lib/libIOReport.dylib")
        self.subscription = None
        self.channels = C.c_void_p()
        self.previous = None
        self.timestamp = None
        signatures = {
            "IOReportCopyChannelsInGroup": (
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
                C.c_uint64,
                C.c_uint64,
                C.c_uint64,
            ),
            "IOReportMergeChannels": (None, C.c_void_p, C.c_void_p, C.c_void_p),
            "IOReportCreateSubscription": (
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
                C.POINTER(C.c_void_p),
                C.c_uint64,
                C.c_void_p,
            ),
            "IOReportCreateSamples": (C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p),
            "IOReportCreateSamplesDelta": (
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
            ),
            "IOReportSimpleGetIntegerValue": (C.c_int64, C.c_void_p, C.c_int32),
            "IOReportStateGetCount": (C.c_int32, C.c_void_p),
            "IOReportStateGetNameForIndex": (C.c_void_p, C.c_void_p, C.c_int32),
            "IOReportStateGetResidency": (C.c_int64, C.c_void_p, C.c_int32),
        }
        for suffix in ("Group", "SubGroup", "ChannelName", "UnitLabel"):
            signatures[f"IOReportChannelGet{suffix}"] = (C.c_void_p, C.c_void_p)
        for name, signature in signatures.items():
            bind(self.lib, name, *signature)
        requested = None
        try:
            for group in ("Energy Model", "GPU Stats", "CPU Stats"):
                with self.cf.string(group) as name:
                    extra = self.lib.IOReportCopyChannelsInGroup(name, None, 0, 0, 0)
                if not extra:
                    continue
                if requested:
                    self.lib.IOReportMergeChannels(requested, extra, None)
                    self.cf.release(extra)
                else:
                    requested = extra
            if not requested:
                raise NativeError("IOReport has no energy or residency channels")
            self.subscription = self.lib.IOReportCreateSubscription(
                None, requested, C.byref(self.channels), 0, None
            )
            if not self.subscription or not self.channels:
                raise NativeError("IOReport subscription failed")
        except Exception:
            self.close()
            raise
        finally:
            self.cf.release(requested)

    def sample(self):
        current = self.lib.IOReportCreateSamples(self.subscription, self.channels, None)
        now = time.monotonic()
        if not current:
            self.cf.release(self.previous)
            self.previous = None
            self.timestamp = None
            raise NativeError("IOReport sample failed")
        previous, before = self.previous, self.timestamp
        self.previous, self.timestamp = current, now
        if not previous:
            return [], None
        delta = None
        try:
            delta = self.lib.IOReportCreateSamplesDelta(previous, current, None)
            if not delta:
                raise NativeError("IOReport delta failed")
            array = self.cf.get(delta, "IOReportChannels")
            if not array:
                raise NativeError("IOReport sample has no channels")
            result = []
            for item in self.cf.items(array):

                def text(suffix):
                    return self.cf.text(
                        getattr(self.lib, f"IOReportChannelGet{suffix}")(item)
                    )

                channel = Channel(
                    text("Group"),
                    text("SubGroup"),
                    text("ChannelName"),
                    text("UnitLabel"),
                )
                if channel.group == "Energy Model":
                    channel.value = self.lib.IOReportSimpleGetIntegerValue(item, 0)
                elif "Performance States" in channel.subgroup:
                    count = self.lib.IOReportStateGetCount(item)
                    if not 0 <= count <= 256:
                        raise NativeError(f"Invalid IOReport state count: {count}")
                    channel.states = [
                        (
                            self.cf.text(
                                self.lib.IOReportStateGetNameForIndex(item, i)
                            ),
                            self.lib.IOReportStateGetResidency(item, i),
                        )
                        for i in range(count)
                    ]
                result.append(channel)
            return result, now - before
        finally:
            self.cf.release(delta)
            self.cf.release(previous)

    def close(self):
        self.cf.release(self.previous)
        self.previous = None
        self.cf.release(self.subscription)
        self.subscription = None
        self.cf.release(self.channels)
        self.channels = C.c_void_p()
        self.timestamp = None
