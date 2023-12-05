from textual.widgets import Label
from textual.app import ComposeResult

from mactop.widgets import DynamicText
from mactop.metrics_store import metrics
from mactop.utils.formatting import packet_speed_fmt, speed_sizeof_fmt
from ._base import BaseStatic
from ._base import SparkLinePanelBase


def format_ops(value):
    return packet_speed_fmt(value, suffix="ops/s")


class DiskIOOpsPerSText(BaseStatic):
    BORDER_TITLE = "Disk IO"

    DEFAULT_CSS = """
    DiskIOOpsPerSText {
        layout: horizontal;
    }
    DiskIOOpsPerSText .disk-io {
        max-width: 19;
    }
    """

    def __init__(self, label="Disk: ", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label, classes="disk-ops-prefix")
        yield DynamicText(
            prefix_label="R:",
            update_fn=lambda: metrics.get_powermetrics().disk.rops_per_s,
            value_render_fn=format_ops,
            classes="disk-io",
            update_interval=self.refresh_interval,
        )
        yield Label(" " * 5, classes="disk-ops-prefix")
        yield DynamicText(
            prefix_label="W:",
            update_fn=lambda: metrics.get_powermetrics().disk.wops_per_s,
            value_render_fn=format_ops,
            classes="disk-io",
            update_interval=self.refresh_interval,
        )


class DiskIOBytesPerSText(BaseStatic):
    BORDER_TITLE = "Disk IO"

    DEFAULT_CSS = """
    DiskIOBytesPerSText {
        layout: horizontal;
    }
    DiskIOBytesPerSText .disk-io {
        max-width: 19;
    }
    """

    def __init__(self, label="Disk: ", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label

    def compose(self) -> ComposeResult:
        yield Label(self.label, classes="disk-bytes-prefix")
        yield DynamicText(
            prefix_label="R:",
            update_fn=lambda: metrics.get_powermetrics().disk.rbytes_per_s,
            value_render_fn=speed_sizeof_fmt,
            classes="disk-io",
            update_interval=self.refresh_interval,
        )
        yield Label(" " * 5, classes="disk-bytes-prefix")
        yield DynamicText(
            prefix_label="W:",
            update_fn=lambda: metrics.get_powermetrics().disk.wbytes_per_s,
            value_render_fn=speed_sizeof_fmt,
            classes="disk-io",
            update_interval=self.refresh_interval,
        )


class DiskROpsPerSSparkline(SparkLinePanelBase):
    BORDER_TITLE = "Disk Read Ops Per Second"

    def __init__(self, label="R: ", reverse=False, show_value=True, *args, **kwargs):
        update_fn = lambda: metrics.get_powermetrics().disk.rops_per_s_history
        super().__init__(
            update_fn=update_fn,
            label=label,
            reverse=reverse,
            show_value=show_value,
            value_format_fn=format_ops,
            *args,
            **kwargs
        )


class DiskWOpsPerSSparkline(SparkLinePanelBase):
    BORDER_TITLE = "Disk Write Ops Per Second"

    def __init__(self, label="W: ", reverse=True, show_value=True, *args, **kwargs):
        update_fn = lambda: metrics.get_powermetrics().disk.wops_per_s_history
        super().__init__(
            update_fn=update_fn,
            label=label,
            reverse=reverse,
            show_value=show_value,
            value_format_fn=format_ops,
            *args,
            **kwargs
        )


class DiskRBytesPerSSparkline(SparkLinePanelBase):
    BORDER_TITLE = "Disk Read Bytes Per Second"

    def __init__(self, label="R: ", reverse=False, show_value=True, *args, **kwargs):
        update_fn = lambda: metrics.get_powermetrics().disk.rbytes_per_s_history
        super().__init__(
            update_fn=update_fn,
            label=label,
            reverse=reverse,
            show_value=show_value,
            value_format_fn=speed_sizeof_fmt,
            *args,
            **kwargs
        )


class DiskWBytesPerSSparkline(SparkLinePanelBase):
    BORDER_TITLE = "Disk Write Bytes Per Second"

    def __init__(self, label="W: ", reverse=True, show_value=True, *args, **kwargs):
        update_fn = lambda: metrics.get_powermetrics().disk.wbytes_per_s_history
        super().__init__(
            update_fn=update_fn,
            label=label,
            reverse=reverse,
            show_value=show_value,
            value_format_fn=speed_sizeof_fmt,
            *args,
            **kwargs
        )
