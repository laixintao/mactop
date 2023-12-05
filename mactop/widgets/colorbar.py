import logging
from rich.console import RenderableType
from rich.style import Style
from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

logger = logging.getLogger(__name__)


class ColorBar(Widget):
    BARS = [
        "▏",  # left 1/8
        "▎",  # left 2/8
        "▍",  # left 3/8
        "▌",  # left 4/8
        "▋",  # left 5/8
        "▊",  # left 6/8
        "▉",  # left 7/8
        "█",  # full
    ]
    percentages = reactive(None)

    def __init__(
        self,
        color_choices,
        percentages=None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.percentages = percentages
        self.color_choices = color_choices

    def render(self) -> RenderableType:
        # TODO not exceeding options.max_width?

        width = self.size.width
        if not self.percentages:
            return " " * width

        _total = sum(self.percentages)
        if not _total:
            return " "
        percentages = [p / _total for p in self.percentages]
        units = width * 8

        if not self.color_choices or len(self.color_choices) != len(self.color_choices):
            return "ERR: color not match"

        total = len(percentages)

        previous_taken_units = 0

        segments = []
        for index, (percent, color) in enumerate(zip(percentages, self.color_choices)):
            current_units = max(units * percent - previous_taken_units, 0)
            full_block_count = int(current_units // 8)
            reminder_units = int(current_units % 8)
            if reminder_units:
                reminder_block = self.BARS[reminder_units - 1]
            else:
                reminder_block = ""

            display = "".join(full_block_count * self.BARS[-1])
            display += reminder_block

            if index < total - 1:
                next_color = self.color_choices[index + 1]
            else:
                next_color = color

            segments.append((display, Style(color=color, bgcolor=next_color)))

        bar = Text.assemble(*segments)

        return bar
