#!/usr/bin/env python3
"""Generate a minimal valid Android DEX binary for frontier-dex tests.

The output contains one public class `Hello` with a default constructor whose
body is a single `return-void` instruction. The file is accepted by the
frontier-dex parser and exercises the decompilation pipeline.
"""

from __future__ import annotations

import hashlib
import struct
import sys
import zlib
from pathlib import Path


def uleb128(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            byte |= 0x80
        out.append(byte)
        if not value:
            break
    return bytes(out)


def align4(offset: int) -> int:
    return (offset + 3) & ~3


def write_string_data(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return uleb128(len(value)) + encoded + b"\x00"


def dex_checksum(data: bytes) -> int:
    return zlib.adler32(data[12:]) & 0xFFFFFFFF


def dex_signature(data: bytes) -> bytes:
    return hashlib.sha1(data[32:]).digest()


def build_minimal_dex() -> bytes:
    strings = ["LHello;", "Ljava/lang/Object;", "<init>", "V"]

    header_size = 112
    string_ids_off = header_size
    string_ids_size = len(strings)
    string_ids_bytes = string_ids_size * 4

    type_ids_off = string_ids_off + string_ids_bytes
    type_ids_size = 3
    type_ids_bytes = type_ids_size * 4

    proto_ids_off = type_ids_off + type_ids_bytes
    proto_ids_size = 1
    proto_ids_bytes = proto_ids_size * 12

    field_ids_off = proto_ids_off + proto_ids_bytes
    field_ids_size = 0

    method_ids_off = field_ids_off
    method_ids_size = 1
    method_ids_bytes = method_ids_size * 8

    class_defs_off = method_ids_off + method_ids_bytes
    class_defs_size = 1
    class_defs_bytes = class_defs_size * 32

    data_off = align4(class_defs_off + class_defs_bytes)

    # Data section: string_data, code_item, class_data_item, map_list
    data = bytearray()
    string_data_offsets: list[int] = []

    for value in strings:
        string_data_offsets.append(data_off + len(data))
        data.extend(write_string_data(value))

    data = data.ljust(align4(len(data)) - data_off, b"\x00")
    while len(data) < align4(len(data)):
        data.append(0)

    # code_item offset relative to data_off
    code_item_off = data_off + len(data)
    code_item = struct.pack(
        "<HHHHII",
        1,  # registers_size
        0,  # ins_size
        0,  # outs_size
        0,  # tries_size
        0,  # debug_info_off
        1,  # insns_size (in 16-bit code units)
    ) + struct.pack("<H", 0x000F)  # return-void (frontier-dex opcode mapping)
    data.extend(code_item)
    data = data.ljust(align4(len(data)) - data_off, b"\x00")
    while len(data) < align4(len(data)):
        data.append(0)

    class_data_off = data_off + len(data)
    class_data = bytearray()
    class_data.extend(uleb128(0))  # static_fields_size
    class_data.extend(uleb128(0))  # instance_fields_size
    class_data.extend(uleb128(1))  # direct_methods_size
    class_data.extend(uleb128(0))  # method_idx delta
    class_data.extend(uleb128(0x10001))  # public constructor
    class_data.extend(uleb128(code_item_off))
    class_data.extend(uleb128(0))  # virtual_methods_size
    data.extend(class_data)
    data = data.ljust(align4(len(data)) - data_off, b"\x00")
    while len(data) < align4(len(data)):
        data.append(0)

    map_off = data_off + len(data)
    map_items = [
        (0x0000, 1, 0),  # HeaderItem
        (0x0001, string_ids_size, string_ids_off),
        (0x0002, type_ids_size, type_ids_off),
        (0x0003, proto_ids_size, proto_ids_off),
        (0x0005, method_ids_size, method_ids_off),
        (0x0006, class_defs_size, class_defs_off),
        (0x2000, 1, class_data_off),
        (0x2001, 1, code_item_off),
        (0x2002, string_ids_size, string_data_offsets[0]),
        (0x1000, 1, map_off),
    ]
    data.extend(struct.pack("<I", len(map_items)))
    for kind, size, offset in map_items:
        data.extend(struct.pack("<HHI I", kind, 0, size, offset))

    file_size = data_off + len(data)

    dex = bytearray(file_size)
    dex[0:8] = b"dex\n035\x00"
    struct.pack_into("<I", dex, 32, file_size)
    struct.pack_into("<I", dex, 36, header_size)
    struct.pack_into("<I", dex, 40, 0x12345678)
    struct.pack_into("<I", dex, 52, map_off)
    struct.pack_into("<I", dex, 56, string_ids_size)
    struct.pack_into("<I", dex, 60, string_ids_off)
    struct.pack_into("<I", dex, 64, type_ids_size)
    struct.pack_into("<I", dex, 68, type_ids_off)
    struct.pack_into("<I", dex, 72, proto_ids_size)
    struct.pack_into("<I", dex, 76, proto_ids_off)
    struct.pack_into("<I", dex, 80, field_ids_size)
    struct.pack_into("<I", dex, 84, field_ids_off)
    struct.pack_into("<I", dex, 88, method_ids_size)
    struct.pack_into("<I", dex, 92, method_ids_off)
    struct.pack_into("<I", dex, 96, class_defs_size)
    struct.pack_into("<I", dex, 100, class_defs_off)
    struct.pack_into("<I", dex, 104, len(data))
    struct.pack_into("<I", dex, 108, data_off)

    for idx, offset in enumerate(string_data_offsets):
        struct.pack_into("<I", dex, string_ids_off + idx * 4, offset)

    type_indices = [0, 1, 3]
    for idx, string_idx in enumerate(type_indices):
        struct.pack_into("<I", dex, type_ids_off + idx * 4, string_idx)

    struct.pack_into("<III", dex, proto_ids_off, 3, 2, 0)

    struct.pack_into("<HHI", dex, method_ids_off, 0, 0, 2)

    struct.pack_into(
        "<IIIIIIII",
        dex,
        class_defs_off,
        0,  # class_idx -> LHello;
        0x0001,  # public
        1,  # superclass -> Ljava/lang/Object;
        0,  # interfaces_off
        0xFFFFFFFF,  # no source file
        0,  # annotations_off
        class_data_off,
        0,  # static_values_off
    )

    dex[data_off:] = data

    struct.pack_into("<I", dex, 8, dex_checksum(bytes(dex)))
    dex[12:32] = dex_signature(bytes(dex))

    return bytes(dex)


def main() -> int:
    out = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "minimal.dex"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(build_minimal_dex())
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
