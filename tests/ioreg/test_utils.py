from mactop.utils.formatting import speed_sizeof_fmt, packet_speed_fmt, hz_format


def test_speed_sizeof_fmt():
    assert "   0.0  B/s" == str(speed_sizeof_fmt(0))
    assert "   1.0KiB/s" == str(speed_sizeof_fmt(1024))
    assert " 200.1  B/s" == str(speed_sizeof_fmt(200.12))
    assert "   4.0MiB/s" == str(speed_sizeof_fmt(1024 * 1024 * 4))
    assert "   4.0GiB/s" == str(speed_sizeof_fmt(1024 * 1024 * 1024 * 4))
    assert "1004.0TiB/s" == str(speed_sizeof_fmt(1024 * 1024 * 1024 * 1024 * 1004))


def test_packet_speed_format():
    assert "  1.0k packets/s" == str(packet_speed_fmt(1024, suffix=" packets/s"))
    assert "200.1 packets/s" == str(packet_speed_fmt(200.12))
    assert "  4.2Mpackets/s" == str(packet_speed_fmt(1024 * 1024 * 4))
    assert "  4.3Bpackets/s" == str(packet_speed_fmt(1024 * 1024 * 1024 * 4))
    assert "  0.0 packets/s" == str(packet_speed_fmt(0))


def test_hz_format():
    assert "2604Mhz" == str(hz_format(2604490000.0))
    assert "2804Mhz" == str(hz_format(2804490000.0))
