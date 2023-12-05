import textual
import logging
from rich.console import RenderableType
from rich.text import Text


from textual.app import ComposeResult
from textual.widget import Widget
from textual.reactive import reactive
from ._base import BaseStatic

from .cpu_total_usage_bar import get_cpu_percentage
from mactop import const


logger = logging.getLogger(__name__)


class Legend(Widget):
    current_value = reactive("N/A")

    def __init__(
        self,
        legend_color,
        legend_text,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.legend_color = legend_color
        self.legend_text = legend_text

    def render(self) -> RenderableType:
        t = Text.assemble(
            (f"█ {self.legend_text} ", self.legend_color), self.current_value
        )

        return t


class CPUTotalUsageTextPanel(BaseStatic):
    BORDER_TITLE = "CPU"

    DEFAULT_CSS = """
    CPUTotalUsageTextPanel {
        layout: horizontal;
        margin-top: 1;
        border-title-align: left;
        height: 1;
    }

    CPUTotalUsageTextPanel Legend {
        content-align-horizontal: center;
        width: 25%;
    }
    """

    percentages = reactive(None)

    def __init__(
        self,
        color_user=const.COLOR_USER,
        color_nice=const.COLOR_NICE,
        color_system=const.COLOR_SYSTEM,
        color_idle=const.COLOR_IDLE,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.color_user = color_user
        self.color_nice = color_nice
        self.color_system = color_system
        self.color_idle = color_idle

    def on_mount(self):
        self.set_interval(self.refresh_interval, self.update_percentages)

    def update_percentages(self):
        self.percentages = get_cpu_percentage()

    def _render_legend_value(self, percet):
        return f"{percet * 100:5.2f}%"

    def watch_percentages(self, percentages):
        if percentages:
            try:
                user_legend = self.query_one(".cpu-legend-user")
                user_legend.current_value = self._render_legend_value(percentages[0])

                nice_legend = self.query_one(".cpu-legend-nice")
                nice_legend.current_value = self._render_legend_value(percentages[1])

                system_legend = self.query_one(".cpu-legend-system")
                system_legend.current_value = self._render_legend_value(percentages[2])

                idle_legend = self.query_one(".cpu-legend-idle")
                idle_legend.current_value = self._render_legend_value(percentages[3])
            except textual.css.query.NoMatches:
                logger.warning("Can not found DOM element in CPUTotalUsageTextPanel")

    def compose(self) -> ComposeResult:
        yield Legend(self.color_user, "user", classes="cpu-legend-user")
        yield Legend(self.color_nice, "nice", classes="cpu-legend-nice")
        yield Legend(self.color_system, "system", classes="cpu-legend-system")
        yield Legend(self.color_idle, "idle", classes="cpu-legend-idle")
