"""Generate apps/desktop/app-icon.png — the source for `tauri icon`.

A 1024x1024 Obelisk-blue tile with a lighter vertical "obelisk" bar (the wordmark
motif). Pure stdlib (zlib + struct) so it runs anywhere with no image deps.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 1024
BG = (10, 10, 11)  # #0A0A0B background
TILE = (31, 78, 121)  # #1F4E79 Obelisk blue
BAR = (160, 202, 252)  # #A0CAFC accent
OUT = Path(__file__).resolve().parent.parent / "apps" / "desktop" / "app-icon.png"


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(
        ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
    )


def main() -> None:
    margin = SIZE // 8
    bar_w = SIZE // 7
    bar_x0 = (SIZE - bar_w) // 2
    bar_y0, bar_y1 = SIZE // 4, SIZE * 3 // 4

    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)  # filter: none
        for x in range(SIZE):
            inside_tile = margin <= x < SIZE - margin and margin <= y < SIZE - margin
            inside_bar = bar_x0 <= x < bar_x0 + bar_w and bar_y0 <= y < bar_y1
            r, g, b = BAR if inside_bar else (TILE if inside_tile else BG)
            raw += bytes((r, g, b, 255))

    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
    png += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _png_chunk(b"IEND", b"")
    OUT.write_bytes(png)
    print(f"Wrote {OUT} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
