import logging
from functools import partial

from textual.app import ComposeResult
from textual.containers import Grid

from mactop.widgets import DynamicText
from mactop.metrics_store import metrics
from mactop.utils.formatting import hz_format
from mactop.widgets import LabeledColorBar
from mactop import const

from ._base import BaseStatic

logger = logging.getLogger(__name__)


def get_cluster(index):
    return metrics.get_powermetrics().processor_m1.clusters[index]


class M1CPUFreqPanel(BaseStatic):
    BORDER_TITLE = "CPU Frequency"
    DEFAULT_CSS = """
    M1CPUFreqPanel {
        height: 7;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cpu_cluster_mouted = False

    def on_mount(self):
        self.set_interval(0.5, self.dynamic_mount_cpu_clusters)

    def dynamic_mount_cpu_clusters(self):
        logger.debug("dynamic_mount_cpu_clusters now run...")
        if self.cpu_cluster_mouted:
            return

        clusters = metrics.get_powermetrics().processor_m1.clusters
        if not clusters:
            return

        max_cpu = 0
        cluster_blocks = []
        for index, cluster in enumerate(clusters):
            cluster_block = M1CPUClusterBlock(
                cluster_name=cluster.name,
                refresh_interval=self.refresh_interval,
                cluster_update_fn=partial(get_cluster, index=index),
            )
            cluster_blocks.append(cluster_block)
            max_cpu = max(max_cpu, len(cluster.cpus))

        container = self.query_one("#m1cpu-freq-container")
        container.mount_all(cluster_blocks)
        container.styles.grid_size_columns = len(clusters)
        logger.info("dynamic_mount_cpu_clusters now mouted all clusters")
        logger.debug("max cpus: %s", max_cpu)
        self.styles.height = 1 + 2 + max_cpu
        self.cpu_cluster_mouted = True

    def compose(self):
        yield Grid(id="m1cpu-freq-container")


class M1CPUClusterBlock(BaseStatic):
    DEFAULT_CSS = """
    M1CPUClusterBlock {
      border: round $secondary;
      border-title-style: bold;
      border-title-align: center;
      padding: 0 1;
    }

    M1CPUFreqPanel Static {
      content-align-horizontal: center;
    }

    """

    def __init__(
        self,
        cluster_name,
        cluster_update_fn,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.border_title = cluster_name
        self.cluster_update_fn = cluster_update_fn

        def get_cluster_ratio():
            cluster = self.cluster_update_fn()
            idle = cluster.idle_ratio
            busy = 1 - idle
            return [busy, idle]

        self.ratio_update_fn = get_cluster_ratio

        def display_cluster_info(cluster):
            cpus = cluster.cpus
            text = []
            for cpu in cpus:
                freq = hz_format(cpu.freq_hz)
                line = f"CPU{cpu.cpu_number:>2}: {freq}"
                text.append(line)
            return "\n".join(text)

        self.text_update_fn = display_cluster_info

    def compose(self) -> ComposeResult:
        yield LabeledColorBar(
            update_interval=self.refresh_interval,
            prefix_label="Busy ",
            color_choices=[const.COLOR_USER, const.COLOR_IDLE],
            percentages_update_fn=self.ratio_update_fn,
            value_render_fn=lambda *_: " Idle",
        )
        yield DynamicText(
            prefix_label="",
            update_fn=self.cluster_update_fn,
            value_render_fn=self.text_update_fn,
            classes="cpucore-display-block",
            update_interval=self.refresh_interval,
        )
