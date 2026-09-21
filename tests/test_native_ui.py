import asyncio
import io
import threading

import pytest
from rich.console import Console
from textual.events import Resize
from textual.geometry import Size

from mactop.layout_loader import XmlLayoutLoader
from mactop.main import Dashboard, MactopApp, try_path
from mactop.metrics_source.collector import append_histories
from mactop.metrics_store import MetricsSnapshot, metrics
from mactop.panels.tasks import TaskTable
from mactop.panels.overview import OverviewPanel


def overview_text(app, width):
    output = io.StringIO()
    Console(file=output, width=width).print(app.query_one(OverviewPanel).render())
    return output.getvalue()


@pytest.mark.parametrize("theme", ["m1.xml", "mactop.xml"])
@pytest.mark.parametrize("size", [(160, 38), (120, 36), (80, 24), (50, 32)])
def test_themes_with_missing_data_and_process_disappearance(theme, size):
    old = metrics.snapshot()

    async def check():
        sample = MetricsSnapshot()
        sample.system.cpu_count = 14
        sample.hardware.tasks = [
            {
                "pid": 123,
                "name": "[bold]process",
                "cpu_percent": 0,
                "rss_bytes": 1024,
                "vms_bytes": None,
            }
        ]
        sample.hardware.power_watts["cpu"] = 0
        append_histories(sample, MetricsSnapshot())
        metrics.publish(sample)
        widgets, css = XmlLayoutLoader(try_path(theme), 0.02).load()
        MactopApp.CSS = css
        exited = threading.Event()
        app = MactopApp(widgets, exited)
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.1)
            table = app.query_one(TaskTable)
            assert table.row_count == 1
            assert str(table.get_row("123")[1]) == "[bold]process"
            assert table.get_row("123")[2].strip() == "0.0"
            assert "0.00 W" in overview_text(app, size[0] - 3)
            metrics.publish(MetricsSnapshot())
            await pilot.pause(0.1)
            assert table.row_count == 0
            rendered = overview_text(app, size[0] - 3)
            assert "N/A" in rendered
            assert "0.00 W" not in rendered
            await pilot.press("q")
        assert exited.is_set()
        assert app.failure is None

    try:
        asyncio.run(check())
    finally:
        metrics.publish(old)


def test_process_ranking_navigation_and_resize():
    old = metrics.snapshot()

    async def check():
        sample = MetricsSnapshot()
        sample.hardware.tasks = [
            dict(
                pid=pid,
                name=f"process-{pid}",
                cpu_percent=cpu,
                rss_bytes=1024,
                vms_bytes=None,
            )
            for pid, cpu in enumerate((2, 11, None, 120))
        ]
        metrics.publish(sample)
        widgets, css = XmlLayoutLoader(try_path("m1.xml"), 0.02).load()
        MactopApp.CSS = css
        app = MactopApp(widgets, threading.Event())
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause(0.1)
            table = app.query_one(TaskTable)
            assert [table.get_row_at(i)[0].strip() for i in range(4)] == [
                "3",
                "1",
                "0",
                "2",
            ]
            sample.hardware.tasks[0]["cpu_percent"] = 150
            await pilot.pause(0.1)
            assert table.get_row_at(0)[0].strip() == "0"
            # Textual 0.35 predates Pilot.resize_terminal.
            size = Size(80, 24)
            app.post_message(Resize(size, size))
            await pilot.pause(0.1)
            assert app.query_one(OverviewPanel).size.width < 80
            assert table.row_count == 4
            await pilot.press("p")
            assert app.focused is table
            assert app.query_one(Dashboard).scroll_y > 0
            await pilot.press("home")
            assert app.focused is None
            assert app.query_one(Dashboard).scroll_y == 0
            await pilot.press("q")
        assert app.failure is None

    try:
        asyncio.run(check())
    finally:
        metrics.publish(old)


@pytest.mark.parametrize("theme", ["m1.xml", "mactop.xml"])
def test_quit_before_the_first_sample_on_a_short_terminal(theme):
    old = metrics.snapshot()

    async def check():
        sample = MetricsSnapshot()
        sample.system.cpu_count = 14
        metrics.publish(sample)
        widgets, css = XmlLayoutLoader(try_path(theme), 1).load()
        MactopApp.CSS = css
        exited = threading.Event()
        app = MactopApp(widgets, exited)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("q")
        assert exited.is_set()
        assert app.failure is None

    try:
        asyncio.run(check())
    finally:
        metrics.publish(old)
