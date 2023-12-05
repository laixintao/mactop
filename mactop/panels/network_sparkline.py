from mactop.metrics_store import metrics
from mactop.utils.formatting import speed_sizeof_fmt, packet_speed_fmt

from ._base import SparkLinePanelBase


class NetworkIByteRateSparkline(SparkLinePanelBase):
    BORDER_TITLE = "Network Input Byte Rate"

    def __init__(self, label=" IN: ", reverse=False, show_value=True, *args, **kwargs):
        update_fn = lambda: metrics.get_powermetrics().network.ibyte_rate_history
        super().__init__(
            update_fn=update_fn,
            label=label,
            reverse=reverse,
            show_value=show_value,
            value_format_fn=speed_sizeof_fmt,
            *args,
            **kwargs
        )


class NetworkOByteRateSparkline(SparkLinePanelBase):
    BORDER_TITLE = "Network Output Byte Rate"

    def __init__(self, label="OUT: ", reverse=True, show_value=True, *args, **kwargs):
        update_fn = lambda: metrics.get_powermetrics().network.obyte_rate_history
        super().__init__(
            update_fn=update_fn,
            label=label,
            reverse=reverse,
            show_value=show_value,
            value_format_fn=speed_sizeof_fmt,
            *args,
            **kwargs
        )


class NetworkIPacketRateSparkline(SparkLinePanelBase):
    BORDER_TITLE = "Network Input Packet Rate"

    def __init__(self, label=" IN: ", reverse=False, show_value=True, *args, **kwargs):
        update_fn = lambda: metrics.get_powermetrics().network.ipacket_rate_history
        super().__init__(
            update_fn=update_fn,
            label=label,
            reverse=reverse,
            show_value=show_value,
            value_format_fn=packet_speed_fmt,
            *args,
            **kwargs
        )


class NetworkOPacketRateSparkline(SparkLinePanelBase):
    BORDER_TITLE = "Network Output Packet Rate"

    def __init__(self, label="OUT: ", reverse=True, show_value=True, *args, **kwargs):
        update_fn = lambda: metrics.get_powermetrics().network.opacket_rate_history
        super().__init__(
            update_fn=update_fn,
            label=label,
            reverse=reverse,
            show_value=show_value,
            value_format_fn=packet_speed_fmt,
            *args,
            **kwargs
        )
