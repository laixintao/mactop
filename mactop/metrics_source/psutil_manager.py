import time
import psutil
import logging
import threading
from mactop.metrics_store import (
    LoadAvg,
    SwapMemory,
    metrics,
    CPUTimesPercent,
    VirtualMemory,
)


logger = logging.getLogger(__name__)


def perf_cpu(interval):
    result = psutil.cpu_times_percent(interval=interval, percpu=True)
    psu = metrics.get_psutilmetrics()
    total_user = 0
    total_nice = 0
    total_system = 0
    total_idle = 0

    percpus = []
    for r in result:
        percpus.append(
            CPUTimesPercent(user=r.user, nice=r.nice, system=r.system, idle=r.idle)
        )
        total_user += r.user
        total_nice += r.nice
        total_system += r.system
        total_idle += r.idle

    psu.cpu_percent_percpu = percpus

    total = total_user + total_system + total_nice + total_idle
    psu.cpu_percent = CPUTimesPercent(
        user=total_user / total,
        system=total_system / total,
        nice=total_nice / total,
        idle=total_idle / total,
    )


def get_swap_memory():
    swap = psutil.swap_memory()
    n = SwapMemory()

    n.free_bytes = swap.free
    n.total_bytes = swap.total
    n.used_bytes = swap.used
    n.percent = swap.percent
    n.sin_bytes = swap.sin
    n.sout_bytes = swap.sout

    psu = metrics.get_psutilmetrics()
    psu.swap_memory = n


def get_virtual_memory():
    vm = psutil.virtual_memory()
    n = VirtualMemory()

    n.total = vm.total
    n.available = vm.available
    n.percent = vm.percent
    n.used = vm.used
    n.free = vm.free
    n.active = vm.active
    n.inactive = vm.inactive
    n.wired = vm.wired

    psu = metrics.get_psutilmetrics()
    psu.virtual_memory = vm


def get_loadavg():
    la = LoadAvg()
    pa = psutil.getloadavg()

    la.load1, la.load5, la.load15 = pa

    psu = metrics.get_psutilmetrics()
    psu.loadavg = la


def get_boot_time():
    t = psutil.boot_time()
    psu = metrics.get_psutilmetrics()
    psu.boot_time = t


def run_psutil(stop_event, interval):
    last_run_time = time.time()
    while not stop_event.is_set():
        perf_cpu(interval)
        get_swap_memory()
        get_virtual_memory()
        get_loadavg()
        get_boot_time()

        current_time = time.time()
        wait_time = current_time - last_run_time
        logger.debug("wait_time: %s", wait_time)
        if wait_time < interval:
            logger.debug("put to wait_time")
            time.sleep(wait_time)

        last_run_time = time.time()


class PsutilManager:
    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.exited_event = threading.Event()

    def start_cpu_prof(self, interval: float):
        def cpu_prof_thread(stop_event, interval):
            try:
                run_psutil(stop_event, interval)
            except Exception as stop_event:
                logger.exception(stop_event)

        # start the backgroud thread to process the stdout
        t = threading.Thread(
            target=cpu_prof_thread, args=(self.exited_event, interval), daemon=True
        )
        t.start()

        logger.info("Background read_stdout started.")

    def start(self):
        self.start_cpu_prof(self.interval)

    def stop(self):
        self.exited_event.set()
