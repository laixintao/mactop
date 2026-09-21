"""Compact, responsive presentation of a single published metrics snapshot."""

import math
import time

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mactop.metrics_store import metrics
from mactop.panels._base import BaseStatic


TEXT = "#dce5ee"
MUTED = "#8293a7"
LINE = "#29394b"
CYAN = "#75cbd3"
GREEN = "#9bc59b"
AMBER = "#e0b77b"
PURPLE = "#b0a6db"


def number(value, unit="", precision=1):
    return "N/A" if value is None else f"{value:.{precision}f}{unit}"


def byte_size(value):
    if value is None:
        return "N/A"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024


def rate(value):
    return "N/A" if value is None else f"{byte_size(value)}/s"


def capacity(used, total):
    if used is None or total is None:
        return "N/A"
    divisor, unit = 1, "B"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(total) / divisor < 1024 or unit == "TiB":
            break
        divisor *= 1024
    return f"{used / divisor:.1f} / {total / divisor:.1f} {unit}"


def ratio(used, total):
    if used is None or total is None:
        return None
    return used / total if total > 0 else 0.0


def memory_used(memory):
    if memory.total is not None and memory.available is not None:
        return memory.total - memory.available
    return memory.used


def meter(value, width=12, color=CYAN):
    filled = round(max(0, min(1, value or 0)) * width)
    return Text.assemble(("━" * filled, color), ("━" * (width - filled), LINE))


def trend(values, width=12):
    """A short, zero-based history; never stretch one sample across the screen."""
    if not values:
        return Text("·" * width, LINE)
    values = values[-width:]
    peak = max(values)
    bars = "▁▂▃▄▅▆▇█"
    graph = "".join(
        bars[round(max(0, value) / peak * 7)] if peak > 0 else "▁" for value in values
    )
    return Text.assemble(("·" * (width - len(values)), LINE), (graph, AMBER))


def pairs(*items):
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(style=MUTED, no_wrap=True, ratio=1)
    table.add_column(justify="right", style=TEXT, no_wrap=True, overflow="ellipsis")
    for label, value in items:
        table.add_row(label, value)
    return table


def card(title, body, height=None):
    title_text = Text(title)
    title_text.stylize(MUTED)
    return Panel(
        body,
        title=title_text,
        title_align="left",
        border_style=LINE,
        padding=(0, 1),
        height=height,
    )


def row(*cards, ratios=None):
    table = Table.grid(expand=True, padding=(0, 1))
    for weight in ratios or [1] * len(cards):
        table.add_column(ratio=weight, overflow="crop")
    table.add_row(*cards)
    return table


