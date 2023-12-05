from mactop.panels.battery import BacklightDisplayText, BatteryPanel
from mactop.panels.cpu_freq import CPUFreqPanel
from mactop.panels.cpu_percpu_usage import CPUUsageBarPanel
from mactop.panels.cpu_total_usage_bar import CPUTotalUsageBarPanel
from mactop.panels.cpu_total_usage_text import CPUTotalUsageTextPanel
from mactop.panels.disk import (
    DiskIOBytesPerSText,
    DiskIOOpsPerSText,
    DiskRBytesPerSSparkline,
    DiskROpsPerSSparkline,
    DiskWBytesPerSSparkline,
    DiskWOpsPerSSparkline,
)
from mactop.panels.energy import IntelProcessorEnergyPanel
from mactop.panels.loadavg import LoadAvgText
from mactop.panels.m1_cpu import M1CPUEnergyPanel
from mactop.panels.m1_gpu import GPUFreqText, GPUUsageBarPanel, M1GPUEnergyPanel
from mactop.panels.m1cpu_freq import M1CPUFreqPanel
from mactop.panels.network_iobyte_rate_text import NetworkIOByteRateText
from mactop.panels.network_iopacket_rate_text import NetworkIOPacketRateText
from mactop.panels.network_sparkline import (
    NetworkIByteRateSparkline,
    NetworkIPacketRateSparkline,
    NetworkOByteRateSparkline,
    NetworkOPacketRateSparkline,
)
from mactop.panels.sensors import SensorsPanel
from mactop.panels.swap_memory import SwapMemoryInOutText, SwapMemoryUsageVBar
from mactop.panels.tasks import TaskTable
from mactop.panels.uptime import UptimeText
from mactop.panels.virtual_memory import MemoryStatsText, MemoryUsageVBar

PANELS = {
    "SensorsPanel": SensorsPanel,
    "BatteryPanel": BatteryPanel,
    "TaskTable": TaskTable,
    "IntelProcessorEnergyPanel": IntelProcessorEnergyPanel,
    "CPUTotalUsageBarPanel": CPUTotalUsageBarPanel,
    "CPUTotalUsageTextPanel": CPUTotalUsageTextPanel,
    "CPUUsageBarPanel": CPUUsageBarPanel,
    "NetworkIOByteRateText": NetworkIOByteRateText,
    "NetworkIByteRateSparkline": NetworkIByteRateSparkline,
    "NetworkOByteRateSparkline": NetworkOByteRateSparkline,
    "NetworkIPacketRateSparkline": NetworkIPacketRateSparkline,
    "NetworkOPacketRateSparkline": NetworkOPacketRateSparkline,
    "NetworkIOPacketRateText": NetworkIOPacketRateText,
    "SwapMemoryInOutText": SwapMemoryInOutText,
    "SwapMemoryUsageVBar": SwapMemoryUsageVBar,
    "MemoryStatsText": MemoryStatsText,
    "MemoryUsageVBar": MemoryUsageVBar,
    "DiskIOOpsPerSText": DiskIOOpsPerSText,
    "DiskIOBytesPerSText": DiskIOBytesPerSText,
    "DiskROpsPerSSparkline": DiskROpsPerSSparkline,
    "DiskWOpsPerSSparkline": DiskWOpsPerSSparkline,
    "DiskRBytesPerSSparkline": DiskRBytesPerSSparkline,
    "DiskWBytesPerSSparkline": DiskWBytesPerSSparkline,
    "LoadAvgText": LoadAvgText,
    "UptimeText": UptimeText,
    "CPUFreqPanel": CPUFreqPanel,
    "GPUFreqText": GPUFreqText,
    "GPUUsageBarPanel": GPUUsageBarPanel,
    "M1GPUEnergyPanel": M1GPUEnergyPanel,
    "M1CPUEnergyPanel": M1CPUEnergyPanel,
    "M1CPUFreqPanel": M1CPUFreqPanel,
    "BacklightDisplayText": BacklightDisplayText,
}
