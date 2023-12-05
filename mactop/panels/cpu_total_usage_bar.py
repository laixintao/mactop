import logging


from textual.app import ComposeResult
from textual.containers import Vertical

from mactop.widgets import LabeledColorBar
from mactop.metrics_store import metrics
from mactop.utils.formatting import render_cpu_percentage_1
from ._base import BaseStatic
from mactop import const


logger = logging.getLogger(__name__)


def get_cpu_percentage():
    cpu_percent = metrics.get_psutilmetrics().cpu_percent

    return [
        cpu_percent.user,
        cpu_percent.nice,
        cpu_percent.system,
        cpu_percent.idle,
    ]




class CPUTotalUsageBarPanel(BaseStatic):
    BORDER_TITLE = "CPU"

    DEFAULT_CSS = """
    CPUTotalUsageBarPanel {
        height: 1;
    }
    """

    def __init__(
        self,
        color_user=const.COLOR_USER,
        color_nice=const.COLOR_NICE,
        color_system=const.COLOR_SYSTEM,
        color_idle=const.COLOR_IDLE,
        prefix="CPU: ",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.color_user = color_user
        self.color_nice = color_nice
        self.color_system = color_system
        self.color_idle = color_idle
        self.prefix = prefix

    def compose(self) -> ComposeResult:
        yield Vertical(
            LabeledColorBar(
                prefix_label=self.prefix,
                color_choices=[
                    self.color_user,
                    self.color_nice,
                    self.color_system,
                    self.color_idle,
                ],
                percentages_update_fn=get_cpu_percentage,
                value_render_fn=render_cpu_percentage_1,
                update_interval=self.refresh_interval,
            ),
        )
