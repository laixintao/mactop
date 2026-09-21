"""Read-only AppleSMC and IOHID temperature access.

SMC ABI reference: context-labs/mactop (MIT), see THIRD_PARTY_NOTICES.md.
Only read-key, read-index and read-info commands are implemented.
"""

import ctypes as C
import math
import struct

from .macos import IOKit, NativeError, bind


class Version(C.Structure):
    _fields_ = [
        ("major", C.c_uint8),
        ("minor", C.c_uint8),
        ("build", C.c_uint8),
        ("reserved", C.c_uint8),
        ("release", C.c_uint16),
    ]


class PowerLimit(C.Structure):
    _fields_ = [
        ("version", C.c_uint16),
        ("length", C.c_uint16),
        ("cpu", C.c_uint32),
        ("gpu", C.c_uint32),
        ("memory", C.c_uint32),
    ]


class KeyInfo(C.Structure):
    _fields_ = [("size", C.c_uint32), ("type", C.c_uint32), ("attributes", C.c_uint8)]


class KeyData(C.Structure):
    _fields_ = [
        ("key", C.c_uint32),
        ("version", Version),
        ("limits", PowerLimit),
        ("info", KeyInfo),
        ("result", C.c_uint8),
        ("status", C.c_uint8),
        ("command", C.c_uint8),
        ("index", C.c_uint32),
        ("data", C.c_uint8 * 32),
    ]


def decode_smc(kind, data):
    if kind == "flt " and len(data) == 4:
        value = struct.unpack("<f", data)[0]
    elif kind == "sp78" and len(data) == 2:
        value = int.from_bytes(data, "big", signed=True) / 256
    elif kind == "fpe2" and len(data) == 2:
        value = int.from_bytes(data, "big") / 4
    elif kind in {"ui8 ", "ui16", "ui32"}:
        value = int.from_bytes(data, "big")
    else:
        return None
    return value if math.isfinite(value) else None


class SMC:
    def __init__(self, kit):
        self.kit = kit
        self.connection = C.c_uint()
        self.info = {}
        self.cpu_keys = []
        self.gpu_keys = []
        lib = kit.lib
        bind(
            lib,
            "IOServiceOpen",
            C.c_int,
            C.c_uint,
            C.c_uint,
            C.c_uint,
            C.POINTER(C.c_uint),
        )
        bind(lib, "IOServiceClose", C.c_int, C.c_uint)
        bind(
            lib,
            "IOConnectCallStructMethod",
            C.c_int,
            C.c_uint,
            C.c_uint,
            C.c_void_p,
            C.c_size_t,
            C.c_void_p,
            C.POINTER(C.c_size_t),
        )
        task = C.c_uint.in_dll(
            C.CDLL("/usr/lib/libSystem.B.dylib"), "mach_task_self_"
        ).value
        with kit.services("AppleSMC") as entries:
            if not entries:
                raise NativeError("AppleSMC service unavailable")
            result = lib.IOServiceOpen(entries[0], task, 0, C.byref(self.connection))
            if result:
                raise NativeError(f"AppleSMC open failed: 0x{result & 0xffffffff:08x}")
        try:
            count = self.read("#KEY")
            if count is None or not 0 < count <= 65536:
                raise NativeError("AppleSMC key enumeration unavailable")
            for index in range(int(count)):
                request = KeyData(command=8, index=index)
                try:
                    response = self.call(request)
                except NativeError:
                    continue
                name = response.key.to_bytes(4, "big").decode("ascii", errors="replace")
                if name.startswith(("Tp", "Te", "TC")):
                    self.cpu_keys.append(name)
                elif name.startswith(("Tg", "TG")):
                    self.gpu_keys.append(name)
        except Exception:
            self.close()
            raise

    def call(self, request):
        response = KeyData()
        size = C.c_size_t(C.sizeof(response))
        code = self.kit.lib.IOConnectCallStructMethod(
            self.connection,
            2,
            C.byref(request),
            C.sizeof(request),
            C.byref(response),
            C.byref(size),
        )
        if code or response.result or size.value != C.sizeof(response):
            raise NativeError(f"AppleSMC read failed: {code}, result={response.result}")
        return response

    def read(self, name):
        try:
            key = int.from_bytes(name.encode("ascii"), "big")
            if name not in self.info:
                self.info[name] = self.call(KeyData(key=key, command=9)).info
            info = self.info[name]
            if not 0 < info.size <= 32:
                return None
            request = KeyData(key=key, command=5)
            request.info.size = info.size
            response = self.call(request)
            kind = info.type.to_bytes(4, "big").decode("ascii", errors="replace")
            return decode_smc(kind, bytes(response.data[: info.size]))
        except (NativeError, UnicodeError):
            return None

    def close(self):
        if self.connection.value:
            self.kit.lib.IOServiceClose(self.connection)
            self.connection = C.c_uint()


