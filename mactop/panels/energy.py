from .power import PowerPanel


class IntelProcessorEnergyPanel(PowerPanel):
    """Compatibility name; unsupported CPU power counters display N/A."""

    def __init__(self, label="CPU Power", show_value=True, *args, **kwargs):
        super().__init__(
            component="cpu", label=label, show_value=show_value, *args, **kwargs
        )
