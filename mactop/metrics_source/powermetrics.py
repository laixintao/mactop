"""
Managing the backgroud process and parse the metrics
"""
import pathlib
import time
import json
import threading
import subprocess
import logging
import plistlib
from datetime import datetime

from mactop.metrics_store import (
    CPU,
    M1GPU,
    M1CPUCluster,
    M1ProcessorPackage,
    ProcessorIntel,
    ProcessorPackage,
    ProcessorType,
    metrics,
    PowerMetricsBattery,
    PowerMetrics,
    Smc,
    Netowrk,
    Disk,
    CPUCore,
)

DEBUG_DUMP_LOCATION = "./debug_json"
logger = logging.getLogger(__name__)


class PowerMetricsParser:
    def __init__(self, raw, old_powermetrics, interval):
        self.raw = raw
        self.interval = interval
        self.old_powermetrics = old_powermetrics
        self.max_history_count = 100

    def parse(self):
        powermetrics = PowerMetrics()
        powermetrics.backlight = self.parse_powermetrics_backlight()

        if smc_data := self.raw.get("smc"):
            powermetrics.smc = self.parse_smc(smc_data)

        if tasks := self.raw.get("tasks"):
            powermetrics.tasks = tasks

        if network := self.raw.get("network"):
            powermetrics.network = self.parse_network(network)
        if disk := self.raw.get("disk"):
            powermetrics.disk = self.parse_disk(disk)

        if gpu := self.raw.get("gpu"):
            powermetrics.m1_gpu = self.parse_m1_gpu(gpu)

        if processor := self.raw.get("processor"):
            if "package_watts" in processor:
                powermetrics.processor_intel = self.parse_processor_intel(processor)
                powermetrics.processor_type = ProcessorType.INTEL
            if "clusters" in processor:
                powermetrics.processor_m1 = self.parse_processor_m1(processor)
                powermetrics.processor_type = ProcessorType.M1
        return powermetrics

    def parse_processor_m1(self, processor):
        package = M1ProcessorPackage()
        package.gpu_energy = processor.get("gpu_energy")
        package.cpu_energy = processor.get("cpu_energy")
        package.clusters = []
        for cluster in processor["clusters"]:
            package.clusters.append(self.parse_processor_m1_cluster(cluster))

        old_hisotry = self.old_powermetrics.processor_m1.cpu_energy_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(package.cpu_energy)
        package.cpu_energy_history = old_hisotry[-self.max_history_count :]

        return package

    def parse_processor_m1_cluster(self, cluster):
        c = M1CPUCluster()
        c.name = cluster.get("name")
        c.idle_ratio = cluster.get("idle_ratio")
        c.cpus = self.parse_processor_packages_cores_cpus(cluster.get("cpus"))

        return c

    def parse_m1_gpu(self, gpu):
        g = M1GPU()
        g.freq_hz = gpu.get("freq_hz")
        g.idle_ratio = gpu.get("idle_ratio")
        g.gpu_energy_ma = gpu.get("gpu_energy")

        old_hisotry = self.old_powermetrics.m1_gpu.gpu_energy_ma_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(g.gpu_energy_ma)
        g.gpu_energy_ma_history = old_hisotry[-self.max_history_count :]

        return g

    def parse_disk(self, disk):
        n = Disk()
        n.rbytes_per_s = disk.get("rbytes_per_s")
        n.wbytes_per_s = disk.get("wbytes_per_s")
        n.rops_per_s = disk.get("rops_per_s")
        n.wops_per_s = disk.get("wops_per_s")

        old_hisotry = self.old_powermetrics.disk.rbytes_per_s_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(n.rbytes_per_s)
        n.rbytes_per_s_history = old_hisotry[-self.max_history_count :]

        old_hisotry = self.old_powermetrics.disk.wbytes_per_s_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(n.wbytes_per_s)
        n.wbytes_per_s_history = old_hisotry[-self.max_history_count :]

        old_hisotry = self.old_powermetrics.disk.rops_per_s_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(n.rops_per_s)
        n.rops_per_s_history = old_hisotry[-self.max_history_count :]

        old_hisotry = self.old_powermetrics.disk.wops_per_s_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(n.wops_per_s)
        n.wops_per_s_history = old_hisotry[-self.max_history_count :]
        return n

    def parse_network(self, network):
        n = Netowrk()
        n.ibyte_rate = network.get("ibyte_rate")
        n.obyte_rate = network.get("obyte_rate")
        n.ipacket_rate = network.get("ipacket_rate")
        n.opacket_rate = network.get("opacket_rate")

        old_hisotry = self.old_powermetrics.network.ibyte_rate_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(n.ibyte_rate)
        n.ibyte_rate_history = old_hisotry[-self.max_history_count :]

        old_hisotry = self.old_powermetrics.network.obyte_rate_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(n.obyte_rate)
        n.obyte_rate_history = old_hisotry[-self.max_history_count :]

        old_hisotry = self.old_powermetrics.network.ipacket_rate_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(n.ipacket_rate)
        n.ipacket_rate_history = old_hisotry[-self.max_history_count :]

        old_hisotry = self.old_powermetrics.network.opacket_rate_history
        if not old_hisotry:
            old_hisotry = []
        old_hisotry.append(n.opacket_rate)
        n.opacket_rate_history = old_hisotry[-self.max_history_count :]
        return n

    def parse_processor_intel(self, processor):
        pi = ProcessorIntel()
        if package_watts := processor.get("package_watts"):
            old_hisotry = self.old_powermetrics.processor_intel.package_watts_history
            new_history = []
            if not old_hisotry:
                new_history = []
            else:
                new_history = old_hisotry

            new_history.append(package_watts)
            pi.package_watts_history = new_history[-self.max_history_count :]

        if "packages" in processor:
            pi.packages = self.parse_processor_packages(processor["packages"])
        return pi

    def parse_processor_packages(self, packages):
        packages_result = []
        for package in packages:
            p = ProcessorPackage()
            p.c_state_ratio = package["c_state_ratio"]
            p.cores = self.parse_processor_packages_cores(package["cores"])
            packages_result.append(p)

        return packages_result

    def parse_processor_packages_cores(self, cores):
        cores_result = []
        for core in cores:
            c = CPUCore()
            c.cpu_core_index = core["core"]
            c.c_state_ratio = core["c_state_ratio"]
            c.cpus = self.parse_processor_packages_cores_cpus(core["cpus"])
            cores_result.append(c)

        return cores_result

    def parse_processor_packages_cores_cpus(self, cpus):
        cpus_result = []
        for cpu in cpus:
            c = CPU()
            c.cpu_number = cpu.get("cpu")
            c.freq_hz = cpu.get("freq_hz")
            c.freq_ratio = cpu.get("freq_ratio")
            cpus_result.append(c)

        return cpus_result

    def parse_battery_data(self):
        data = self.raw
        if "battery" not in data:
            return
        battery_data = data["battery"]

        pm = PowerMetricsBattery()
        if battery_data.get("plugged_in"):
            pm.plugged_in = bool(battery_data.get("plugged_in"))
        if battery_data.get("discharge_rate"):
            pm.discharge_rate = float(battery_data.get("discharge_rate"))

        return pm

    def parse_powermetrics_backlight(self):
        if backlight := self.raw.get("backlight"):
            return int(backlight["value"])

    def parse_smc(self, data):
        smc = Smc()

        if cpu_die := data.get("cpu_die"):
            smc.cpu_die = cpu_die
        if gpu_die := data.get("gpu_die"):
            smc.gpu_die = gpu_die
        if fan := data.get("fan"):
            smc.fan = fan

        logger.info("Smc parsed: %s", smc)
        return smc