class OverviewPanel(BaseStatic):
    DEFAULT_CSS = """
    OverviewPanel {
        height: auto;
        color: #dce5ee;
    }
    """

    def on_mount(self):
        self.set_interval(self.refresh_interval, lambda: self.refresh(layout=True))

    def on_resize(self):
        self.refresh(layout=True)

    def render(self):
        snapshot = metrics.snapshot()
        hardware, system = snapshot.hardware, snapshot.system
        width = max(24, self.size.width)
        wide = width >= 110
        narrow = width < 64
        cpu_width = width if narrow else (width - (4 if wide else 2)) // 2
        core_columns = 4 if cpu_width >= 36 else 2
        clusters = hardware.processor_m1.clusters or []
        cpu_height = math.ceil(system.cpu_count / core_columns) + len(clusters) + 3
        main_height = max(10, cpu_height)
        cpu = card(
            f"CPU · {system.cpu_count} cores",
            self.cpu(snapshot, cpu_width - 4, core_columns),
            main_height,
        )
        power_width = (
            width if narrow else ((width - 4) // 4 if wide else (width - 2) // 2)
        )
        power = card(
            "Power & thermals", self.power(snapshot, power_width - 4), main_height
        )
        memory = card(
            "Memory & system",
            self.memory(snapshot, spacious=wide),
            main_height if wide else 8,
        )
        battery = card(
            "Battery", self.battery(snapshot, compact=wide), 6 if wide else 8
        )
        disk = card("Disk", self.disk(snapshot), 6)
        network = card("Network", self.network(snapshot), 6)
        summary = self.summary(snapshot, narrow)
        if narrow:
            return Group(summary, cpu, power, memory, disk, network, battery)
        if wide:
            return Group(
                summary,
                "",
                row(cpu, power, memory, ratios=[2, 1, 1]),
                "",
                row(disk, network, battery),
            )
        return Group(
            summary,
            "",
            row(cpu, power),
            "",
            row(
                card("Memory & I/O", self.compact_io(snapshot), 8),
                card("Battery & system", self.compact_battery(snapshot), 8),
            ),
        )

    def summary(self, snapshot, narrow):
        hardware, system = snapshot.hardware, snapshot.system
        cpu = system.cpu_percent
        gpu = hardware.m1_gpu
        memory = system.virtual_memory
        used = ratio(memory_used(memory), memory.total)
        items = [
            (
                "CPU",
                number(None if cpu is None else (1 - cpu.idle) * 100, "%"),
                f"{system.cpu_count} cores",
                CYAN,
            ),
            (
                "GPU",
                number(
                    None if gpu.idle_ratio is None else (1 - gpu.idle_ratio) * 100, "%"
                ),
                number(None if gpu.freq_hz is None else gpu.freq_hz / 1e6, " MHz", 0),
                PURPLE,
            ),
            (
                "Memory",
                number(None if used is None else used * 100, "%"),
                byte_size(memory_used(memory)),
                GREEN,
            ),
            (
                "System power",
                number(hardware.power_watts.get("system"), " W", 2),
                "whole machine",
                AMBER,
            ),
        ]
        cards = [
            card(
                title,
                Group(
                    Text(value, f"bold {color}"),
                    Text(hint, MUTED, no_wrap=True, overflow="ellipsis"),
                ),
            )
            for title, value, hint, color in items
        ]
        return Group(row(*cards[:2]), row(*cards[2:])) if narrow else row(*cards)

    def cpu(self, snapshot, width, columns):
        system = snapshot.system
        table = Table.grid(expand=True, padding=(0, 1))
        for _ in range(columns):
            table.add_column(ratio=1, no_wrap=True)
        cores = system.cpu_percent_percpu or []
        bar_width = min(10, max(0, width // columns - 10))
        cells = []
        for index in range(system.cpu_count):
            busy = 100 - cores[index].idle if index < len(cores) else None
            cell = Text(f"{index:02d} ", MUTED)
            if bar_width:
                cell.append_text(meter(None if busy is None else busy / 100, bar_width))
                cell.append(" ")
            cell.append(
                f"{number(busy, '%', 0):>4}", CYAN if busy is not None else MUTED
            )
            cells.append(cell)
        for start in range(0, len(cells), columns):
            table.add_row(*cells[start : start + columns])
        clusters = snapshot.hardware.processor_m1.clusters or []
        cluster_table = pairs(
            *[
                (
                    cluster.name or "CPU",
                    Text.assemble(
                        (
                            number(
                                (
                                    None
                                    if cluster.freq_hz is None
                                    else cluster.freq_hz / 1e6
                                ),
                                " MHz",
                                0,
                            ),
                            TEXT,
                        ),
                        ("  ·  ", LINE),
                        (
                            number(
                                (
                                    None
                                    if cluster.idle_ratio is None
                                    else (1 - cluster.idle_ratio) * 100
                                ),
                                "%",
                                0,
                            ),
                            MUTED,
                        ),
                    ),
                )
                for cluster in clusters
            ]
        )
        return Group(table, "", cluster_table) if clusters else table

    def power(self, snapshot, width):
        hardware = snapshot.hardware
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(style=MUTED, width=6)
        table.add_column(ratio=1, no_wrap=True, overflow="crop")
        table.add_column(justify="right", style=TEXT, width=8)
        for key, label in (
            ("cpu", "CPU"),
            ("gpu", "GPU"),
            ("ane", "ANE"),
            ("dram", "DRAM"),
            ("system", "System"),
        ):
            table.add_row(
                label,
                trend(hardware.power_history.get(key), min(12, max(1, width - 20))),
                number(hardware.power_watts.get(key), " W", 2),
            )
        return Group(
            table,
            "",
            pairs(
                (
                    "CPU / GPU",
                    f"{number(hardware.smc.cpu_die, '°', 0)} / {number(hardware.smc.gpu_die, '°', 0)}",
                ),
                ("Fan", number(hardware.smc.fan, " rpm", 0)),
            ),
        )

    def memory(self, snapshot, spacious=False):
        memory, swap = snapshot.system.virtual_memory, snapshot.system.swap_memory
        used = memory_used(memory)
        sections = [
            pairs(("RAM", capacity(used, memory.total))),
            meter(ratio(used, memory.total), 16, GREEN),
            pairs(("Swap", capacity(swap.used_bytes, swap.total_bytes))),
            meter(ratio(swap.used_bytes, swap.total_bytes), 16, PURPLE),
            self.system(snapshot),
        ]
        if spacious:
            sections.insert(4, "")
            sections.insert(2, "")
        return Group(*sections)

    def system(self, snapshot):
        load = snapshot.system.loadavg
        boot = snapshot.system.boot_time
        if boot is None:
            uptime = "N/A"
        else:
            hours, minutes = divmod(
                max(0, int(((snapshot.timestamp or time.time()) - boot) / 60)), 60
            )
            days, hours = divmod(hours, 24)
            uptime = f"{days}d {hours:02d}h {minutes:02d}m"
        return pairs(
            (
                "Load",
                "  ".join(
                    number(value, precision=2)
                    for value in (load.load1, load.load5, load.load15)
                ),
            ),
            ("Up", uptime),
        )

    def compact_io(self, snapshot):
        memory, swap = snapshot.system.virtual_memory, snapshot.system.swap_memory
        disk, network = snapshot.hardware.disk, snapshot.hardware.network
        return pairs(
            ("RAM", capacity(memory_used(memory), memory.total)),
            ("Swap", capacity(swap.used_bytes, swap.total_bytes)),
            ("Disk read", rate(disk.rbytes_per_s)),
            ("Disk write", rate(disk.wbytes_per_s)),
            ("↓ Network", rate(network.ibyte_rate)),
            ("↑ Network", rate(network.obyte_rate)),
        )

    def compact_battery(self, snapshot):
        return Group(self.battery(snapshot, compact=True), self.system(snapshot))

    def disk(self, snapshot):
        disk = snapshot.hardware.disk
        return pairs(
            ("Read", rate(disk.rbytes_per_s)),
            ("Write", rate(disk.wbytes_per_s)),
            ("Read IOPS", number(disk.rops_per_s, precision=0)),
            ("Write IOPS", number(disk.wops_per_s, precision=0)),
        )

    def network(self, snapshot):
        network = snapshot.hardware.network
        return pairs(
            ("↓ In", rate(network.ibyte_rate)),
            ("↑ Out", rate(network.obyte_rate)),
            ("Packets in", number(network.ipacket_rate, "/s", 0)),
            ("Packets out", number(network.opacket_rate, "/s", 0)),
        )

    def battery(self, snapshot, compact=False):
        battery = snapshot.battery.apple_smart_battery
        capacity = ratio(
            battery.apple_raw_current_capacity, battery.apple_raw_max_capacity
        )
        health = ratio(battery.apple_raw_max_capacity, battery.design_capacity)
        if battery.external_connected is None:
            state = "N/A"
        elif battery.is_charging:
            state = "Charging"
        elif battery.external_connected:
            state = "AC · not charging"
        else:
            state = "On battery"
        charge = number(None if capacity is None else capacity * 100, "%", 0)
        health = number(None if health is None else health * 100, "%", 0)
        temperature = number(
            None if battery.temperature is None else battery.temperature / 100, " °C"
        )
        if compact:
            return pairs(
                (Text(charge, f"bold {GREEN}"), state),
                ("Adapter", number(battery.adapter_details.watts, " W", 0)),
                (
                    "Health / cycles",
                    f"{health} / {number(battery.cycle_count, precision=0)}",
                ),
                ("Temperature", temperature),
            )
        return Group(
            pairs((Text(charge, f"bold {GREEN}"), state)),
            meter(capacity, 16, GREEN),
            pairs(
                ("Adapter", number(battery.adapter_details.watts, " W", 0)),
                ("Health", health),
                ("Cycles", number(battery.cycle_count, precision=0)),
                ("Temperature", temperature),
            ),
        )
