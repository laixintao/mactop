"""Convert battery properties read directly from IOKit to UI metrics."""

import time

from mactop.metrics_store import AdapterDetails, AppleSmartBattery, IORegMetrics


def parse_battery(raw, previous, timestamp=None):
    if not raw:
        return IORegMetrics()
    battery = AppleSmartBattery()
    fields = {
        "apple_raw_current_capacity": "AppleRawCurrentCapacity",
        "apple_raw_max_capacity": "AppleRawMaxCapacity",
        "design_capacity": "DesignCapacity",
        "temperature": "Temperature",
        "cycle_count": "CycleCount",
        "external_charge_cable": "ExternalChargeCapable",
        "external_connected": "ExternalConnected",
        "is_charging": "IsCharging",
    }
    for field, key in fields.items():
        setattr(battery, field, raw.get(key))
    old = previous.apple_smart_battery.battery_capacity_history or []
    if battery.apple_raw_current_capacity is not None:
        timestamp = time.time() if timestamp is None else timestamp
        battery.battery_capacity_history = (
            old + [(timestamp, battery.apple_raw_current_capacity)]
        )[-3600:]
    adapter = raw.get("AdapterDetails") or {}
    if battery.external_connected:
        battery.adapter_details = AdapterDetails(
            adapter_voltage=adapter.get("AdapterVoltage"),
            current=adapter.get("Current"),
            watts=adapter.get("Watts"),
            description=adapter.get("Description"),
            manufacturer=adapter.get("Manufacturer"),
            name=adapter.get("Name"),
        )
    return IORegMetrics(apple_smart_battery=battery)