def streaming_powermetrics(stdout_fd, interval, sleep=0, debug=False):
    """
    The delimiter is \x00
    but I haven't figure out how to read effciently mean while using this \x00

    ref:
    https://stackoverflow.com/questions/375427
    """
    read_content = b""
    while True:
        line = stdout_fd.readline()
        read_content += line

        # handle one batch
        if b"</plist>" in line:
            read_content = read_content.replace(b"&", b"and")
            try:
                data = plistlib.loads(read_content)
            except:
                dumpfile = f"powermetrics_dump_{time.time()}.plist"
                logger.exception("Error when load powermetrics, dump output...")
                with open(dumpfile, "w") as f:
                    f.write(read_content.decode())
                continue

            read_content = b""
            stdout_fd.read(1)

            if debug:
                pathlib.Path(DEBUG_DUMP_LOCATION).mkdir(parents=True, exist_ok=True)
                debug_file = (
                    f"{DEBUG_DUMP_LOCATION}/mactop_debug_{ datetime.now().strftime('%Y%m%d_%H:%M:%S')}.json"
                )
                logger.info("Got metrics, debug file saved to %s", debug_file)
                with open(debug_file, "w") as d:
                    json.dump(data, d, default=str)

            metrics.powermetrics = PowerMetricsParser(
                data, metrics.get_powermetrics(), interval
            ).parse()

            time.sleep(sleep)


class PowerMetricsManager:
    def __init__(self, refresh_interval_seconds: float, debug: bool) -> None:
        self.process = None
        self.refresh_interval_seconds = refresh_interval_seconds
        self.debug = debug

    def start_background_process(self):
        sample_rate = int(self.refresh_interval_seconds * 1000)
        command = [
            "sudo",
            "powermetrics",
            "--format",
            "plist",
            "--samplers",
            "all",
            "--sample-rate",
            f"{sample_rate}",
        ]
        logger.info("Start powermetrics process: %s", command)
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout = self.process.stdout
        stderr = self.process.stderr

        def read_stdout(stdout_fd, stderr, interval):
            try:
                streaming_powermetrics(stdout_fd, interval, debug=self.debug)
            except Exception as e:
                logger.exception(e)

        # start the backgroud thread to process the stdout
        t = threading.Thread(
            target=read_stdout,
            args=(stdout, stderr, self.refresh_interval_seconds),
            daemon=True,
        )
        t.start()

        logger.info("Background read_stdout started.")

    def start(self):
        self.start_background_process()

    def start_fake_data(self, filepath):
        def read_stdout(filepath, interval):
            f = open(filepath, "br")
            try:
                streaming_powermetrics(f, interval, sleep=1, debug=self.debug)
            except Exception as e:
                logger.exception(e)
            finally:
                f.close()

        # start the backgroud thread to process the stdout
        t = threading.Thread(
            target=read_stdout,
            args=(filepath, self.refresh_interval_seconds),
            daemon=True,
        )
        t.start()

        logger.info("Background read_stdout with fake data started.")

    def stop(self):
        try:
            if self.process is not None:
                self.process.terminate()
        except Exception as e:
            logger.error("Error when try to stop the process: %s", str(e))
