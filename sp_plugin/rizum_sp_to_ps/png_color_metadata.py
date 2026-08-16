"""Normalize PNG color chunks without decoding or changing pixel payloads."""

from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_COLOR_CHUNKS = {b"cHRM", b"gAMA", b"iCCP", b"sRGB"}
_SRGB_CHUNK = b"sRGB"
_SRGB_PERCEPTUAL_INTENT = b"\x00"


def normalize_png(path, encoding):
    """Make a PNG explicitly sRGB or raw while preserving its IDAT bytes."""
    source_path = Path(path)
    encoding = str(encoding or "").lower()
    if encoding not in {"srgb", "raw"}:
        raise ValueError(f"Unsupported PNG color encoding: {encoding!r}")

    color_chunks = _read_color_chunks(source_path)
    if _is_normalized(color_chunks, encoding):
        return {
            "encoding": encoding,
            "changed": False,
            "removed_chunks": [],
            "added_srgb_chunk": False,
        }

    temporary_path = source_path.with_name(
        f".{source_path.name}.rizum-color-{os.getpid()}.tmp"
    )
    removed = []
    try:
        with source_path.open("rb") as source, temporary_path.open("wb") as target:
            if source.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
                raise ValueError(f"Not a PNG file: {source_path}")
            target.write(PNG_SIGNATURE)

            inserted_srgb = False
            while True:
                length_bytes = source.read(4)
                if not length_bytes:
                    break
                if len(length_bytes) != 4:
                    raise ValueError(f"Truncated PNG chunk length: {source_path}")
                length = struct.unpack(">I", length_bytes)[0]
                chunk_type = source.read(4)
                chunk_data = source.read(length)
                chunk_crc = source.read(4)
                if len(chunk_type) != 4 or len(chunk_data) != length or len(chunk_crc) != 4:
                    raise ValueError(f"Truncated PNG chunk: {source_path}")

                if chunk_type in _COLOR_CHUNKS:
                    removed.append(chunk_type.decode("ascii"))
                else:
                    target.write(length_bytes)
                    target.write(chunk_type)
                    target.write(chunk_data)
                    target.write(chunk_crc)

                if chunk_type == b"IHDR" and encoding == "srgb":
                    _write_chunk(target, _SRGB_CHUNK, _SRGB_PERCEPTUAL_INTENT)
                    inserted_srgb = True
                if chunk_type == b"IEND":
                    break

            if encoding == "srgb" and not inserted_srgb:
                raise ValueError(f"PNG has no IHDR chunk: {source_path}")
        os.replace(temporary_path, source_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return {
        "encoding": encoding,
        "changed": True,
        "removed_chunks": removed,
        "added_srgb_chunk": encoding == "srgb",
    }


def _read_color_chunks(path):
    chunks = []
    with Path(path).open("rb") as source:
        if source.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
            raise ValueError(f"Not a PNG file: {path}")
        while True:
            length_bytes = source.read(4)
            if not length_bytes:
                break
            if len(length_bytes) != 4:
                raise ValueError(f"Truncated PNG chunk length: {path}")
            length = struct.unpack(">I", length_bytes)[0]
            chunk_type = source.read(4)
            if len(chunk_type) != 4:
                raise ValueError(f"Truncated PNG chunk type: {path}")
            if chunk_type in _COLOR_CHUNKS:
                chunks.append((chunk_type, source.read(length)))
            else:
                source.seek(length, os.SEEK_CUR)
            if len(source.read(4)) != 4:
                raise ValueError(f"Truncated PNG chunk CRC: {path}")
            if chunk_type == b"IEND":
                break
    return chunks


def _is_normalized(chunks, encoding):
    if encoding == "raw":
        return not chunks
    return chunks == [(_SRGB_CHUNK, _SRGB_PERCEPTUAL_INTENT)]


def _write_chunk(target, chunk_type, data):
    target.write(struct.pack(">I", len(data)))
    target.write(chunk_type)
    target.write(data)
    target.write(struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF))
