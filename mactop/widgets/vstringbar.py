import logging
from rich.console import RenderableType
from rich.style import Style
from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

logger = logging.getLogger(__name__)


class VStringBar(Widget):
    BAR = "|"
    percentages = reactive(None)

    def __init__(
        self,
        color_choices,
        percentages=None,
        last_empty=True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.percentages = percentages
        self.color_choices = color_choices
        self.last_empty = last_empty

    def render(self) -> RenderableType:
        width = self.size.width
        content_width = width - 2
        content = self.render_content(content_width)
        return Text.assemble(
            ("[", Style(bold=True)),
            content,
            ("]", Style(bold=True)),
        )

    def render_content(self, width):
        if not self.percentages:
            return " " * width

        _total = sum(self.percentages)

        if not _total:
            return " " * width
        percentages = [p / _total for p in self.percentages]

        if not self.color_choices or len(self.color_choices) != len(self.color_choices):
            return "ERR: color not match"

        segments = []
        left_spaces = width
        count = len(self.percentages)
        for index, (percent, color) in enumerate(zip(percentages, self.color_choices)):
            if index == count - 1:  # last one
                if self.last_empty:
                    b = " "
                else:
                    b = self.BAR
                segments.append((b * left_spaces, Style(color=color)))
                break
            current = int(width * percent)
            segments.append((self.BAR * current, Style(color=color)))
            left_spaces -= current

        bar = Text.assemble(*segments)

        return bar
