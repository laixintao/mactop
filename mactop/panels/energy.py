import logging


from textual.app import ComposeResult

from mactop.metrics_store import metrics
from mactop.widgets import LabeledSparkline
from ._base import BaseStatic

logger = logging.getLogger(__name__)


class IntelProcessorEnergyPanel(BaseStatic):
    BORDER_TITLE = "Energy"

    DEFAULT_CSS = """
    IntelProcessorEnergyPanel {
    }
    """

    def __init__(self, label="CPU Power", show_value=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        show_value = str(show_value).lower() == "true"
        if show_value:
            self.value_render_fn = lambda v: f" {v:.1f} W"
        else:
            self.value_render_fn = lambda *_: ""
        self.label = label

    def compose(self) -> ComposeResult:
        yield LabeledSparkline(
            update_fn=lambda: metrics.get_powermetrics().processor_intel.package_watts_history,
            value_render_fn=self.value_render_fn,
            update_interval=self.refresh_interval,
            prefix_label=self.label,
        )
