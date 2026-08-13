#!/usr/bin/env python3
"""Re-encode the homepage shield art as WebP at the resolution each layer
actually renders at.

The source PNGs are all 1024x1024 exports, but almost none of them are shown
that way: the nav mark renders at 32-60 CSS px, and several shield layers are
blurred, mask-only, or composited at low opacity, where extra pixels are
invisible by construction. This script encodes each asset at the size its own
CSS treatment can actually resolve.

Run from the repo root after changing any source PNG:

    python3 scripts/optimize_images.py            # write backend/webapp/static/*.webp
    python3 scripts/optimize_images.py --check    # report only, touch nothing

`--check` exits non-zero when an output is missing or stale, so CI can catch a
PNG that was updated without regenerating its WebP.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "backend" / "webapp" / "static"

# width=None keeps the source resolution.
#
# "why" is the CSS treatment that justifies the target — read it before lowering
# a number, because a layer that stops being blurred needs its pixels back.
PLAN = [
    {
        "src": "shield-crystal-front.png",
        "width": 128,
        "quality": 90,
        "why": "nav brand mark, rendered 32-60px on every page (2x = 120px max)",
    },
    {
        "src": "shield-crystal.png",
        "width": None,
        "quality": 90,
        "why": "hero shield: visible at 560px + alpha mask for 3 layers, keep 1024 for 2x",
    },
    {
        "src": "shield-lettering.png",
        "width": None,
        "lossless": True,
        "why": (
            "crisp lettering plate at opacity .92 — the sharpest thing on the page. "
            "Lossy plateaus at ~27dB at every quality (libwebp rewrites RGB under "
            "alpha regardless of q), so buy certainty: lossless is still 24% under PNG"
        ),
    },
    {
        "src": "shield-crystal-alt.png",
        "width": 512,
        "quality": 82,
        "why": "blur(6px) at opacity .28 — detail past 512 is destroyed by the blur",
    },
    {
        "src": "shield-swirl-tex.png",
        "width": 640,
        "quality": 82,
        "why": "soft ribbon texture, masked, effective opacity ~.39, always rotating",
    },
    {
        "src": "shield-swirl-tex-b.png",
        "width": 640,
        "quality": 82,
        "why": "soft ribbon texture, masked, effective opacity ~.22 crossfading",
    },
    # claw-rips.png is deliberately absent: at 16KB it is already smaller than
    # any WebP re-encode of it (WebP came out 25KB), so it stays a PNG.
]


def encode(spec: dict, dry_run: bool = False) -> tuple[str, int, int]:
    """Encode one asset. Returns (name, png_bytes, webp_bytes)."""
    # Imported here, not at module scope, so `--check` runs in CI without
    # pulling Pillow into the test job just to compare two mtimes.
    from PIL import Image

    src = STATIC / spec["src"]
    dst = src.with_suffix(".webp")
    if not src.exists():
        raise FileNotFoundError(src)

    img = Image.open(src)
    # Alpha is load-bearing here: these composite over the page and several are
    # used as alpha masks, so RGBA must survive the round-trip.
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    width = spec["width"]
    if width and img.width > width:
        height = round(img.height * width / img.width)
        img = img.resize((width, height), Image.LANCZOS)

    if not dry_run:
        if spec.get("lossless"):
            img.save(dst, "WEBP", lossless=True, method=6)
        else:
            img.save(dst, "WEBP", quality=spec["quality"], method=6)

    return spec["src"], src.stat().st_size, dst.stat().st_size if dst.exists() else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify every .webp exists and is newer than its .png; write nothing",
    )
    args = parser.parse_args()

    if args.check:
        stale = []
        for spec in PLAN:
            src = STATIC / spec["src"]
            dst = src.with_suffix(".webp")
            if not dst.exists():
                stale.append(f"{dst.name} is missing")
            elif src.exists() and src.stat().st_mtime > dst.stat().st_mtime:
                stale.append(f"{dst.name} is older than {src.name}")
        if stale:
            print("Stale optimized images — run scripts/optimize_images.py:")
            for line in stale:
                print(f"  - {line}")
            return 1
        print(f"All {len(PLAN)} optimized images are current.")
        return 0

    total_png = total_webp = 0
    print(f"{'asset':<28}{'png':>10}{'webp':>10}{'saved':>9}")
    print("-" * 57)
    for spec in PLAN:
        name, png_bytes, webp_bytes = encode(spec)
        total_png += png_bytes
        total_webp += webp_bytes
        pct = (1 - webp_bytes / png_bytes) * 100 if png_bytes else 0
        print(f"{name:<28}{png_bytes / 1024:>9.0f}K{webp_bytes / 1024:>9.0f}K{pct:>8.0f}%")
    print("-" * 57)
    saved = (1 - total_webp / total_png) * 100 if total_png else 0
    print(f"{'total':<28}{total_png / 1024:>9.0f}K{total_webp / 1024:>9.0f}K{saved:>8.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
