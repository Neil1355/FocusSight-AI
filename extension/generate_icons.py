"""Generate minimal placeholder PNG icons for the FocusSight browser extension.

Run from the repository root:
    python extension/generate_icons.py

Requires Pillow:
    pip install Pillow

Produces:
    extension/icons/icon16.png
    extension/icons/icon32.png
    extension/icons/icon48.png
    extension/icons/icon128.png
"""

import os
import struct
import zlib


def _make_png(size: int) -> bytes:
    """Create a minimal valid PNG of ``size x size`` green pixels."""
    width = height = size
    raw_rows = []
    for _ in range(height):
        # Filter byte 0 (None) + RGBA pixels (green, fully opaque)
        row = b"\x00" + b"\x27\xae\x60\xff" * width
        raw_rows.append(row)
    raw_data = b"".join(raw_rows)
    compressed = zlib.compress(raw_data, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        payload = tag + data
        crc = struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        return length + payload + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = (
        struct.pack(">I", width)
        + struct.pack(">I", height)
        + bytes([8, 2, 0, 0, 0])
    )
    raw_rows_rgb = []
    for _ in range(height):
        row = b"\x00" + b"\x27\xae\x60" * width  # filter=0 + RGB green
        raw_rows_rgb.append(row)
    compressed = zlib.compress(b"".join(raw_rows_rgb), 9)

    return (
        signature
        + chunk(b"IHDR", ihdr_data)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def main():
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    os.makedirs(icons_dir, exist_ok=True)
    for size in (16, 32, 48, 128):
        path = os.path.join(icons_dir, f"icon{size}.png")
        with open(path, "wb") as fh:
            fh.write(_make_png(size))
        print(f"Written: {path}")
    print("Done – replace icons with real artwork before publishing.")


if __name__ == "__main__":
    main()
