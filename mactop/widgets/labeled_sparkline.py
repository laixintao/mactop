import copy
import logging
from typing import Callable, List

import textual
from textual.app import ComposeResult, RenderResult
from textual.widgets import Static, Sparkline, Label
from textual.reactive import reactive
from textual.renderables.sparkline import Sparkline as SparklineRenderable
from textual.renderables._blend_colors import blend_colors

from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style

logger = logging.getLogger(__name__)


class LabeledSparkline(Static):
    value = reactive(None)

    DEFAULT_CSS = """
    LabeledSparkline {
        layout: horizontal;
        height: 1;
    }
    LabeledSparkline > Sparkline {
        width: 1fr;
    }

    LabeledSparkline .sparkline--max-color {
        color: $warning;
    }
    LabeledSparkline .sparkline--min-color {
        color: $warning 50%;
    }

    ReversedSparkline {
        text-style: reverse;
    }
    """

    def __init__(
        self,
        prefix_label,
        update_fn: Callable[[], List[float]],
        value_render_fn,
        update_interval=1.0,
        sparkline_reverse=False,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.update_fn = update_fn
        self.value_render_fn = value_render_fn
        self.update_interval = update_interval
        self.prefix_label = prefix_label
        self.sparkline_reverse = sparkline_reverse

    def on_mount(self) -> None:
        self.set_interval(self.update_interval, self.update_value)

    def update_value(self) -> None:
        result = self.update_fn()
        if result is not None:
            self.value = copy.copy(result)

    def watch_value(self, value) -> None:
        if not value:
            return
        last = value[-1]

        try:
            number_widget = self.query_one("Static.sparklineValue")
            number_str = self.value_render_fn(last)
            number_widget.styles.width = len(number_str)
            number_widget.update(number_str)

            sparkline = self.query_one(".sparkline-chart")
        except textual.css.query.NoMatches:
            logger.warning(
                "Can not found DOM element in Sparkline"
            )
            return
        sparkline.data = value

    def compose(self) -> ComposeResult:
        yield Label(f"{self.prefix_label} ", classes="sparklineLabel")
        if self.sparkline_reverse:
            yield ReversedSparkline(self.value, classes="sparkline-chart")
        else:
            Sparkline.DEFAULT_CSS = ""
            yield Sparkline(self.value, classes="sparkline-chart")
        yield Static(" ", classes="sparklineValue")


class ReversedSparklineRenderable(SparklineRenderable):
    BARS = "▇▆▅▄▃▂▁ "

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = self.width or options.max_width
        len_data = len(self.data)
        if len_data == 0:
            yield Segment("▇" * width, self.min_color)
            return
        if len_data == 1:
            yield Segment(" " * width, self.max_color)
            return

        minimum, maximum = min(self.data), max(self.data)
        extent = maximum - minimum or 1

        buckets = tuple(self._buckets(self.data, num_buckets=width))

        bucket_index = 0.0
        bars_rendered = 0
        step = len(buckets) / width
        summary_function = self.summary_function
        min_color, max_color = self.min_color.color, self.max_color.color
        assert min_color is not None
        assert max_color is not None
        while bars_rendered < width:
            partition = buckets[int(bucket_index)]
            partition_summary = summary_function(partition)
            height_ratio = (partition_summary - minimum) / extent
            bar_index = int(height_ratio * (len(self.BARS) - 1))
            bar_color = blend_colors(min_color, max_color, height_ratio)
            bars_rendered += 1
            bucket_index += step
            yield Segment(self.BARS[bar_index], Style.from_color(bar_color))


class ReversedSparkline(Sparkline):
    def render(self) -> RenderResult:
        """Renders the sparkline when there is data available."""
        if not self.data:
            return " "
        _, base = self.background_colors
        return ReversedSparklineRenderable(
            self.data,
            width=self.size.width,
            min_color=(
                base + self.get_component_styles("sparkline--min-color").color
            ).rich_color,
            max_color=(
                base + self.get_component_styles("sparkline--max-color").color
            ).rich_color,
            summary_function=self.summary_function,
        )