def average_temperature(values):
    valid = [value for value in values if value is not None and 0 < value < 150]
    return sum(valid) / len(valid) if valid else None


class HID:
    def __init__(self, kit):
        self.kit = kit
        self.client = None
        signatures = {
            "IOHIDEventSystemClientCreate": (C.c_void_p, C.c_void_p),
            "IOHIDEventSystemClientSetMatching": (None, C.c_void_p, C.c_void_p),
            "IOHIDEventSystemClientCopyServices": (C.c_void_p, C.c_void_p),
            "IOHIDServiceClientCopyProperty": (C.c_void_p, C.c_void_p, C.c_void_p),
            "IOHIDServiceClientCopyEvent": (
                C.c_void_p,
                C.c_void_p,
                C.c_int64,
                C.c_int32,
                C.c_int64,
            ),
            "IOHIDEventGetFloatValue": (C.c_double, C.c_void_p, C.c_int64),
        }
        for name, signature in signatures.items():
            bind(kit.lib, name, *signature)
        self.client = kit.lib.IOHIDEventSystemClientCreate(None)
        if not self.client:
            raise NativeError("IOHID client unavailable")
        try:
            with kit.cf.from_python(
                {"PrimaryUsagePage": 0xFF00, "PrimaryUsage": 5}
            ) as matching:
                kit.lib.IOHIDEventSystemClientSetMatching(self.client, matching)
        except Exception:
            self.close()
            raise

    def temperatures(self):
        cf, lib = self.kit.cf, self.kit.lib
        cpu, gpu = [], []
        services = lib.IOHIDEventSystemClientCopyServices(self.client)
        try:
            for service in cf.items(services):
                with cf.string("Product") as key:
                    product = lib.IOHIDServiceClientCopyProperty(service, key)
                event = None
                try:
                    name = cf.text(product)
                    event = lib.IOHIDServiceClientCopyEvent(service, 15, 0, 0)
                    if not event:
                        continue
                    value = lib.IOHIDEventGetFloatValue(event, 15 << 16)
                    if any(part in name for part in ("PMU tdie", "pACC", "eACC")):
                        cpu.append(value)
                    elif "GPU" in name:
                        gpu.append(value)
                finally:
                    cf.release(product)
                    cf.release(event)
        finally:
            cf.release(services)
        return average_temperature(cpu), average_temperature(gpu)

    def close(self):
        self.kit.cf.release(self.client)
        self.client = None


class Sensors:
    def __init__(self, kit):
        self.smc = None
        self.hid = None
        self.errors = {}
        try:
            self.smc = SMC(kit)
        except (NativeError, OSError, AttributeError) as error:
            self.errors["smc"] = str(error)
        try:
            self.hid = HID(kit)
        except (NativeError, OSError, AttributeError) as error:
            self.errors["hid"] = str(error)

    def sample(self):
        cpu = gpu = fan = power = None
        if self.smc:
            cpu = average_temperature(self.smc.read(key) for key in self.smc.cpu_keys)
            gpu = average_temperature(self.smc.read(key) for key in self.smc.gpu_keys)
            fan = self.smc.read("F0Ac")
            power = self.smc.read("PSTR")
            if power is not None and power < 0:
                power = None
        if self.hid and (cpu is None or gpu is None):
            hid_cpu, hid_gpu = self.hid.temperatures()
            cpu = hid_cpu if cpu is None else cpu
            gpu = hid_gpu if gpu is None else gpu
        return cpu, gpu, fan, power

    def close(self):
        if self.smc:
            self.smc.close()
        if self.hid:
            self.hid.close()
