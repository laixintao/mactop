from rich.text import Text
from textual.widgets import DataTable

from mactop.metrics_store import metrics
from mactop.utils.formatting import sizeof_fmt_plain


class CPUPercent(str):
    """Keep display formatting while sorting CPU numerically, including N/A."""

    def __new__(cls, value):
        return super().__new__(cls, f"{'N/A':>9}" if value is None else f"{value:9.1f}")

    def __lt__(self, other):
        return (float(self) if self.strip() != "N/A" else -1) < (
            float(other) if other.strip() != "N/A" else -1
        )


class TaskTable(DataTable):
    """Process CPU is per-core percent; RSS/VMS are byte snapshots."""

    COLUMNS = (
        ("pid", "PID"),
        ("name", "PROCESS"),
        ("cpu_percent", "CPU % ↓"),
        ("rss_bytes", "MEMORY"),
        ("vms_bytes", "VIRTUAL"),
    )

    def __init__(self, refresh_interval, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refresh_interval = float(refresh_interval)
        self._table_width = None

    def on_mount(self):
        self.cursor_type = "row"
        self.show_cursor = False
        self.zebra_stripes = True
        self.border_title = "Processes"
        self.configure_columns()
        self.set_interval(self.refresh_interval, self.update_tasks)

    def on_resize(self):
        self.configure_columns()

    def on_focus(self):
        self.show_cursor = True

    def on_blur(self):
        self.show_cursor = False

    def configure_columns(self):
        width = self.scrollable_content_region.width
        if width <= 0 or self._table_width == width:
            return
        self._table_width = width
        self.clear(columns=True)
        widths = (7, max(12, width - 49), 9, 11, 11)
        for (key, label), column_width in zip(self.COLUMNS, widths):
            self.add_column(
                Text(label if key == "name" else label.rjust(column_width)),
                key=key,
                width=column_width,
            )
        self.update_tasks()

    def update_tasks(self):
        if not self.columns:
            return
        tasks = metrics.get_hardware().tasks
        count = "N/A" if tasks is None else f"{len(tasks)} processes"
        self.border_subtitle = f"{count} · CPU 100% = one core"
        tasks = tasks or []
        existing = {key.value for key in self.rows}
        current = {str(task["pid"]) for task in tasks}
        for key in existing - current:
            self.remove_row(key)
        for task in tasks:
            key = str(task["pid"])
            cells = [
                key.rjust(7),
                Text(task["name"], no_wrap=True, overflow="ellipsis"),
                CPUPercent(task["cpu_percent"]),
                (
                    "N/A"
                    if task["rss_bytes"] is None
                    else sizeof_fmt_plain(task["rss_bytes"])
                ).rjust(11),
                (
                    "N/A"
                    if task["vms_bytes"] is None
                    else sizeof_fmt_plain(task["vms_bytes"])
                ).rjust(11),
            ]
            if key not in existing:
                self.add_row(*cells, key=key)
            else:
                for (column, _), cell in zip(self.COLUMNS, cells):
                    self.update_cell(key, column, cell)
        self.sort("cpu_percent", reverse=True)
