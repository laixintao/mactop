from rich.text import Text


def sizeof_fmt_plain(num, suffix="B"):
    """
    credit: Fred Cirera
      - https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
      - https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
    """
    f = "{num:.1f}{unit}{suffix}"
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f.format(num=num, unit=unit, suffix=suffix)
        num /= 1024.0
    return f.format(num=num, unit="Yi", suffix=suffix)


def sizeof_fmt(num, suffix="B"):
    """
    return Text
    """
    f = "{num:>6.1f}[b]{unit:<2}{suffix}[/b]"
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return Text.from_markup(f.format(num=num, unit=unit, suffix=suffix))
        num /= 1024.0
    return Text.from_markup(f.format(num=num, unit="Yi", suffix=suffix))


def speed_sizeof_fmt(num, suffix="B"):
    """
    Return 11 chars constant
    """
    f = "{num:>6.1f}[b]{unit:<2}{suffix}/s[/b]"
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return Text.from_markup(f.format(num=num, unit=unit, suffix=suffix))
        num /= 1024.0
    return Text.from_markup(f.format(num=num, unit="Yi", suffix=suffix))


def packet_speed_fmt(num, suffix="packets/s", align=">"):
    """
    always return 16 chars
    """
    f = "{num:%s5.1f}[b]{unit:<1}[/b]%s" % (align, suffix)
    for unit in ("", "k", "M"):
        if abs(num) < 1000:
            return Text.from_markup(f.format(num=num, unit=unit))
        num /= 1000.0
    return Text.from_markup(f.format(num=num, unit="B"))


def render_cpu_percentage_1(percentages):
    busy = (1 - percentages[-1]) * 100
    return f"{busy:5.2f}%"


def render_cpu_percentage_100(percentages):
    busy = 100 - percentages[-1]
    return f"{busy:2.0f}%"


def hz_format(num, suffix="hz"):
    f = "{num:>4d}{unit:<1}{suffix}"
    for unit in ("", "k"):
        num = int (num)
        if abs(num) < 1000:
            return Text.from_markup(f.format(num=num, unit=unit, suffix=suffix))
        num //= 1000
    return Text.from_markup(f.format(num=num, unit="M", suffix=suffix))
