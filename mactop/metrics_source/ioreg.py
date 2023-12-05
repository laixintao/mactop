import time
import logging
import subprocess
import threading
import plistlib
from mactop.metrics_store import (
    IORegMetrics,
    metrics,
    AppleSmartBattery,
    AdapterDetails,
)

logger = logging.getLogger(__name__)


class IORegParser:
    def __init__(self, raw, old_ioreg) -> None:
        self.raw = raw
        self.old_ioreg = old_ioreg

    def parse(self):
        ioreg_metrics = IORegMetrics()
        battery_raw = self.raw[0]
        ioreg_metrics.apple_smart_battery = self.parse_apple_smart_battery(battery_raw)

        return ioreg_metrics

    def parse_apple_smart_battery_adapter_details(self, adapter_details):
        ad = AdapterDetails()

        if (a := adapter_details.get("AdapterVoltage")) is not None:
            ad.adapter_voltage = a
        if (a := adapter_details.get("Current")) is not None:
            ad.current = a
        if (a := adapter_details.get("Watts")) is not None:
            ad.watts = a
        if (a := adapter_details.get("Description")) is not None:
            ad.description = a
        if (a := adapter_details.get("Manufacturer")) is not None:
            ad.manufacturer = a
        if (a := adapter_details.get("Name")) is not None:
            ad.name = a

        return ad

    def parse_apple_smart_battery(self, battery_data):
        a = AppleSmartBattery()

        a.apple_raw_current_capacity = battery_data["AppleRawCurrentCapacity"]
        a.apple_raw_max_capacity = battery_data["AppleRawMaxCapacity"]
        a.design_capacity = battery_data["DesignCapacity"]
        a.temperature = battery_data["Temperature"]

        a.cycle_count = battery_data["CycleCount"]

        a.external_charge_cable = battery_data["ExternalChargeCapable"]
        a.external_connected = battery_data["ExternalConnected"]
        a.is_charging = battery_data["IsCharging"]

        old_history = self.old_ioreg.apple_smart_battery.battery_capacity_history
        if not old_history:
            old_history = []

        old_history.append((time.time(), a.apple_raw_current_capacity))
        a.battery_capacity_history = old_history

        logger.info("Adapter is currently connected? %s", a.external_connected)
        if a.external_connected:
            a.adapter_details = self.parse_apple_smart_battery_adapter_details(
                battery_data["AdapterDetails"]
            )
            logger.info("Adapter details: %s", a.adapter_details)

        return a


def run_ioreg_periodic(stop_event, command, interval):
    while not stop_event.is_set():
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = process.communicate()

        logger.info(
            "Running command %s, return_code=%d, stderr=%s",
            " ".join(command),
            process.returncode,
            err,
        )
        raw_data = plistlib.loads(out)
        ioreg = IORegParser(raw_data, metrics.get_ioregmetrics()).parse()
        metrics.ioregmetrics = ioreg

        time.sleep(interval)


class IORegManager:
    COMMAND = [
        "ioreg",
        "-w",
        "0",
        "-r",
        "-a",
        "-c",
        "AppleSmartBattery",
    ]

    def __init__(self, interval) -> None:
        self.process = None
        self.exited_event = threading.Event()
        self.interval = interval

    def start_loop_thread(self):
        def loop_thread(stop_event, command, interval):
            try:
                run_ioreg_periodic(stop_event, command, interval)
            except Exception as stop_event:
                logger.exception(stop_event)

        # start the backgroud thread to process the stdout
        t = threading.Thread(
            target=loop_thread,
            args=(self.exited_event, self.COMMAND, self.interval),
            daemon=True,
        )
        t.start()

        logger.info("Background read_stdout started.")

    def start(self):
        self.start_loop_thread()

    def stop(self):
        self.exited_event.set()
