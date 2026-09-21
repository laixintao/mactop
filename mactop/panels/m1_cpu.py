from .power import PowerPanel


class M1CPUEnergyPanel(PowerPanel):
    """Compatibility name for existing XML themes."""

    def __init__(self, label="CPU Power", show_value=True, *args, **kwargs):
        super().__init__(
            component="cpu", label=label, show_value=show_value, *args, **kwargs
        )
