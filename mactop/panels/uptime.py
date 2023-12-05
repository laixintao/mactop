import time
from datetime import timedelta
from textual.app import ComposeResult

from mactop.widgets import DynamicText
from mactop.metrics_store import metrics
from ._base import BaseStatic


def refresh_callback(*_):
    boot_time = metrics.get_psutilmetrics().boot_time
    if not boot_time:
        return "  "
    uptime_s = int(time.time() - boot_time)
    return str(timedelta(seconds=uptime_s))


class UptimeText(BaseStatic):
    BORDER_TITLE = "Uptime"

    def __init__(self, label="Uptime: ", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield DynamicText(
            prefix_label=self.label,
            update_fn=refresh_callback,
            value_render_fn=lambda x: x,
            classes="uptime-text",
            update_interval=self.refresh_interval,
        )
