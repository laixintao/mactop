import copy
import logging
from typing import Callable, List

import textual
from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.reactive import reactive

from mactop.widgets import ColorBar

logger = logging.getLogger(__name__)


class LabeledColorBar(Static):
    percentages = reactive(None)

    DEFAULT_CSS = """
    LabeledColorBar {
        layout: horizontal;
    }
    LabeledColorBar > ColorBar {
        width: 1fr;
    }
    """

    def __init__(
        self,
        prefix_label,
        color_choices,
        update_interval,
        percentages_update_fn: Callable[[], List[float]],
        value_render_fn: Callable[[List[float]], str],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.percentages_update_fn = percentages_update_fn
        self.color_choices = color_choices
        self.update_interval = update_interval
        self.prefix_label = prefix_label
        self.value_render_fn = value_render_fn

    def on_mount(self) -> None:
        self.set_interval(self.update_interval, self.update_percentages)

    def update_percentages(self) -> None:
        result = self.percentages_update_fn()
        if result is not None:
            self.percentages = copy.copy(result)

    def watch_percentages(self, percentages) -> None:
        if not percentages:
            return

        try:
            number_widget = self.query_one(".colorbar-value")
        except textual.css.query.NoMatches:
            logger.warning(
                "Can not found DOM element in .colorbar-value in LabeledColorBar"
            )
            return
        number_str = self.value_render_fn(percentages)
        number_widget.styles.width = len(number_str)
        number_widget.update(number_str)

        colorbar = self.query_one("ColorBar")
        colorbar.percentages = percentages

    def compose(self) -> ComposeResult:
        yield Label(f"{self.prefix_label}", classes="colorbar-label")
        yield ColorBar(self.color_choices)
        yield Static("  ", classes="colorbar-value")
