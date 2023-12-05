from textual.widgets import Label
from textual.app import ComposeResult

from mactop.widgets import DynamicText
from mactop.metrics_store import metrics
from mactop.utils.formatting import packet_speed_fmt
from ._base import BaseStatic


class NetworkIOPacketRateText(BaseStatic):
    BORDER_TITLE = "Network Packet Rate"

    DEFAULT_CSS = """
    NetworkIOPacketRateText {
        layout: horizontal;
    }
    NetworkIOPacketRateText .network-speed {
        max-width: 19;
    }
    """

    def __init__(self, label="Network: ", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label, classes="network-iorate-packet-prefix")
        yield DynamicText(
            prefix_label="[b]↑[/b] ",
            update_fn=lambda: metrics.get_powermetrics().network.opacket_rate,
            value_render_fn=packet_speed_fmt,
            classes="network-speed",
            update_interval=self.refresh_interval,
        )
        yield Label(" " * 5, classes="network-iorate-packet-prefix")
        yield DynamicText(
            prefix_label="[b]↓[/b] ",
            update_fn=lambda: metrics.get_powermetrics().network.ipacket_rate,
            value_render_fn=packet_speed_fmt,
            classes="network-speed",
            update_interval=self.refresh_interval,
        )
