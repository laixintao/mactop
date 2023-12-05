from textual.app import ComposeResult

from mactop.widgets import DynamicText
from mactop.metrics_store import metrics
from ._base import BaseStatic


def refresh_callback(*_):
    loadavg = metrics.get_psutilmetrics().loadavg
    return f"[b]{loadavg.load1:.2f}[/b] {loadavg.load5:.2f} {loadavg.load15:.2f}"


class LoadAvgText(BaseStatic):
    BORDER_TITLE = "Load Average"

    def __init__(self, label="Load average: ", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield DynamicText(
            prefix_label=self.label,
            update_fn=refresh_callback,
            value_render_fn=lambda x: x,
            classes="loadavg-text",
            update_interval=self.refresh_interval,
        )
