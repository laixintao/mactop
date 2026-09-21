from textual.app import ComposeResult
from textual.containers import Horizontal

from mactop import const
from mactop.metrics_store import metrics
from mactop.widgets import DynamicText, LabeledColorBar
from ._base import BaseStatic


class M1CPUFreqPanel(BaseStatic):
    BORDER_TITLE = "CPU Cluster Frequency"
    DEFAULT_CSS = """
    M1CPUFreqPanel { height: 6; }
    M1CPUFreqPanel Horizontal { height: 5; }
    M1CPUClusterBlock {
        border: round $secondary;
        border-title-align: center;
        width: 1fr;
        padding: 0 1;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mounted_names = set()

    def on_mount(self):
        self.set_interval(self.refresh_interval, self.mount_clusters)

    def mount_clusters(self):
        for cluster in metrics.get_hardware().processor_m1.clusters or []:
            if cluster.name not in self.mounted_names:
                self.query_one(Horizontal).mount(
                    M1CPUClusterBlock(
                        cluster.name, refresh_interval=self.refresh_interval
                    )
                )
                self.mounted_names.add(cluster.name)

    def compose(self):
        yield Horizontal()


class M1CPUClusterBlock(BaseStatic):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cluster_name = self.border_title = name

    def cluster(self):
        return next(
            (
                item
                for item in metrics.get_hardware().processor_m1.clusters or []
                if item.name == self.cluster_name
            ),
            None,
        )

    def usage(self):
        cluster = self.cluster()
        if cluster is not None and cluster.idle_ratio is not None:
            return [1 - cluster.idle_ratio, cluster.idle_ratio]
        return None

    def frequency(self):
        cluster = self.cluster()
        return cluster.freq_hz if cluster else None

    def compose(self) -> ComposeResult:
        yield LabeledColorBar(
            prefix_label="Busy ",
            color_choices=[const.COLOR_USER, const.COLOR_IDLE],
            update_interval=self.refresh_interval,
            percentages_update_fn=self.usage,
            value_render_fn=lambda values: f"{values[0] * 100:.1f}%",
        )
        yield DynamicText(
            prefix_label="Active: ",
            update_fn=self.frequency,
            value_render_fn=lambda hz: f"{hz / 1_000_000:.0f} MHz",
            update_interval=self.refresh_interval,
        )
