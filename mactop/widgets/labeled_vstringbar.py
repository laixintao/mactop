import copy
import logging
from typing import Callable, List

from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.reactive import reactive

from mactop.widgets import VStringBar

logger = logging.getLogger(__name__)


class LabeledVStringBar(Static):
    percentages = reactive(None)

    DEFAULT_CSS = """
    LabeledVStringBar {
        layout: horizontal;
    }
    LabeledVStringBar > VStringBar {
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

        number_widget = self.query_one("Static.colorbar-value")
        number_str = self.value_render_fn(percentages)
        number_widget.styles.width = len(number_str)
        number_widget.update(number_str)

        colorbar = self.query_one("VStringBar")
        colorbar.percentages = percentages

    def compose(self) -> ComposeResult:
        yield Label(f"{self.prefix_label} ", classes="colorbar-label")
        yield VStringBar(self.color_choices)
        yield Static("  ", classes="colorbar-value")
