"""Lightweight offline biometric helpers (prototype).

This module intentionally avoids heavy ML to stay compatible with:
- low-end devices
- offline-first flows

We use a perceptual image hash (dHash) as a simple *face identity gate*:
- first login: enroll hash
- next logins: compare hamming distance against enrolled hash

This is not bank-grade biometrics; it is a pragmatic prototype step-up signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass(frozen=True)
class FaceHash:
    algo: str
    hex64: str


def compute_dhash64_from_png(png_bytes: bytes) -> FaceHash:
    # dHash (difference hash) 64-bit, returned as 16 hex chars.
    image = Image.open(BytesIO(png_bytes)).convert("L").resize((9, 8), Image.Resampling.BILINEAR)
    pixels = list(image.getdata())
    bits: list[int] = []
    for row in range(8):
        row_start = row * 9
        for col in range(8):
            left_px = pixels[row_start + col]
            right_px = pixels[row_start + col + 1]
            bits.append(1 if left_px > right_px else 0)

    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return FaceHash(algo="dhash64", hex64=f"{value:016x}")


def hamming_distance_hex64(a_hex: str, b_hex: str) -> int:
    # Compare two 64-bit hex strings (16 hex chars).
    a = int((a_hex or "0").strip(), 16)
    b = int((b_hex or "0").strip(), 16)
    return (a ^ b).bit_count()

