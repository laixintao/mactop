import logging
from pathlib import Path
import xml.etree.ElementTree as ET

from mactop.layouts import LAYOUTS
from mactop.panels import PANELS


logger = logging.getLogger(__name__)

CACHE_LOCATION = Path("~/.config/mactop/cache").expanduser()


class XmlLayoutLoader:
    COMMON_ATTRS = ("id", "class", "name")

    def __init__(self, location, refresh_interval) -> None:
        self.file_location = location
        self.refresh_interval = refresh_interval

    def load(self):
        tree = ET.parse(self.file_location)
        root = tree.getroot()

        css = ""
        style = root.find("style")
        if style is not None and style.text is not None:
            logger.debug("parse")
            css = style.text

        layout = root.find("layout")
        app_body_items = self.compose_body(layout)

        return app_body_items, css

    def compose_body(self, layout):
        widgets = []
        for child_node in layout:
            child_widget = None
            widget_name = child_node.tag
            init_args = []

            logger.debug("loading node: %s", widget_name)

            is_panel = False
            if panel := PANELS.get(widget_name):
                child_widget = panel
                is_panel = True

            elif child_layout := LAYOUTS.get(widget_name):
                child_widget = child_layout
                init_args = self.compose_body(child_node)

            if not child_widget:
                raise Exception(f"Unsupported node: {widget_name}")

            kwargs = dict(child_node.items())

            logger.info("node %s attrs: %s", child_widget, kwargs)
            if css_class := kwargs.pop("class", None):
                kwargs["classes"] = css_class

            if "refresh_interval" not in kwargs and is_panel:
                kwargs["refresh_interval"] = self.refresh_interval

            logger.debug(
                "init child widget, name=%s, init_args=%s, kwargs=%s",
                widget_name,
                init_args,
                kwargs,
            )
            w = child_widget(*init_args, **kwargs)
            widgets.append(w)

        return widgets
