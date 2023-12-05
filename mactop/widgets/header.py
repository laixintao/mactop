from textual.widgets import Header
from textual.widgets._header import HeaderTitle, HeaderClock, HeaderClockSpace
from textual.reactive import Reactive
from textual.app import RenderResult
from textual.widget import Widget


class HeaderIcon(Widget):
    """Display an 'icon' on the left of the header."""

    DEFAULT_CSS = """
    HeaderIcon {
        dock: left;
        padding: 0 1;
        width: 8;
        content-align: left middle;
    }
    """

    icon = Reactive("")
    """The character to use as the icon within the header."""

    def render(self) -> RenderResult:
        """Render the header icon.

        Returns:
            The rendered icon.
        """
        return self.icon


class MactopHeader(Header):
    def compose(self):
        yield HeaderIcon()
        yield HeaderTitle()
        yield HeaderClock() if self._show_clock else HeaderClockSpace()
