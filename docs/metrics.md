# Metrics reference

Mactop collects metrics directly inside the Python process. Native bindings use
`ctypes` for CoreFoundation, IOKit, IOReport, AppleSMC, and IOHID. psutil supplies
the macOS Mach, sysctl, and libproc access used for system and process counters.

## Sampling and publication

`MetricsManager` owns one sampling thread. It initializes the readers, takes a
baseline sample, and then collects at the requested refresh interval. Each
collection creates a new `MetricsSnapshot`; the store publishes the completed
snapshot atomically. The dashboard and JSON output consume these snapshots.
Individual sources are read sequentially, so atomic publication does not imply
that every measurement was taken at exactly the same instant.

IOReport keeps its subscription and previous sample between updates. Each new
sample is compared with the previous one using
`IOReportCreateSamplesDelta()`. Power and I/O rates use actual elapsed monotonic
time. Changing the refresh interval changes the averaging window.

The JSON queue keeps the latest unread snapshot. If the output consumer is
slower than collection, older unread snapshots can be replaced. `--count`
counts emitted snapshots. Debug mode writes each published snapshot to disk.

Power and I/O histories retain at most 100 samples. An unavailable current
reading clears its history so an old value cannot appear as a fresh sample.
Battery capacity history retains at most 3,600 samples. Sampling stops and
native resources are closed when the application exits.

## Data sources and calculations

| Metric | Source | Calculation |
| --- | --- | --- |
| CPU, GPU, ANE, DRAM, GPU SRAM power | IOReport `Energy Model` | Energy delta in joules divided by elapsed seconds |
| GPU activity and frequency | IOReport `GPU Stats` and IORegistry frequency tables | Active residency fraction and active-time-weighted frequency |
| CPU cluster activity and frequency | IOReport `CPU Stats` and IORegistry frequency tables | Active residency fraction and active-time-weighted frequency |
| Per-core and total CPU activity | Mach CPU counters through psutil | Tick deltas for user, nice, system, and idle time |
| CPU and GPU temperature | AppleSMC, with IOHID fallback | Mean of valid sensor values |
| Whole-machine power | AppleSMC `PSTR` | Direct reading in watts |
| Fan speed | AppleSMC `F0Ac` | Direct reading in revolutions per minute |
| Battery and charger | IOKit `AppleSmartBattery` properties | Capacity, charging state, health inputs, temperature, and adapter values |
| Process CPU and memory | sysctl/libproc through psutil | CPU time delta, RSS, and virtual memory snapshots |
| Memory and swap | psutil | Current system snapshots |
| Network and disk activity | psutil per-interface and per-device counters | Counter delta divided by elapsed seconds |

### Power

```text
average power (W) = energy delta (J) / elapsed time (s)
```

Recognized energy units are `J`, `mJ`, `uJ`/`µJ`, and `nJ`. Channel names map
readings to components. If a `CPU Energy` total exists, it takes precedence
over per-cluster CPU energy channels to avoid double counting. Otherwise,
recognized CPU component channels are summed.

Unknown units, negative energy deltas, and invalid time intervals produce
unavailable readings. Whole-machine power is a separate SMC measurement, so it
need not equal the sum of the listed component values.

The dashboard's short power charts scale independently to their recent peak.
They show trends; use the numeric watt values to compare components.

### CPU and GPU activity

```text
CPU busy fraction = Δ(user + nice + system) / Δ(user + nice + system + idle)
active residency fraction = active residency / total residency
active frequency = Σ(state frequency × active state residency) / active residency
```

CPU busy values come from kernel tick counters. Cluster and GPU activity come
from performance-state residency, excluding `OFF`, `IDLE`, and `DOWN`. These
measure different kinds of activity and may differ.

Frequency is the average during active time. It is unavailable when there is
no active residency or when a frequency table cannot be matched unambiguously
to the reported states. The collector does not guess a frequency table.

### Memory, processes, and I/O

The dashboard computes RAM in use as `total - available` and displays its
fraction of total memory. JSON also includes psutil's separate `used`,
`active`, `inactive`, `wired`, and other memory fields; these should not be
treated as interchangeable definitions of RAM usage.

Process CPU is `Δ(user CPU seconds + system CPU seconds) / elapsed seconds ×
100`. A process can exceed 100% by using multiple cores. Processes are tracked
by PID and creation time, preventing PID reuse from carrying over a previous
process's CPU baseline. Newly observed processes can initially have `null` CPU
usage. RSS is resident memory; VMS is virtual address space rather than physical
memory consumption.

