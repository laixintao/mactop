import math
import logging
from typing import Callable
from rich.text import Text
from textual.app import ComposeResult
from functools import partial

from mactop.widgets import DynamicText
from mactop.metrics_store import CPUCore, metrics
from ._base import BaseStatic
from mactop.utils.formatting import hz_format
from mactop.widgets import LabeledColorBar
from mactop import const

logger = logging.getLogger(__name__)


def display_callback(core: CPUCore):
    line = []
    if not core.cpus:
        return ""
    for cpu in core.cpus:
        if not cpu.freq_hz or not cpu.freq_ratio:
            return ""
        ratio_percent = int(cpu.freq_ratio * 100)
        freq = hz_format(cpu.freq_hz)
        line.append(f"CPU{cpu.cpu_number:>2}: {ratio_percent:>3}% ({freq})")
    return "\n".join(line)


CSTATE_LABEL = "[{0}]C [/{0}]".format(const.COLOR_C_STATE)
PSTATE_LABEL = Text.from_markup("[{0}] P[/{0}]".format(const.COLOR_P_STATE))
PSTATE_FN = lambda _: PSTATE_LABEL

UNIT_WIDTH = 25
UNIT_HEIGHT = 5


class CPUCoreBlock(BaseStatic):

    DEFAULT_CSS = """
    CPUCoreBlock {
      border: round $secondary;
      border-title-style: bold;
      border-title-align: center;
      padding: 0 1;
      width: %s;
      height: 5;
    }
    """ % UNIT_WIDTH

    def __init__(self, index, update_fn: Callable[[], CPUCore], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = f"core {index}"
        self.update_core_fn = update_fn

    def get_cp_state(self):
        core = self.update_core_fn()
        if not core:
            return
        c = core.c_state_ratio
        p = 1 - c
        return [c, p]

    def compose(self) -> ComposeResult:
        yield LabeledColorBar(
            update_interval=self.refresh_interval,
            prefix_label=CSTATE_LABEL,
            color_choices=[const.COLOR_C_STATE, const.COLOR_P_STATE],
            percentages_update_fn=self.get_cp_state,
            value_render_fn=PSTATE_FN,
        )
        yield DynamicText(
            prefix_label="",
            update_fn=self.update_core_fn,
            value_render_fn=display_callback,
            classes="cpucore-display-block",
            update_interval=self.refresh_interval,
        )

    def render(self, *args, **kwargs):
        logger.info("render with size: %s", self.size)
        return super().render(*args, **kwargs)


def get_package_info(core_index):
    pi = metrics.get_powermetrics().processor_intel
    return pi.get_core(core_index)


class CPUFreqPanel(BaseStatic):
    BORDER_TITLE = "CPU Frequency"
    DEFAULT_CSS = """
    CPUFreqPanel {
        layout: grid;
        align: center middle;
        min-height: 5;
        grid-size-columns: 4;
    }
    """

    def __init__(self, *args, **kwargs):
        self.core_count = metrics.psutilmetrics.cpu_physical_count
        super().__init__(*args, **kwargs)

    def on_resize(self, e):
        w = e.size.width
        total = self.core_count

        max_items = w // UNIT_WIDTH
        rows = math.ceil(total / max_items)
        cols = total // rows

        self.styles.grid_size_columns = cols

    def compose(self):
        for core_index in range(self.core_count):
            yield CPUCoreBlock(
                index=core_index,
                refresh_interval=self.refresh_interval,
                update_fn=partial(get_package_info, core_index),
            )
