import logging
import math
import os
import platform
import sys
from pathlib import Path
import threading

import click
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Footer

from mactop.layout_loader import XmlLayoutLoader
from mactop.metrics_source import MetricsManager
from mactop.metrics_source.collector import snapshot_json
from mactop.metrics_store import metrics
from mactop.panels.tasks import TaskTable
from mactop.widgets.header import MactopHeader

from . import __version__


LOG_LOCATION = "/tmp/mactop.log"
logger = logging.getLogger(__name__)


def setup_log(enabled, level, loglocation):
    if enabled:
        logging.disable(logging.NOTSET)
        logging.basicConfig(
            filename=os.path.expanduser(loglocation),
            filemode="a",
            format="%(asctime)s %(levelname)5s (%(module)s) %(message)s",
            level=level,
        )
    else:
        logging.disable(logging.CRITICAL)
    logger.info("------ mactop ------")


class Dashboard(VerticalScroll):
    DEFAULT_CSS = """
    Dashboard {
        height: 1fr;
        overflow-y: scroll;
        scrollbar-gutter: stable;
    }
    """


class MactopApp(App):
    # Keep the overview visible; focusing an off-screen table during startup
    # can trigger repeated scroll/layout animations in Textual 0.35.
    AUTO_FOCUS = None
    BINDINGS = [
        Binding("ctrl+c,q", "exit", "Quit", show=True, priority=True, key_display="Q"),
        Binding("p", "processes", "Processes", key_display="P"),
        Binding("home", "overview", "Overview", priority=True, key_display="Home"),
        Binding("down,j", "dashboard_down", "Scroll", show=False),
        Binding("up,k", "dashboard_up", "Scroll", show=False),
        Binding("pagedown", "dashboard_page_down", "Page down", show=False),
        Binding("pageup", "dashboard_page_up", "Page up", show=False),
    ]

    def __init__(self, app_body_items, user_exited_event, *args, **kwargs):
        self.failure = None
        super().__init__(*args, **kwargs)
        self.app_body_items = app_body_items
        self.user_exited_event = user_exited_event

    def _handle_exception(self, error):
        self.failure = error
        super()._handle_exception(error)

    def on_mount(self) -> None:
        self.title = "mactop"
        self.update_source_status()
        self.set_interval(1, self.update_source_status)

    def update_source_status(self):
        unavailable = ", ".join(metrics.snapshot().errors)
        self.sub_title = f"v{__version__}" + (
            f" | N/A: {unavailable}" if unavailable else ""
        )

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield MactopHeader(show_clock=True)
        yield Footer()

        yield Dashboard(*self.app_body_items)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_exit(self) -> None:
        self.user_exited_event.set()
        self.exit()

    def action_processes(self):
        tables = list(self.query(TaskTable))
        if tables:
            self.query_one(Dashboard).scroll_to_widget(tables[0], animate=False)
            tables[0].focus()

    def action_overview(self):
        self.set_focus(None)
        self.query_one(Dashboard).scroll_home(animate=False)

    def action_dashboard_down(self):
        self.query_one(Dashboard).scroll_relative(y=3, animate=False)

    def action_dashboard_up(self):
        self.query_one(Dashboard).scroll_relative(y=-3, animate=False)

    def action_dashboard_page_down(self):
        self.query_one(Dashboard).scroll_page_down(animate=False)

    def action_dashboard_page_up(self):
        self.query_one(Dashboard).scroll_page_up(animate=False)


LOG_LEVEL = {0: logging.CRITICAL, 1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(__version__)
    ctx.exit()


@click.command()
@click.option(
    "--theme",
    "-t",
    default=None,
    help="Theme file (default: m1.xml on Apple Silicon, mactop.xml on Intel).",
)
@click.option(
    "--auto-reload",
    "-a",
    default=False,
    help="Debug mode for designing new theme, when theme changed, app will auto reload",
    is_flag=True,
    show_default=True,
)
@click.option(
    "--refresh-interval",
    "-r",
    default=1.0,
    type=click.FloatRange(min=0, min_open=True),
    help="Refresh interval seconds",
)
@click.option("-v", "--verbose", count=True, default=2)
@click.option("-l", "--log-to", type=click.Path(), default=None)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Print each metrics snapshot as JSON without a TUI.",
)
@click.option(
    "--count",
    type=click.IntRange(min=1),
    default=None,
    help="Number of JSON samples; otherwise stream until interrupted.",
)
@click.option(
    "--version", is_flag=True, callback=print_version, expose_value=False, is_eager=True
)
@click.option("--debug/--no-debug", default=False)
def main(
    theme, auto_reload, refresh_interval, verbose, log_to, json_output, count, debug
):
    if sys.platform != "darwin":
        raise click.ClickException("Native metrics require macOS.")
    if not math.isfinite(refresh_interval):
        raise click.BadParameter("must be finite", param_hint="--refresh-interval")
    if count is not None and not json_output:
        raise click.UsageError("--count requires --json")
    verbose = max(min(int(verbose), 3), 0)
    log_level = LOG_LEVEL[verbose]
    setup_log(log_to is not None, log_level, log_to)

    if not json_output:
        theme = try_path(
            theme or ("m1.xml" if platform.machine() == "arm64" else "mactop.xml")
        )
    user_exited_event = threading.Event()
    manager = MetricsManager(refresh_interval, debug=debug)
    manager.start()
    try:
        if json_output:
            emitted = 0
            while count is None or emitted < count:
                click.echo(snapshot_json(manager.next_sample()))
                emitted += 1
        else:
            while not user_exited_event.is_set():
                app_body_items, styles_content = XmlLayoutLoader(
                    theme, refresh_interval
                ).load()
                MactopApp.CSS = styles_content
                app = MactopApp(app_body_items, user_exited_event)
                watcher_stop = threading.Event()
                reloaded = threading.Event()
                watcher = (
                    watch_theme_file_with_app(theme, app, watcher_stop, reloaded)
                    if auto_reload
                    else None
                )
                try:
                    app.run()
                finally:
                    watcher_stop.set()
                    if watcher:
                        watcher.join(timeout=2)
                if app.failure:
                    raise click.ClickException(
                        "Terminal UI failed; see the traceback above."
                    )
                if not reloaded.is_set():
                    break
    except RuntimeError as error:
        raise click.ClickException(str(error)) from error
    finally:
        manager.stop()
        logger.info("Mactop exited; metrics stopped")


def watch_theme_file_with_app(theme_file, app, stop_event, reloaded):
    def watch_file_bg_t(theme_file, app):
        try:
            last_content = Path(theme_file).read_text()
            while not stop_event.wait(1):
                with open(theme_file) as f:
                    content = f.read()

                if last_content != content:
                    logger.info(
                        "Theme file %s has been changed, restart the app...", theme_file
                    )
                    last_content = content
                    reloaded.set()
                    app.call_from_thread(app.exit)
                    return
        except Exception:
            logger.exception(f"error when watch the theme file {theme_file=}")

    t = threading.Thread(target=watch_file_bg_t, args=(theme_file, app), daemon=True)
    t.start()
    return t


def try_path(theme):
    if os.path.exists(theme):
        return theme

    current = Path(__file__).parent / "themes"

    buildin = current / theme
    logger.debug("%s doesn't exist, try %s", theme, buildin)
    if buildin.exists():
        logger.debug("n in, %s", buildin)
        return buildin

    logger.debug("theme try %s", buildin)
    buildin = current / f"{theme}.xml"
    if buildin.exists():
        return buildin

    raise click.FileError(theme, f"{theme} doesn't exist.")
