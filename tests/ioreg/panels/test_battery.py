from mactop.panels.battery import ChargingRateDisplay


def test_battery_changing_get_second_last():
    b = ChargingRateDisplay()
    charging_history = [
        (1693963302.615168, 3461),
        (1693963303.615168, 3469),
        (1693963304.654001, 3469),
        (1693963305.694818, 3469),
        (1693963306.738291, 3469),
        (1693963307.7792552, 3469),
        (1693963308.820713, 3469),
        (1693963309.862436, 3469),
        (1693963310.9057229, 3469),
        (1693963311.9352791, 3469),
        (1693963312.973173, 3469),
        (1693963314.013309, 3469),
        (1693963315.055441, 3469),
        (1693963316.09519, 3469),
        (1693963317.1332538, 3469),
        (1693963318.187357, 3469),
        (1693963319.230877, 3469),
        (1693963320.277039, 3519),
        (1693963321.313658, 3519),
        (1693963322.361393, 3519),
    ]
    result = b._get_last_change(charging_history)
    assert result == (
        (1693963303.615168, 3469),
        (1693963320.277039, 3519),
    )


def test_battery_changing_get_second_last_only_1_or_empty():
    b = ChargingRateDisplay()
    charging_history = [
        (1693963322.361393, 3519),
    ]
    result = b._get_last_change(charging_history)
    assert result == (None, None)
    charging_history = []
    result = b._get_last_change(charging_history)
    assert result == (None, None)


def test_battery_changing_get_second_last_only_2():
    b = ChargingRateDisplay()
    charging_history = [
        (1693963317.1332538, 3469),
        (1693963322.361393, 3519),
    ]
    result = b._get_last_change(charging_history)
    assert result == (None, None)
