import logging


from textual.app import ComposeResult
from textual.containers import Vertical

from mactop.metrics_store import metrics
from mactop.widgets.labeled_progress import LabelProgressWidget
from ._base import BaseStatic

logger = logging.getLogger(__name__)


class SensorsPanel(BaseStatic):
    BORDER_TITLE = "Sensors"

    DEFAULT_CSS = """
    SensorsPanel {
        border-title-align: left;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            LabelProgressWidget(
                update_fn=lambda: metrics.get_powermetrics().smc.cpu_die,
                value_render_fn=lambda cput: f"{cput:.1f} °C",
                update_interval=self.refresh_interval,
                progress_total=120,
                prefix_label="CPU",
            ),
            LabelProgressWidget(
                update_fn=lambda: metrics.get_powermetrics().smc.gpu_die,
                value_render_fn=lambda cput: f"{cput:.1f} °C",
                update_interval=self.refresh_interval,
                progress_total=120,
                prefix_label="GPU",
            ),
            LabelProgressWidget(
                update_fn=lambda: metrics.get_powermetrics().smc.fan,
                value_render_fn=lambda cput: f"{cput:.1f} RPM",
                update_interval=self.refresh_interval,
                progress_total=7000,
                prefix_label="FAN",
            ),
        )
