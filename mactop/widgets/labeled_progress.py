import logging

from typing import Callable


from textual.app import ComposeResult
from textual.widgets import Static, ProgressBar, Label
from textual.reactive import reactive

INTERVAL = 0.3
logger = logging.getLogger(__name__)


class LabelProgressWidget(Static):
    value = reactive(None)

    DEFAULT_CSS = """
    LabelProgressWidget {
        layout: horizontal;
    }
    """

    def __init__(
        self,
        prefix_label,
        update_fn: Callable[[], float],
        value_render_fn,
        update_interval=INTERVAL,
        progress_total=100,
        progress_total_update_fn: None | Callable[[], float] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.update_fn = update_fn
        self.value_render_fn = value_render_fn
        self.update_interval = update_interval
        self.prefix_label = prefix_label
        self.progress_total = progress_total
        self.progress_total_update_fn = progress_total_update_fn

    def on_mount(self) -> None:
        self.set_interval(INTERVAL, self.update_value)

    def update_value(self) -> None:
        if self.progress_total_update_fn:
            total = self.progress_total_update_fn()
            if total:
                self.progress_total = total

        result = self.update_fn()
        if result is not None:
            self.value = result

    def watch_value(self, value) -> None:
        if value is not None:
            number_widget = self.query_one("Static.value")
            rendered_str = self.value_render_fn(value)
            number_widget.styles.width = len(rendered_str)
            number_widget.update(rendered_str)

            progress = self.query_one("ProgressBar")
            progress.update(progress=value, total=self.progress_total)

    def compose(self) -> ComposeResult:
        yield Label(f"{self.prefix_label} ", classes="label")
        yield ProgressBar(show_eta=False, show_percentage=False, classes="progress-bar")
        yield Static("loading", classes="value")
