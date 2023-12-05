import logging

import textual
from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.reactive import reactive


logger = logging.getLogger(__name__)


class DynamicText(Static):
    value = reactive(None)

    DEFAULT_CSS = """
    DynamicText {
        layout: horizontal;
    }
    
    """

    def __init__(
        self,
        prefix_label,
        update_fn,
        value_render_fn,
        update_interval,
        warning_threshold=None,
        error_threshold=None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.update_fn = update_fn
        self.value_render_fn = value_render_fn
        self.update_interval = update_interval
        self.prefix_label = prefix_label

        self.warning_threshold = warning_threshold
        self.error_threshold = error_threshold

    def on_mount(self) -> None:
        self.set_interval(self.update_interval, self.update_value)

    def update_value(self) -> None:
        result = self.update_fn()
        if result is not None:
            self.value = result

    def watch_value(self, value) -> None:
        if value is not None:
            try:
                number = self.query_one("Static.value")
            except textual.css.query.NoMatches:
                logger.warning(
                    "Can not found DOM element in Static.value in DynamicText"
                )
                return
            rendered_str = self.value_render_fn(value)
            number.update(rendered_str)

    def compose(self) -> ComposeResult:
        yield Label(f"{self.prefix_label}", classes="label")
        yield Static("loading", classes="value")
