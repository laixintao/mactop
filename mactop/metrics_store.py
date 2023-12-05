from dataclasses import dataclass, field

import psutil
from mactop.utils import RWLock
from typing import List, Tuple
import enum


class ProcessorType(enum.Enum):
    INTEL = "intel"
    M1 = "M1"


@dataclass
class Smc:
    cpu_die: int | None = None
    gpu_die: int | None = None
    fan: float | None = None


@dataclass
class PowerMetricsBattery:
    plugged_in: bool | None = None
    discharge_rate: float | None = None


@dataclass
class Netowrk:
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
    gpu_energy_ma: int | None = None
    gpu_energy_ma_history: List[float] | None = None
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
    cpus: List[CPU] | None = None


@dataclass
class M1ProcessorPackage:
    cpu_energy: float | None = None
    cpu_energy_history: List[float] | None = None
    gpu_energy: float | None = None
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
            if total_cores < core_index:
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
class PowerMetrics:
    backlight: int | None = None
    battery: PowerMetricsBattery = field(default_factory=PowerMetricsBattery)
    smc: Smc = field(default_factory=Smc)

    tasks: List[dict] | None = None
    processor_intel: ProcessorIntel = field(default_factory=ProcessorIntel)
    processor_type: ProcessorType | None = None

    network: Netowrk = field(default_factory=Netowrk)
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
    total_bytes: int | None = 0
    used_bytes: int | None = 0
    free_bytes: int | None = 0
    percent: float | None = 0
    sin_bytes: int | None = 0
    sout_bytes: int | None = 0


@dataclass
class VirtualMemory:
    total: int | None = 0
    available: int | None = 0
    percent: float | None = 0
    used: int | None = 0
    free: int | None = 0
    active: int | None = 0
    inactive: int | None = 0
    wired: int | None = 0


@dataclass
class LoadAvg:
    load1: float | None = 0
    load5: float | None = 0
    load15: float | None = 0


@dataclass
class PsutilMetrics:
    cpu_percent_percpu: List[CPUTimesPercent] | None = None
    cpu_percent: CPUTimesPercent = field(default_factory=CPUTimesPercent)
    cpu_count: int = psutil.cpu_count()
    cpu_physical_count: int = psutil.cpu_count(logical=False)
    swap_memory: SwapMemory = field(default_factory=SwapMemory)
    virtual_memory: VirtualMemory = field(default_factory=VirtualMemory)
    loadavg: LoadAvg = field(default_factory=LoadAvg)
    boot_time: float | None = None


@dataclass
class Metrics:
    powermetrics = PowerMetrics()
    ioregmetrics = IORegMetrics()
    psutilmetrics = PsutilMetrics()

    _powermetrics_rwlock = RWLock()
    _ioreg_rwlock = RWLock()

    def get_psutilmetrics(self):
        return self.psutilmetrics

    def set_psutilmetrics(self, p: PsutilMetrics):
        self.psutilmetrics = p

    def get_powermetrics(self):
        with self._powermetrics_rwlock.r_locked():
            return self.powermetrics

    def set_powermetrics(self, metrics):
        with self._powermetrics_rwlock.w_locked():
            self.ioregmetrics = metrics

    def get_ioregmetrics(self):
        with self._ioreg_rwlock.r_locked():
            return self.ioregmetrics

    def set_ioregmetrics(self, metrics):
        with self._ioreg_rwlock.w_locked():
            self.ioregmetrics = metrics


metrics = Metrics()
