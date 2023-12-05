from dataclasses import dataclass
import logging
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive

from mactop.metrics_store import metrics
from mactop.widgets import DynamicText, LabelProgressWidget
from ._base import BaseStatic

logger = logging.getLogger(__name__)


class ChargerDispaly(BaseStatic):
    adapter = reactive(None)
    connected = reactive(None)
    charging = reactive(None)

    def on_mount(self) -> None:
        self.set_interval(self.refresh_interval, self.update_adapter)

    def update_adapter(self) -> None:
        if (ioreg := metrics.get_ioregmetrics()) is not None:
            self.connected = ioreg.apple_smart_battery.external_connected
            self.charging = ioreg.apple_smart_battery.is_charging

            if self.connected:
                self.adapter = ioreg.apple_smart_battery.adapter_details
            else:
                self.adapter = None

    def watch_adapter(self, adapter) -> None:
        if not self.connected:
            text = "⌁ "
            text += "[bold success]On battery[/]"
        else:
            text = "[green]⌁ [/green]"
            text += "[green]On external power[/]"
            if adapter:
                if self.charging:
                    text += ", battery is charging"
                else:
                    text += ", battery is not charging"

                adapter_description = []
                if adapter.name:
                    adapter_description.append(adapter.name)
                if adapter.manufacturer:
                    adapter_description.append(f"by {adapter.manufacturer}")
                if adapter.description:
                    adapter_description.append(adapter.description)

                if adapter_description:
                    adapter_details_info = " ".join(adapter_description)
                    text += f"\n  Input: {adapter_details_info}"

                if adapter.watts and adapter.current and adapter.adapter_voltage:
                    text += (
                        f"\n  {adapter.watts}Watts ="
                        f" {adapter.adapter_voltage/1000:.1f}V x"
                        f" {adapter.current/1000}A"
                    )

        self.update(text)


class BacklightDisplayText(BaseStatic):
    backlight = reactive("loading")

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.set_interval(self.refresh_interval, self.update_backlight)

    def update_backlight(self) -> None:
        if (backlight := metrics.powermetrics.backlight) is not None:
            self.backlight = backlight

    def watch_backlight(self, backlight: int) -> None:
        self.update(f"Backlight: {backlight}")


class BatteryHealthInfo(BaseStatic):
    capacity = reactive(None)

    def on_mount(self) -> None:
        self.set_interval(self.refresh_interval, self.update_capacity)

    def update_capacity(self) -> None:
        if (ioreg := metrics.get_ioregmetrics()) is not None:
            self.capacity = ioreg.apple_smart_battery

    def watch_capacity(self, capacity) -> None:
        if not capacity:
            return
        if capacity.apple_raw_max_capacity is None or capacity.design_capacity is None:
            return
        health_percent = (
            capacity.apple_raw_max_capacity / capacity.design_capacity * 100
        )
        self.update(
            f"Current Max Capacity: {capacity.apple_raw_max_capacity}mAh,"
            f" {health_percent:.1f}% of Designed Capacity"
            f" {capacity.design_capacity}mAh"
        )


@dataclass
class BatteryState:
    total_time: float = 0
    history_accumulated: float = 0
    minute_rate: float = 0
    # always positive
    estimate_minutes: float = 0


