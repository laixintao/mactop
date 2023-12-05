import logging
from textual.widgets import Static
from textual.app import ComposeResult
from mactop.widgets import LabeledSparkline


logger = logging.getLogger(__name__)


class BaseStatic(Static):
    def __init__(self, refresh_interval, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refresh_interval = float(refresh_interval)


class SparkLinePanelBase(BaseStatic):
    DEFAULT_CSS = """
    SparkLinePanelBase {
        height: 1;
    }
    """

    def __init__(
        self, update_fn, label, reverse, show_value, value_format_fn, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.label = label
        self.reverse = reverse
        self.update_fn = update_fn

        if show_value:
            self.format_fn = value_format_fn
        else:
            self.format_fn = lambda *_: ""

    def compose(self) -> ComposeResult:
        if not self.update_fn:
            raise NotImplementedError("update_fn can not be None")
        yield LabeledSparkline(
            update_fn=self.update_fn,
            value_render_fn=self.format_fn,
            update_interval=self.refresh_interval,
            prefix_label=self.label,
            sparkline_reverse=self.reverse,
        )
