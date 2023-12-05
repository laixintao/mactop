from textual.widgets import Label
from textual.app import ComposeResult

from mactop.widgets import DynamicText
from mactop.metrics_store import metrics
from mactop.utils.formatting import speed_sizeof_fmt
from ._base import BaseStatic


class NetworkIOByteRateText(BaseStatic):
    BORDER_TITLE = "Network Byte Rate"

    DEFAULT_CSS = """
    NetworkIOByteRateText {
        layout: horizontal;
    }
    NetworkIOByteRateText .network-speed {
        max-width: 14;
    }
    """

    def __init__(self, label="Network: ", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label, classes="network-iorate-byte-prefix")
        yield DynamicText(
            prefix_label="[b]↑[/b] ",
            update_fn=lambda: metrics.get_powermetrics().network.obyte_rate,
            value_render_fn=speed_sizeof_fmt,
            classes="network-speed",
            update_interval=self.refresh_interval,
        )
        yield Label(" " * 5, classes="network-iorate-byte-prefix")
        yield DynamicText(
            prefix_label="[b]↓[/b] ",
            update_fn=lambda: metrics.get_powermetrics().network.ibyte_rate,
            value_render_fn=speed_sizeof_fmt,
            classes="network-speed",
            update_interval=self.refresh_interval,
        )
