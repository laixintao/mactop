"""Small, owned CoreFoundation/IOKit bindings. No helper processes are spawned."""

import ctypes as C
import plistlib
import sys
from contextlib import contextmanager


class NativeError(RuntimeError):
    pass


def bind(lib, name, result, *args):
    function = getattr(lib, name)
    function.restype = result
    function.argtypes = list(args)
    return function


class CoreFoundation:
    UTF8 = 0x08000100

    def __init__(self):
        if sys.platform != "darwin":
            raise NativeError("Native metrics require macOS")
        self.lib = C.CDLL(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        signatures = {
            "CFRelease": (None, C.c_void_p),
            "CFStringCreateWithCString": (
                C.c_void_p,
                C.c_void_p,
                C.c_char_p,
                C.c_uint32,
            ),
            "CFStringGetLength": (C.c_long, C.c_void_p),
            "CFStringGetMaximumSizeForEncoding": (C.c_long, C.c_long, C.c_uint32),
            "CFStringGetCString": (
                C.c_bool,
                C.c_void_p,
                C.c_void_p,
                C.c_long,
                C.c_uint32,
            ),
            "CFDictionaryGetValue": (C.c_void_p, C.c_void_p, C.c_void_p),
            "CFArrayGetCount": (C.c_long, C.c_void_p),
            "CFArrayGetValueAtIndex": (C.c_void_p, C.c_void_p, C.c_long),
            "CFPropertyListCreateData": (
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
                C.c_long,
                C.c_ulong,
                C.POINTER(C.c_void_p),
            ),
            "CFPropertyListCreateWithData": (
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
                C.c_ulong,
                C.c_void_p,
                C.POINTER(C.c_void_p),
            ),
            "CFDataCreate": (C.c_void_p, C.c_void_p, C.c_char_p, C.c_long),
            "CFDataGetLength": (C.c_long, C.c_void_p),
            "CFDataGetBytePtr": (C.c_void_p, C.c_void_p),
        }
        for name, signature in signatures.items():
            bind(self.lib, name, *signature)

    def release(self, ref):
        if ref:
            self.lib.CFRelease(ref)

    @contextmanager
    def string(self, value):
        ref = self.lib.CFStringCreateWithCString(None, value.encode(), self.UTF8)
        if not ref:
            raise NativeError("Could not allocate CFString")
        try:
            yield ref
        finally:
            self.release(ref)

    def text(self, ref):
        if not ref:
            return ""
        length = self.lib.CFStringGetLength(ref)
        size = self.lib.CFStringGetMaximumSizeForEncoding(length, self.UTF8) + 1
        buffer = C.create_string_buffer(size)
        if not self.lib.CFStringGetCString(ref, buffer, size, self.UTF8):
            raise NativeError("Could not decode CFString")
        return buffer.value.decode("utf-8")

    def get(self, dictionary, key):
        with self.string(key) as key_ref:
            return self.lib.CFDictionaryGetValue(dictionary, key_ref)

    def items(self, array):
        if array:
            for index in range(self.lib.CFArrayGetCount(array)):
                yield self.lib.CFArrayGetValueAtIndex(array, index)

    def to_python(self, ref):
        error = C.c_void_p()
        data = self.lib.CFPropertyListCreateData(None, ref, 200, 0, C.byref(error))
        try:
            if not data:
                raise NativeError("Could not serialize IOKit properties")
            raw = C.string_at(
                self.lib.CFDataGetBytePtr(data), self.lib.CFDataGetLength(data)
            )
            return plistlib.loads(raw)
        finally:
            self.release(data)
            self.release(error)

    @contextmanager
    def from_python(self, value):
        raw = plistlib.dumps(value, fmt=plistlib.FMT_BINARY)
        data = self.lib.CFDataCreate(None, raw, len(raw))
        error = C.c_void_p()
        ref = None
        try:
            ref = self.lib.CFPropertyListCreateWithData(
                None, data, 0, None, C.byref(error)
            )
            if not ref:
                raise NativeError("Could not create CoreFoundation property list")
            yield ref
        finally:
            self.release(ref)
            self.release(data)
            self.release(error)


class IOKit:
    def __init__(self, cf=None):
        self.cf = cf or CoreFoundation()
        self.lib = C.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
        signatures = {
            "IOServiceMatching": (C.c_void_p, C.c_char_p),
            "IOServiceGetMatchingServices": (
                C.c_int,
                C.c_uint,
                C.c_void_p,
                C.POINTER(C.c_uint),
            ),
            "IOIteratorNext": (C.c_uint, C.c_uint),
            "IOObjectRelease": (C.c_int, C.c_uint),
            "IORegistryEntryGetName": (C.c_int, C.c_uint, C.c_void_p),
            "IORegistryEntryCreateCFProperties": (
                C.c_int,
                C.c_uint,
                C.POINTER(C.c_void_p),
                C.c_void_p,
                C.c_uint,
            ),
        }
        for name, signature in signatures.items():
            bind(self.lib, name, *signature)

    @contextmanager
    def services(self, service_class):
        matching = self.lib.IOServiceMatching(service_class.encode())
        if not matching:
            raise NativeError(f"No matching dictionary for {service_class}")
        iterator = C.c_uint()
        # IOServiceGetMatchingServices consumes the matching dictionary.
        result = self.lib.IOServiceGetMatchingServices(0, matching, C.byref(iterator))
        if result:
            raise NativeError(
                f"{service_class}: IOKit error 0x{result & 0xffffffff:08x}"
            )
        entries = []
        try:
            while entry := self.lib.IOIteratorNext(iterator):
                entries.append(entry)
            yield entries
        finally:
            for entry in entries:
                self.lib.IOObjectRelease(entry)
            self.lib.IOObjectRelease(iterator)

    def name(self, entry):
        buffer = C.create_string_buffer(128)
        if self.lib.IORegistryEntryGetName(entry, buffer):
            return ""
        return buffer.value.decode(errors="replace")

    def properties(self, entry):
        ref = C.c_void_p()
        result = self.lib.IORegistryEntryCreateCFProperties(
            entry, C.byref(ref), None, 0
        )
        try:
            if result or not ref:
                raise NativeError(f"Could not read IOKit properties: {result}")
            return self.cf.to_python(ref)
        finally:
            self.cf.release(ref)

    def battery(self):
        with self.services("AppleSmartBattery") as entries:
            return self.properties(entries[0]) if entries else None

    def frequency_tables(self):
        tables = {}
        with self.services("AppleARMIODevice") as entries:
            for entry in entries:
                if self.name(entry) in ("pmgr", "clpc"):
                    for key, data in self.properties(entry).items():
                        if key.startswith("voltage-states") and isinstance(data, bytes):
                            tables.setdefault(key, data)
        return tables