Network totals include all reported interfaces, including loopback. Rates use
devices present in both samples; a new device's lifetime counters are not
counted as activity in its first interval. Counter resets and unusable device
transitions establish a new baseline instead of producing a negative rate.

## JSON fields and units

Run `uv run mactop --json --count 1` for a complete snapshot from your machine.
The structure is defined by the dataclasses in
[metrics_store.py](../mactop/metrics_store.py).

| Field | Meaning and unit |
| --- | --- |
| `timestamp` | Unix wall-clock timestamp in seconds |
| `hardware.power_watts` | Component and whole-machine power in W |
| `hardware.power_history` | Recent component power samples in W |
| `hardware.m1_gpu.idle_ratio` | GPU idle fraction, from 0 to 1 |
| `hardware.m1_gpu.freq_hz` | Active-time-weighted GPU frequency in Hz |
| `hardware.processor_m1.clusters` | Named CPU clusters with idle fractions and frequencies in Hz |
| `hardware.smc.cpu_die`, `hardware.smc.gpu_die` | Temperatures in °C |
| `hardware.smc.fan` | Fan speed in rpm |
| `hardware.disk` | Read/write byte rates, operations per second, and histories |
| `hardware.network` | Inbound/outbound byte and packet rates, and histories |
| `hardware.tasks` | PID, name, per-core CPU percentage, `rss_bytes`, and `vms_bytes` |
| `system.cpu_percent_percpu` | Per-core user, nice, system, and idle percentages, from 0 to 100 |
| `system.cpu_percent` | Aggregate user, nice, system, and idle fractions, from 0 to 1 |
| `system.virtual_memory` | Memory fields in bytes, plus `percent` on a 0–100 scale |
| `system.swap_memory` | Swap byte fields and usage percentage on a 0–100 scale |
| `system.loadavg` | 1-, 5-, and 15-minute load averages |
| `system.boot_time` | Unix boot timestamp in seconds |
| `battery.apple_smart_battery` | Native battery and charger properties |
| `errors` | Source names mapped to diagnostic messages |

Battery capacities are in mAh, battery temperature is in hundredths of a degree
Celsius, adapter voltage is in mV, and adapter current is in mA. Adapter watts
are the reported charger value, not a measurement of current system power.
The dashboard converts battery temperature to °C and derives health from
maximum capacity divided by design capacity.

The `m1` field names are retained for compatibility and also carry readings
from newer Apple Silicon hardware. Unsupported legacy fields can remain `null`.

## Missing values and failures

An unavailable numeric reading is `null` in JSON and `N/A` in the dashboard.
Zero means a valid measured zero. Empty histories represent unavailable current
readings, and a missing process list is distinct from an empty process list.

Recoverable source failures are isolated so other metrics continue to update.
Source-level diagnostic messages appear in `errors`, the dashboard header,
and enabled logs. Individual unsupported readings, including an idle GPU's
active frequency, may be unavailable without a separate error entry. A fatal
collector failure publishes a diagnostic snapshot and causes a JSON stream to
exit with an error.

Channel names, sensor keys, and access permissions vary by hardware and macOS
version. For diagnostics, run:

```shell
uv run mactop --json --count 2 -vvv --log-to mactop.log --debug
```

## Source map

| Module | Responsibility |
| --- | --- |
| [collector.py](../mactop/metrics_source/collector.py) | Sampling lifecycle, source coordination, histories, and JSON serialization |
| [macos.py](../mactop/metrics_source/macos.py) | CoreFoundation and IOKit bindings and resource ownership |
| [ioreport.py](../mactop/metrics_source/ioreport.py) | Subscriptions, sample deltas, energy conversion, and residency calculations |
| [sensors.py](../mactop/metrics_source/sensors.py) | AppleSMC and IOHID temperature, fan, and system power readings |
| [system.py](../mactop/metrics_source/system.py) | psutil counters, process identity, and rates |
| [ioreg.py](../mactop/metrics_source/ioreg.py) | Battery property conversion and capacity history |
| [metrics_store.py](../mactop/metrics_store.py) | Snapshot dataclasses and atomic publication |
| [overview.py](../mactop/panels/overview.py) | Responsive dashboard cards and display formatting |
| [tasks.py](../mactop/panels/tasks.py) | Process table updates and numeric CPU sorting |
| [main.py](../mactop/main.py) | CLI options, keyboard navigation, and theme reloading |

Native API reference attribution is recorded in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
