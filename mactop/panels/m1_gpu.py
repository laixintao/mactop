from textual.app import ComposeResult

from mactop.widgets import DynamicText
from mactop.metrics_store import metrics
from ._base import BaseStatic
from mactop import const
from mactop.widgets import LabeledColorBar, LabeledSparkline


def refresh_callback(*_):
    gpu_freq = metrics.get_powermetrics().m1_gpu.freq_hz
    return gpu_freq


class GPUFreqText(BaseStatic):
    BORDER_TITLE = "GPU Freq"

    def __init__(self, label="GPU Freq: ", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield DynamicText(
            prefix_label=self.label,
            update_fn=refresh_callback,
            value_render_fn=lambda x: f"{x:.2f}MHz",
            classes="gpu-freq-text",
            update_interval=self.refresh_interval,
        )


def get_gpu_usage():
    idle = metrics.get_powermetrics().m1_gpu.idle_ratio
    if idle is None:
        return [0, 1]
    busy = 1 - idle
    return [busy, idle]


def display_gpu_ration(x):
    if not x:
        return "NA%"
    return f"{x[0]*100:.2f}%"


class GPUUsageBarPanel(BaseStatic):
    def __init__(
        self,
        color_busy=const.COLOR_USER,
        color_idle=const.COLOR_IDLE,
        label="GPU: ",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.color_busy = color_busy
        self.color_idle = color_idle
        self.label = label

    def compose(self) -> ComposeResult:
        yield LabeledColorBar(
            prefix_label=self.label,
            color_choices=[
                self.color_busy,
                self.color_idle,
            ],
            percentages_update_fn=get_gpu_usage,
            value_render_fn=display_gpu_ration,
            update_interval=self.refresh_interval,
        )


def get_gpu_energy():
    energy_ma = metrics.get_powermetrics().m1_gpu.gpu_energy_ma_history
    return energy_ma


class M1GPUEnergyPanel(BaseStatic):
    BORDER_TITLE = "GPU Energy"

    def __init__(self, label="GPU Power", show_value=True, *args, **kwargs):
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
            update_fn=get_gpu_energy,
            value_render_fn=self.value_render_fn,
            update_interval=self.refresh_interval,
            prefix_label=self.label,
        )
