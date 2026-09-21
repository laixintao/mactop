# Custom layouts

The `--theme` option loads an XML layout with Textual CSS. To start with the
current dashboard, copy a bundled layout from your checkout:

```shell
cp mactop/themes/m1.xml my-theme.xml
uv run --locked mactop --theme ./my-theme.xml --auto-reload
```

Save the file to reload the UI. If you installed mactop as a uv tool, use
`mactop --theme /path/to/my-theme.xml --auto-reload`.

## Layout structure

The default layout consists of two widgets:

```xml
<Mactop>
  <layout>
    <OverviewPanel />
    <TaskTable id="processes" />
  </layout>
  <style>
    Dashboard {
      padding: 1;
    }
    #processes {
      height: 12;
      margin-top: 1;
    }
  </style>
</Mactop>
```

`OverviewPanel` renders the summary cards and adapts their arrangement to the
available width. `TaskTable` renders processes sorted by CPU usage. Copying a
bundled layout also preserves its colors, borders, and scrollbar styles; the
minimal example above only defines spacing and table height.

`Vertical` and `Horizontal` containers can group widgets. Widgets accept `id`,
`name`, and space-separated `class` or `classes` attributes. Metric panels accept
`refresh_interval` to control their display refresh; the CLI `-r` option controls
the collector's sampling interval.

## Styling limits

The overview renders its cards as a single widget. XML and CSS can position or
style that widget, but cannot select individual cards inside it. Their colors
and arrangement are defined in
[overview.py](../mactop/panels/overview.py).

For an individual component's power history, `PowerPanel` can be used outside
the overview:

```xml
<PowerPanel component="ane" label="ANE Power" />
```

Supported component keys are `cpu`, `gpu`, `ane`, `dram`, `gpu_sram`, and `system`.
The value is `N/A` when the native source has no reading for that component.

The [widget registry](../mactop/panels/__init__.py) also contains older widgets
for existing layouts. Registration does not guarantee that the current
collector supplies their data: `BacklightDisplayText` and the legacy Intel
`CPUFreqPanel` have no active data source. Use the overview for the readings
listed in the [README](../README.md#what-it-shows).