class ChargingRateDisplay(BaseStatic):
    battery_state = reactive(BatteryState())

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.set_interval(self.refresh_interval, self.update_charing_history)

    def _get_last_change(self, charging_history):
        """
        Returns the last changed time range:
        A 1, B 1, C 2, D 2, E 2, F 3, G 3
        should return C 2 and F 3
        """
        changes_last = None
        changes_start = None

        if len(charging_history) < 2:
            return None, None

        for item in charging_history[::-1]:
            if not changes_last:
                changes_last = item
                continue

            if changes_last[1] == item[1]:
                changes_last = item
                continue

            if not changes_start:
                changes_start = item
                continue

            if changes_start[1] == item[1]:
                changes_start = item
            else:
                return changes_start, changes_last

        return None, None

    def update_charing_history(self) -> None:
        ioreg_metrics = metrics.get_ioregmetrics()
        charging_history = ioreg_metrics.apple_smart_battery.battery_capacity_history
        max_cap = ioreg_metrics.apple_smart_battery.apple_raw_max_capacity
        curr_cap = ioreg_metrics.apple_smart_battery.apple_raw_current_capacity

        # charged to full or not charging
        if not ioreg_metrics.apple_smart_battery.is_charging:
            self.battery_state = BatteryState()

        if not charging_history or not max_cap or not curr_cap:
            return

        if len(charging_history) < 2:
            return

        last_item = charging_history[-1]
        first_item = charging_history[0]

        new_bs = BatteryState()
        new_bs.total_time = last_item[0] - first_item[0]
        new_bs.history_accumulated = last_item[1] - first_item[1]

        changes_start, changes_last = self._get_last_change(charging_history)

        if not changes_start or not changes_last:
            return

        minrate = new_bs.minute_rate = (
            (changes_last[1] - changes_start[1])
            / (changes_last[0] - changes_start[0])
            * 60
        )

        logger.info("------> min rate changed")

        if minrate > 0:
            new_bs.estimate_minutes = (max_cap - curr_cap) / minrate

        if minrate < 0:
            new_bs.estimate_minutes = -(curr_cap / minrate)

        logger.debug(
            f"{changes_start=}, {changes_last=}, {minrate=},"
            f" {self.battery_state.estimate_minutes=}"
        )
        self.battery_state = new_bs

    def watch_battery_state(self, battery_state: BatteryState) -> None:
        logger.info("watch_battery_state")
        minute_rate = battery_state.minute_rate

        if not minute_rate:
            self.update("Battery capacity is not changing")
            return

        if minute_rate > 0:
            _action = "[bold green]⬆[/]"

            _estimate_action = "full"
        else:
            _action = "[bold red]⬇[/]"
            _estimate_action = "shutdown"

        self.update(
            f"Battery {_action} {battery_state.history_accumulated:.0f} mAh in"
            f" {battery_state.total_time:.0f}s,"
            f" {battery_state.minute_rate:.1f} mAh/minute,"
            f" {battery_state.estimate_minutes:.0f} minutes to {_estimate_action}."
        )


class BatteryPanel(BaseStatic):
    DEFAULT_CSS = """
    BatteryPanel {
        border-title-align: left;
    }
    """

    BORDER_TITLE = "Battery"

    def compose(self) -> ComposeResult:
        yield Vertical(
            ChargerDispaly(refresh_interval=self.refresh_interval),
            LabelProgressWidget(
                update_fn=lambda: metrics.get_ioregmetrics().apple_smart_battery.apple_raw_current_capacity,
                progress_total_update_fn=lambda: metrics.get_ioregmetrics().apple_smart_battery.apple_raw_max_capacity,
                value_render_fn=lambda cput: f"{cput:.0f} mAh",
                update_interval=self.refresh_interval,
                progress_total=8000,
                prefix_label="Capacity",
            ),
            ChargingRateDisplay(refresh_interval=self.refresh_interval),
            DynamicText(
                prefix_label="Battery Temperature: ",
                update_fn=lambda: metrics.get_ioregmetrics().apple_smart_battery.temperature,
                value_render_fn=lambda cput: cput is not None and f"{cput/100:.1f} °C",
                update_interval=self.refresh_interval,
            ),
            DynamicText(
                prefix_label="Cycle Count:",
                update_fn=lambda: metrics.get_ioregmetrics().apple_smart_battery.cycle_count,
                value_render_fn=lambda value: f"{value}",
                update_interval=self.refresh_interval,
            ),
            BatteryHealthInfo(refresh_interval=self.refresh_interval),
        )
