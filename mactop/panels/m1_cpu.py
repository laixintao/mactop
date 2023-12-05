from textual.app import ComposeResult

from mactop.metrics_store import metrics
from ._base import BaseStatic
from mactop.widgets import LabeledSparkline


def get_cpu_energy():
    energy_ma = metrics.get_powermetrics().processor_m1.cpu_energy_history
    return energy_ma


class M1CPUEnergyPanel(BaseStatic):
    BORDER_TITLE = "CPU Energy"

    def __init__(self, label="CPU Power", show_value=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        show_value = str(show_value).lower() == "true"
        if show_value:

            def show_energy(x):
                if x:
                    return f" {x} mW"
                return "N/A"

            self.value_render_fn = show_energy
        else:
            self.value_render_fn = lambda *_: ""
        self.label = label

    def compose(self) -> ComposeResult:
        yield LabeledSparkline(
            update_fn=get_cpu_energy,
            value_render_fn=self.value_render_fn,
            update_interval=self.refresh_interval,
            prefix_label=self.label,
        )
