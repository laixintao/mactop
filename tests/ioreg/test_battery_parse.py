def test_macbookpro_16_1_charge_94w():
    data = {
        "AdapterDetails": {
            "AdapterID": 1,
            "AdapterVoltage": 20000,
            "Current": 4700,
            "FamilyCode": -1,
            "FwVersion": "00001",
            "HwVersion": "1.0",
            "IsWireless": False,
            "Manufacturer": "Apple Inc.",
            "Model": "0x7002",
            "Name": "96W USB-C Power Adapter",
            "PMUConfiguration": 4648,
            "SerialString": "CAAAAAAAAAAAAAAA",
            "Watts": 94,
        }
    }


def test_macbookpro_16_1_no_charge():
    data = {"AdapterDetails": {"FamilyCode": 0}}
