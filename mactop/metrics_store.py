from dataclasses import dataclass, field

import psutil
import threading
from typing import List, Tuple
import enum


class ProcessorType(enum.Enum):
    INTEL = "intel"
    M1 = "M1"


@dataclass
class Smc:
    cpu_die: float | None = None
    gpu_die: float | None = None
    fan: float | None = None


@dataclass
class Network:
    ipacket_rate: float | None = None
    opacket_rate: float | None = None
    ibyte_rate: float | None = None
    obyte_rate: float | None = None

    ipacket_rate_history: List[float] | None = None
    opacket_rate_history: List[float] | None = None
    ibyte_rate_history: List[float] | None = None
    obyte_rate_history: List[float] | None = None


@dataclass
class CPU:
    cpu_number: int | None = None
    freq_hz: float | None = None
    freq_ratio: float | None = None


@dataclass
class M1GPU:
    idle_ratio: float | None = None
    freq_hz: float | None = None


@dataclass
class CPUCore:
    cpu_core_index: int | None = None
    c_state_ratio: float | None = None
    cpus: List[CPU] | None = None


@dataclass
class ProcessorPackage:
    cores: List[CPUCore] | None = None
    c_state_ratio: float | None = None


@dataclass
class M1CPUCluster:
    name: str | None = None
    idle_ratio: float | None = None
    freq_hz: float | None = None
    cpus: List[CPU] | None = None


@dataclass
class M1ProcessorPackage:
    clusters: List[M1CPUCluster] | None = None


@dataclass
class ProcessorIntel:
    package_watts_history: List[float] | None = None
    packages: List[ProcessorPackage] | None = None

    def get_core(self, core_index):
        if not self.packages:
            return
        for package in self.packages:
            if not package.cores:
                return
            total_cores = len(package.cores)
            if total_cores <= core_index:
                core_index -= total_cores
            else:
                return package.cores[core_index]


@dataclass
class Disk:
    rops_per_s: float | None = None
    wops_per_s: float | None = None
    rbytes_per_s: float | None = None
    wbytes_per_s: float | None = None

    rops_per_s_history: List[float] | None = None
    wops_per_s_history: List[float] | None = None
    rbytes_per_s_history: List[float] | None = None
    wbytes_per_s_history: List[float] | None = None


@dataclass
class HardwareMetrics:
    backlight: int | None = None
    smc: Smc = field(default_factory=Smc)

    # Window averages in W. Missing counters must not be represented as zero.
    power_watts: dict[str, float | None] = field(
        default_factory=lambda: dict.fromkeys(
            ("cpu", "gpu", "ane", "dram", "gpu_sram", "system")
        )
    )
    power_history: dict[str, List[float]] = field(default_factory=dict)

    tasks: List[dict] | None = None
    processor_intel: ProcessorIntel = field(default_factory=ProcessorIntel)
    processor_type: ProcessorType | None = None

    network: Network = field(default_factory=Network)
    disk: Disk = field(default_factory=Disk)

    m1_gpu: M1GPU = field(default_factory=M1GPU)
    processor_m1: M1ProcessorPackage = field(default_factory=M1ProcessorPackage)


@dataclass
class AdapterDetails:
    adapter_voltage: int | None = None
    current: int | None = None
    watts: int | None = None
    description: str | None = None

    manufacturer: str | None = None
    name: str | None = None


@dataclass
class AppleSmartBattery:
    # from https://opensource.apple.com/source/xnu/xnu-4570.71.2/iokit/IOKit/pwr_mgt/IOPMPowerSource.h.auto.html
    apple_raw_current_capacity: int | None = None
    apple_raw_max_capacity: int | None = None
    design_capacity: int | None = None
    temperature: int | None = None  # celsius * 100
    cycle_count: int | None = None

    # True if external power is capable of charging internal battery
    external_charge_cable: bool | None = None

    # True if computer is drawing external power
    external_connected: bool | None = None

    is_charging: bool | None = None

    adapter_details: AdapterDetails = field(default_factory=AdapterDetails)

    battery_capacity_history: List[Tuple[float, int]] | None = None


@dataclass
class IORegMetrics:
    apple_smart_battery: AppleSmartBattery = field(default_factory=AppleSmartBattery)


@dataclass
class CPUTimesPercent:
    user: float = 0
    nice: float = 0
    system: float = 0
    idle: float = 0


@dataclass
class SwapMemory:
    total_bytes: int | None = None
    used_bytes: int | None = None
    free_bytes: int | None = None
    percent: float | None = None
    sin_bytes: int | None = None
    sout_bytes: int | None = None


@dataclass
class VirtualMemory:
    total: int | None = None
    available: int | None = None
    percent: float | None = None
    used: int | None = None
    free: int | None = None
    active: int | None = None
    inactive: int | None = None
    wired: int | None = None


@dataclass
class LoadAvg:
    load1: float | None = None
    load5: float | None = None
    load15: float | None = None


@dataclass
class PsutilMetrics:
    cpu_percent_percpu: List[CPUTimesPercent] | None = None
    cpu_percent: CPUTimesPercent | None = None
    cpu_count: int = field(default_factory=lambda: psutil.cpu_count() or 1)
    cpu_physical_count: int = field(
        default_factory=lambda: psutil.cpu_count(logical=False) or 1
    )
    swap_memory: SwapMemory = field(default_factory=SwapMemory)
    virtual_memory: VirtualMemory = field(default_factory=VirtualMemory)
    loadavg: LoadAvg = field(default_factory=LoadAvg)
    boot_time: float | None = None


@dataclass
class MetricsSnapshot:
    timestamp: float | None = None
    hardware: HardwareMetrics = field(default_factory=HardwareMetrics)
    system: PsutilMetrics = field(default_factory=PsutilMetrics)
    battery: IORegMetrics = field(default_factory=IORegMetrics)
    errors: dict[str, str] = field(default_factory=dict)


class Metrics:
    """Publish whole snapshots; readers never see a partly updated sample."""

    def __init__(self):
        self._snapshot = MetricsSnapshot()
        self._lock = threading.Lock()

    def snapshot(self):
        with self._lock:
            return self._snapshot

    def publish(self, snapshot):
        with self._lock:
            self._snapshot = snapshot

    @property
    def psutilmetrics(self):
        return self.snapshot().system

    @property
    def ioregmetrics(self):
        return self.snapshot().battery

    def get_psutilmetrics(self):
        return self.snapshot().system

    def get_hardware(self):
        return self.snapshot().hardware

    def get_ioregmetrics(self):
        return self.snapshot().battery


metrics = Metrics()
