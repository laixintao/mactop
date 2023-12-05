import logging
from textual.app import ComposeResult

from mactop.widgets import DynamicText, LabeledVStringBar
from mactop.metrics_store import metrics
from mactop.utils.formatting import sizeof_fmt_plain
from ._base import BaseStatic

logger = logging.getLogger(__name__)


class MemoryStatsText(BaseStatic):
    BORDER_TITLE = "Memory"

    DEFAULT_CSS = """
    MemoryStatsText {
      layout: grid;
    }
    """

    def __init__(self, label="", columns=4, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label
        self.columns = int(columns)

    def compose(self) -> ComposeResult:
        self.styles.grid_size_columns = self.columns
        yield DynamicText(
            prefix_label="available:",
            update_fn=lambda: metrics.get_psutilmetrics().virtual_memory.available,
            value_render_fn=sizeof_fmt_plain,
            classes="virtual-memory-text",
            update_interval=self.refresh_interval,
        )
        yield DynamicText(
            prefix_label="total:",
            update_fn=lambda: metrics.get_psutilmetrics().virtual_memory.total,
            value_render_fn=sizeof_fmt_plain,
            classes="virtual-memory-text",
            update_interval=self.refresh_interval,
        )
        yield DynamicText(
            prefix_label="used:",
            update_fn=lambda: metrics.get_psutilmetrics().virtual_memory.used,
            value_render_fn=sizeof_fmt_plain,
            classes="virtual-memory-text",
            update_interval=self.refresh_interval,
        )
        yield DynamicText(
            prefix_label="wired:",
            update_fn=lambda: metrics.get_psutilmetrics().virtual_memory.wired,
            value_render_fn=sizeof_fmt_plain,
            classes="virtual-memory-text",
            update_interval=self.refresh_interval,
        )
        yield DynamicText(
            prefix_label="free:",
            update_fn=lambda: metrics.get_psutilmetrics().virtual_memory.free,
            value_render_fn=sizeof_fmt_plain,
            classes="virtual-memory-text",
            update_interval=self.refresh_interval,
        )
        yield DynamicText(
            prefix_label="active:",
            update_fn=lambda: metrics.get_psutilmetrics().virtual_memory.active,
            value_render_fn=sizeof_fmt_plain,
            classes="virtual-memory-text",
            update_interval=self.refresh_interval,
        )
        yield DynamicText(
            prefix_label="inactive:",
            update_fn=lambda: metrics.get_psutilmetrics().virtual_memory.inactive,
            value_render_fn=sizeof_fmt_plain,
            classes="virtual-memory-text",
            update_interval=self.refresh_interval,
        )


def get_available_vm_percentages():
    vm = metrics.get_psutilmetrics().virtual_memory
    if not vm.total or not vm.available:
        return []
    return [
        vm.total - vm.available,
        vm.available,
    ]


def get_vm_display(*_):
    vm = metrics.get_psutilmetrics().virtual_memory
    if not vm.total or not vm.available:
        return []
    in_use = vm.total - vm.available
    u = sizeof_fmt_plain(in_use)
    t = sizeof_fmt_plain(vm.total)
    return f"{u}/{t}"


class MemoryUsageVBar(BaseStatic):
    BORDER_TITLE = "Memory"

    def __init__(self, label="Mem", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield LabeledVStringBar(
            prefix_label=self.label,
            color_choices=["red", "black"],
            update_interval=self.refresh_interval,
            percentages_update_fn=get_available_vm_percentages,
            value_render_fn=get_vm_display,
        )
