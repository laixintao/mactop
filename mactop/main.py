import logging
import os
from pathlib import Path
import threading
import time

import click
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from mactop.layout_loader import XmlLayoutLoader
from mactop.metrics_source import IORegManager, PowerMetricsManager, PsutilManager
from mactop.widgets.header import MactopHeader

from . import __version__


LOG_LOCATION = "/tmp/mactop.log"
logger = logging.getLogger(__name__)
user_exited_event = threading.Event()


def setup_log(enabled, level, loglocation):
    if enabled:
        logging.basicConfig(
            filename=os.path.expanduser(loglocation),
            filemode="a",
            format="%(asctime)s %(levelname)5s (%(module)s) %(message)s",
            level=level,
        )
    else:
        logging.disable(logging.CRITICAL)
    logger.info("------ mactop ------")


class MactopApp(App):
    BINDINGS = [
        Binding("ctrl+c,q", "exit", "Exit", show=True, priority=True, key_display="Q"),
    ]

    def __init__(self, app_body_items, user_exited_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_body_items = app_body_items
        self.user_exited_event = user_exited_event

    def on_mount(self) -> None:
        self.title = "mactop"
        self.sub_title = f"v{__version__}"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield MactopHeader(show_clock=True)
        yield Footer()

        for item in self.app_body_items:
            yield item

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_exit(self) -> None:
        self.user_exited_event.set()
        self.exit()


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
    default=(Path(__file__).parent / "themes/mactop.xml"),
    help="Mactop theme file location.",
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
    help="Refresh interval seconds",
)
@click.option("-v", "--verbose", count=True, default=2)
@click.option("-l", "--log-to", type=click.Path(), default=None)
@click.option("--powermetrics-fake", type=click.Path(), default=None)
@click.option(
    "--version", is_flag=True, callback=print_version, expose_value=False, is_eager=True
)
@click.option("--debug/--no-debug", default=False)
def main(
    theme, auto_reload, refresh_interval, verbose, log_to, powermetrics_fake, debug
):
    verbose = max(min(int(verbose), 5), 0)
    log_level = LOG_LEVEL[verbose]
    setup_log(log_to is not None, log_level, log_to)

    theme = try_path(theme)
    logger.debug("Using theme file %s", theme)

    metrics_source_manager = PowerMetricsManager(refresh_interval, debug=debug)
    if not powermetrics_fake:
        metrics_source_manager.start()
    else:
        metrics_source_manager.start_fake_data(str(powermetrics_fake))

    ioreg_manager = IORegManager(refresh_interval)
    ioreg_manager.start()

    psutil_manager = PsutilManager(refresh_interval)
    psutil_manager.start()

    while not user_exited_event.is_set():
        layout_loader = XmlLayoutLoader(theme, refresh_interval)
        app_body_items, styles_content = layout_loader.load()
        MactopApp.CSS = styles_content
        app = MactopApp(app_body_items, user_exited_event)
        if auto_reload:
            watch_theme_file_with_app(theme, app)
        app.run()

    logger.info("Mactop exited")
    metrics_source_manager.stop()
    ioreg_manager.stop()
    logger.info("Metrics stopped")


def watch_theme_file_with_app(theme_file, app):
    def watch_file_bg_t(theme_file, app):
        try:
            last_content = None
            while True:
                with open(theme_file) as f:
                    content = f.read()

                if last_content is None:
                    last_content = content
                    continue

                if last_content != content:
                    logger.info(
                        "Theme file %s has been changed, restart the app...", theme_file
                    )
                    last_content = content
                    app.exit()
                    return

                time.sleep(1)
        except:
            logger.exception(f"error when watch the theme file {theme_file=}")

    t = threading.Thread(target=watch_file_bg_t, args=(theme_file, app), daemon=True)
    t.start()


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
