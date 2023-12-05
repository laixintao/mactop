from textual.widgets import Label
from textual.app import ComposeResult

from mactop.widgets import DynamicText
from mactop.metrics_store import metrics
from mactop.utils.formatting import sizeof_fmt_plain, sizeof_fmt
from ._base import BaseStatic
from mactop.widgets import LabeledVStringBar


class SwapMemoryInOutText(BaseStatic):
    BORDER_TITLE = "Swap memory"

    DEFAULT_CSS = """
    SwapMemoryInOutText {
        layout: horizontal;
    }
    SwapMemoryInOutText .swap-memory-inout {
        max-width: 20;
    }
    """

    def __init__(self, label="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label, classes="swap-memory-inout-label")
        yield DynamicText(
            prefix_label="sin: ",
            update_fn=lambda: metrics.get_psutilmetrics().swap_memory.sin_bytes,
            value_render_fn=sizeof_fmt,
            classes="swap-memory-inout",
            update_interval=self.refresh_interval,
        )
        yield Label(" " * 3, classes="swap-memory-inout-delimiter")
        yield DynamicText(
            prefix_label="sout: ",
            update_fn=lambda: metrics.get_psutilmetrics().swap_memory.sout_bytes,
            value_render_fn=sizeof_fmt,
            classes="swap-memory-inout",
            update_interval=self.refresh_interval,
        )


def get_swap_percentages():
    swap = metrics.get_psutilmetrics().swap_memory
    return [swap.used_bytes, swap.free_bytes]


def get_swap_display(*_):
    swap = metrics.get_psutilmetrics().swap_memory
    u = sizeof_fmt_plain(swap.used_bytes)
    t = sizeof_fmt_plain(swap.total_bytes)
    return f"{u}/{t}"


class SwapMemoryUsageVBar(BaseStatic):
    BORDER_TITLE = "Swap memory"

    def __init__(self, label="Swp", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield LabeledVStringBar(
            prefix_label=self.label,
            color_choices=["red", "black"],
            update_interval=self.refresh_interval,
            percentages_update_fn=get_swap_percentages,
            value_render_fn=get_swap_display,
        )
