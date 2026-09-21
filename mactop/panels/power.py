from textual.app import ComposeResult

from mactop.metrics_store import metrics
from mactop.widgets import LabeledSparkline
from ._base import BaseStatic


class PowerPanel(BaseStatic):
    """Any native component's average power, consistently displayed in watts."""

    def __init__(self, component="cpu", label=None, show_value=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.component = component
        self.label = label if label is not None else f"{component.upper()} Power"
        self.show_value = str(show_value).lower() == "true"

    def compose(self) -> ComposeResult:
        yield LabeledSparkline(
            update_fn=lambda: metrics.get_hardware().power_history.get(self.component),
            value_render_fn=(
                (lambda value: f" {value:.2f} W") if self.show_value else (lambda _: "")
            ),
            update_interval=self.refresh_interval,
            prefix_label=self.label,
        )
