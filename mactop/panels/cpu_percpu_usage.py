import logging
from functools import partial


from textual.app import ComposeResult

from mactop.widgets import LabeledColorBar
from mactop.metrics_store import metrics
from mactop.utils.formatting import render_cpu_percentage_100
from ._base import BaseStatic
from mactop import const


logger = logging.getLogger(__name__)


def get_percpu_percent(index):
    cpus = metrics.psutilmetrics.cpu_percent_percpu
    if not cpus:
        return [0, 0, 0, 0]
    cpu_percent = cpus[index]
    return [
        cpu_percent.user,
        cpu_percent.nice,
        cpu_percent.system,
        cpu_percent.idle,
    ]


class CPUUsageBarPanel(BaseStatic):
    BORDER_TITLE = "CPU"

    DEFAULT_CSS = """
    CPUUsageBarPanel {
        layout: grid;
        grid-gutter: 0 1;
    }
    """

    def __init__(
        self,
        color_user=const.COLOR_USER,
        color_nice=const.COLOR_NICE,
        color_system=const.COLOR_SYSTEM,
        color_idle=const.COLOR_IDLE,
        columns=4,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.color_user = color_user
        self.color_nice = color_nice
        self.color_system = color_system
        self.color_idle = color_idle
        self.columns = int(columns)

    def compose(self) -> ComposeResult:
        self.styles.grid_size_columns = self.columns
        cpu_count = metrics.psutilmetrics.cpu_count
        for index in range(cpu_count):
            yield LabeledColorBar(
                prefix_label=f"[#FFFFE0]{index:>2}[/#FFFFE0]",
                color_choices=[
                    self.color_user,
                    self.color_nice,
                    self.color_system,
                    self.color_idle,
                ],
                percentages_update_fn=partial(get_percpu_percent, index=index),
                value_render_fn=render_cpu_percentage_100,
                update_interval=self.refresh_interval,
            )
