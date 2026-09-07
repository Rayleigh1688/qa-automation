"""FILBET CBOR subset and response decoding.

This is not a general-purpose CBOR implementation. Unsupported forms retain the
legacy behavior; protocol changes should be reviewed separately from migration.
"""

from __future__ import annotations

import json
import struct


class CborDecodeError(ValueError):
    pass


def cbor_encode(value: object) -> bytes:
    if value is None:
        return b"\xf6"
    if value is False:
        return b"\xf4"
    if value is True:
        return b"\xf5"
    if isinstance(value, int):
        return _cbor_encode_type_value(0 if value >= 0 else 1, value if value >= 0 else -1 - value)
    if isinstance(value, str):
        data = value.encode("utf-8")
        return _cbor_encode_type_value(3, len(data)) + data
    if isinstance(value, list):
        return _cbor_encode_type_value(4, len(value)) + b"".join(cbor_encode(item) for item in value)
    if isinstance(value, dict):
        chunks = []
        for key, item in value.items():
            chunks.append(cbor_encode(str(key)))
            chunks.append(cbor_encode(item))
        return _cbor_encode_type_value(5, len(value)) + b"".join(chunks)
    raise TypeError(f"unsupported CBOR value: {type(value)!r}")


def _cbor_encode_type_value(major: int, value: int) -> bytes:
    prefix = major << 5
    if value < 24:
        return bytes([prefix | value])
    if value < 256:
        return bytes([prefix | 24, value])
    if value < 65536:
        return bytes([prefix | 25]) + value.to_bytes(2, "big")
    if value < 4294967296:
        return bytes([prefix | 26]) + value.to_bytes(4, "big")
    return bytes([prefix | 27]) + value.to_bytes(8, "big")


def cbor_decode(data: bytes) -> object:
    value, offset = _cbor_decode_one(data, 0)
    if offset != len(data):
        return value
    return value


def _cbor_decode_one(data: bytes, offset: int) -> tuple[object, int]:
    if offset >= len(data):
        raise CborDecodeError("unexpected end of CBOR")
    initial = data[offset]
    offset += 1
    major = initial >> 5
    additional = initial & 0x1F

    if major == 7:
        if additional == 20:
            return False, offset
        if additional == 21:
            return True, offset
        if additional in {22, 23}:
            return None, offset
        if additional == 24:
            return data[offset], offset + 1
        if additional == 25:
            return None, offset + 2
        if additional == 26:
            return struct.unpack(">f", data[offset : offset + 4])[0], offset + 4
        if additional == 27:
            return struct.unpack(">d", data[offset : offset + 8])[0], offset + 8
        return None, offset

    value, offset = _cbor_read_value(data, offset, additional)

    if major == 0:
        return value, offset
    if major == 1:
        return -1 - value, offset
    if major == 2:
        end = offset + value
        return data[offset:end], end
    if major == 3:
        end = offset + value
        return data[offset:end].decode("utf-8", errors="replace"), end
    if major == 4:
        items = []
        for _ in range(value):
            item, offset = _cbor_decode_one(data, offset)
            items.append(item)
        return items, offset
    if major == 5:
        obj = {}
        for _ in range(value):
            key, offset = _cbor_decode_one(data, offset)
            item, offset = _cbor_decode_one(data, offset)
            obj[key] = item
        return obj, offset
    raise CborDecodeError(f"unsupported CBOR major={major} additional={additional}")


def _cbor_read_value(data: bytes, offset: int, additional: int) -> tuple[int, int]:
    if additional < 24:
        return additional, offset
    if additional == 24:
        return data[offset], offset + 1
    if additional == 25:
        return int.from_bytes(data[offset : offset + 2], "big"), offset + 2
    if additional == 26:
        return int.from_bytes(data[offset : offset + 4], "big"), offset + 4
    if additional == 27:
        return int.from_bytes(data[offset : offset + 8], "big"), offset + 8
    raise CborDecodeError(f"unsupported additional value: {additional}")


def decode_body_sample(body: bytes) -> tuple[object | None, str]:
    if not body:
        return None, ""
    # JSON objects begin with 0x7b, also a valid CBOR text prefix. A permissive
    # CBOR decode can otherwise consume part of the JSON and discard status/data.
    if body.lstrip().startswith((b"{", b"[")):
        try:
            decoded = json.loads(body.decode("utf-8"))
            return decoded, json.dumps(decoded, ensure_ascii=False)[:1000]
        except (ValueError, UnicodeDecodeError):
            pass
    try:
        decoded = cbor_decode(body)
        return decoded, json.dumps(decoded, ensure_ascii=False)[:1000]
    except Exception:
        pass
    try:
        decoded = json.loads(body.decode("utf-8"))
        return decoded, json.dumps(decoded, ensure_ascii=False)[:1000]
    except Exception:
        return None, body[:200].hex(" ")


